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


def find_mesh_object(bmodel):
    """Find the Blender mesh object associated with this BModel."""
    # The mesh object was named after the BMD file
    filename = getattr(bmodel, '_bmdFileName', None)
    if filename and filename in bpy.data.objects:
        obj = bpy.data.objects[filename]
        if obj.type == 'MESH':
            return obj

    # Search all mesh objects for one that has an armature matching our model
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            # Check if its parent armature name matches
            if obj.parent and obj.parent.type == 'ARMATURE':
                arm_name = obj.name + '_armature'
                if obj.parent.name == arm_name:
                    if filename and filename in obj.name:
                        return obj
            # Direct name match
            if filename and obj.name.startswith(filename):
                return obj

    return None


def mesh_was_modified(bmodel):
    """Check if the Blender mesh has been modified since import.

    Returns True only if the raw section data has been cleared (indicating
    the sections need reconstruction). The vertex count heuristic was unreliable
    because Blender's mesh.vertices count doesn't match VTX1's deduplicated
    position pool count.

    For now, raw round-trip is the default. Reconstruction only happens when
    force_reconstruct=True is passed to export_bmd.
    """
    # If raw section data is missing from either VTX1 or SHP1, reconstruction is needed
    if not hasattr(bmodel.vtx, '_rawSectionData') or bmodel.vtx._rawSectionData is None:
        return True
    if not hasattr(bmodel.shp, '_rawSectionData') or bmodel.shp._rawSectionData is None:
        return True

    return False


def _extract_batch_material_order(inf):
    """Walk the INF1 scene graph and extract the batch-to-blender-material mapping.

    During import, Blender material slot indices are assigned by incrementing
    a counter each time a material node (0x11) is encountered in DFS order.
    Shape nodes (0x12) reference SHP1 batch indices. The most recently seen
    material determines the Blender material_index for faces in that batch.

    Returns a list of (batch_index, blender_material_index) in scene graph order.
    This tells us which Blender material_index each SHP1 batch should contain.
    """
    result = []  # [(batch_index, blender_mat_index)]
    mat_counter = [0]  # mutable counter for material node encounters

    def _walk(sg, current_mat_idx):
        if sg.type == 0x11:  # Material node
            current_mat_idx = mat_counter[0]
            mat_counter[0] += 1
        elif sg.type == 0x12:  # Shape (batch) node
            result.append((sg.index, current_mat_idx))

        for child in sg.children:
            _walk(child, current_mat_idx)

    _walk(inf.rootSceneGraph, 0)
    return result


def reconstruct_mesh_sections(bmodel):
    """Rebuild VTX1 and SHP1 from the current Blender mesh.

    INF1 is NOT rebuilt — it stays as the raw data from import.
    The original INF1 scene graph references batches by index (0..N-1),
    so SHP1 must produce exactly the same number of batches in the same
    material order as the original.
    """
    mesh_obj = find_mesh_object(bmodel)
    if mesh_obj is None:
        log.warning("Cannot find Blender mesh object for reconstruction.")
        return

    log.info("Reconstructing VTX1 and SHP1 from Blender mesh: %s", mesh_obj.name)

    jnt = getattr(bmodel, 'jnt', None)
    drw = getattr(bmodel, 'drw', None)
    evp = getattr(bmodel, 'evp', None)

    # Extract original batch ordering from INF1 scene graph
    # This gives us [(batch_index, blender_material_index), ...] in scene graph order
    batch_mat_order = _extract_batch_material_order(bmodel.inf)
    # Sort by batch_index to get: batch 0 -> mat X, batch 1 -> mat Y, ...
    batch_mat_order.sort(key=lambda x: x[0])
    batch_order = [blender_mat for _, blender_mat in batch_mat_order]
    log.info("INF1 batch->material order: %s", batch_order)

    # Pre-compute per-vertex DRW assignments so VTX1 and SHP1 agree
    # on which transform each vertex uses.
    vert_drw, mat_classification = Shp1.Shp1.PrecomputeVertexDRW(
        mesh_obj, drw, evp, batch_order)
    log.info("Pre-computed DRW assignments for %d vertices", len(vert_drw))

    # Reconstruct VTX1 — uses DRW assignments for inverse skinning so that
    # positions are consistent with the runtime transform SHP1 will apply.
    new_vtx, loop_indices = Vtx1.Vtx1.FromBlenderMesh(
        mesh_obj, jnt=jnt, drw=drw, evp=evp, vert_drw=vert_drw)
    if hasattr(bmodel.vtx, 'arrayFormats') and bmodel.vtx.arrayFormats:
        new_vtx.arrayFormats = bmodel.vtx.arrayFormats
    if hasattr(bmodel.vtx, '_formatSentinel'):
        new_vtx._formatSentinel = bmodel.vtx._formatSentinel
    bmodel.vtx = new_vtx

    # Reconstruct SHP1 (majority-vote: rigid or weighted per material batch)
    # Pass batch_order so batches are produced in the same order as the original INF1
    new_shp = Shp1.Shp1.FromBlenderMesh(
        mesh_obj, new_vtx, loop_indices, bmodel.drw, batch_order=batch_order, evp1=evp)
    bmodel.shp = new_shp

    # INF1 is NOT touched — it stays as the raw data from import.


def export_bmd(filepath, bmodel, force_reconstruct=False):
    """Write a complete BMD file from imported section data.

    Header: 'J3D2bmd3' (8 bytes) + u32 file_size (backfill) + u32 section_count + 16 bytes padding.
    Sections in order: INF1, VTX1, EVP1, DRW1, JNT1, SHP1, MAT3, TEX1, [MDL3].

    If the mesh has been modified (or force_reconstruct=True), VTX1 and SHP1
    are reconstructed from the current Blender mesh data.
    """
    # Check if mesh reconstruction is needed
    if force_reconstruct or mesh_was_modified(bmodel):
        reconstruct_mesh_sections(bmodel)
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
        has_raw = hasattr(section, '_rawSectionData') and section._rawSectionData is not None
        print("BMD Export: Writing %s at offset 0x%x (raw=%s)" % (tag, section_start, has_raw))
        section.DumpData(bw)
        section_end = bw.Position()
        section_size = section_end - section_start
        print("BMD Export:   %s size: %d bytes (0x%x)" % (tag, section_size, section_size))
        # No padding between sections — sizeOfSection includes internal padding,
        # and the import loop uses sizeOfSection to find the next section tag.

    # Backfill file size
    file_size = bw.Position()
    bw.SeekSet(8)
    bw.writeDword(file_size)

    # Also patch section count in case original header had different value
    bw.writeDword(section_count)

    bw.Close()
    log.info("BMD export complete: %s (%d bytes)", filepath, file_size)
    return file_size
