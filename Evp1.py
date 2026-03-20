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
        self._rawSectionData = None

    def LoadData(self, br):

        evp1Offset = br.Position()

        header = Evp1Header()
        header.LoadData(br)

        # Store raw section bytes for round-trip export
        savedPos = br.Position()
        br.SeekSet(evp1Offset)
        self._rawSectionData = br._f.read(header.sizeOfSection)
        br.SeekSet(savedPos)

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

    def BuildFromMesh(self, armature_obj, mesh_obj):
        """Build EVP1 envelope/skinning data from Blender armature and mesh.

        Computes inverse bind matrices for each bone and collects unique
        multi-bone envelope entries from mesh vertex groups.
        """
        bones = armature_obj.data.bones
        bone_names = [b.name for b in bones]
        num_bones = len(bone_names)
        mesh = mesh_obj.data

        # --- Inverse bind matrices (one per bone) ---
        # bone.matrix_local is the bone's rest-pose world matrix in Blender space.
        # Convert to GC space, then invert to get the inverse bind matrix.
        self.matrices = [None] * num_bones
        for i, bone in enumerate(bones):
            gc_world = Evp1._blender_to_gc_matrix(bone.matrix_local)
            inv_bind = gc_world.inverted()
            self.matrices[i] = inv_bind

        # --- Envelope entries (unique multi-bone weight sets) ---
        # Map vertex group index -> bone index
        vgroup_to_bone = {}
        for vg in mesh_obj.vertex_groups:
            if vg.name in bone_names:
                vgroup_to_bone[vg.index] = bone_names.index(vg.name)

        # Collect unique envelopes from vertices with 2+ bones
        envelope_map = {}  # frozen key -> MultiMatrix index
        self.weightedIndices = []

        for vert in mesh.vertices:
            sig_groups = [(g.group, g.weight) for g in vert.groups
                          if g.weight > 0.001 and g.group in vgroup_to_bone]
            if len(sig_groups) < 2:
                continue

            # Normalize weights
            total = sum(w for _, w in sig_groups)
            if total < 1e-6:
                continue
            normalized = [(vgroup_to_bone[gi], w / total) for gi, w in sig_groups]
            normalized.sort(key=lambda x: x[0])  # sort by bone index for consistency

            # Create dedup key: (bone_idx, rounded_weight) tuples
            key = tuple((bi, round(w, 6)) for bi, w in normalized)
            if key not in envelope_map:
                mm = MultiMatrix()
                mm.indices = [bi for bi, w in normalized]
                mm.weights = [w for bi, w in normalized]
                envelope_map[key] = len(self.weightedIndices)
                self.weightedIndices.append(mm)

        self._rawSectionData = None  # force DumpData reconstruction

    def DumpData(self, bw):
        """Write EVP1 section. If raw data was captured during import, write it back."""
        if hasattr(self, '_rawSectionData') and self._rawSectionData is not None:
            bw._f.write(self._rawSectionData)
            return

        evp1Offset = bw.Position()

        header = Evp1Header()
        numMatrices = len(self.matrices)
        header.count = len(self.weightedIndices)
        counts = [len(self.weightedIndices[i].indices)
                      for i in range(header.count)]
        countsum = sum(counts)
        header.pad = 0xffff

        header.offsets[0] = bw.addPadding(Evp1Header.size)
        header.offsets[1] = header.offsets[0] + header.count
        header.offsets[2] = header.offsets[1] + 2 * countsum
        header.offsets[3] = header.offsets[2] + 4 * countsum
        header.sizeOfSection = header.offsets[3] + numMatrices * 12 * 4
        header.sizeOfSection = bw.addPadding(header.sizeOfSection)

        header.DumpData(bw)

        bw.writePadding(header.offsets[0] - Evp1Header.size)

        for i in range(header.count):
            bw.writeByte(counts[i])

        # write indices of weighted matrices
        for i in range(header.count):
            for j in range(counts[i]):
                bw.writeWord(self.weightedIndices[i].indices[j])

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