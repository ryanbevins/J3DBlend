#! /usr/bin/python3

from math import ceil
import logging
log = logging.getLogger('bpy.ops.import_mesh.bmd.inf1')

class Inf1Header:
    size = 24

    def __init__(self):  # GENERATED!
        pass

    def LoadData(self, br):
        self.tag = br.ReadFixedLengthString(4)
        self.sizeOfSection = br.ReadDWORD()
        self.unknown1 = br.ReadWORD()
        self.pad = br.ReadWORD()  # 0xffff
        self.packetCount = br.ReadDWORD()
        self.vertexCount = br.ReadDWORD()
        # number of coords in VTX1 section
        self.offsetToEntries = br.ReadDWORD()
        # offset relative to Inf1Header start
    # only used during file load
    # This stores the scene graph of the file

    def DumpData(self, bw):
        bw.writeString("INF1")
        bw.writeDword(self.sizeOfSection)
        bw.writeWord(self.unknown1)
        bw.writeWord(self.pad)  # 0xffff
        bw.writeDword(self.packetCount)
        bw.writeDword(self.vertexCount)
        # number of coords in VTX1 section
        bw.writeDword(self.offsetToEntries)

class Inf1Entry:
    size = 4
    def __init__(self):  # GENERATED!
        pass

    def LoadData(self, br):
        # 0x10: Joint
        # 0x11: Material
        # 0x12: Shape (ie. Batch)
        # 0x01: Hierarchy down (insert node), new child
        # 0x02: Hierarchy up, close child
        # 0x00: Terminator
        self.type = br.ReadWORD()
        # Index into Joint, Material or Shape table
        # always zero for types 0, 1 and 2
        self.index = br.ReadWORD()

    def DumpData(self, bw):
        bw.writeWord(self.type)
        bw.writeWord(self.index)
        # see LoadDate for meaning


class SceneGraph:
    def __init__(self):
        self.type = 0
        self.index = 0
        self.children = []
        # this var is only used as cache for the export process
        self.material = None



class Inf1:
    def __init__(self):  # GENERATED!
        self.rootSceneGraph = SceneGraph()
        self._rawSectionData = None

    def buildSceneGraph(self, sg, j=0):
        """builds sceneGraph tree from inf1 descriptors in an array"""
        i = j
        while i < len(self.entries):
            n = self.entries[i]
            if n.type == 1:
                i += self.buildSceneGraph(sg.children[-1], i+1)
            elif n.type == 2:
                return i - j + 1
            elif n.type == 0x10 or n.type == 0x11 or n.type == 0x12:
                t = SceneGraph()
                t.type = n.type
                t.index = n.index
                sg.children.append(t)
            else:
                log.error("buildSceneGraph(): unexpected node type %d", n.type)
            i += 1

        # note: this code can only be reached by the top level function,
        # AKA the one where the loops end by itself
        # return first "real" node
        if len(sg.children) == 1:
            return sg.children[0]
        else:
            sg.type = sg.index = -1
            log.error("buildSceneGraph(): Unexpected size %d for root SG", len(sg.children))
        return 0

    def extractEntries(self, sg, dest):
        e = Inf1Entry()
        e.type = sg.type
        e.index = sg.index

        dest.append(e)
        if sg.children:
            down_e = Inf1Entry()
            down_e.type = 0x01  # hierarchy down
            down_e.index = 0
            dest.append(down_e)
            for s2 in sg.children:
                self.extractEntries(s2, dest)
            up_e = Inf1Entry()
            up_e.type = 0x02  # hierarchy up
            up_e.index = 0
            dest.append(up_e)



    def LoadData(self, br):

        inf1Offset = br.Position()
        self.entries = []  # -- vector<Inf1Entry>
        header = Inf1Header()
        header.LoadData(br)
        self.numVertices = header.vertexCount  # int no idea what's this good for ;-)
        self._unknown1 = header.unknown1  # transform mode
        self._packetCount = header.packetCount

        # Store raw section bytes for round-trip export
        savedPos = br.Position()
        br.SeekSet(inf1Offset)
        self._rawSectionData = br._f.read(header.sizeOfSection)
        br.SeekSet(savedPos)

        # -- read scene graph
        br.SeekSet(inf1Offset + header.offsetToEntries)

        entry = Inf1Entry()
        entry.LoadData(br)

        while entry.type != 0:
            self.entries.append(entry)
            entry = Inf1Entry()
            entry.LoadData(br)

        self.rootSceneGraph = self.buildSceneGraph(self.rootSceneGraph)


    @staticmethod
    def Rebuild(batch_material_indices, num_vertices, packet_count, old_inf=None,
                batch_info=None, drw1=None, armature_obj=None):
        """Build a new INF1 from a batch list with per-batch material indices.

        Builds the full bone hierarchy from the Blender armature. Rigid batches
        are placed under their respective bone's joint node. Weighted batches
        are placed at the root level (under joint 0).

        Args:
            batch_material_indices: list of material index per batch (len = batch count)
            num_vertices: vertex count for the INF1 header
            packet_count: total packet count for the INF1 header
            old_inf: optional existing Inf1 to preserve unknown1
            batch_info: list of (is_rigid, drw_idx_or_None) per batch
            drw1: Drw1 instance (to map DRW index -> bone index for rigid batches)
            armature_obj: Blender armature object (for bone hierarchy)

        Returns a new Inf1 instance with _rawSectionData = None (forces DumpData path).
        """
        inf = Inf1()
        inf._rawSectionData = None  # force reconstruction
        inf.numVertices = num_vertices
        inf._unknown1 = getattr(old_inf, '_unknown1', 0) if old_inf else 0
        inf._packetCount = packet_count

        # Build bone hierarchy from armature
        bone_names = []
        bone_children = {}  # bone_index -> [child_bone_indices]
        root_bones = []
        if armature_obj is not None and armature_obj.type == 'ARMATURE':
            bones = armature_obj.data.bones
            bone_names = [b.name for b in bones]
            for i, bone in enumerate(bones):
                bone_children[i] = []
            for i, bone in enumerate(bones):
                if bone.parent is None:
                    root_bones.append(i)
                else:
                    parent_idx = bone_names.index(bone.parent.name)
                    bone_children[parent_idx].append(i)

        # Map bone_index -> list of (batch_idx, mat_idx) for rigid batches at that bone
        bone_batches = {}
        weighted_batches = []  # (batch_idx, mat_idx)

        if batch_info is not None and drw1 is not None:
            for batch_idx, (is_rigid, drw_idx) in enumerate(batch_info):
                mat_idx = batch_material_indices[batch_idx]
                if is_rigid and drw_idx is not None:
                    # Look up the bone index from DRW1
                    if drw_idx < len(drw1.data):
                        bone_idx = drw1.data[drw_idx]
                    else:
                        bone_idx = 0
                    if bone_idx not in bone_batches:
                        bone_batches[bone_idx] = []
                    bone_batches[bone_idx].append((batch_idx, mat_idx))
                else:
                    weighted_batches.append((batch_idx, mat_idx))
        else:
            # No batch info: fall back to flat structure
            for batch_idx, mat_idx in enumerate(batch_material_indices):
                weighted_batches.append((batch_idx, mat_idx))

        def _make_batch_nodes(batch_idx, mat_idx):
            """Create material -> shape node chain."""
            mat_node = SceneGraph()
            mat_node.type = 0x11  # Material
            mat_node.index = mat_idx
            shape_node = SceneGraph()
            shape_node.type = 0x12  # Shape
            shape_node.index = batch_idx
            mat_node.children.append(shape_node)
            return mat_node

        def _build_joint_tree(bone_idx):
            """Recursively build joint hierarchy with attached batches."""
            joint = SceneGraph()
            joint.type = 0x10  # Joint
            joint.index = bone_idx

            # Attach rigid batches for this bone
            if bone_idx in bone_batches:
                for batch_idx, mat_idx in bone_batches[bone_idx]:
                    joint.children.append(_make_batch_nodes(batch_idx, mat_idx))

            # Recurse into children
            for child_idx in bone_children.get(bone_idx, []):
                joint.children.append(_build_joint_tree(child_idx))

            return joint

        if root_bones:
            # Build from armature hierarchy
            if len(root_bones) == 1:
                root = _build_joint_tree(root_bones[0])
            else:
                # Multiple root bones: wrap in a virtual root
                root = SceneGraph()
                root.type = 0x10
                root.index = 0
                for rb in root_bones:
                    root.children.append(_build_joint_tree(rb))

            # Attach weighted batches at the deepest point of the last bone
            # in the hierarchy (matching the original BMD pattern where weighted
            # batches nest inside the deepest leaf). Actually, the original puts
            # weighted batches at the top level under root. Let's do that.
            # Insert weighted batches as first children of root (before bone hierarchy)
            for batch_idx, mat_idx in weighted_batches:
                root.children.insert(0, _make_batch_nodes(batch_idx, mat_idx))
        else:
            # No armature: flat structure
            root = SceneGraph()
            root.type = 0x10
            root.index = 0
            for batch_idx, mat_idx in enumerate(batch_material_indices):
                root.children.append(_make_batch_nodes(batch_idx, mat_idx))

        inf.rootSceneGraph = root
        return inf

    def DumpData(self, bw):
        """Write INF1 section. If raw data was captured during import, write it back."""
        if self._rawSectionData is not None:
            bw._f.write(self._rawSectionData)
            return

        inf1Offset = bw.Position()
        self.entries = []
        self.extractEntries(self.rootSceneGraph, self.entries)

        # Terminator entry
        temp_e = Inf1Entry()
        temp_e.type = temp_e.index = 0
        self.entries.append(temp_e)

        header = Inf1Header()
        header.sizeOfSection = 0
        header.unknown1 = getattr(self, '_unknown1', 0)
        header.pad = 0xffff
        header.packetCount = getattr(self, '_packetCount', 0)
        header.vertexCount = self.numVertices
        header.offsetToEntries = bw.addPadding(Inf1Header.size)

        header.DumpData(bw)
        bw.writePadding(header.offsetToEntries - Inf1Header.size)

        if inf1Offset + header.offsetToEntries != bw.Position():
            raise ValueError('something went wrong with the sizes in inf1')

        for entry in self.entries:
            entry.DumpData(bw)

        bw.writePaddingTo16()

        header.sizeOfSection = bw.Position() - inf1Offset
        bw.SeekSet(inf1Offset + 4)
        bw.writeDword(header.sizeOfSection)

        bw.SeekSet(inf1Offset + header.sizeOfSection)
