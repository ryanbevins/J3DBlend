#! /usr/bin/python3
from .Matrix44 import *
from mathutils import Matrix
from math import ceil
import math

class Evp1Header:
    size = 28

    def __init__(self):  # GENERATED!
        self.offsets = [0, 0, 0, 0]

    def LoadData(self, br):

        self.tag = br.ReadFixedLengthString(4)
        self.sizeOfSection = br.ReadDWORD()
        self.count = br.ReadWORD()
        self.pad = br.ReadWORD()
        # 0 - count many bytes, each byte describes how many bones belong to this index
        # 1 - sum over all bytes in 0 many shorts (index into some joint stuff? into matrix table?)
        # 2 - bone weights table (as many floats as shorts in 1)
        # 3 - matrix table (matrix is 3x4 float array)

        for i in range(4):
            self.offsets[i] = br.ReadDWORD()

    def DumpData(self, bw):

        bw.writeString('EVP1')
        bw.writeDword(self.sizeOfSection)
        bw.writeWord(self.count)
        bw.writeWord(self.pad)
        # 0 - count many bytes, each byte describes how many bones belong to this index
        # 1 - sum over all bytes in 0 many shorts (index into some joint stuff? into matrix table?)
        # 2 - bone weights table (as many floats as shorts in 1)
        # 3 - matrix table (matrix is 3x4 float array)

        for i in range(4):
            bw.writeDword(self.offsets[i])


class MultiMatrix:
    def __init__(self):  # GENERATED!
        self.weights = []
        self.indices = []  # indices into Evp1.matrices (?)


class Evp1:
    def __init__(self):  # GENERATED!
        self.matrices = []
        self.weightedIndices = []

    def LoadData(self, br):

        evp1Offset = br.Position()

        header = Evp1Header()
        header.LoadData(br)

        # -- read counts array
        br.SeekSet(evp1Offset + header.offsets[0])
        counts = [0] * header.count
        sum = 0
        for i in range(header.count):
            v = br.GetByte()
            sum += v
            counts[i] = v

        self.weightedIndices = []  # size : h.count

        # -- read indices of weighted self.matrices
        br.SeekSet(evp1Offset + header.offsets[1])
        numMatrices = 0

        for i in range(header.count):
            self.weightedIndices.append(MultiMatrix())
            self.weightedIndices[i].indices = [0] * counts[i]
            for j in range(counts[i]):
                d = br.ReadWORD()  # index to array (starts at one)
                self.weightedIndices[i].indices[j] = d
                numMatrices = max(numMatrices, d+1)  # XCX does the '+1' skrew it up?
                # XCX(probably not, it might just create extra, unused, junk, data)

        # -- read weights of weighted self.matrices
        br.SeekSet(evp1Offset + header.offsets[2])

        for i in range(header.count):
            self.weightedIndices[i].weights = [0] * counts[i]
            for j in range(counts[i]):
                fz = br.GetFloat()
                self.weightedIndices[i].weights[j] = fz


        # -- read matrices
        # Compute actual matrix count from section layout (not just max referenced index)
        # Each matrix is 3x4 floats = 48 bytes
        matBytesAvailable = header.sizeOfSection - header.offsets[3]
        actualNumMatrices = matBytesAvailable // 48
        # Use whichever is larger: referenced count or stored count
        numMatrices = max(numMatrices, actualNumMatrices)

        self.matrices = []  # size: numMatrices
        br.SeekSet(evp1Offset + header.offsets[3])
        self.matrices = [None] * numMatrices
        for i in range(numMatrices):
            self.matrices[i] = Matrix.Identity(4)
            for j in range(3):
                for k in range(4):
                    self.matrices[i][j][k] = br.GetFloat()

    @staticmethod
    def _blender_to_gc_matrix(blender_mtx):
        """Convert a Blender Z-up 4x4 matrix to GC Y-up coordinate space.

        Blender (x, y, z) -> GC (x, z, -y).
        This is a similarity transform: M_gc = S @ M_bl @ S^-1
        where S swaps Y/Z and negates the new Y (old Z).
        """
        # Swap matrix: maps Blender coords to GC coords
        # GC.x = Bl.x, GC.y = Bl.z, GC.z = -Bl.y
        S = Matrix((
            (1,  0,  0, 0),
            (0,  0,  1, 0),
            (0, -1,  0, 0),
            (0,  0,  0, 1),
        ))
        S_inv = Matrix((
            (1, 0,  0, 0),
            (0, 0, -1, 0),
            (0, 1,  0, 0),
            (0, 0,  0, 1),
        ))
        return S @ blender_mtx @ S_inv

    @staticmethod
    def _gc_world_matrix_from_props(bone, all_bones_by_name):
        """Reconstruct a bone's GC-space world matrix from gc_rest_* properties.

        Walks up the parent chain, composing local transforms in GC space
        to produce the world matrix for this bone.
        """
        from mathutils import Euler as _Euler
        import struct as _struct

        def _bits2f(bits_val):
            return _struct.unpack('>f', _struct.pack('>i', int(bits_val)))[0]

        def _local_gc_matrix(b):
            rx = b.get("gc_rest_rx", 0.0)
            ry = b.get("gc_rest_ry", 0.0)
            rz = b.get("gc_rest_rz", 0.0)
            if "gc_rest_tx_bits" in b:
                tx = _bits2f(b["gc_rest_tx_bits"])
                ty = _bits2f(b["gc_rest_ty_bits"])
                tz = _bits2f(b["gc_rest_tz_bits"])
            else:
                tx = b.get("gc_rest_tx", 0.0)
                ty = b.get("gc_rest_ty", 0.0)
                tz = b.get("gc_rest_tz", 0.0)
            t_mtx = Matrix.Translation((tx, ty, tz))
            r_mtx = _Euler((rx, ry, rz), 'XYZ').to_matrix().to_4x4()
            return t_mtx @ r_mtx

        # Build chain from root to this bone
        chain = []
        b = bone
        while b is not None:
            chain.append(b)
            b = b.parent
        chain.reverse()

        world = Matrix.Identity(4)
        for b in chain:
            world = world @ _local_gc_matrix(b)
        return world

    @staticmethod
    def _compute_world_matrices_from_scenegraph(jnt, inf):
        """Walk INF1 scene graph to compute GC-space world matrices for each bone.

        This mirrors BModel.CreateBones: world = parent_world @ FrameMatrix(frame).
        Uses the rotation SHORT values (via round-trip through JntEntry) to match
        the exact precision of the original game tool.
        """
        from mathutils import Euler as _Euler
        from math import pi

        world_matrices = [None] * len(jnt.frames)

        def _frame_matrix(f):
            # Use raw translation floats if available (preserves -0.0)
            tx = getattr(f, '_raw_tx', f.t.x)
            ty = getattr(f, '_raw_ty', f.t.y)
            tz = getattr(f, '_raw_tz', f.t.z)
            t = Matrix.Translation((tx, ty, tz))
            # Convert radians back to shorts and then to radians again
            # to match the precision loss of the original SHORT encoding
            rx_short = round(f.rx * 32768.0 / pi)
            ry_short = round(f.ry * 32768.0 / pi)
            rz_short = round(f.rz * 32768.0 / pi)
            rx_rad = rx_short / 32768.0 * pi
            ry_rad = ry_short / 32768.0 * pi
            rz_rad = rz_short / 32768.0 * pi
            r = _Euler((rx_rad, ry_rad, rz_rad), 'XYZ').to_matrix().to_4x4()
            return t @ r

        def _walk(sg, parent_mtx):
            eff = parent_mtx.copy()
            if sg.type == 0x10:  # joint node
                f = jnt.frames[sg.index]
                eff = parent_mtx @ _frame_matrix(f)
                world_matrices[sg.index] = eff
            for child in sg.children:
                _walk(child, eff)

        _walk(inf.rootSceneGraph, Matrix.Identity(4))
        return world_matrices

    def BuildFromMesh(self, armature_obj, mesh_obj, jnt=None, inf=None):
        """Build EVP1 envelope/skinning data from Blender armature and mesh.

        If jnt and inf are provided, computes inverse bind matrices by walking
        the INF1 scene graph (matching the import path exactly). Otherwise
        falls back to gc_rest_* properties on bones.
        """
        bones = armature_obj.data.bones
        bone_names = [b.name for b in bones]
        num_bones = len(bone_names)
        mesh = mesh_obj.data

        # --- Inverse bind matrices (one per bone) ---
        if jnt is not None and inf is not None:
            # Compute world matrices by walking scene graph (same as CreateBones)
            world_matrices = Evp1._compute_world_matrices_from_scenegraph(jnt, inf)
            self.matrices = [None] * num_bones
            for i in range(num_bones):
                if world_matrices[i] is not None:
                    self.matrices[i] = world_matrices[i].inverted()
                else:
                    self.matrices[i] = Matrix.Identity(4)
        else:
            has_gc_props = len(bones) > 0 and "gc_rest_rx" in bones[0]
            bones_by_name = {b.name: b for b in bones}
            self.matrices = [None] * num_bones
            for i, bone in enumerate(bones):
                if has_gc_props:
                    gc_world = Evp1._gc_world_matrix_from_props(bone, bones_by_name)
                else:
                    gc_world = Evp1._blender_to_gc_matrix(bone.matrix_local)
                self.matrices[i] = gc_world.inverted()

        # --- Envelope entries (unique multi-bone weight sets) ---
        vgroup_to_bone = {}
        for vg in mesh_obj.vertex_groups:
            if vg.name in bone_names:
                vgroup_to_bone[vg.index] = bone_names.index(vg.name)

        envelope_map = {}
        self.weightedIndices = []

        for vert in mesh.vertices:
            sig_groups = [(g.group, g.weight) for g in vert.groups
                          if g.weight > 0.001 and g.group in vgroup_to_bone]
            if len(sig_groups) < 2:
                continue

            total = sum(w for _, w in sig_groups)
            if total < 1e-6:
                continue
            normalized = [(vgroup_to_bone[gi], w / total) for gi, w in sig_groups]
            normalized.sort(key=lambda x: x[0])

            key = tuple((bi, round(w, 6)) for bi, w in normalized)
            if key not in envelope_map:
                mm = MultiMatrix()
                mm.indices = [bi for bi, w in normalized]
                mm.weights = [w for bi, w in normalized]
                envelope_map[key] = len(self.weightedIndices)
                self.weightedIndices.append(mm)

    def DumpData(self, bw):
        """Write EVP1 section."""
        evp1Offset = bw.Position()

        header = Evp1Header()
        numMatrices = len(self.matrices)
        header.count = len(self.weightedIndices)
        counts = [len(self.weightedIndices[i].indices)
                      for i in range(header.count)]
        countsum = sum(counts)
        header.pad = 0xffff

        header.offsets[0] = Evp1Header.size  # No padding after header
        header.offsets[1] = header.offsets[0] + header.count
        raw_weight_off = header.offsets[1] + 2 * countsum
        header.offsets[2] = (raw_weight_off + 3) & ~3  # 4-byte align for floats
        header.offsets[3] = header.offsets[2] + 4 * countsum
        header.sizeOfSection = header.offsets[3] + numMatrices * 12 * 4
        header.sizeOfSection = bw.addPadding(header.sizeOfSection)

        header.DumpData(bw)

        for i in range(header.count):
            bw.writeByte(counts[i])

        # write indices of weighted matrices
        for i in range(header.count):
            for j in range(counts[i]):
                bw.writeWord(self.weightedIndices[i].indices[j])

        # Pad to 4-byte alignment before weights
        pad_needed = (evp1Offset + header.offsets[2]) - bw.Position()
        if pad_needed > 0:
            bw.writePadding(pad_needed)

        # write weights of weighted matrices
        for i in range(header.count):
            for j in range(counts[i]):
                bw.writeFloat(self.weightedIndices[i].weights[j])

        # write inverse bind matrices (3x4)
        for i in range(numMatrices):
            for j in range(3):
                for k in range(4):
                    bw.writeFloat(self.matrices[i][j][k])

        bw.writePadding(evp1Offset + header.sizeOfSection - bw.Position())