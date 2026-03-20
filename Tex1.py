#! /usr/bin/python3
import re
import struct
import logging
log = logging.getLogger('bpy.ops.import_mesh.bmd.tex1')

class ImageHeader:
    # <variable data>
    # -- Image* 
    # <variable name>
    # -- std::string 
    #
    #    from gx.h:
    #    0: clamp to edge
    #    1: repeat
    #    2: mirror
    #      # <variable wrapS>
    # <variable wrapT>
    # -- u8
    # --TODO: unknown fields
    def __init__(self):  # GENERATED!
        pass
# ------------------------------------------------------------------------------------------------


class Image:
    """# <variable format>
    # -- int
    # <variable width>
    # <variable height>
    # -- int
    # <variable mipmaps>
    # --std::vector<u8*>  points into imageData
    # <variable sizes>
    # -- std::vector<int> image data size for each mipmap
    # <variable imageData>
    # -- std::vector<u8> 
    #
    #  //NOTE: palettized images are converted
    #  //to non-palettized images during load time,
    #  //i4 and i4a4 are converted to i8 and i8a8
    #  //(i8a8 is then converted to a8i8 for opengl),
    #  //r5g5b5a3 and r5g6b5 to rgba8 (actually, to agbr8,
    #  //that is rgba8 backwards - for opengl. rgba8
    #  //is converted to agbr8 as well).
    #  //(that is, only formats 1, 3, 6 and 14 are
    #  //used after conversion)
    #    # --TODO: gl image conversions (rgba -> abgr, ia -> ai
    # --somewhere else?)
    # --TODO: this is temporary and belongs somewhere else:
    # <variable texId>
    # -- unsigned int """
    def __init__(self):  # GENERATED!
        self.mipmaps = []
        self.sizes = []
        self.imageData = []
# ------------------------------------------------------------------------------------------------
# -- header format for 'bmd3' files, seems to be slightly different for 'jpa1'


class Tex1Header:
    """# <variable tag>
    # --char [4]  'TEX1'
    # <variable sizeOfSection>
    # -- u32
    # <variable numImages>
    # -- u16
    # <variable unknown>
    # -- u16 padding, usually 0xffff
    # <variable textureHeaderOffset>
    # -- u32numImages bti image headers are stored here (see bti spec)
    # --note: several image headers may point to same image data
    # --offset relative to Tex1Header start
    # <variable stringTableOffset>
    # -- u32stores one filename for each image (TODO: details on stringtables)
    # --offset relative to Tex1Header start  
    # <function>"""
    def __init__(self):  # GENERATED!
        self.tag = None
        self.sizeOfSection = None
        self.numImages = 0
        self.unknown = None
        self.textureHeaderOffset = None
        self.stringTableOffset = None

    size = 16  # bytes

    def LoadData(self, br):
        self.tag = br.ReadFixedLengthString(4)
        self.sizeOfSection = br.ReadDWORD()
        self.numImages = br.ReadWORD()
        self.unknown = br.ReadWORD()
        self.textureHeaderOffset = br.ReadDWORD()
        self.stringTableOffset = br.ReadDWORD()

    def DumpData(self, bw):
        bw.writeString("TEX1")
        bw.writeDword(self.sizeOfSection)
        bw.writeWord(self.numImages)
        bw.writeWord(self.unknown if self.unknown is not None else 0xffff)
        bw.writeDword(self.textureHeaderOffset)
        bw.writeDword(self.stringTableOffset)
# ------------------------------------------------------------------------------------------------


class TextureHeader:
    """# <variable format>
    # -- u8data format - seems to match tpl's format (see yagcd)
    # <variable unknown>
    # -- u8
    # <variable width>
    # -- u16 
    # <variable height>
    # -- u16
    #
    #    from gx.h:
    #    0: clamp to edge
    #    1: repeat
    #    2: mirror
    #      # <variable wrapS>
    # -- u8
    # <variable wrapT>
    # -- u8 
    # <variable unknown3>
    # --   u8
    # <variable paletteFormat>
    # -- u8 palette format - matches tpl palette format (-> yagcd)
    # <variable paletteNumEntries>
    # -- u16
    # <variable paletteOffset>
    # -- u32 palette data
    # <variable unknown5>
    # -- u32
    # <variable unknown6>
    # -- u16 prolly two u8s, first is 5 or 1, second 1 most of the time
    # <variable unknown7>
    # -- u16 0 most of the time, sometimes 0x10, 0x18, 0x20, 0x28
    # <variable mipmapCount>
    # -- u8
    # <variable unknown8>
    # -- u8
    # <variable unknown9>
    # -- u16
    # <variable dataOffset>
    # -- u32 image data
    # --some of the unknown data could be render state?
    # --(lod bias, min/mag filter, clamp s/t, ...)
    # <function>"""
    size = 32  # bytes per texture header entry

    def __init__(self):  # GENERATED!
        pass

    def LoadData(self, br):
        self.format = br.GetByte()
        self.unknown = br.GetByte()
        self.width = br.ReadWORD()
        self.height = br.ReadWORD()
        self.wrapS = br.GetByte()
        self.wrapT = br.GetByte()
        self.unknown3 = br.GetByte()
        self.paletteFormat = br.GetByte()
        self.paletteNumEntries = br.ReadWORD()
        self.paletteOffset = br.ReadDWORD()
        self.unknown5 = br.ReadDWORD()
        self.unknown6 = br.ReadWORD()
        self.unknown7 = br.ReadWORD()
        self.mipmapCount = br.GetByte()
        self.unknown8 = br.GetByte()
        self.unknown9 = br.ReadWORD()
        self.dataOffset = br.ReadDWORD()

    def DumpData(self, bw):
        bw.writeByte(self.format)
        bw.writeByte(self.unknown)
        bw.writeWord(self.width)
        bw.writeWord(self.height)
        bw.writeByte(self.wrapS)
        bw.writeByte(self.wrapT)
        bw.writeByte(self.unknown3)
        bw.writeByte(self.paletteFormat)
        bw.writeWord(self.paletteNumEntries)
        bw.writeDword(self.paletteOffset)
        bw.writeDword(self.unknown5)
        bw.writeWord(self.unknown6)
        bw.writeWord(self.unknown7)
        bw.writeByte(self.mipmapCount)
        bw.writeByte(self.unknown8)
        bw.writeWord(self.unknown9)
        bw.writeDword(self.dataOffset)
# ------------------------------------------------------------------------------------------------
class Tex1:
    # --imageHeaders = #(), -- std::vector<ImageHeader> 
    # <variable texHeaders>
    # <variable stringtable>
    # --because several image headers might point to the
    # --same image data, this data is stored
    # --separately to save some memory
    # --(this way only about 1/6 of the memory required
    # --otherwise is used)
    # -- images = #(), -- std::vector<Image > 
    # <function>
    def __init__(self):  # GENERATED!
        self.texHeaders = []
        self._rawSectionData = None  # raw bytes for round-trip export

    def LoadData(self, br):
        tex1Offset = br.Position()
        # -- read textureblock header
        h = Tex1Header()
        h.LoadData(br)

        # Store the entire raw TEX1 section for byte-identical export
        savedPos = br.Position()
        br.SeekSet(tex1Offset)
        self._rawSectionData = br._f.read(h.sizeOfSection)
        br.SeekSet(savedPos)

        # -- read self.stringtable
        self.stringtable = br.ReadStringTable(tex1Offset + h.stringTableOffset)  # readStringtable(tex1Offset + h.stringTableOffset, f, self.stringtable);
        for i in range(len(self.stringtable)):
            if re.search(r'[\\/]', self.stringtable[i]):
                log.critical('weird characters found in image stringtable. THIS MIGHT HAVE BEEN AN ATTACK')
                raise KeyboardInterrupt('\n\n>>>>>>POSSIBLE ATTACK. TERMINATING. <<<<<<')

        if len(self.stringtable) != h.numImages:
            if common.GLOBALS.PARANOID:
                raise ValueError("tex1: number of strings doesn't match number of images")
            else:
                for i in range(h.numImages - len(self.stringtable)):
                    self.stringtable.append('unknown name %d' %i)

          # -- read all image headers before loading the actual image
          # -- data, because several headers can refer to the same data
        br.SeekSet(tex1Offset + h.textureHeaderOffset)
        self.texHeaders = []
        imageOffsets = []

        for _ in range(h.numImages):
            texHeader = TextureHeader()
            texHeader.LoadData(br)
            self.texHeaders.append(texHeader)

    def DumpData(self, bw):
        """Write TEX1 section to binary writer.

        If raw section data was captured during import, write it back
        byte-identical. Otherwise, reconstruct from parsed headers
        and string table (without image pixel data).
        """
        if self._rawSectionData is not None:
            bw._f.write(self._rawSectionData)
            return

        # Reconstruct TEX1 from parsed data (headers + string table only,
        # no image pixel data — this path is for newly constructed Tex1 objects)
        tex1Offset = bw.Position()

        numImages = len(self.texHeaders)

        # Header is 16 bytes, texture headers start right after
        textureHeaderOffset = Tex1Header.size
        texHeadersSize = numImages * TextureHeader.size
        stringTableOffset = textureHeaderOffset + texHeadersSize

        # Write placeholder header
        header = Tex1Header()
        header.numImages = numImages
        header.unknown = 0xffff
        header.textureHeaderOffset = textureHeaderOffset
        header.stringTableOffset = stringTableOffset
        header.sizeOfSection = 0  # placeholder
        header.DumpData(bw)

        # Write texture headers
        for th in self.texHeaders:
            th.DumpData(bw)

        # Write string table
        bw.WriteStringTable(self.stringtable)

        # Write image data if present (from BuildFromImages)
        imageDataList = getattr(self, '_imageData', None)
        if imageDataList and len(imageDataList) == numImages:
            # Pad to 32-byte alignment before image data
            rawPos = bw.Position() - tex1Offset
            padTo32 = ((rawPos + 31) // 32) * 32
            if padTo32 > rawPos:
                bw.writePadding(padTo32 - rawPos)

            imageDataStart = bw.Position() - tex1Offset

            # Write each image's encoded data and record offsets
            dataOffsets = []
            for imgData in imageDataList:
                dataOffsets.append(bw.Position() - tex1Offset)
                bw._f.write(imgData)

            # Patch dataOffset in each texture header
            # Headers start at textureHeaderOffset, each is 32 bytes
            # dataOffset is at byte 28 within each header
            for i, offset in enumerate(dataOffsets):
                # dataOffset is relative to the start of the texture header entry
                headerPos = tex1Offset + textureHeaderOffset + i * TextureHeader.size
                relOffset = offset - (textureHeaderOffset + i * TextureHeader.size)
                bw.SeekSet(headerPos + 28)  # dataOffset field at offset 28
                bw.writeDword(relOffset)

            # Seek to end of last image data
            endPos = dataOffsets[-1] + len(imageDataList[-1])
            bw.SeekSet(tex1Offset + endPos)

        # Pad to 32-byte alignment
        rawSize = bw.Position() - tex1Offset
        sectionSize = ((rawSize + 31) // 32) * 32
        padNeeded = sectionSize - rawSize
        if padNeeded > 0:
            bw.writePadding(padNeeded)

        # Go back and write section size
        bw.SeekSet(tex1Offset + 4)
        bw.writeDword(sectionSize)
        bw.SeekSet(tex1Offset + sectionSize)

    def FromMaterials(self, materials):
        """Reconstruct TEX1 from Blender materials' gc_tex custom properties.

        This collects unique textures referenced by materials and rebuilds
        the texHeaders and stringtable arrays.
        """
        self.texHeaders = []
        self.stringtable = []
        seen = {}  # name -> index

        for mat in materials:
            if mat is None:
                continue
            for texIdx in range(8):
                prefix = "gc_tex%d_" % texIdx
                name = mat.get(prefix + "name")
                if name is None or name in seen:
                    continue

                th = TextureHeader()
                th.format = mat.get(prefix + "format", 0)
                th.unknown = mat.get(prefix + "unknown", 0)
                th.width = mat.get(prefix + "width", 0)
                th.height = mat.get(prefix + "height", 0)
                th.wrapS = mat.get(prefix + "wrapS", 0)
                th.wrapT = mat.get(prefix + "wrapT", 0)
                th.unknown3 = mat.get(prefix + "unknown3", 0)
                th.paletteFormat = mat.get(prefix + "paletteFormat", 0)
                th.paletteNumEntries = mat.get(prefix + "paletteNumEntries", 0)
                th.paletteOffset = mat.get(prefix + "paletteOffset", 0)
                th.unknown5 = mat.get(prefix + "unknown5", 0)
                th.unknown6 = mat.get(prefix + "unknown6", 0)
                th.unknown7 = mat.get(prefix + "unknown7", 0)
                th.mipmapCount = mat.get(prefix + "mipmapCount", 0)
                th.unknown8 = mat.get(prefix + "unknown8", 0)
                th.unknown9 = mat.get(prefix + "unknown9", 0)
                th.dataOffset = 0  # will need to be fixed up with actual image data

                seen[name] = len(self.texHeaders)
                self.texHeaders.append(th)
                self.stringtable.append(name)

    @staticmethod
    def _encode_rgba8(pixels, width, height):
        """Encode RGBA pixel data to GC RGBA8 tile format.

        RGBA8 (format 6): 4x4 tiles, each tile is 64 bytes.
        First 32 bytes: AR values (row by row within the 4x4 tile)
        Last 32 bytes: GB values (row by row within the 4x4 tile)

        Args:
            pixels: flat list/array of RGBA floats (0.0-1.0), length = width*height*4
            width: image width in pixels
            height: image height in pixels

        Returns bytes of the encoded image data.
        """
        # Pad dimensions to multiples of 4
        pad_w = ((width + 3) // 4) * 4
        pad_h = ((height + 3) // 4) * 4

        data = bytearray()

        for ty in range(0, pad_h, 4):
            for tx in range(0, pad_w, 4):
                ar_block = bytearray(32)
                gb_block = bytearray(32)

                for row in range(4):
                    for col in range(4):
                        px = tx + col
                        py = ty + row

                        if px < width and py < height:
                            idx = (py * width + px) * 4
                            r = int(pixels[idx + 0] * 255 + 0.5)
                            g = int(pixels[idx + 1] * 255 + 0.5)
                            b = int(pixels[idx + 2] * 255 + 0.5)
                            a = int(pixels[idx + 3] * 255 + 0.5)
                            r = max(0, min(255, r))
                            g = max(0, min(255, g))
                            b = max(0, min(255, b))
                            a = max(0, min(255, a))
                        else:
                            r = g = b = a = 0

                        offset = row * 4 + col
                        ar_block[offset * 2 + 0] = a
                        ar_block[offset * 2 + 1] = r
                        gb_block[offset * 2 + 0] = g
                        gb_block[offset * 2 + 1] = b

                data.extend(ar_block)
                data.extend(gb_block)

        return bytes(data)

    def BuildFromImages(self, images):
        """Build TEX1 from Blender image objects.

        Encodes each image in RGBA8 format (GC format 6). Sets up texture
        headers, string table, and encoded image data.

        Args:
            images: list of (name, blender_image) tuples. Each blender_image
                    must have .pixels, .size[0] (width), .size[1] (height).

        Sets _rawSectionData = None to force DumpData reconstruction path.
        Sets _imageData list with encoded bytes per texture.
        """
        self.texHeaders = []
        self.stringtable = []
        self._imageData = []
        self._rawSectionData = None

        for name, img in images:
            width = img.size[0]
            height = img.size[1]

            # Get pixel data as flat list of RGBA floats
            pixels = list(img.pixels)

            # Encode as RGBA8
            encoded = Tex1._encode_rgba8(pixels, width, height)

            th = TextureHeader()
            th.format = 6  # RGBA8
            th.unknown = 1  # alpha flag
            th.width = width
            th.height = height
            th.wrapS = 1  # repeat
            th.wrapT = 1  # repeat
            th.unknown3 = 0
            th.paletteFormat = 0
            th.paletteNumEntries = 0
            th.paletteOffset = 0
            th.unknown5 = 0
            th.unknown6 = (1 << 8) | 1  # min/mag filter: linear
            th.unknown7 = 0
            th.mipmapCount = 1
            th.unknown8 = 0
            th.unknown9 = 0
            th.dataOffset = 0  # filled in during DumpData

            self.texHeaders.append(th)
            self.stringtable.append(name)
            self._imageData.append(encoded)

        log.info("TEX1 BuildFromImages: %d textures", len(self.texHeaders))
