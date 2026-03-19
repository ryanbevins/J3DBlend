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