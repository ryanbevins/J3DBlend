#! /usr/bin/python3
from mathutils import Vector
import mathutils
import logging
from . import common
import math
log = logging.getLogger('bpy.ops.import_mesh.bmd.vtx1')


class VertColor:
    # -- unsigned char 
    # <variable r>
    # <variable g>
    # <variable b>
    # <variable a>
    # -- all params are floats, must cast to char
    # <function>

    def __init__(self):  # GENERATED!
        pass

    def SetRGBA(self, ri, gi, bi, ai):
        log.debug("useless func!")
        # -- TODO
        # --self.r = (unsigned char)(ri + .5f);
        # --self.g = (unsigned char)(gi + .5f);
        # --self.b = (unsigned char)(bi + .5f);
        # --self.a = (unsigned char)(ai + .5f);


class TexCoord:
    # <variable s>
    # <variable t>
    # -- float 
    # <function>

    def __init__(self):  # GENERATED!
        pass

    def SetST(self, si, ti):
        self.s = si
        self.t = ti
  

class ArrayFormat:
    """# -- see ogc/gx.h for a more complete list of these values:
    # <variable arrayType>
    # -- u32 9: coords, a: normal, b: color, d: tex0 (gx.h: "Attribute")
    # <variable componentCount>
    # -- u32 meaning depends on dataType (gx.h: "CompCount")
    # <variable dataType>
    # -- u32 3: s16, 4: float, 5: rgba8 (gx.h: "CompType")
    # -- values i've seem for this: 7, e, 8, b, 0
    # ---> number of mantissa bits for fixed point numbers!
    # -- (position of decimal point)
    # <variable decimalPoint>
    # -- u8 
    # <variable unknown3>
    # -- u8 seems to be always 0xff
    # <variable unknown4>
    # -- u16 seems to be always 0xffff
    # <function>"""

    def __init__(self):  # GENERATED!
        pass

    def LoadData(self, br):
        self.arrayType = br.ReadDWORD()
        self.componentCount = br.ReadDWORD()
        self.dataType = br.ReadDWORD()
        self.decimalPoint = br.GetByte()
        self.unknown3 = br.GetByte()
        self.unknown4 = br.ReadWORD()

    def DumpData(self, bw):
        bw.writeDword(self.arrayType)
        bw.writeDword(self.componentCount)
        bw.writeDword(self.dataType)
        bw.writeByte(self.decimalPoint)
        bw.writeByte(getattr(self, 'unknown3', 0xff))
        bw.writeWord(getattr(self, 'unknown4', 0xffff))
  

class Vtx1Header:
    # <variable tag>
    # -- char[4] 'VTX1'
    # <variable sizeOfSection>
    # -- u32 
    # <variable arrayFormatOffset>
    # -- u32 for each offsets[i] != 0, an ArrayFormat
    # -- is stored for that offset
    # -- offset relative to Vtx1Header start
    #
    #    content is described by ArrayFormat - for each offset != 0,
    #    an ArrayFormat struct is stored at Vtx1Header.arrayFormatOffset
    #      # <variable offsets>
    # -- u32[13]  offsets relative to Vtx1Header start
    # <function>

    # <function>

    def __init__(self):  # GENERATED!
        self.offsets= []

    def LoadData(self, br):
        self.tag = br.ReadFixedLengthString(4)
        self.sizeOfSection = br.ReadDWORD()
        self.arrayFormatOffset = br.ReadDWORD()
        for _ in range(13):
            self.offsets.append(br.ReadDWORD())

    def GetLength(self, offsetIndex):
        startOffset = self.offsets[offsetIndex]
        for i in range(offsetIndex + 1, 13):
            # --  for(int i = k + 1; i < 13; ++i)
            if self.offsets[i] != 0:
                return self.offsets[i] - startOffset
        return self.sizeOfSection - startOffset


class Vtx1:
    """# <variable positions>
    # -- std::vector<Vector3f> 
    # <variable normals>
    # -- std::vector<Vector3f>
    # <variable colors>
    # -- std::vector<Color> colors[2] 
    # <variable texCoords>
    # -- std::vector<TexCoord> texCoords[8]  
    # -- pass in floats. Round up?
    # <function>

    # --void readVertexArray(Vtx1& arrays, const bmd::ArrayFormat& af, int length,
    # --                  FILE* f, long offset)
    # <function>

    # <function>"""

    def __init__(self, UVoffset=0):  # GENERATED!
        self.positions= []
        self.colors= []
        self.texCoords= [[],[],[],[],[],[],[],[]]
        self.normals= []
        self.UVoffset = UVoffset  # DEBUG OPTION
        self._rawSectionData = None

    def GetColor(self, ri, gi, bi, ai):
                
        #r = (ri + 0.5)
        #g = (gi + 0.5)
        #b = (bi + 0.5)
        #a = (ai + 0.5)
        return (ri/255, gi/255, bi/255, ai/255)
        # return color r g b a # XCX need color format
  

    def ReadVertexArray(self, af, length, br, offset):
        br.SeekSet(offset)
        # ----------------------------------------------------------------------
        # -- convert array to float (so we have n + m cases, not n*m)
        data = []
        # -- vector<float>

         # -- print ("af.dataType=" + (af.dataType as string) + ": af.arrayType=" + (af.arrayType as string)  )

        if af.dataType == 3:  # u16
            tmp = []
            # -- size = length/2
            count = length/2
            if int(count) != count:
                if common.GLOBALS.PARANOID:
                    raise ValueError('invalid count (length not even)')
                else:
                    log.error('invalid array length. last point will use whatever is neext in file')
            count = int(count)
            scale = 1/(2**af.decimalPoint)
            tmp = [-1] * count
            data = tmp.copy()
            for i in range(count):
                tmp[i] = br.GetSHORT()
                data[i] = tmp[i]*scale
            # --throw "TODO: testing"
            # --messageBox "3"

        elif af.dataType == 4:  # f32
            count = length/4
            if int(count) != count:
                if common.GLOBALS.PARANOID:
                    raise ValueError('invalid count (length not *4)')
                else:
                    log.error('invalid array length. last point will use whatever is neext in file')
            count = int(count)
            for _ in range(count):
                data.append(br.GetFloat())
            # --throw "TODO: testing2"
            # --print (format "ZZZ % %" length count )

        elif af.dataType == 5:  # rgb(a)
            tmp = []
            # -- size = length
            for _ in range(length):
                data.append(br.GetByte())
            # --messageBox "Vtx1: af.dataType == 5. NYI"

        else:
            if common.GLOBALS.PARANOID:
                raise ValueError('unknown array type %d' % af.dataType)
            else:
                log.warning("unknown array data type %d", af.dataType)

        # --print "DATA: "
        # --print data
        # ----------------------------------------------------------------------
        # -- stuff floats into appropriate vertex array
        if af.arrayType == 9:  # -- positions
            if af.componentCount == 0 :  # -- xy [Needs testing]
                self.positions = []
                posCount = len(data) / 2
                if int(posCount) != posCount:
                    if common.GLOBALS.PARANOID:
                        raise ValueError('invalid posCount (length not even)')
                    else:
                        log.error('invalid array posCount. last point will use whatever is neext in file')
                    
                posCount = math.ceil(posCount)
                k = 0
                for j in range(posCount):
                    pos = Vector((data[k], data[k+1], 0))
                    self.positions.append(pos)
                    k += 2
                log.info("DT %d %d. Needs testings", af.dataType, af.componentCount)

            elif af.componentCount == 1:  # -- xyz

                self.positions = []
                posCount = len(data) / 3
                if int(posCount) != posCount:
                    log.info("amount of position coordinates (%d) is not //3", len(data))
                    for com in range(int(posCount - int(posCount)*3)):
                        data.append(None)
                #raise ValueError('invalid posCount (length not *3)')
                posCount = int(posCount)
                k = 0
                for _ in range(posCount):
                    pos = Vector((data[k], data[k+1], data[k+2]))
                    self.positions.append(pos)
                    # pos.setXYZFlip(data[k], data[k+1], data[k+2])
                    k += 3
                if len(data) - posCount*3 == 1:
                    pos = Vector((data[-2], data[-1], max(data) * 2))
                    self.positions.append(pos)

                if len(data) - posCount*3 == 2:
                    pos = Vector((data[-1], max(data)*2, max(data)*2))
                    self.positions.append(pos)
            # --
            # --print (format "LEN %. COUNT %" length (data.count / 3))
            # --print self.positions

            # --messagebox (format "DT % %" af.dataType af.componentCount)

            else:
                log.warning("unsupported componentCount for self.positions array")
                # --messageBox (format "vtx1: unsupported componentCount for self.positions array: %" af.componentCount)

        elif af.arrayType == 0xa:  # -- normals TODO: Test [0xa=10]
            if af.componentCount == 0:  # -- xyz
                normalsCount = len(data) // 3
                if normalsCount != len(data):
                    log.info("length of normal coordinates (%d) is not //3", len(data))
                self.normals = []
                # -- arrays.self.normals.resize(data.size()/3);
                k = 0
                for _ in range(normalsCount):
                    utmp = Vector((data[k], data[k+1], data[k+2]))
                    self.normals.append(utmp)
                    k += 3

                if len(data) - normalsCount*3 == 1:
                    pos = Vector((data[-2], data[-1], max(data) * 2))
                    self.normals.append(pos)

                if len(data) - normalsCount*3 == 2:
                    pos = Vector((data[-1], max(data)*2, max(data)*2))
                    self.normals.append(pos)
                    # --for(int j = 0, k = 0; j < arrays.self.normals.size(); ++j, k += 3)
                    # --  arrays.self.normals[j].setXYZ(data[k], data[k + 1], data[k + 2]);
            else:
                if common.GLOBALS.PARANOID:
                    raise ValueError("vtx1: unsupported componentCount for normals array")
                else:
                    log.warning("unsupported componentCount for normals array")


        elif af.arrayType == 0xb or af.arrayType == 0xc:  # -- color0 or color1
            index = af.arrayType - 0xb
            if len(self.colors) <= index:
                self.colors.append(list())
            if af.componentCount == 0:  # -- rgb
                # -- self.colors[data.count / 3] = 0 --initialize???
                colorCount = len(data) // 3
                k = 1
                for j in range(colorCount):
                    self.colors[index].append(self.GetColor(data[k], data[k+1], data[k+2], 255))
                    k += 3
            elif af.componentCount == 1:  # -- rgba
                self.colors[index] = []
                colorCount = len(data) // 4
                k = 0  # fixed
                for j in range(colorCount):
                    self.colors[index].append(self.GetColor(data[k], data[k+1], data[k+2], data[k+3]))
                    k += 4

            else:
                if common.GLOBALS.PARANOID:
                    raise ValueError("vtx1: unsupported componentCount for colors array")
                else:
                    log.warning("unsupported componentCount for colors array")
        # -- texcoords 0 - 7 [13]

        elif af.arrayType == 0xd or\
             af.arrayType == 0xe or\
             af.arrayType == 0xf or\
             af.arrayType == 0x10 or\
             af.arrayType == 0x11 or\
             af.arrayType == 0x12 or\
             af.arrayType == 0x13 or\
             af.arrayType == 0x14:
            # -- std::vector<TexCoord> self.texCoords[8] self.texCoords
            index = (af.arrayType - 0xd)
            if af.componentCount == 0:  # --s
                # self.texCoords[index] = []  # DONE BEFORE
                # -- self.texCoords[index].resize(data.size());
                for j in range(len(data)):
                    utmp = TexCoord()
                    utmp.SetST(data[j], 0)
                    self.texCoords[index].append(utmp)

                # --for(int j = 0; j < arrays.self.texCoords[index].size(); ++j)
                # --  arrays.self.texCoords[index][j].setST(data[j], 0);

            elif af.componentCount == 1:  # -- st
                texCount = len(data)//2
                if texCount * 2 != len(data):
                    log.warning("wrong length of UV coords (not even)")
                # self.texCoords[index] = []
                # -- arrays.self.texCoords[index].resize(data.size()/2);

                k = 0  # fixed
                for j in range(texCount):
                    utmp = TexCoord()
                    utmp.SetST(data[k], data[k+1])
                    self.texCoords[index].append(utmp)
                    k += 2
                # --for(int j = 0, k = 0; j < arrays.self.texCoords[index].size(); ++j, k += 2)
                # --   arrays.self.texCoords[index][j].setST(data[k], data[k + 1]);

            else:
                if common.GLOBALS.PARANOID:
                    raise ValueError("vtx1: unsupported componentCount for texcoords array")
                else:
                    log.warning('unsupported componentCount for texcoords array')
        else:
            if common.GLOBALS.PARANOID:
                raise ValueError("WRONG ArrayType in VTX1")
            else:
                log.warning('WRONG ArrayType in VTX1')

    def LoadData(self, br):

        vtx1Offset = br.Position()

        header = Vtx1Header()
        header.LoadData(br)  # gets 64 bytes

        # Store raw section bytes for round-trip export
        savedPos = br.Position()
        br.SeekSet(vtx1Offset)
        self._rawSectionData = br._f.read(header.sizeOfSection)
        br.SeekSet(savedPos)

        # --messageBox "x"
        numArrays = 0
        for i in range(13):
            if header.offsets[i]:
                numArrays += 1
        # -- read vertex array format descriptions
        formats = []
        # -- vector<bmd::ArrayFormat>
        for i in range(numArrays):
            af = ArrayFormat()
            af.LoadData(br)
            formats.append(af)
        # Check for sentinel/terminator format entry (arrayType=0xFF)
        sentinel_pos = br.Position()
        sentinel_check = ArrayFormat()
        sentinel_check.LoadData(br)
        if sentinel_check.arrayType == 0xFF:
            self._formatSentinel = sentinel_check
        else:
            self._formatSentinel = None
            br.SeekSet(sentinel_pos)  # rewind if not a sentinel
        # Store array formats for BMD export round-tripping
        self.arrayFormats = [None] * 13

        # -- read arrays
        br.SeekSet(vtx1Offset + header.arrayFormatOffset)  # ? returns back?

        j = 0
        for i in range(13):
            if header.offsets[i]:
                f = formats[j]
                self.arrayFormats[i] = f
                len = header.GetLength(i)
                # print("Vert "+str(i)+":"+str(len))
                if f.arrayType >= 0xd:  # UV coords
                    self.ReadVertexArray(f, len, br, (vtx1Offset+header.offsets[i]+self.UVoffset))
                else:
                    self.ReadVertexArray(f, len, br, (vtx1Offset+header.offsets[i]))
                j += 1

    def WriteVertexArray(self, af, bw):
        """Write a single vertex array in the format described by af."""
        if af.arrayType == 9:  # positions (xyz floats)
            for pos in self.positions:
                if af.dataType == 4:  # f32
                    bw.writeFloat(pos.x)
                    bw.writeFloat(pos.y)
                    bw.writeFloat(pos.z)
                elif af.dataType == 3:  # s16 fixed-point
                    scale = 2**af.decimalPoint
                    bw.writeShort(round(pos.x * scale))
                    bw.writeShort(round(pos.y * scale))
                    bw.writeShort(round(pos.z * scale))

        elif af.arrayType == 0xa:  # normals (xyz)
            for nrm in self.normals:
                if af.dataType == 4:  # f32
                    bw.writeFloat(nrm.x)
                    bw.writeFloat(nrm.y)
                    bw.writeFloat(nrm.z)
                elif af.dataType == 3:  # s16 fixed-point
                    scale = 2**af.decimalPoint
                    bw.writeShort(round(nrm.x * scale))
                    bw.writeShort(round(nrm.y * scale))
                    bw.writeShort(round(nrm.z * scale))

        elif af.arrayType in (0xb, 0xc):  # color0, color1
            index = af.arrayType - 0xb
            if index < len(self.colors):
                for col in self.colors[index]:
                    if af.componentCount == 1:  # rgba
                        bw.writeByte(min(255, max(0, round(col[0] * 255))))
                        bw.writeByte(min(255, max(0, round(col[1] * 255))))
                        bw.writeByte(min(255, max(0, round(col[2] * 255))))
                        bw.writeByte(min(255, max(0, round(col[3] * 255))))
                    else:  # rgb
                        bw.writeByte(min(255, max(0, round(col[0] * 255))))
                        bw.writeByte(min(255, max(0, round(col[1] * 255))))
                        bw.writeByte(min(255, max(0, round(col[2] * 255))))

        elif 0xd <= af.arrayType <= 0x14:  # texcoords 0-7
            index = af.arrayType - 0xd
            if index < len(self.texCoords):
                for tc in self.texCoords[index]:
                    if af.dataType == 4:  # f32
                        bw.writeFloat(tc.s)
                        if af.componentCount == 1:  # st
                            bw.writeFloat(tc.t)
                    elif af.dataType == 3:  # s16 fixed-point
                        scale = 2**af.decimalPoint
                        bw.writeShort(round(tc.s * scale))
                        if af.componentCount == 1:  # st
                            bw.writeShort(round(tc.t * scale))

    def DumpData(self, bw):
        """Write VTX1 section. If raw data was captured during import, write it back."""
        if self._rawSectionData is not None:
            bw._f.write(self._rawSectionData)
            return

        vtx1Offset = bw.Position()

        # Collect which array slots are active
        activeSlots = []
        if not hasattr(self, 'arrayFormats') or self.arrayFormats is None:
            # Build default arrayFormats from available data
            self.arrayFormats = [None] * 13
            if self.positions:
                af = ArrayFormat()
                af.arrayType = 0x9
                af.componentCount = 1  # xyz
                af.dataType = 4  # f32
                af.decimalPoint = 0
                af.unknown3 = 0xff
                af.unknown4 = 0xffff
                self.arrayFormats[0] = af
            if self.normals:
                af = ArrayFormat()
                af.arrayType = 0xa
                af.componentCount = 0  # xyz
                af.dataType = 4  # f32
                af.decimalPoint = 0
                af.unknown3 = 0xff
                af.unknown4 = 0xffff
                self.arrayFormats[1] = af
            for ci in range(2):
                if ci < len(self.colors) and self.colors[ci]:
                    af = ArrayFormat()
                    af.arrayType = 0xb + ci
                    af.componentCount = 1  # rgba
                    af.dataType = 5  # rgba8
                    af.decimalPoint = 0
                    af.unknown3 = 0xff
                    af.unknown4 = 0xffff
                    self.arrayFormats[3 + ci] = af
            for ti in range(8):
                if ti < len(self.texCoords) and self.texCoords[ti]:
                    af = ArrayFormat()
                    af.arrayType = 0xd + ti
                    af.componentCount = 1  # st
                    af.dataType = 4  # f32
                    af.decimalPoint = 0
                    af.unknown3 = 0xff
                    af.unknown4 = 0xffff
                    self.arrayFormats[5 + ti] = af

        for i in range(13):
            if self.arrayFormats[i] is not None:
                activeSlots.append(i)

        numArrays = len(activeSlots)

        # VTX1 Header: tag(4) + size(4) + arrayFormatOffset(4) + offsets[13](52) = 64 bytes
        HEADER_SIZE = 64
        arrayFormatOffset = HEADER_SIZE  # formats start right after header
        arrayFormatSize = numArrays * 16  # each ArrayFormat is 16 bytes
        # Add sentinel format entry size if present
        hasSentinel = hasattr(self, '_formatSentinel') and self._formatSentinel is not None
        if hasSentinel:
            arrayFormatSize += 16

        # Calculate data offsets — first data block starts after formats, aligned to 32
        dataStart = arrayFormatOffset + arrayFormatSize
        # Align to 32 bytes
        dataStart = ((dataStart + 31) // 32) * 32

        # Calculate size of each array's data
        arraySizes = {}
        for i in activeSlots:
            af = self.arrayFormats[i]
            size = 0
            if af.arrayType == 0x9:  # positions
                if af.dataType == 4:
                    size = len(self.positions) * 3 * 4
                elif af.dataType == 3:
                    size = len(self.positions) * 3 * 2
            elif af.arrayType == 0xa:  # normals
                if af.dataType == 4:
                    size = len(self.normals) * 3 * 4
                elif af.dataType == 3:
                    size = len(self.normals) * 3 * 2
            elif af.arrayType in (0xb, 0xc):  # colors
                idx = af.arrayType - 0xb
                count = len(self.colors[idx]) if idx < len(self.colors) else 0
                if af.componentCount == 1:  # rgba
                    size = count * 4
                else:  # rgb
                    size = count * 3
            elif 0xd <= af.arrayType <= 0x14:  # texcoords
                idx = af.arrayType - 0xd
                count = len(self.texCoords[idx]) if idx < len(self.texCoords) else 0
                if af.dataType == 4:
                    bytesPerComp = 4
                elif af.dataType == 3:
                    bytesPerComp = 2
                else:
                    bytesPerComp = 4
                numComps = 2 if af.componentCount == 1 else 1
                size = count * numComps * bytesPerComp
            arraySizes[i] = size

        # Assign offsets for each array
        offsets = [0] * 13
        currentOffset = dataStart
        for i in activeSlots:
            offsets[i] = currentOffset
            currentOffset += arraySizes[i]
            # Align each array to 32 bytes
            currentOffset = ((currentOffset + 31) // 32) * 32

        # Write header placeholder
        bw.writeString("VTX1")
        bw.writeDword(0)  # sizeOfSection placeholder
        bw.writeDword(arrayFormatOffset)
        for i in range(13):
            bw.writeDword(offsets[i])

        # Write array format descriptors
        for i in activeSlots:
            self.arrayFormats[i].DumpData(bw)

        # Write sentinel format entry if present (arrayType=0xFF terminator)
        if hasattr(self, '_formatSentinel') and self._formatSentinel is not None:
            self._formatSentinel.DumpData(bw)

        # Pad to first data offset
        if activeSlots:
            firstDataOffset = offsets[activeSlots[0]]
            padNeeded = vtx1Offset + firstDataOffset - bw.Position()
            if padNeeded > 0:
                bw.writePadding(padNeeded)

        # Write each array's data
        for idx, i in enumerate(activeSlots):
            bw.SeekSet(vtx1Offset + offsets[i])
            self.WriteVertexArray(self.arrayFormats[i], bw)
            # Pad to next array or end
            if idx + 1 < len(activeSlots):
                nextOffset = offsets[activeSlots[idx + 1]]
                padNeeded = vtx1Offset + nextOffset - bw.Position()
                if padNeeded > 0:
                    bw.writePadding(padNeeded)

        # Compute final section size (align to 32)
        rawSize = bw.Position() - vtx1Offset
        sectionSize = ((rawSize + 31) // 32) * 32
        padNeeded = sectionSize - rawSize
        if padNeeded > 0:
            bw.writePadding(padNeeded)

        # Go back and write section size
        bw.SeekSet(vtx1Offset + 4)
        bw.writeDword(sectionSize)
        bw.SeekSet(vtx1Offset + sectionSize)


    @staticmethod
    def FromBlenderMesh(mesh_obj, jnt=None, drw=None):
        """Reconstruct VTX1 data from a Blender mesh object.

        Extracts positions, normals, UVs, and vertex colors from the Blender mesh,
        applies coordinate/UV conversions, and deduplicates into pools.

        When jnt and drw are provided (imported BMD), vertex positions and normals
        are transformed back to bone-local space by applying the inverse of the
        bone's world matrix. This reverses the transform applied during import.

        Returns a new Vtx1 instance with populated pools and arrayFormats.

        Also returns a per-loop index mapping dict for SHP1 to use:
            loop_indices[loop_index] = {
                'posIndex': int, 'normalIndex': int,
                'colorIndex': [int, int], 'texCoordIndex': [int, int, ...]
            }
        """
        from mathutils import Matrix as MathMatrix
        mesh = mesh_obj.data
        # Ensure we have loop triangles computed
        mesh.calc_loop_triangles()
        # Ensure normals are up to date
        if hasattr(mesh, 'calc_normals_split'):
            mesh.calc_normals_split()

        vtx = Vtx1()
        vtx.arrayFormats = None  # will be auto-built by DumpData

        # --- Build bone inverse matrix table for un-transforming vertices ---
        # During import, each vertex was transformed: world_pos = bone_matrix @ local_pos
        # We need to reverse this: local_pos = bone_matrix^-1 @ world_pos
        vert_bone_inv_matrix = {}  # blender vert index -> inverse bone matrix (4x4)
        has_armature = (hasattr(mesh_obj, 'parent') and mesh_obj.parent is not None
                        and mesh_obj.parent.type == 'ARMATURE')

        if has_armature and jnt is not None and drw is not None and mesh_obj.vertex_groups:
            arm_obj = mesh_obj.parent
            bone_names = [b.name for b in arm_obj.data.bones]

            # Build vgroup_index -> bone_index mapping
            vgroup_to_bone = {}
            for vg in mesh_obj.vertex_groups:
                if vg.name in bone_names:
                    vgroup_to_bone[vg.index] = bone_names.index(vg.name)

            # Build bone_index -> DRW1 rigid entry -> JNT1 bone index mapping
            # For rigid DRW1 entries: drw.data[drw_idx] = jnt bone index
            # The import used jnt.frames[drw.data[drw_idx]].matrix as the transform
            bone_to_jnt_matrix = {}
            for bi in range(len(bone_names)):
                # Find the rigid DRW1 entry for this bone
                for di, (isW, data_val) in enumerate(zip(drw.isWeighted, drw.data)):
                    if not isW and data_val == bi:
                        # This bone has a rigid DRW1 entry -> use jnt frame matrix
                        if bi < len(jnt.frames) and jnt.frames[bi].matrix is not None:
                            bone_to_jnt_matrix[bi] = jnt.frames[bi].matrix
                        break
                else:
                    # No rigid DRW1 entry — use the JNT frame matrix directly
                    # (these bones' vertices go through weighted path but still need un-transform)
                    if bi < len(jnt.frames) and jnt.frames[bi].matrix is not None:
                        bone_to_jnt_matrix[bi] = jnt.frames[bi].matrix

            # For each vertex, find primary bone and compute inverse matrix
            for vi, vert in enumerate(mesh.vertices):
                if vert.groups:
                    best_group = max(vert.groups, key=lambda g: g.weight)
                    bone_idx = vgroup_to_bone.get(best_group.group, None)
                    if bone_idx is not None and bone_idx in bone_to_jnt_matrix:
                        mat = bone_to_jnt_matrix[bone_idx]
                        try:
                            vert_bone_inv_matrix[vi] = mat.inverted()
                        except ValueError:
                            pass  # singular matrix, skip

        # --- Positions (deduplicated from mesh vertices) ---
        # GC coordinate conversion: blender(x,y,z) -> gc(x, z, -y)
        pos_map = {}  # (x,y,z) gc-space -> pool index
        vtx.positions = []
        vert_to_posIndex = {}  # blender vert index -> vtx1 pool index

        for vi, vert in enumerate(mesh.vertices):
            bx, by, bz = vert.co.x, vert.co.y, vert.co.z
            gc_pos_world = Vector((bx, bz, -by))

            # Un-transform from world space to bone-local space
            if vi in vert_bone_inv_matrix:
                gc_pos = vert_bone_inv_matrix[vi] @ gc_pos_world
            else:
                gc_pos = gc_pos_world

            key = (gc_pos.x, gc_pos.y, gc_pos.z)
            if key not in pos_map:
                pos_map[key] = len(vtx.positions)
                vtx.positions.append(Vector(gc_pos))
            vert_to_posIndex[vi] = pos_map[key]

        # --- Normals (per-loop, deduplicated) ---
        # We use loop normals for per-face smooth/flat shading
        # Normals also need to be un-transformed (import rotated them by bone matrix)
        nrm_map = {}  # (nx,ny,nz) gc-space -> pool index
        vtx.normals = []
        # Build per-loop vertex index lookup for normal un-transform
        _vert_bone_inv_matrix = vert_bone_inv_matrix

        # --- UVs (per-loop, deduplicated, up to 8 layers) ---
        # Filter to UV layers that actually have data
        active_uv_layers = [uv for uv in mesh.uv_layers if len(uv.data) > 0]
        num_uv_layers = min(len(active_uv_layers), 8)
        vtx.texCoords = [[] for _ in range(8)]
        uv_maps = [{} for _ in range(8)]  # (s,t) gc-space -> pool index per layer

        # --- Vertex Colors (per-loop, deduplicated, up to 2 layers) ---
        # Blender 5.0 uses color_attributes instead of vertex_colors
        color_attrs = []
        if hasattr(mesh, 'color_attributes'):
            color_attrs = [ca for ca in mesh.color_attributes if ca.domain == 'CORNER']
        elif hasattr(mesh, 'vertex_colors'):
            color_attrs = list(mesh.vertex_colors)
        num_color_layers = min(len(color_attrs), 2)
        vtx.colors = [[] for _ in range(num_color_layers)]
        color_maps = [{} for _ in range(2)]  # (r,g,b,a) 0-255 -> pool index per layer

        # --- Build per-loop index mapping ---
        loop_indices = {}

        for loop_idx, loop in enumerate(mesh.loops):
            entry = {}

            # Position index
            entry['posIndex'] = vert_to_posIndex[loop.vertex_index]

            # Normal (use loop normal for correct smooth/flat)
            nx, ny, nz = loop.normal.x, loop.normal.y, loop.normal.z
            gc_nrm_vec = Vector((nx, nz, -ny))
            # Un-rotate normal from world space to bone-local space
            vi = loop.vertex_index
            if vi in _vert_bone_inv_matrix:
                gc_nrm_vec = gc_nrm_vec.copy()
                gc_nrm_vec.rotate(_vert_bone_inv_matrix[vi])
            gc_nrm = (round(gc_nrm_vec.x, 6), round(gc_nrm_vec.y, 6), round(gc_nrm_vec.z, 6))
            if gc_nrm not in nrm_map:
                nrm_map[gc_nrm] = len(vtx.normals)
                vtx.normals.append(Vector(gc_nrm))
            entry['normalIndex'] = nrm_map[gc_nrm]

            # UVs
            entry['texCoordIndex'] = [None] * 8
            for uv_idx in range(num_uv_layers):
                uv_data = active_uv_layers[uv_idx].data[loop_idx].uv
                # UV conversion: gc_v = 1.0 - blender_v
                gc_uv = (round(uv_data[0], 6), round(1.0 - uv_data[1], 6))
                if gc_uv not in uv_maps[uv_idx]:
                    uv_maps[uv_idx][gc_uv] = len(vtx.texCoords[uv_idx])
                    tc = TexCoord()
                    tc.SetST(gc_uv[0], gc_uv[1])
                    vtx.texCoords[uv_idx].append(tc)
                entry['texCoordIndex'][uv_idx] = uv_maps[uv_idx][gc_uv]

            # Vertex Colors
            entry['colorIndex'] = [None, None]
            for ci in range(num_color_layers):
                ca = color_attrs[ci]
                col = ca.data[loop_idx].color  # (r, g, b, a) as floats 0-1
                # Quantize to u8 for dedup
                r8 = min(255, max(0, round(col[0] * 255)))
                g8 = min(255, max(0, round(col[1] * 255)))
                b8 = min(255, max(0, round(col[2] * 255)))
                a8 = min(255, max(0, round(col[3] * 255))) if len(col) > 3 else 255
                gc_col = (r8, g8, b8, a8)
                if gc_col not in color_maps[ci]:
                    color_maps[ci][gc_col] = len(vtx.colors[ci])
                    vtx.colors[ci].append((r8/255, g8/255, b8/255, a8/255))
                entry['colorIndex'][ci] = color_maps[ci][gc_col]

            loop_indices[loop_idx] = entry

        # Clean up empty texcoord/color arrays
        for i in range(8):
            if not vtx.texCoords[i]:
                vtx.texCoords[i] = []
        for i in range(len(vtx.colors)):
            if not vtx.colors[i]:
                vtx.colors[i] = []
        # Remove trailing empty color arrays
        while vtx.colors and not vtx.colors[-1]:
            vtx.colors.pop()

        return vtx, loop_indices


# small iter-generators to iterate triangles from GL_strips and GL_fans.
def StripIterator(lst):
    if False and common.GLOBALS.no_rot_conversion:
        flip = True
    else:
        flip = False  # odd faces are in reversed index
    for com in range(len(lst)-2):
        if flip:
            yield (lst[com], lst[com+1], lst[com+2])  # correct order to have correct normals
        else:
            yield (lst[com+2], lst[com+1], lst[com])
        flip = not flip


def FanIterator(lst):
    log.warning('This is a fan!')
    if False and common.GLOBALS.no_rot_conversion:
        for com in range(1, len(lst)-1):
            yield (lst[0], lst[com], lst[com+1])  # faces need to be described like this in order to have correct normals
    else:
        for com in range(1, len(lst)-1):
            yield (lst[0], lst[com+1], lst[com])  # faces need to be described like this in order to have correct normals

def SimpleIterator(lst):
    log.warning('this might be a simple list of triangles but we don\'t yet know for sure')
    for com in range(len(lst)//3):
        yield (lst[3*com], lst[3*com+1], lst[3*com+2])
def SimpleQuadIterator(lst):
    log.warning('this might be a simple list of (assumed-coplanar) quads but we don\'t yet know for sure')
    for com in range(len(lst)//4):
        yield (lst[4*com], lst[4*com+1], lst[4*com+2])
        yield (lst[4*com+2], lst[4*com+3], lst[4*com])


def findFace(model, facelist, v0, v1, v2, exclude):
    for face in facelist:
        fv0, fv1, fv2 = model.getVerts(face)
        if exclude==2:
            if fv0 == v0 and fv1 == v1 and fv2 != v2:
                return face
        elif exclude == 0:
            if fv0 != v0 and fv1 == v1 and fv2 == v2:
                return face
        else:
            log.critical("findFace wasn't meant to exclude second vert in match. ***report bug***")
            raise ValueError('~the dev is an idiot~')
    return None


def getStrip(model, facelist, startFace, v0, v1, v2):
    stFaces = [startFace]
    stVerts = [v2, v1, v0]  # first face is in reverse order
    stLoops = [model.getLoop(startFace, 2),
               model.getLoop(startFace, 1),
               model.getLoop(startFace, 0)]

    # faces have to be found from the 2->1 edge of the previous triangle (on their 1->2)
    # or from the 1->0 edge of the previous triangle (on their 0->1), alternatively.
    newFace = findFace(model, facelist, v0, v1, v2)  # second face found from 2->1
    flip = False  # odd faces from 1->0 (False), even faces from 2->1 (True)
    while newFace is not None:
        stFaces.append(newFace)
        fv0, fv1, fv2 = model.getVerts(newFace)
        if flip:  # order: 2-1-0. append 0
            stVerts.append(fv0)
            stLoops.append(model.getLoop(newFace, 0))
            flip = False
            newFace = findFace(model, facelist, fv1, fv0, fv2, 2)  # find (odd face) from 1->0 on 0->1
        else:  # order: 0-1-2. append 2
            stVerts.append(fv2)
            stLoops.append(model.getLoop(newFace, 2))
            flip = True
            newFace = findFace(model, facelist, fv0, fv2, fv1, 0)  # find (even face) from 2->1 on 1->2
    return (stFaces, stLoops)


def makestrips(model, facelist):
    # notice : this function operates under the asumption that the faces make a somewhat manifold mesh,
    # but won't crash if otherwise : it will only cause optimisation problems
    strips = []
    while facelist:
        # generate a single strip from the first face of the facelist
        face = facelist[0]
        v0 = model.getLoop(face, 0).vertex
        v1 = model.getLoop(face, 1).vertex
        v2 = model.getLoop(face, 2).vertex

        # starting from a single face, there are three strips that can be made.
        st0 = getStrip(model, facelist, face, v0, v1, v2)
        st1 = getStrip(model, facelist, face, v1, v2, v0)
        st2 = getStrip(model, facelist, face, v2, v0, v1)

        # only get the longest
        if len(st0[0]) >= len(st1[0]):
            st3 = st0
        else:
            st3 = st1
        if len(st3[0]) >= len(st2[0]):
            st = st3
        else:
            st = st2

        strips.append(st)

        # exclude strip faces from future strips
        for face in st[0]:
            facelist.remove(face)

    return strips