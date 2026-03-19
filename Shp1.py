#! /usr/bin/python
import logging
from . import common
log = logging.getLogger('bpy.ops.import_mesh.bmd.shp1')

"""
Okay.
Mesh structure:
Batches list the attributes that are defined for every loop contained in them (see ShpAttributes)
Packets define the relative weights
Primitives contain `ShpIndex`es, aka blender loops
"""


class ShpIndex:
    # <variable matrixIndex>
    # -- u16 -- can be undefined
    # <variable posIndex>
    # -- u16
    # <variable normalIndex>
    # -- u16
    # <variable colorIndex>
    # -- u16[2]
    # <variable texCoordIndex>
    # -- u16[8]
    def __init__(self):  # GENERATED!
        self.colorIndex= []
        self.texCoordIndex= []
# ---------------------------------------------------------------------------------------------------------------------


class ShpPrimitive:
    # <variable primitiveType>
    # --u8 see above
    # <variable numVertices>
    # --u16 that many vertices included in this primitive - for
    # --each vertex indices are stored according to batch type
    def __init__(self):  # GENERATED!
        self.points = []
    #---------------------------------------------------------------------------------------------------------------------
    #--for every packet a MatrixData struct is stored at
    #--Shp1Header.offsetToMatrixData + Batch.firstMatrixData*sizeof(MatrixData).
    #--This struct stores which part of the MatrixTable belongs to this packet
    #--(the matrix table is stored at Shp1Header.offsetToMatrixTable)
# ---------------------------------------------------------------------------------------------------------------------


class ShpPacket:
    def __init__(self):  # GENERATED!
        self.matrixTable = []
        # maps attribute matrix index to draw array index
        # -- Shp1BatchAttrib[] attribs
        # -- Packet& dst
        self.primitives = []

    def LoadPacketPrimitives(self, attribs, dataSize, br):
        done = False
        readBytes = 0
        primIndex = 0  # fixed

        while not done:
            type = br.GetByte()
            readBytes += 1
            if type == 0 or readBytes >= dataSize:
                done = True
            else:
                curPrimative = ShpPrimitive()
                curPrimative.type = type
                if len(self.primitives) <= primIndex:
                    self.primitives.append(None)
                self.primitives[primIndex] = curPrimative
                primIndex += 1

                count = br.ReadWORD()

                readBytes += 2
                curPrimative.points = []
                # --  primative.points.resize(count)
                for j in range(count):
                    curPoint = ShpIndex()
                    for k in range(len(attribs)):
                        val = 0
                        # -- get value
                        if attribs[k].dataType == 1:  # -- s8
                            val = br.GetByte()
                            readBytes += 1
                        elif attribs[k].dataType == 3:  # -- s16
                            val = br.ReadWORD()
                            readBytes += 2
                        else:
                            log.error("X shp1: got invalid data type in packet. should never happen because dumpBatch() should check this before calling dumpPacket()")
                            if common.GLOBALS.PARANOID:
                                raise ValueError("ERROR")

                        # -- set appropriate index
                        if attribs[k].attrib == 0:
                            curPoint.matrixIndex = val
                        elif attribs[k].attrib == 9:
                            curPoint.posIndex = val
                        elif attribs[k].attrib == 0xa:
                            curPoint.normalIndex = val
                        elif attribs[k].attrib == 0xb or attribs[k].attrib == 0xc:
                            while len(curPoint.colorIndex) < 2:
                                curPoint.colorIndex.append(None)
                            curPoint.colorIndex[(attribs[k].attrib - 0xb)] = val  # fixed
                        elif 0xd <= attribs[k].attrib <= 0x14:
                            while len(curPoint.texCoordIndex)<8:
                                curPoint.texCoordIndex.append(None)
                            curPoint.texCoordIndex[(attribs[k].attrib - 0xd)] = val  # fixed
                        else:
                            log.error("impossible SHP attribute %d", attribs[k].attrib)
                            if common.GLOBALS.PARANOID and False:
                                raise ValueError('~the dev was an idiot~')
                            #-- messageBox "WARNING shp1: got invalid attrib in packet. should never happen because dumpBatch() should check this before calling dumpPacket()"
                            #--print curPrimative
                            #-- throw "shp1: got invalid attrib in packet. should never happen because dumpBatch() should check this before calling dumpPacket()"
                            #-- ignore unknown types, it's enough to warn() in dumpBatch
                    # end for k = 0 to attribs.count

                    if len(curPrimative.points) <= j:
                        curPrimative.points.append(None)
                    curPrimative.points[j] = curPoint
                # for j = 1 to count do
            # -- end else (type == 0 || readBytes >= dataSize) then
         # -- end while not done do

    def DumpPacketPrimitives(self, attribs, bw):
        writtenBytes = 0

        if not self.primitives:
            return 0  # empty packet

        for curPrimative in self.primitives:
            bw.writeByte(curPrimative.type)
            writtenBytes += 1

            bw.writeWord(len(curPrimative.points))
            writtenBytes += 2
            for curPoint in curPrimative.points:
                for k in range(len(attribs)):
                    # -- set appropriate index
                    if attribs[k].attrib == 0:
                        val = curPoint.matrixIndex
                    elif attribs[k].attrib == 9:
                        val = curPoint.posIndex
                    elif attribs[k].attrib == 0xa:
                        val = curPoint.normalIndex
                    elif attribs[k].attrib == 0xb or attribs[k].attrib == 0xc:
                        while len(curPoint.colorIndex) < 2:
                            curPoint.colorIndex.append(None)
                        val = curPoint.colorIndex[(attribs[k].attrib - 0xb)]  # fixed
                    elif 0xd <= attribs[k].attrib <= 0x14:
                        while len(curPoint.texCoordIndex) < 8:
                            curPoint.texCoordIndex.append(None)
                        val = curPoint.texCoordIndex[(attribs[k].attrib - 0xd)]  # fixed
                    else:
                        log.error("impossible SHP attribute %d", attribs[k].attrib)
                        if common.GLOBALS.PARANOID:
                            raise ValueError('~the dev was an idiot~')

                    if val is None:
                        val = 0  # default for missing attribute data

                    if attribs[k].dataType == 1:  # -- s8
                        bw.writeByte(val)
                        writtenBytes += 1
                    elif attribs[k].dataType == 3:  # -- s16
                        bw.writeWord(val)
                        writtenBytes += 2
                    else:
                        log.error("shp1: invalid data type %d", attribs[k].dataType)
                        if common.GLOBALS.PARANOID:
                            raise ValueError("ERROR")
                        # -- messageBox "WARNING shp1: got invalid attrib in packet. should never happen because dumpBatch() should check this before calling dumpPacket()"
                        # --print curPrimative
                        # -- throw "shp1: got invalid attrib in packet. should never happen because dumpBatch() should check this before calling dumpPacket()"
                        # -- ignore unknown types, it's enough to warn() in dumpBatch
        bw.writeByte(0)  # create the incomplete 'termination primitive'
        writtenBytes += 1

        return writtenBytes
# ---------------------------------------------------------------------------------------------------------------------


class ShpAttributes:
    # <variable hasMatrixIndices>
    # <variable hasPositions>
    # <variable hasNormals>
    # -- bool
    # <variable hasColors>
    # -- bool[2]
    # <variable hasTexCoords>
    # -- bool[8];
    def __init__(self):  # GENERATED!
        self.hasColors = [False]*2  # Bools[2]
        self.hasTexCoords = [False]*8  # Bools[8]



class ShpBatch:
    def __init__(self):  # GENERATED!
        self.attribs = ShpAttributes()
        self.packets = None


class Shp1BatchDescriptor:
    size = 40
    def __init__(self):  # GENERATED!
        self.unknown4 = []

    def LoadData(self, br):
        self.unknown = br.ReadWORD()
        # seems to be always 0x00ff ("matrix type, unk")
        self.packetCount = br.ReadWORD()
        # u16 number of packets belonging to this batch
        # attribs used for the strips in this batch. relative to
        # Shp1Header.offsetToBatchAttribs
        # Read StripTypes until you encounter an 0x000000ff/0x00000000,
        # for all these types indices are included. If, for example,
        # a Batch has types (9, 3), (a, 3), (0xff, 0), then for this batch two shorts (= 3)
        # are stored per vertex: position index and normal index
        self.offsetToAttribs = br.ReadWORD()
        self.firstMatrixData = br.ReadWORD()  # index to first matrix data (packetCount consecutive indices)
        self.firstPacketLocation = br.ReadWORD()  # index to first packet position (packetCount consecutive indices)
        self.unknown3 = br.ReadWORD()  # 0xffff
        for _ in range(7):
            self.unknown4.append(br.GetFloat())
        # great... (seems to match the last 7 floats of joint info sometimes)
        # (one unknown float, 6 floats bounding box?)

    def DumpData(self, bw):
        bw.writeWord(self.unknown)
        bw.writeWord(self.packetCount)
        bw.writeWord(self.offsetToAttribs)
        bw.writeWord(self.firstMatrixData)
        bw.writeWord(self.firstPacketLocation)
        bw.writeWord(0xffff)
        for i in range(7):
            bw.writeFloat(self.unknown4[i] if i < len(self.unknown4) else 0.0)


class Shp1Header:
    size = 44
    def __init__(self):  # GENERATED!
        pass

    def LoadData(self, br):
        self.tag = br.ReadFixedLengthString(4)
        self.sizeOfSection = br.ReadDWORD()
        self.batchCount = br.ReadWORD()
        self.pad = br.ReadWORD()
        self.offsetToBatches = br.ReadDWORD()
        self.offsetUnknown = br.ReadDWORD()
        self.zero = br.ReadDWORD()
        self.offsetToBatchAttribs = br.ReadDWORD()
        # batch vertex attrib start
        # The matrixTable is an array of u16, which maps from the matrix data indices
        # to Drw1Data arrays indices. If a batch contains multiple packets, for the
        # 2nd, 3rd, ... packet this array may contain 0xffff values, which means that
        # the corresponding index from the previous packet should be used.
        self.offsetToMatrixTable = br.ReadDWORD()

        self.offsetData = br.ReadDWORD()
        # start of the actual primitive data
        self.offsetToMatrixData = br.ReadDWORD()
        self.offsetToPacketLocations = br.ReadDWORD()
        # u32 offset to packet start/length info
        # (all offsets relative to Shp1Header start)

    def DumpData(self, bw):
        bw.writeString("SHP1")
        bw.writeDword(self.sizeOfSection)
        bw.writeWord(self.batchCount)
        bw.writeWord(self.pad)
        bw.writeDword(self.offsetToBatches)
        bw.writeDword(self.offsetUnknown)
        bw.writeDword(self.zero)
        bw.writeDword(self.offsetToBatchAttribs)
        # batch vertex attrib start
        # The matrixTable is an array of u16, which maps from the matrix data indices
        # to Drw1Data arrays indices. If a batch contains multiple packets, for the
        # 2nd, 3rd, ... packet this array may contain 0xffff values, which means that
        # the corresponding index from the previous packet should be used.
        bw.writeDword(self.offsetToMatrixTable)

        bw.writeDword(self.offsetData)
        # start of the actual primitive data
        bw.writeDword(self.offsetToMatrixData)
        bw.writeDword(self.offsetToPacketLocations)
        # u32 offset to packet start/length info
        # (all offsets relative to Shp1Header start)
# ---------------------------------------------------------------------------------------------------------------------


class Shp1BatchAttrib:
    size = 8
    def __init__(self):  # GENERATED!
        pass

    def LoadData(self, br):

        self.attrib = br.ReadDWORD()
        # cf. ArrayFormat.arrayType
        self.dataType= br.ReadDWORD()
        # cf. ArrayFormat.dataType (always bytes or shorts...)

        ###########################################
        # for every packet a PacketLocation struct is stored at
        # Shp1Header.offsetToPacketLocation + Batch.firstPacketLocation*sizeof(PacketLocation).
        # This struct stores where the primitive data for this packet is stored in the
        # data block.

    def DumpData(self, bw):
        bw.writeDword(self.attrib)
        bw.writeDword(self.dataType)


class Shp1PacketLocation:
    size = 8
    def __init__(self):  # GENERATED!
        pass

    def LoadData(self, br):
        self.packetSize = br.ReadDWORD()  # size in bytes of packet
        self.offset = br.ReadDWORD()  # relative to Shp1Header.offsetData

    def DumpData(self, bw):
        bw.writeDword(self.packetSize)  # size in bytes of packet
        bw.writeDword(self.offset)  # relative to Shp1Header.offsetData
#---------------------------------------------------------------------------------------------------------------------


class Shp1MatrixData:
    size = 8
    def __init__(self):  # GENERATED!
        pass

    def LoadData(self, br):
        # from yaz0r's source (animation stuff)
        self.unknown1 = br.ReadWORD()
        # TODO: figure this out... 0xffff is a valid value: probably means "keep last instance", but for what?
        self.count = br.ReadWORD()
        # count many consecutive indices into matrixTable
        self.firstIndex = br.ReadDWORD()
        # first index into matrix table

    def DumpData(self, bw):
        # from yaz0r's source (animation stuff)
        bw.writeWord(self.unknown1)
        bw.writeWord(self.count)
        # count many consecutive indices into matrixTable
        bw.writeDword(self.firstIndex)
        # first index into matrix table
# ---------------------------------------------------------------------------------------------------------------------


class Shp1:
    def __init__(self):  # GENERATED!
        self.batches = []

        self.all_attribs = []
        self.all_p_locs = []
        self.matrices_data = []
        self.matrices_table = []
        self._rawSectionData = None

    def GetBatchAttribs(self, br, offset):

        origPos = br.Position()
        br.SeekSet(offset)
        batchAttribs = []
        # -- of type Shp1BatchAttrib
        attrib = Shp1BatchAttrib()
        attrib.LoadData(br)

        while attrib.attrib != 0xff:
            batchAttribs.append(attrib)
            attrib = Shp1BatchAttrib()
            attrib.LoadData(br)

        br.SeekSet(origPos)

        return batchAttribs

    def makeBatch(self, br, batchSrc, header, baseOffset, dst):

        # -- read and interpret batch vertex attribs
        attribs = self.GetBatchAttribs(br, baseOffset + header.offsetToBatchAttribs + batchSrc.offsetToAttribs)

        dst.attribs.hasMatrixIndices = False
        dst.attribs.hasPositions = False
        dst.attribs.hasNormals = False


        for i in range(len(attribs)):
            if attribs[i].dataType not in (1, 3):
                # --print "Warning: shp1, dumpBatch(): unknown attrib data type %d, skipping batch"
                log.warning("shp1, dumpBatch(): unknown attrib data type %d, skipping batch")
                return None

            if attribs[i].attrib == 0:
                dst.attribs.hasMatrixIndices = True
            elif attribs[i].attrib == 9:
                dst.attribs.hasPositions = True
            elif attribs[i].attrib == 0xa:
                dst.attribs.hasNormals = True
            elif attribs[i].attrib == 0xb or attribs[i].attrib == 0xc:
                dst.attribs.hasColors[(attribs[i].attrib - 0xb)] = True  # fixed
            elif attribs[i].attrib >= 0xd and attribs[i].attrib <= 0x14:
                dst.attribs.hasTexCoords[(attribs[i].attrib - 0xd)] = True  # fixed
            else:
                log.warning("shp1, dumpBatch(): unknown attrib %d in batch, it might not display correctly")
                # -- return; //it's enough to warn
        # -- end for i=1 to attribs.count do

        # -- read packets
        dst.packets = []
        # -- dst.packets.resize(batch.packetCount);
        for i in range(batchSrc.packetCount):
            br.SeekSet(baseOffset + header.offsetToPacketLocations +
                       (batchSrc.firstPacketLocation + i)*8)  # -- sizeof(packetLocation) = 8
            packetLoc = Shp1PacketLocation()
            packetLoc.LoadData(br)

            # -- read packet's primitives
            dstPacket = ShpPacket()
            br.SeekSet(baseOffset + header.offsetData + packetLoc.offset)
            dstPacket.LoadPacketPrimitives(attribs, packetLoc.packetSize, br)
            # Preserve original packet size (includes padding) for round-trip
            dstPacket._originalPacketSize = packetLoc.packetSize
            if len(dst.packets) <= i:
                dst.packets.append(None)
            dst.packets[i] = dstPacket

            # -- read matrix data for current packet
            matrixData = Shp1MatrixData()
            br.SeekSet(baseOffset + header.offsetToMatrixData + (batchSrc.firstMatrixData + i)*matrixData.size)
            matrixData.LoadData(br)

            # Preserve useMtxIndex for round-trip
            dstPacket._useMtxIndex = matrixData.unknown1

            # -- read packet's matrix table
            # --dstPacket.matrixTable.resize(matrixData.count);
            dstPacket.matrixTable = [None] * matrixData.count
            br.SeekSet(baseOffset + header.offsetToMatrixTable + 2*matrixData.firstIndex)

            for j in range(matrixData.count):
                dstPacket.matrixTable[j] = br.ReadWORD()
            # --print (dstPacket.matrixTable.count as string) -- matrixTable
            # --print (dstPacket.matrixTable[1] as string)
    # end for i=1 to batchSrc.packetCount do

    def decomposeBatch(self, bww, batch, header, baseOffset, batchDst):

        # Use preserved descriptor values from import if available
        orig_desc = getattr(batch, '_descriptor', None)

        if orig_desc is not None:
            batchDst.unknown = orig_desc.unknown
            batchDst.unknown4 = orig_desc.unknown4
        else:
            # Reconstructed batch: compute from flags
            is_rigid = getattr(batch, '_is_rigid', not batch.attribs.hasMatrixIndices)
            batchDst.unknown = 0x00ff if is_rigid else 0x03ff
            batchDst.unknown4 = getattr(batch, '_bbox', [0.0] * 7)

        batch.raw_attribs = attribs = []

        if batch.attribs.hasMatrixIndices:
            attrib = Shp1BatchAttrib()
            attrib.attrib = 0
            attrib.dataType = 1
            attribs.append(attrib)
        if batch.attribs.hasPositions:
            attrib = Shp1BatchAttrib()
            attrib.attrib = 9
            attrib.dataType = 3
            attribs.append(attrib)
        if batch.attribs.hasNormals:
            attrib = Shp1BatchAttrib()
            attrib.attrib = 0xa
            attrib.dataType = 3
            attribs.append(attrib)
        for i in (0, 1):
            if batch.attribs.hasColors[i]:
                attrib = Shp1BatchAttrib()
                attrib.attrib = 0xb+i
                attrib.dataType = 3
                attribs.append(attrib)
        for i in range(8):
            if batch.attribs.hasTexCoords[i]:
                attrib = Shp1BatchAttrib()
                attrib.attrib = 0xd + i
                attrib.dataType = 3
                attribs.append(attrib)

        # Deduplicate attrib lists: check if an identical list already exists
        attrib_sig = tuple((a.attrib, a.dataType) for a in attribs)
        if not hasattr(self, '_attrib_cache'):
            self._attrib_cache = {}  # signature -> byte offset

        if attrib_sig in self._attrib_cache:
            batchDst.offsetToAttribs = self._attrib_cache[attrib_sig]
        else:
            batchDst.offsetToAttribs = len(self.all_attribs) * Shp1BatchAttrib.size
            self._attrib_cache[attrib_sig] = batchDst.offsetToAttribs

            # Separator goes into all_attribs (for the batch attribute table in the file)
            # but NOT into batch.raw_attribs (which is passed to DumpPacketPrimitives)
            separator = Shp1BatchAttrib()
            separator.attrib = 0xff
            separator.dataType = 0x00

            self.all_attribs += attribs
            self.all_attribs.append(separator)

        batchDst.firstMatrixData = len(self.matrices_data)

        batch.p_locs = p_locs = []  # give the batch a reference for future completion

        batchDst.packetCount = len(batch.packets)
        batchDst.firstPacketLocation = len(self.all_p_locs)

        for i in range(len(batch.packets)):
            packet = batch.packets[i]

            packetLoc = Shp1PacketLocation()
            p_locs.append(packetLoc)

            matrixData = Shp1MatrixData()

            # useMtxIndex: For rigid batches (J3DShapeMtx), this IS the DRW1
            # index used by load() — it MUST be correct or the wrong bone matrix
            # gets applied. For weighted batches (J3DShapeMtxMulti), load() uses
            # the packet matrix table instead, so this value is less critical.
            if hasattr(packet, '_useMtxIndex'):
                matrixData.unknown1 = packet._useMtxIndex
            elif packet.matrixTable:
                matrixData.unknown1 = packet.matrixTable[0]
            else:
                matrixData.unknown1 = 0
            matrixData.count = len(packet.matrixTable)

            self.matrices_data.append(matrixData)

            matrixData.firstIndex = len(self.matrices_table)

            for j in range(matrixData.count):
                self.matrices_table.append(packet.matrixTable[j])

        self.all_p_locs += p_locs

    @staticmethod
    def _get_vert_drw_index(vert, vgroup_to_drw):
        """Get the DRW1 rigid index for a vertex based on its heaviest vertex group.

        Returns the DRW1 index if the heaviest group has a rigid entry,
        or None if no rigid entry exists (vertex must go into a weighted batch).
        """
        if vert.groups:
            best_group = max(vert.groups, key=lambda g: g.weight)
            drw_idx = vgroup_to_drw.get(best_group.group, None)
            return drw_idx
        return None

    _drw_fallback_count = 0
    _drw_fallback_logged = 0

    @staticmethod
    def _get_vert_drw_index_weighted(vert, vgroup_to_drw, bone_set_to_drw_candidates,
                                      bone_to_any_weighted_drw, vgroup_to_bone_idx):
        """Get the correct DRW1 index for a vertex in a weighted batch.

        Single bone → rigid DRW entry (bone-local position).
        Multiple bones → find weighted DRW entry matching the bone combination
        via EVP1 envelope lookup.
        """
        if not vert.groups:
            return 0

        sig_groups = [(g.group, g.weight) for g in vert.groups if g.weight > 0.001]

        if len(sig_groups) == 1:
            # Single bone — use rigid DRW entry
            rigid = vgroup_to_drw.get(sig_groups[0][0], None)
            if rigid is not None:
                return rigid

        # Multiple bones (or single bone without rigid entry):
        # Find weighted DRW entry by matching bone set against EVP1 envelopes
        bone_indices = frozenset(
            vgroup_to_bone_idx[g] for g, w in sig_groups
            if g in vgroup_to_bone_idx
        )

        # Find DRW entry matching bone set AND closest weights.
        # Multiple DRW entries can share the same bone set with different weights.
        candidates = bone_set_to_drw_candidates.get(bone_indices)
        if candidates:
            if len(candidates) == 1:
                return candidates[0][0]
            # Build vertex weight map for comparison
            vert_weights = {}
            for vg_idx, w in sig_groups:
                bi = vgroup_to_bone_idx.get(vg_idx)
                if bi is not None:
                    vert_weights[bi] = w
            # Pick candidate with smallest total weight difference
            best_drw = candidates[0][0]
            best_diff = float('inf')
            for drw_idx, cand_weights in candidates:
                diff = sum(abs(vert_weights.get(bi, 0) - cand_weights.get(bi, 0))
                          for bi in set(vert_weights) | set(cand_weights))
                if diff < best_diff:
                    best_diff = diff
                    best_drw = drw_idx
            return best_drw

        # DEBUG: log fallback cases
        Shp1._drw_fallback_count += 1
        if Shp1._drw_fallback_logged < 30:
            Shp1._drw_fallback_logged += 1
            bone_names_str = sorted(bone_indices) if bone_indices else "empty"
            all_groups = [(g.group, g.weight, vgroup_to_bone_idx.get(g.group, '?'))
                         for g in vert.groups]
            avail_sets = [sorted(bs) for bs in bone_set_to_drw_candidates.keys()]
            log.warning("DRW FALLBACK #%d: vert %d, %d sig_groups, bone_set=%s, "
                       "all_groups=%s, available_sets=%s",
                       Shp1._drw_fallback_count, vert.index, len(sig_groups),
                       bone_names_str, all_groups, avail_sets[:10])

        # Fallback: find the BEST matching EVP envelope by bone set similarity,
        # rather than falling back to rigid (which creates a transform mismatch).
        # Strategy: find the envelope whose bone set has the most overlap with
        # the vertex's bone set, weighted by the vertex's bone weights.
        if bone_indices and bone_set_to_drw_candidates:
            best_drw = None
            best_score = -1
            for cand_bones, cand_list in bone_set_to_drw_candidates.items():
                overlap = bone_indices & cand_bones
                if not overlap:
                    continue
                # Score = sum of vertex weights for overlapping bones
                score = sum(w for g, w in sig_groups
                           if g in vgroup_to_bone_idx and vgroup_to_bone_idx[g] in overlap)
                if score > best_score:
                    best_score = score
                    # Pick the candidate with closest weights from this bone set
                    vert_weights = {}
                    for vg_idx, w in sig_groups:
                        bi = vgroup_to_bone_idx.get(vg_idx)
                        if bi is not None:
                            vert_weights[bi] = w
                    best_diff = float('inf')
                    for drw_idx, cand_weights in cand_list:
                        diff = sum(abs(vert_weights.get(bi, 0) - cand_weights.get(bi, 0))
                                  for bi in set(vert_weights) | set(cand_weights))
                        if diff < best_diff:
                            best_diff = diff
                            best_drw = drw_idx
            if best_drw is not None:
                return best_drw

        # Last resort fallback: rigid entry for heaviest bone
        if sig_groups:
            best_vg = max(sig_groups, key=lambda x: x[1])[0]
            rigid = vgroup_to_drw.get(best_vg)
            if rigid is not None:
                return rigid
            # Try any weighted DRW referencing the heaviest bone
            bi = vgroup_to_bone_idx.get(best_vg)
            if bi is not None:
                drw = bone_to_any_weighted_drw.get(bi)
                if drw is not None:
                    return drw

        return 0

    @staticmethod
    def PrecomputeVertexDRW(mesh_obj, drw1, evp1, batch_order):
        """Pre-compute per-vertex DRW1 assignment for all vertices.

        This determines, for each vertex, whether it will use a rigid or
        weighted DRW entry, and which one. Both VTX1 (inverse skinning)
        and SHP1 (matrix indices) must use the same assignment.

        Returns:
            vert_drw: dict mapping blender vertex index -> drw1 index (or None)
            mat_classification: dict mapping material_index -> (is_rigid, drw_idx, bone_idx)
        """
        mesh = mesh_obj.data
        mesh.calc_loop_triangles()

        has_armature = (hasattr(mesh_obj, 'parent') and mesh_obj.parent is not None
                        and mesh_obj.parent.type == 'ARMATURE')

        bone_names = []
        vgroup_to_drw = {}
        vgroup_to_bone_idx = {}
        bone_set_to_drw_candidates = {}
        bone_to_any_weighted_drw = {}

        if has_armature and mesh_obj.vertex_groups:
            arm_obj = mesh_obj.parent
            bone_names = [b.name for b in arm_obj.data.bones]

            # Rigid DRW mapping: vgroup -> DRW1 rigid entry
            for vg in mesh_obj.vertex_groups:
                if vg.name in bone_names:
                    bone_idx = bone_names.index(vg.name)
                    vgroup_to_bone_idx[vg.index] = bone_idx
                    for di, (isW, data_val) in enumerate(zip(drw1.isWeighted, drw1.data)):
                        if not isW and data_val == bone_idx:
                            vgroup_to_drw[vg.index] = di
                            break

            # Weighted DRW mapping: bone set -> DRW1 weighted candidates
            if evp1 is not None:
                for di, (isW, data_val) in enumerate(zip(drw1.isWeighted, drw1.data)):
                    if isW and data_val < len(evp1.weightedIndices):
                        mm = evp1.weightedIndices[data_val]
                        bone_key = frozenset(mm.indices)
                        weight_map = {mm.indices[i]: mm.weights[i]
                                     for i in range(len(mm.indices))}
                        if bone_key not in bone_set_to_drw_candidates:
                            bone_set_to_drw_candidates[bone_key] = []
                        bone_set_to_drw_candidates[bone_key].append((di, weight_map))
                        for bi in mm.indices:
                            if bi not in bone_to_any_weighted_drw:
                                bone_to_any_weighted_drw[bi] = di

        # Classify materials (rigid vs weighted)
        mat_triangles = {}
        for lt in mesh.loop_triangles:
            mi = lt.material_index
            if mi not in mat_triangles:
                mat_triangles[mi] = []
            mat_triangles[mi].append(lt)

        mat_classification = {}
        for mat_idx in (batch_order if batch_order else sorted(mat_triangles.keys())):
            triangles = mat_triangles.get(mat_idx, [])
            is_rigid, drw_idx = Shp1._classify_batch_majority(
                mesh, triangles, vgroup_to_drw)
            if is_rigid and drw_idx is not None and drw_idx < len(drw1.data):
                bone_idx = drw1.data[drw_idx]
                mat_classification[mat_idx] = (True, drw_idx, bone_idx)
            else:
                mat_classification[mat_idx] = (False, None, None)

        # Compute per-vertex DRW assignment
        # For rigid batches: all vertices use the batch's single DRW entry
        # For weighted batches: each vertex gets its own DRW via envelope matching
        vert_drw = {}  # vert_index -> (drw_idx, is_weighted_drw, evp_idx_or_bone_idx)

        for mat_idx, (is_rigid, batch_drw, batch_bone) in mat_classification.items():
            triangles = mat_triangles.get(mat_idx, [])
            seen = set()
            for lt in triangles:
                for vi in lt.vertices:
                    if vi in seen:
                        continue
                    seen.add(vi)

                    if is_rigid:
                        # All verts in rigid batch use the batch bone
                        vert_drw[vi] = (batch_drw, False, batch_bone)
                    else:
                        # Weighted: find best DRW for this vertex
                        vert = mesh.vertices[vi]
                        drw_idx = Shp1._get_vert_drw_index_weighted(
                            vert, vgroup_to_drw, bone_set_to_drw_candidates,
                            bone_to_any_weighted_drw, vgroup_to_bone_idx)
                        if drw_idx is not None and drw_idx < len(drw1.isWeighted):
                            is_w = drw1.isWeighted[drw_idx]
                            data_val = drw1.data[drw_idx]
                            vert_drw[vi] = (drw_idx, bool(is_w), data_val)
                        else:
                            vert_drw[vi] = (0, False, 0)

        return vert_drw, mat_classification

    @staticmethod
    def ClassifyMaterials(mesh_obj, drw1, batch_order):
        """Pre-compute per-material bone assignment for VTX1 transform.

        Returns dict: material_index -> (is_rigid, drw_index_or_None, bone_index_or_None)
        For rigid materials, bone_index is the JNT1 bone whose inverse transform
        should be applied to ALL vertices in that material (not just single-bone ones).
        For weighted materials, bone_index is None (no transform).
        """
        mesh = mesh_obj.data
        mesh.calc_loop_triangles()

        has_armature = (hasattr(mesh_obj, 'parent') and mesh_obj.parent is not None
                        and mesh_obj.parent.type == 'ARMATURE')

        vgroup_to_drw = {}
        if has_armature and mesh_obj.vertex_groups:
            arm_obj = mesh_obj.parent
            bone_names = [b.name for b in arm_obj.data.bones]
            for vg in mesh_obj.vertex_groups:
                if vg.name in bone_names:
                    bone_idx = bone_names.index(vg.name)
                    for di, (isW, data_val) in enumerate(zip(drw1.isWeighted, drw1.data)):
                        if not isW and data_val == bone_idx:
                            vgroup_to_drw[vg.index] = di
                            break

        # Group triangles by material
        mat_triangles = {}
        for lt in mesh.loop_triangles:
            mi = lt.material_index
            if mi not in mat_triangles:
                mat_triangles[mi] = []
            mat_triangles[mi].append(lt)

        result = {}
        for mat_idx in (batch_order if batch_order else sorted(mat_triangles.keys())):
            triangles = mat_triangles.get(mat_idx, [])
            is_rigid, drw_idx = Shp1._classify_batch_majority(mesh, triangles, vgroup_to_drw)
            if is_rigid and drw_idx is not None and drw_idx < len(drw1.data):
                bone_idx = drw1.data[drw_idx]
                result[mat_idx] = (True, drw_idx, bone_idx)
            else:
                result[mat_idx] = (False, None, None)

        return result

    @staticmethod
    def _classify_batch_majority(mesh, triangles, vgroup_to_drw):
        """Classify a batch as rigid or weighted.

        Count vertices with exactly 1 significant bone group vs multiple.
        A batch is RIGID only if ALL vertices are single-bone (no multi-bone
        vertices at all). If any vertex has multiple significant bone groups,
        the batch is WEIGHTED. This matches how the original BMD format works:
        rigid batches have no per-vertex matrix index, so every vertex must
        share the same bone transform.

        Returns (is_rigid, most_common_drw_index_or_None).
        For rigid batches, most_common_drw_index is the DRW1 index used by
        the most vertices (single matrix table entry).
        """
        from collections import Counter
        single_count = 0
        multi_count = 0
        rigid_drw_counter = Counter()
        seen_verts = set()

        for lt in triangles:
            for vi in lt.vertices:
                if vi in seen_verts:
                    continue
                seen_verts.add(vi)
                vert = mesh.vertices[vi]
                sig_groups = [g for g in vert.groups if g.weight > 0.001]
                if len(sig_groups) <= 1:
                    single_count += 1
                    drw_idx = Shp1._get_vert_drw_index(vert, vgroup_to_drw)
                    if drw_idx is not None:
                        rigid_drw_counter[drw_idx] += 1
                else:
                    multi_count += 1

        total = single_count + multi_count
        if total == 0:
            return True, 0  # empty batch, treat as rigid

        # Rigid if majority are single-bone AND they all agree on ONE DRW entry.
        # If single-bone vertices reference multiple different DRW entries,
        # the batch needs per-vertex matrix selection = weighted.
        num_unique_drw = len(rigid_drw_counter)
        is_rigid = (single_count >= multi_count and num_unique_drw <= 1)
        if is_rigid:
            if rigid_drw_counter:
                most_common_drw = rigid_drw_counter.most_common(1)[0][0]
            else:
                most_common_drw = 0
            return True, most_common_drw
        else:
            return False, None

    @staticmethod
    def _compute_bounding_box(mesh, triangles, vtx1):
        """Compute bounding box from vertex positions in GC space.

        Returns (unknown_float, bbMin[3], bbMax[3]) — 7 floats total for batch descriptor.
        """
        min_x = min_y = min_z = float('inf')
        max_x = max_y = max_z = float('-inf')
        seen_verts = set()
        for lt in triangles:
            for vi in lt.vertices:
                if vi in seen_verts:
                    continue
                seen_verts.add(vi)
                # Use Blender vertex position, convert to GC: (x, z, -y)
                v = mesh.vertices[vi].co
                gc_x, gc_y, gc_z = v.x, v.z, -v.y
                min_x = min(min_x, gc_x)
                min_y = min(min_y, gc_y)
                min_z = min(min_z, gc_z)
                max_x = max(max_x, gc_x)
                max_y = max(max_y, gc_y)
                max_z = max(max_z, gc_z)
        if min_x == float('inf'):
            return [0.0] * 7
        # unknown float, then bbMin xyz, bbMax xyz
        unknown = max(abs(max_x - min_x), abs(max_y - min_y), abs(max_z - min_z))
        return [unknown, min_x, min_y, min_z, max_x, max_y, max_z]

    @staticmethod
    def _split_into_packets(triangles, mesh, vgroup_to_drw, bone_set_to_drw_candidates, bone_to_any_weighted_drw, vgroup_to_bone_idx, max_bones=10):
        """Split triangles into packets, each using at most max_bones unique DRW1 indices.

        Returns list of (tri_list, drw_index_list) tuples.
        """
        # Collect per-triangle bone sets
        tri_bones = []
        for lt in triangles:
            bones = set()
            for vi in lt.vertices:
                vert = mesh.vertices[vi]
                drw_idx = Shp1._get_vert_drw_index_weighted(vert, vgroup_to_drw, bone_set_to_drw_candidates, bone_to_any_weighted_drw, vgroup_to_bone_idx)
                bones.add(drw_idx)
            tri_bones.append((lt, bones))

        packets = []
        remaining = list(tri_bones)

        while remaining:
            packet_tris = []
            packet_bones = set()

            # Greedy: add triangles that fit within bone limit
            still_remaining = []
            for lt, bones in remaining:
                combined = packet_bones | bones
                if len(combined) <= max_bones:
                    packet_tris.append(lt)
                    packet_bones = combined
                else:
                    still_remaining.append((lt, bones))

            if not packet_tris:
                # Force-add the first remaining triangle even if it exceeds the limit
                # (shouldn't happen with max_bones=10 and tris having 1-3 bones each)
                lt, bones = still_remaining.pop(0)
                packet_tris.append(lt)
                packet_bones = bones

            packets.append((packet_tris, sorted(packet_bones)))
            remaining = still_remaining

        return packets

    @staticmethod
    def FromBlenderMesh(mesh_obj, vtx1, loop_indices, drw1, batch_order=None, evp1=None):
        """Reconstruct SHP1 from a Blender mesh, VTX1 pools, and loop index mapping.

        Each material gets ONE batch. Batches are classified as rigid or weighted
        using majority vote: if >50% of vertices have exactly 1 significant bone
        group, the batch is RIGID; otherwise WEIGHTED.

        Rigid batches: hasMatrixIndices=False, _is_rigid=True, mattype=0x00.
        ONE packet with ONE matrix table entry = the most common rigid DRW1 index.
        All vertices use this bone transform (no per-vertex matrixIndex).

        Weighted batches: hasMatrixIndices=True, _is_rigid=False, mattype=0x03.
        Packets split by 10-bone limit. Each vertex has matrixIndex.

        Batches are NOT sorted — they follow material index order (or batch_order).

        Args:
            mesh_obj: Blender mesh object
            vtx1: Vtx1 instance with populated pools
            loop_indices: dict from Vtx1.FromBlenderMesh, mapping loop_idx to indices
            drw1: Drw1 instance (for matrix table references)
            batch_order: optional list of Blender material indices, one per batch,
                         in the order the INF1 scene graph expects. If provided,
                         batches are produced in this exact order. If None, batches
                         are sorted by material index.

        Returns a new Shp1 instance ready for DumpData.
        """
        mesh = mesh_obj.data
        mesh.calc_loop_triangles()

        shp = Shp1()
        shp._rawSectionData = None  # force reconstruction path

        # Determine which attributes are present
        num_uv_layers = min(len(mesh.uv_layers), 8)
        color_attrs = []
        if hasattr(mesh, 'color_attributes'):
            color_attrs = [ca for ca in mesh.color_attributes if ca.domain == 'CORNER']
        elif hasattr(mesh, 'vertex_colors'):
            color_attrs = list(mesh.vertex_colors)
        num_color_layers = min(len(color_attrs), 2)

        has_normals = len(vtx1.normals) > 0
        has_armature = (hasattr(mesh_obj, 'parent') and mesh_obj.parent is not None
                        and mesh_obj.parent.type == 'ARMATURE')

        # Build vertex group -> DRW1 rigid index mapping
        # (vgroup blender index -> DRW1 index for rigid entries)
        vgroup_to_drw = {}
        bone_names = []
        if has_armature and mesh_obj.vertex_groups:
            arm_obj = mesh_obj.parent
            bone_names = [b.name for b in arm_obj.data.bones]
            log.info("SHP1 FromBlenderMesh: bone_names = %s", bone_names)
            log.info("SHP1 FromBlenderMesh: DRW1 has %d entries (%d rigid)",
                     len(drw1.isWeighted),
                     sum(1 for w in drw1.isWeighted if not w))
            for vg in mesh_obj.vertex_groups:
                if vg.name in bone_names:
                    bone_idx = bone_names.index(vg.name)
                    found = False
                    for di, (isW, data_val) in enumerate(zip(drw1.isWeighted, drw1.data)):
                        if not isW and data_val == bone_idx:
                            vgroup_to_drw[vg.index] = di
                            log.info("  vgroup[%d] '%s' -> bone_idx=%d -> DRW1[%d]",
                                     vg.index, vg.name, bone_idx, di)
                            found = True
                            break
                    if not found:
                        log.info("  vgroup[%d] '%s' -> bone_idx=%d -> no rigid DRW1 entry",
                                 vg.index, vg.name, bone_idx)

        # Build weighted DRW1 lookup: maps frozenset of bone indices -> list of
        # (DRW1_index, {bone_idx: weight}) candidates. Multiple DRW entries can
        # share the same bone set but have different weight distributions.
        # We pick the closest weight match for each vertex.
        bone_set_to_drw_candidates = {}  # frozenset(bone_indices) -> [(drw_idx, {bone: weight}), ...]
        bone_to_any_weighted_drw = {}  # single bone_idx -> first weighted DRW1 that references it
        if has_armature and evp1 is not None:
            for di, (isW, data_val) in enumerate(zip(drw1.isWeighted, drw1.data)):
                if isW and data_val < len(evp1.weightedIndices):
                    mm = evp1.weightedIndices[data_val]
                    bone_key = frozenset(mm.indices)
                    weight_map = {mm.indices[i]: mm.weights[i] for i in range(len(mm.indices))}
                    if bone_key not in bone_set_to_drw_candidates:
                        bone_set_to_drw_candidates[bone_key] = []
                    bone_set_to_drw_candidates[bone_key].append((di, weight_map))
                    for bi in mm.indices:
                        if bi not in bone_to_any_weighted_drw:
                            bone_to_any_weighted_drw[bi] = di

        # Map vgroup_index -> bone_index for ALL bones (not just rigid-mapped ones)
        vgroup_to_bone_idx = {}
        if has_armature and mesh_obj.vertex_groups:
            for vg in mesh_obj.vertex_groups:
                if vg.name in bone_names:
                    vgroup_to_bone_idx[vg.index] = bone_names.index(vg.name)

        # ---- Group triangles by material index ----
        mat_triangles = {}  # mat_idx -> [loop_triangle]
        for lt in mesh.loop_triangles:
            mi = lt.material_index
            if mi not in mat_triangles:
                mat_triangles[mi] = []
            mat_triangles[mi].append(lt)

        # Determine batch ordering.
        # If batch_order is provided (from INF1 scene graph), use it exactly.
        # Otherwise fall back to sorted material indices.
        if batch_order is not None:
            all_mat_indices = list(batch_order)
            log.info("SHP1 FromBlenderMesh: using INF1 batch order: %s", all_mat_indices)
        else:
            valid_mat_indices = set()
            for mi in range(len(mesh.materials)):
                mat = mesh.materials[mi]
                if mat and mat.name.startswith("ERROR"):
                    continue
                valid_mat_indices.add(mi)
            valid_mat_indices.update(mat_triangles.keys())
            all_mat_indices = sorted(valid_mat_indices)

        log.info("SHP1 FromBlenderMesh: %d batches, %d materials",
                 len(all_mat_indices), len(mesh.materials))

        # ---- Build one batch per material ----
        shp._batch_material_indices = []

        for mat_idx in all_mat_indices:
            triangles = mat_triangles.get(mat_idx, [])

            batch = ShpBatch()
            shp._batch_material_indices.append(mat_idx)

            # Classify batch using majority vote
            is_rigid, rigid_drw_idx = Shp1._classify_batch_majority(
                mesh, triangles, vgroup_to_drw)

            # Set attribute flags
            batch.attribs = ShpAttributes()
            batch.attribs.hasPositions = True
            batch.attribs.hasNormals = has_normals
            for uv in range(num_uv_layers):
                batch.attribs.hasTexCoords[uv] = True
            for ci in range(num_color_layers):
                batch.attribs.hasColors[ci] = True

            batch._bbox = Shp1._compute_bounding_box(mesh, triangles, vtx1)

            if is_rigid:
                # ---- RIGID BATCH ----
                batch.attribs.hasMatrixIndices = False
                batch._is_rigid = True

                if rigid_drw_idx is None:
                    rigid_drw_idx = 0

                log.info("  Batch mat=%d: RIGID (drw=%d, %d tris)",
                         mat_idx, rigid_drw_idx, len(triangles))

                # ONE packet, ONE matrix table entry
                packet = ShpPacket()
                packet.matrixTable = [rigid_drw_idx]

                if not triangles:
                    packet.primitives = []
                else:
                    prim = ShpPrimitive()
                    prim.type = 0x90  # GX_TRIANGLES
                    prim.points = []

                    for lt in triangles:
                        # Rigid batches: emit in Blender order (0,1,2).
                        # The import's StripIterator already set correct winding
                        # for rigid geometry during face creation.
                        for i in range(3):
                            loop_idx = lt.loops[i]
                            li = loop_indices.get(loop_idx, {})

                            point = ShpIndex()
                            point.posIndex = li.get('posIndex', 0)
                            point.normalIndex = li.get('normalIndex', 0) if has_normals else 0
                            point.texCoordIndex = list(li.get('texCoordIndex', [None]*8))
                            point.colorIndex = list(li.get('colorIndex', [None, None]))
                            # No matrixIndex for rigid batches

                            prim.points.append(point)

                    packet.primitives = [prim]

                batch.packets = [packet]
            else:
                # ---- WEIGHTED BATCH ----
                batch.attribs.hasMatrixIndices = True
                batch._is_rigid = False

                log.info("  Batch mat=%d: WEIGHTED (%d tris)",
                         mat_idx, len(triangles))

                if not triangles:
                    # EMPTY BATCH: placeholder
                    packet = ShpPacket()
                    packet.matrixTable = [0]
                    packet.primitives = []
                    batch.packets = [packet]
                else:
                    # Split into packets by bone limit (max 10 DRW1 entries per packet)
                    packet_splits = Shp1._split_into_packets(
                        triangles, mesh, vgroup_to_drw, bone_set_to_drw_candidates,
                        bone_to_any_weighted_drw, vgroup_to_bone_idx, max_bones=10)

                    batch.packets = []
                    for pkt_tris, pkt_drw_list in packet_splits:
                        packet = ShpPacket()
                        packet.matrixTable = pkt_drw_list
                        local_mtx_map = {drw_idx: local_idx
                                         for local_idx, drw_idx in enumerate(pkt_drw_list)}

                        prim = ShpPrimitive()
                        prim.type = 0x90  # GX_TRIANGLES
                        prim.points = []

                        for lt in pkt_tris:
                            # Reverse winding: Blender CCW -> GX CW (emit 0, 2, 1)
                            for i in (0, 2, 1):
                                loop_idx = lt.loops[i]
                                vert_idx = lt.vertices[i]
                                li = loop_indices.get(loop_idx, {})

                                point = ShpIndex()
                                point.posIndex = li.get('posIndex', 0)
                                point.normalIndex = li.get('normalIndex', 0) if has_normals else 0
                                point.texCoordIndex = list(li.get('texCoordIndex', [None]*8))
                                point.colorIndex = list(li.get('colorIndex', [None, None]))

                                # Matrix index: local_index * 3
                                vert = mesh.vertices[vert_idx]
                                drw_idx = Shp1._get_vert_drw_index_weighted(
                                    vert, vgroup_to_drw, bone_set_to_drw_candidates,
                                    bone_to_any_weighted_drw, vgroup_to_bone_idx)
                                local_idx = local_mtx_map.get(drw_idx, 0)
                                point.matrixIndex = local_idx * 3

                                prim.points.append(point)

                        packet.primitives = [prim]
                        batch.packets.append(packet)

            shp.batches.append(batch)

        return shp

    def LoadData(self, br):
        shp1Offset = br.Position()
        header = Shp1Header()
        header.LoadData(br)

        # Store raw section bytes for round-trip export
        savedPos = br.Position()
        br.SeekSet(shp1Offset)
        self._rawSectionData = br._f.read(header.sizeOfSection)
        br.SeekSet(savedPos)

        # -- print ("1: " + (br.Position() as string))

        # -- read self.batches
        br.SeekSet(header.offsetToBatches + shp1Offset)
        self.batches = []
        for _ in range(header.batchCount):
            # -- print ("2: " + str(br.Position()))
            d = Shp1BatchDescriptor()
            d.LoadData(br)

            # --print ("3: " + (br.Position() as string))

            # -- TODO: check code
            dstBatch = ShpBatch()
            # Preserve raw batch descriptor for round-trip export
            dstBatch._descriptor = d
            self.batches.append(dstBatch)

            # --Batch& dstBatch = dst.batches[i]; dst = this
            curPos = br.Position()
            self.makeBatch(br, d, header, shp1Offset, dstBatch)
            # --  print ("4: " + (br.Position() as string))
            br.SeekSet(curPos)

    def DumpData(self, bw):
        """Write SHP1 section. If raw data was captured during import, write it back."""
        if self._rawSectionData is not None:
            bw._f.write(self._rawSectionData)
            return

        shp1Offset = bw.Position()
        header = Shp1Header()

        header.pad = 0xffff
        header.zero = 0

        header.batchCount = len(self.batches)
        header.offsetToBatches = header.size
        header.offsetUnknown = 000  # a short per batch?
        header.offsetToBatchAttribs = 000  # aligned
        header.offsetToMatrixTable = 000
        header.offsetData = 000  # aligned
        header.offsetToMatrixData = 000
        header.offsetToPacketLocations = 000

        bw.writePadding(header.size)
        #header.DumpData(bw)


        for batch in self.batches:
            # -- print ("2: " + str(br.Position()))
            d = Shp1BatchDescriptor()


            # -- TODO: check code
            # --Batch& dstBatch = dst.batches[i]; dst = this
            curPos = bw.Position()
            self.decomposeBatch(bw, batch, header, shp1Offset, d)
            # --  print ("4: " + (br.Position() as string))
            bw.SeekSet(curPos)
            d.DumpData(bw)

        header.offsetUnknown = bw.Position() - shp1Offset
        for i in range(header.batchCount):
            bw.writeWord(i)
        bw.writePaddingTo16()

        header.offsetToBatchAttribs = bw.Position() - shp1Offset
        for attrib in self.all_attribs:
            attrib.DumpData(bw)
        # this includes the separator attribs

        header.offsetToMatrixTable = bw.Position() - shp1Offset
        for mtx in self.matrices_table:
            bw.writeWord(mtx)
        # GX display lists require 32-byte aligned addresses.
        # Since the section itself is 32-byte aligned, offsetData must also
        # be 32-byte aligned so that section_start + offsetData + packet_offset
        # produces a 32-byte aligned absolute address for GXCallDisplayList.
        bw.writePaddingTo32()

        header.offsetData = bw.Position() - shp1Offset
        total_length = 0
        for batch in self.batches:
            for i, packet in enumerate(batch.packets):
                batch.p_locs[i].offset = total_length
                length = packet.DumpPacketPrimitives(batch.raw_attribs, bw)
                # GX hardware requires each display list (packet) to be
                # 32-byte aligned. Pad each packet individually.
                pad = (32 - (length % 32)) % 32
                if pad > 0:
                    bw.writePadding(pad)
                    length += pad
                batch.p_locs[i].packetSize = length
                total_length += length

        header.offsetToMatrixData = bw.Position() - shp1Offset
        for mdat in self.matrices_data:
            mdat.DumpData(bw)

        header.offsetToPacketLocations = bw.Position() - shp1Offset
        for p_loc in self.all_p_locs:
            p_loc.DumpData(bw)

        # Pad to 32-byte alignment (BMD section boundary requirement)
        remainder = (bw.Position() - shp1Offset) % 32
        if remainder != 0:
            bw.writePadding(32 - remainder)
        header.sizeOfSection = bw.Position() - shp1Offset
        bw.SeekSet(shp1Offset)
        header.DumpData(bw)
        bw.SeekSet(shp1Offset + header.sizeOfSection)
