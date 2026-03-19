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
            if len(dst.packets) <= i:
                dst.packets.append(None)
            dst.packets[i] = dstPacket

            # -- read matrix data for current packet
            matrixData = Shp1MatrixData()
            br.SeekSet(baseOffset + header.offsetToMatrixData + (batchSrc.firstMatrixData + i)*matrixData.size)
            matrixData.LoadData(br)

            # --print (matrixData as string)

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

        batchDst.offsetToAttribs = len(self.all_attribs) * Shp1BatchAttrib.size

        # Set batch descriptor type: 0x00FF for rigid, 0x03FF for weighted
        is_rigid = getattr(batch, '_is_rigid', not batch.attribs.hasMatrixIndices)
        batchDst.unknown = 0x00ff if is_rigid else 0x03ff

        # Set bounding box floats
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

        # Separator goes into all_attribs (for the batch attribute table in the file)
        # but NOT into batch.raw_attribs (which is passed to DumpPacketPrimitives)
        separator = Shp1BatchAttrib()
        separator.attrib = 0xff
        separator.dataType = 0xff

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

            # unknown1: use the first entry in the matrix table for this packet
            # (matches original behavior observed in diagnostic)
            if packet.matrixTable:
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
        """Get the DRW1 index for a vertex based on its heaviest vertex group."""
        if vert.groups:
            best_group = max(vert.groups, key=lambda g: g.weight)
            return vgroup_to_drw.get(best_group.group, 0)
        return 0

    @staticmethod
    def _is_batch_rigid(mesh, triangles, vgroup_to_drw):
        """Check if all vertices in a batch use exactly one bone (rigid skinning).

        Returns (True, drw_index) if rigid, (False, None) if weighted.
        """
        drw_indices_seen = set()
        for lt in triangles:
            for vi in lt.vertices:
                vert = mesh.vertices[vi]
                drw_idx = Shp1._get_vert_drw_index(vert, vgroup_to_drw)
                drw_indices_seen.add(drw_idx)
                if len(drw_indices_seen) > 1:
                    return False, None
        if len(drw_indices_seen) == 1:
            return True, next(iter(drw_indices_seen))
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
    def _split_into_packets(triangles, mesh, vgroup_to_drw, max_bones=10):
        """Split triangles into packets, each using at most max_bones unique DRW1 indices.

        Returns list of (tri_list, drw_index_list) tuples.
        """
        # Collect per-triangle bone sets
        tri_bones = []
        for lt in triangles:
            bones = set()
            for vi in lt.vertices:
                vert = mesh.vertices[vi]
                drw_idx = Shp1._get_vert_drw_index(vert, vgroup_to_drw)
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
    def FromBlenderMesh(mesh_obj, vtx1, loop_indices, drw1):
        """Reconstruct SHP1 from a Blender mesh, VTX1 pools, and loop index mapping.

        Groups faces by material into batches. Determines rigid vs weighted per batch.
        Rigid batches: single bone, no matrix attrib, one packet.
        Weighted batches: matrix attrib, packets split at 10-bone limit.

        Args:
            mesh_obj: Blender mesh object
            vtx1: Vtx1 instance with populated pools
            loop_indices: dict from Vtx1.FromBlenderMesh, mapping loop_idx to indices
            drw1: Drw1 instance (for matrix table references)

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

        # Group loop_triangles by material index
        mat_groups = {}  # material_index -> list of loop_triangles
        for lt in mesh.loop_triangles:
            mi = lt.material_index
            if mi not in mat_groups:
                mat_groups[mi] = []
            mat_groups[mi].append(lt)

        # Build vertex group -> DRW1 index mapping
        vgroup_to_drw = {}
        if has_armature and mesh_obj.vertex_groups:
            arm_obj = mesh_obj.parent
            bone_names = [b.name for b in arm_obj.data.bones]
            for vg in mesh_obj.vertex_groups:
                if vg.name in bone_names:
                    bone_idx = bone_names.index(vg.name)
                    # Find the rigid DRW1 entry for this bone
                    for di, (isW, data_val) in enumerate(zip(drw1.isWeighted, drw1.data)):
                        if not isW and data_val == bone_idx:
                            vgroup_to_drw[vg.index] = di
                            break

        # Build batches (one per material)
        for mat_idx in sorted(mat_groups.keys()):
            triangles = mat_groups[mat_idx]
            batch = ShpBatch()

            # Determine if this batch is rigid (single bone) or weighted (multi-bone)
            is_rigid = False
            rigid_drw_idx = 0
            if has_armature:
                is_rigid, rigid_drw_idx = Shp1._is_batch_rigid(mesh, triangles, vgroup_to_drw)
                if rigid_drw_idx is None:
                    rigid_drw_idx = 0

            # Set attribute flags
            batch.attribs = ShpAttributes()
            batch.attribs.hasPositions = True
            batch.attribs.hasNormals = has_normals
            # Only weighted batches need matrix indices
            batch.attribs.hasMatrixIndices = has_armature and not is_rigid
            for uv in range(num_uv_layers):
                batch.attribs.hasTexCoords[uv] = True
            for ci in range(num_color_layers):
                batch.attribs.hasColors[ci] = True

            # Store batch type for descriptor writing
            batch._is_rigid = is_rigid

            # Compute bounding box for batch descriptor
            batch._bbox = Shp1._compute_bounding_box(mesh, triangles, vtx1)

            if is_rigid:
                # RIGID BATCH: one packet, one bone, no matrix attrib per vertex
                packet = ShpPacket()
                packet.matrixTable = [rigid_drw_idx]

                prim = ShpPrimitive()
                prim.type = 0x90  # raw triangles
                prim.points = []

                for lt in triangles:
                    for i in range(3):
                        loop_idx = lt.loops[i]
                        li = loop_indices.get(loop_idx, {})

                        point = ShpIndex()
                        point.posIndex = li.get('posIndex', 0)
                        point.normalIndex = li.get('normalIndex', 0) if has_normals else 0
                        point.texCoordIndex = list(li.get('texCoordIndex', [None]*8))
                        point.colorIndex = list(li.get('colorIndex', [None, None]))
                        prim.points.append(point)

                packet.primitives = [prim]
                batch.packets = [packet]
            else:
                # WEIGHTED BATCH: split into packets by bone limit
                packet_splits = Shp1._split_into_packets(triangles, mesh, vgroup_to_drw, max_bones=10)

                batch.packets = []
                for pkt_tris, pkt_drw_list in packet_splits:
                    packet = ShpPacket()
                    packet.matrixTable = pkt_drw_list
                    local_mtx_map = {drw_idx: local_idx for local_idx, drw_idx in enumerate(pkt_drw_list)}

                    prim = ShpPrimitive()
                    prim.type = 0x90  # raw triangles
                    prim.points = []

                    for lt in pkt_tris:
                        for i in range(3):
                            loop_idx = lt.loops[i]
                            vert_idx = lt.vertices[i]
                            li = loop_indices.get(loop_idx, {})

                            point = ShpIndex()
                            point.posIndex = li.get('posIndex', 0)
                            point.normalIndex = li.get('normalIndex', 0) if has_normals else 0
                            point.texCoordIndex = list(li.get('texCoordIndex', [None]*8))
                            point.colorIndex = list(li.get('colorIndex', [None, None]))

                            # Matrix index: local_index_in_packet_table * 3
                            vert = mesh.vertices[vert_idx]
                            drw_idx = Shp1._get_vert_drw_index(vert, vgroup_to_drw)
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
        for _ in range(header.batchCount):
            bw.writeWord(0)
        bw.writePaddingTo16()

        header.offsetToBatchAttribs = bw.Position() - shp1Offset
        for attrib in self.all_attribs:
            attrib.DumpData(bw)
        # this includes the separator attribs

        header.offsetToMatrixTable = bw.Position() - shp1Offset
        for mtx in self.matrices_table:
            bw.writeWord(mtx)
        bw.writePaddingTo16()

        header.offsetData = bw.Position() - shp1Offset
        total_length = 0
        for batch in self.batches:
            for i, packet in enumerate(batch.packets):
                batch.p_locs[i].offset = total_length
                length = packet.DumpPacketPrimitives(batch.raw_attribs, bw)
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
