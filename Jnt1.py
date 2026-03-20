#! /usr/bin/python3
from .common import MessageBox
from mathutils import Vector, Matrix, Euler
from math import pi, ceil
from . import common
import logging
log = logging.getLogger('bpy.ops.import_mesh.bmd.jnt1')

class Jnt1Header:
    size = 24
    def __init__(self):  # GENERATED!
        pass

    def LoadData(self, br):
        self.tag = br.ReadFixedLengthString(4)  # "JNT1"
        self.sizeOfSection = br.ReadDWORD()
        self.count = br.ReadWORD()  # number of joints
        self.pad = br.ReadWORD()  # padding?
        self.jntEntryOffset = br.ReadDWORD()  # joints are stored at this place
                                              # offset relative to Jnt1Header start
        self.unknownOffset = br.ReadDWORD()  # there are count u16's stored at this point,
                                             # always the numbers 0 to count - 1 (in that order).
                                             # perhaps an index-to-stringtable-index map?
                                             # offset relative to Jnt1Header start
        self.stringTableOffset = br.ReadDWORD()  # names of joints

    def DumpData(self, bw):
        bw.writeString("JNT1")
        bw.writeDword(self.sizeOfSection)
        bw.writeWord(self.count)
        bw.writeWord(self.pad)

        bw.writeDword(self.jntEntryOffset)
        # offset relative to Jnt1Header start
        bw.writeDword(self.unknownOffset)
        # always the numbers 0 to count - 1 (in that order).
        # perhaps an index-to-stringtable-index map?
        # offset relative to Jnt1Header start
        bw.writeDword(self.stringTableOffset)


class JntEntry:
    size = 0x40
    def __init__(self):  # GENERATED!
        self.bbMin = []
        self.bbMax = []

    def LoadData(self, br):

        # values flipped late
        self.unknown = br.ReadWORD()
        # no idea how this works...always 0, 1 or 2.
        # "matrix type" according to yaz0r - whatever this means ;-)
        self.pad = br.ReadWORD()
        # always 0x00ff in mario, but not in zelda
        self.sx = br.GetFloat()
        self.sy = br.GetFloat()
        self.sz = br.GetFloat()

        self.rx = br.GetSHORT()  # short: each increment is an 1/2**16 of turn
        self.ry = br.GetSHORT()
        self.rz = br.GetSHORT()

        self.pad2 = br.ReadWORD()  # always 0xffff

        self.tx = br.GetFloat()  # translation floats
        self.ty = br.GetFloat()
        self.tz = br.GetFloat()

        self.unknown2 = br.GetFloat()

        self.bbMin = []  # bounding box?
        for _ in range(3):
            self.bbMin.append(br.GetFloat())
        self.bbMax = []
        for _ in range(3):
            self.bbMax.append(br.GetFloat())

        if self.unknown < 0 or self.unknown > 2:
            msg = "jnt1: self.unknown of " + str(self.unknown) + " joint not in [0, 2]"
            if common.GLOBALS.PARANOID:
                raise ValueError(msg)
            else:
                log.error(msg)


    def FromFrame(self, f):
        self.sx = f.sx
        self.sy = f.sy
        self.sz = f.sz

        self.rx = round(f.rx * 32768./pi)
        self.ry = round(f.ry * 32768./pi)
        self.rz = round(f.rz * 32768./pi)

        # Use raw floats to preserve -0.0 if available
        self.tx = getattr(f, '_raw_tx', f.t.x)
        self.ty = getattr(f, '_raw_ty', f.t.y)
        self.tz = getattr(f, '_raw_tz', f.t.z)
        self.bbMin = f._bbMin if f._bbMin else [0.0, 0.0, 0.0]
        self.bbMax = f._bbMax if f._bbMax else [0.0, 0.0, 0.0]

        # Use round-trip fields from import if available, otherwise defaults
        self.unknown = getattr(f, 'matrix_type', 0)
        self.pad = getattr(f, 'jnt_pad', 0x00ff)
        self.pad2 = getattr(f, 'jnt_pad2', 0xffff)
        self.unknown2 = getattr(f, 'jnt_unknown2', 0.0)

    def DumpData(self, bw):
        # values flipped late
        bw.writeWord(self.unknown)
        # no idea how this works...always 0, 1 or 2.
        # "matrix type" according to yaz0r - whatever this means ;-)
        bw.writeWord(self.pad)
        # always 0x00ff in mario, but not in zelda
        bw.writeFloat(self.sx)
        bw.writeFloat(self.sy)
        bw.writeFloat(self.sz)

        bw.writeShort(self.rx)  # short: each increment is an 1/2**16 of turn
        bw.writeShort(self.ry)
        bw.writeShort(self.rz)

        bw.writeWord(self.pad2)  # always 0xffff

        bw.writeFloat(self.tx)  # translation floats
        bw.writeFloat(self.ty)
        bw.writeFloat(self.tz)

        bw.writeFloat(self.unknown2)

        # bounding box?
        for i in range(3):
            bw.writeFloat(self.bbMin[i])
        for i in range(3):
            bw.writeFloat(self.bbMax[i])


class JntFrame:
    def __init__(self):  # GENERATED!
        self.matrix = None

    def InitFromJntEntry(self, e):

        self.sx = e.sx  # scale
        self.sy = e.sy
        self.sz = e.sz

        flag = False  # for logging purposes
        if e.sx**2 < 0.01:
            self.sx = 1
            flag = True
        if e.sy**2 < 0.01:
            self.sy = 1
            flag = True
        if e.sz**2 < 0.01:
            self.sz = 1
            flag = True
        if flag:
            log.warning('Joint has zero scaling by default: corecting to 1 (mesh aspect may be weird)')

        self.rx = (e.rx/32768. * pi)  # angles are coded to be a full turn in 2**16 'ticks'
        self.ry = (e.ry/32768. * pi)  # and we need to use radians
        self.rz = (e.rz/32768. * pi)

        self.t = Vector((e.tx, e.ty, e.tz))  # displacement

        self._bbMin = e.bbMin  # is this even needed? (bounding box)
        self._bbMax = e.bbMax

        # Store raw JntEntry fields for round-trip BMD export
        self.matrix_type = e.unknown  # u16: 0, 1, or 2
        self.jnt_pad = e.pad          # u16: usually 0x00ff
        self.jnt_pad2 = e.pad2        # u16: usually 0xffff
        self.jnt_unknown2 = e.unknown2  # f32: unknown float after tz


    def getFrameMatrix(self):
        return Matrix.Translation(self.t) @ Euler((self.rx, self.ry, self.rz), 'XYZ').to_matrix().to_4x4()
    def getRotMatrix(self):
        return Euler((self.rx, self.ry, self.rz), 'XYZ').to_matrix().to_4x4()
    def getInvRotMatrix(self):
        return Euler((-self.rx, -self.ry, -self.rz), 'ZYX').to_matrix().to_4x4()


class Jnt1:
    def __init__(self):  # GENERATED!
        self.frames = []  # base position of bones, used as a reference to compute animations as a difference to this
        self._rawSectionData = None

    def FromArmature(self, arm_obj):
        """Populate JNT1 frames from Blender armature using gc_ custom properties."""
        self.frames = []
        self.matrices = []
        self.isMatrixValid = []

        for bone in arm_obj.data.bones:
            f = JntFrame()
            f.name = bone.name

            # Read GC rest-pose from custom properties stored during import
            f.rx = bone.get("gc_rest_rx", 0.0)
            f.ry = bone.get("gc_rest_ry", 0.0)
            f.rz = bone.get("gc_rest_rz", 0.0)
            # Store as raw floats to preserve -0.0 (Blender Vector normalizes it)
            f._raw_tx = bone.get("gc_rest_tx", 0.0)
            f._raw_ty = bone.get("gc_rest_ty", 0.0)
            f._raw_tz = bone.get("gc_rest_tz", 0.0)
            f.t = Vector((f._raw_tx, f._raw_ty, f._raw_tz))
            f.sx = bone.get("gc_rest_sx", 1.0)
            f.sy = bone.get("gc_rest_sy", 1.0)
            f.sz = bone.get("gc_rest_sz", 1.0)

            f._bbMin = [
                bone.get("gc_bb_min_x", 0.0),
                bone.get("gc_bb_min_y", 0.0),
                bone.get("gc_bb_min_z", 0.0),
            ]
            f._bbMax = [
                bone.get("gc_bb_max_x", 0.0),
                bone.get("gc_bb_max_y", 0.0),
                bone.get("gc_bb_max_z", 0.0),
            ]

            f.matrix_type = bone.get("gc_matrix_type", 0)
            f.jnt_pad = bone.get("gc_jnt_pad", 0x00ff)
            f.jnt_pad2 = bone.get("gc_jnt_pad2", 0xffff)
            f.jnt_unknown2 = bone.get("gc_jnt_unknown2", 0.0)

            self.frames.append(f)
            self.matrices.append(None)
            self.isMatrixValid.append(False)

    @staticmethod
    def BuildFromArmature(armature_obj):
        """Build JNT1 purely from Blender armature rest pose data.

        Does NOT rely on gc_* custom properties. Computes local transforms
        from bone.matrix_local, converts from Blender Z-up to GC Y-up
        coordinate space, and returns a Jnt1 with frames populated.
        """
        import math

        # Blender-to-Nintendo coordinate conversion matrix:
        # Blender (x, y, z) Z-up -> GC (x, z, -y) Y-up
        BtoN = Matrix([[1, 0, 0, 0],
                        [0, 0, 1, 0],
                        [0, -1, 0, 0],
                        [0, 0, 0, 1]])

        def _radians_to_s16(rad):
            """Convert radians to GC s16 rotation format."""
            val = int(round(rad * 32768.0 / math.pi))
            # Clamp to s16 range
            if val > 32767:
                val = 32767
            elif val < -32768:
                val = -32768
            return val

        def _collect_bones_dfs(armature):
            """Collect bones in depth-first order matching BMD convention."""
            bones = armature.data.bones
            result = []
            roots = [b for b in bones if b.parent is None]
            def _recurse(bone):
                result.append(bone)
                for child in bone.children:
                    _recurse(child)
            for root in roots:
                _recurse(root)
            return result

        jnt = Jnt1()
        jnt._rawSectionData = None  # force DumpData reconstruction
        jnt.frames = []
        jnt.matrices = []
        jnt.isMatrixValid = []

        ordered_bones = _collect_bones_dfs(armature_obj)

        for bone in ordered_bones:
            # Compute local transform in Blender space
            if bone.parent is not None:
                local_mtx = bone.parent.matrix_local.inverted() @ bone.matrix_local
            else:
                local_mtx = bone.matrix_local.copy()

            # Convert to GC coordinate space
            # For root: gc_local = BtoN @ blender_local @ BtoN^-1
            # For children: same — the parent-relative transform needs basis change
            gc_local = BtoN @ local_mtx @ BtoN.inverted()

            # Decompose into translation, rotation, scale
            loc, quat, scale = gc_local.decompose()
            euler = quat.to_euler('XYZ')

            f = JntFrame()
            f.name = bone.name

            # Scale
            f.sx = scale.x
            f.sy = scale.y
            f.sz = scale.z

            # Rotation in radians (JntFrame stores radians; JntEntry.FromFrame converts to s16)
            f.rx = euler.x
            f.ry = euler.y
            f.rz = euler.z

            # Translation
            f.t = Vector((loc.x, loc.y, loc.z))

            # Bounding box defaults
            f._bbMin = [0.0, 0.0, 0.0]
            f._bbMax = [0.0, 0.0, 0.0]

            # Default JntEntry fields
            f.matrix_type = 0
            f.jnt_pad = 0x00ff
            f.jnt_pad2 = 0xffff
            f.jnt_unknown2 = 0.0

            jnt.frames.append(f)
            jnt.matrices.append(None)
            jnt.isMatrixValid.append(False)

        return jnt

    def LoadData(self, br):

        jnt1Offset = br.Position()

        header = Jnt1Header()
        header.LoadData(br)

        # Store raw section bytes for round-trip export
        savedPos = br.Position()
        br.SeekSet(jnt1Offset)
        self._rawSectionData = br._f.read(header.sizeOfSection)
        br.SeekSet(savedPos)

        stringTable = br.ReadStringTable (jnt1Offset + header.stringTableOffset)


        if len(stringTable) != header.count :
            log.error("jnt1: number of strings doesn't match number of joints")
            if common.GLOBALS.PARANOID:
                raise ValueError("jnt1: number of strings doesn't match number of joints")
            else:
                for i in range(header.count-len(stringTable)):
                    stringTable.append('unknown name %d' %i)




        # -- read joints
        br.SeekSet(jnt1Offset + header.jntEntryOffset)
        self.frames = [None]*header.count
        # -- self.frames.resize(h.count);
        self.matrices = [None]*header.count
        # -- self.matrices.resize(h.count);
        self.isMatrixValid = [False]*header.count
        # -- self.isMatrixValid.resize(h.count);
        for i in range(header.count):
            e = JntEntry()
            e.LoadData(br)
            f = JntFrame()
            f.InitFromJntEntry(e)

            f.name = stringTable[i]
            self.frames[i] = f

    def DumpData(self, bw):
        """Write JNT1 section. If raw data was captured during import, write it back."""
        if self._rawSectionData is not None:
            bw._f.write(self._rawSectionData)
            return

        jnt1Offset = bw.Position()

        # prepare (incomplete) header, then write it
        header = Jnt1Header()
        header.sizeOfSection = 0  # placeholder, backfilled at end
        header.count = len(self.frames)
        header.jntEntryOffset = 0x18  # header is 20 bytes + 4 padding
        header.unknownOffset = header.jntEntryOffset + header.count*JntEntry.size
        rawStringTableOffset = header.unknownOffset + 2 * header.count
        header.stringTableOffset = (rawStringTableOffset + 3) & ~3  # 4-byte align
        header.pad = 0xffff  # padding

        header.DumpData(bw)
        bw.writePadding(header.jntEntryOffset - Jnt1Header.size)

        if bw.Position() != jnt1Offset + header.jntEntryOffset:
            raise ValueError('incorrect lengths in writing Jnt1')

        stringTable = header.count * [""]

        e = JntEntry()
        for i in range(header.count):
            e.FromFrame(self.frames[i])
            stringTable[i] = self.frames[i].name
            e.DumpData(bw)

        if bw.Position() != jnt1Offset + header.unknownOffset:
            raise ValueError('incorrect lengths in writing Jnt1')

        for i in range(header.count):
            bw.writeWord(i)

        # Pad to 4-byte alignment before string table
        padBytes = (jnt1Offset + header.stringTableOffset) - bw.Position()
        if padBytes > 0:
            bw.writePadding(padBytes)

        if bw.Position() != jnt1Offset + header.stringTableOffset:
            raise ValueError('incorrect lengths in writing Jnt1')

        bw.WriteStringTable(stringTable)

        # now complete and rewrite header
        header.sizeOfSection = bw.addPadding((bw.Position()-jnt1Offset))
        bw.writePadding(jnt1Offset + header.sizeOfSection - bw.Position())
        bw.SeekSet(jnt1Offset + 4)
        bw.writeDword(header.sizeOfSection)
        bw.SeekSet(jnt1Offset + header.sizeOfSection)
