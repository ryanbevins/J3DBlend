#! /usr/bin/python3
#     -- loads correctly: count=113, offsetToW=20, offsetToD=134 [20 + 113 = 133 (nextBit = offsetToD)]

from math import ceil


class Drw1Header:
    size = 20
    def __init__(self):  # GENERATED!
        pass

    def LoadData(self, br):
        self.tag = br.ReadFixedLengthString(4)
        self.sizeOfSection = br.ReadDWORD()
        self.count = br.ReadWORD()
        self.pad = br.ReadWORD()
        # stores for each matrix if it's weighted (normal (0)/skinned (1) matrix types)
        self.offsetToIsWeighted = br.ReadDWORD()
        # for normal (0) matrices, this is an index into the global matrix
        # table (which stores a matrix for every joint). for skinned
        # matrices (1), I'm not yet totally sure how this works (but it's
        # probably an offset into the Evp1-array)
        self.offsetToData = br.ReadDWORD()

    def DumpData(self, bw):
        bw.writeString('DRW1')
        bw.writeDword(self.sizeOfSection)
        bw.writeWord(self.count)
        bw.writeWord(self.pad)
        bw.writeDword(self.offsetToIsWeighted)
        bw.writeDword(self.offsetToData)
  

class Drw1:
    def __init__(self):  # GENERATED!
        self.data= []
        self.isWeighted= []

    def BuildFromMesh(self, armature_obj, mesh_obj, evp1):
        """Build DRW1 draw matrix table from Blender mesh vertex groups."""
        bones = armature_obj.data.bones
        bone_names = [b.name for b in bones]
        mesh = mesh_obj.data

        vgroup_to_bone = {}
        for vg in mesh_obj.vertex_groups:
            if vg.name in bone_names:
                vgroup_to_bone[vg.index] = bone_names.index(vg.name)

        envelope_map = {}
        for ei, mm in enumerate(evp1.weightedIndices):
            key = tuple((mm.indices[j], round(mm.weights[j], 6))
                        for j in range(len(mm.indices)))
            envelope_map[key] = ei

        rigid_set = set()
        weighted_set = set()
        rigid_entries = []
        weighted_entries = []

        for vert in mesh.vertices:
            sig_groups = [(g.group, g.weight) for g in vert.groups
                          if g.weight > 0.001 and g.group in vgroup_to_bone]

            if len(sig_groups) == 0:
                continue
            elif len(sig_groups) == 1:
                bone_idx = vgroup_to_bone[sig_groups[0][0]]
                if bone_idx not in rigid_set:
                    rigid_set.add(bone_idx)
                    rigid_entries.append(bone_idx)
            else:
                total = sum(w for _, w in sig_groups)
                if total < 1e-6:
                    continue
                normalized = [(vgroup_to_bone[gi], w / total) for gi, w in sig_groups]
                normalized.sort(key=lambda x: x[0])
                key = tuple((bi, round(w, 6)) for bi, w in normalized)
                evp_idx = envelope_map.get(key)
                if evp_idx is not None and evp_idx not in weighted_set:
                    weighted_set.add(evp_idx)
                    weighted_entries.append(evp_idx)

        rigid_entries.sort()
        weighted_entries.sort()

        self.isWeighted = []
        self.data = []

        for bone_idx in rigid_entries:
            self.isWeighted.append(False)
            self.data.append(bone_idx)

        # Nintendo duplicates weighted entries as two complete sequential passes
        for evp_idx in weighted_entries:
            self.isWeighted.append(True)
            self.data.append(evp_idx)
        for evp_idx in weighted_entries:
            self.isWeighted.append(True)
            self.data.append(evp_idx)

    def LoadData(self, br):

        drw1Offset = br.Position()

        header = Drw1Header()
        header.LoadData(br)

        # -- read bool array
        self.isWeighted = [False] * header.count
        # -- self.isWeighted.resize(h.count);
        br.SeekSet(drw1Offset + header.offsetToIsWeighted)
        for i in range(header.count):
            v = br.GetByte()  # -- u8 v; fread(&v, 1, 1, f);

            if v == 0:
                pass
                # self.isWeighted[i] = False
                # already done when initialized
            elif v == 1:
                self.isWeighted[i] = True
            else:
                raise ValueError("drw1: unexpected value in isWeighted array: " + str(v))

        # -- read self.data array
        self.data = [0] * header.count
        # -- dst.self.data.resize(h.count);
        br.SeekSet(drw1Offset + header.offsetToData)
        for i in range(header.count):
            self.data[i] = br.ReadWORD()

    def DumpData(self, bw):
        """Write DRW1 section."""
        drw1Offset = bw.Position()

        header = Drw1Header()
        header.count = len(self.data)
        if len(self.isWeighted) != header.count:
            raise ValueError('Broken Drw1 section')
        header.pad = 0xffff
        header.offsetToIsWeighted = Drw1Header.size  # No padding after header
        header.offsetToData = header.offsetToIsWeighted + header.count
        header.sizeOfSection = bw.addPadding(header.offsetToData + 2*header.count)

        header.DumpData(bw)

        for isW in self.isWeighted:
            bw.writeByte(int(isW))

        for index in self.data:
            bw.writeWord(index)

        bw.writePadding(drw1Offset + header.sizeOfSection - bw.Position())
