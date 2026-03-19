# -*- coding: utf-8 -*-
import logging
log = logging.getLogger('bpy.ops.import_mesh.bmd.export')

if "bpy" in locals():
    LOADED = True
else:
    LOADED = False

import bpy

if LOADED:
    from importlib import reload
    reload(BinaryWriter)
    reload(Inf1)
    reload(Vtx1)
    reload(Shp1)
    reload(Jnt1)
    reload(Evp1)
    reload(Drw1)
    reload(Mat3)
    reload(Tex1)
    reload(Mdl3)
else:
    from . import (
        BinaryWriter,
        Inf1, Vtx1, Shp1, Jnt1, Evp1, Drw1, Tex1, Mdl3, Mat3,
    )

del LOADED

# Registry of imported BModel instances keyed by armature/mesh object name.
# Populated during import, consumed during export.
_imported_models = {}


def register_model(obj_name, bmodel):
    """Store a BModel reference for later export. Called from BModel after import."""
    _imported_models[obj_name] = bmodel


def find_model(context):
    """Find the BModel for the active object or its parent armature.

    The registry is keyed by BMD filename (without extension).
    We check the active object name, parent name, and child names against the registry.
    If there's only one model registered, return it directly.
    """
    # If only one model is registered, just return it
    if len(_imported_models) == 1:
        return next(iter(_imported_models.values()))

    obj = context.active_object
    if obj is None:
        return None

    # Check the object itself (mesh is named after the BMD file)
    if obj.name in _imported_models:
        return _imported_models[obj.name]

    # Check parent (mesh parented to armature; armature name = meshname + '_armature')
    if obj.parent and obj.parent.name in _imported_models:
        return _imported_models[obj.parent.name]

    # Check children (armature selected, mesh is child)
    for child in obj.children:
        if child.name in _imported_models:
            return _imported_models[child.name]

    # Try stripping suffixes (Blender appends .001 etc. for name collisions)
    for name in [obj.name, getattr(obj.parent, 'name', '')]:
        base = name.rsplit('.', 1)[0] if '.' in name else name
        # Also try stripping _armature suffix
        base2 = base.replace('_armature', '')
        for key in (base, base2):
            if key in _imported_models:
                return _imported_models[key]

    return None


def export_bmd(filepath, bmodel):
    """Write a complete BMD file from imported section data.

    Header: 'J3D2bmd3' (8 bytes) + u32 file_size (backfill) + u32 section_count + 16 bytes padding.
    Sections in order: INF1, VTX1, EVP1, DRW1, JNT1, SHP1, MAT3, TEX1, [MDL3].
    """
    bw = BinaryWriter.BinaryWriter()
    bw.Open(filepath)

    # Determine section count
    has_mdl3 = (hasattr(bmodel, 'mdl') and
                bmodel.mdl is not None and
                hasattr(bmodel.mdl, '_rawSectionData') and
                bmodel.mdl._rawSectionData is not None)
    section_count = 9 if has_mdl3 else 8

    # Write file header (32 bytes)
    if hasattr(bmodel, '_fileHeader') and bmodel._fileHeader is not None:
        # Round-trip: write back original header, then patch file_size and section_count later
        bw._f.write(bmodel._fileHeader)
    else:
        # New file header
        bw.writeString("J3D2bmd3")       # 8 bytes magic
        bw.writeDword(0)                  # file_size placeholder (backfill)
        bw.writeDword(section_count)      # section count
        # 16 bytes padding (SVR3 tag area)
        bw.writeString("SVR3")
        bw.writeDword(0xFFFFFFFF)
        bw.writeDword(0xFFFFFFFF)
        bw.writeDword(0xFFFFFFFF)

    assert bw.Position() == 0x20, "Header must be exactly 32 bytes"

    # Write sections in order
    sections = [
        ('INF1', bmodel.inf),
        ('VTX1', bmodel.vtx),
        ('EVP1', bmodel.evp),
        ('DRW1', bmodel.drw),
        ('JNT1', bmodel.jnt),
        ('SHP1', bmodel.shp),
        ('MAT3', bmodel._mat1),
        ('TEX1', bmodel.tex),
    ]

    if has_mdl3:
        sections.append(('MDL3', bmodel.mdl))

    for tag, section in sections:
        section_start = bw.Position()
        log.info("Writing %s at offset 0x%x", tag, section_start)
        section.DumpData(bw)
        section_end = bw.Position()
        log.info("  %s size: %d bytes", tag, section_end - section_start)

        # Pad to 32-byte alignment
        remainder = bw.Position() % 32
        if remainder != 0:
            pad_count = 32 - remainder
            bw.writePadding(pad_count)

    # Backfill file size
    file_size = bw.Position()
    bw.SeekSet(8)
    bw.writeDword(file_size)

    # Also patch section count in case original header had different value
    bw.writeDword(section_count)

    bw.Close()
    log.info("BMD export complete: %s (%d bytes)", filepath, file_size)
    return file_size
