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


def _rebuild_inf1(bmodel, mesh_obj, shp, drw):
    """Rebuild INF1 from reconstructed SHP1 data and armature hierarchy.

    Extracts batch_info (is_rigid, drw_idx) from SHP1 batches, then calls
    Inf1.Rebuild to produce a new scene graph matching the batch ordering.
    """
    # Build batch_info: (is_rigid, first_drw_idx_or_None) per batch
    batch_info = []
    for batch in shp.batches:
        is_rigid = getattr(batch, '_is_rigid', not batch.attribs.hasMatrixIndices)
        drw_idx = None
        if is_rigid and batch.packets:
            # Rigid batch: first matrix table entry is the DRW1 index
            mt = batch.packets[0].matrixTable
            if mt:
                drw_idx = mt[0]
        batch_info.append((is_rigid, drw_idx))

    # Get batch->material mapping from SHP1
    batch_mat_indices = getattr(shp, '_batch_material_indices',
                                list(range(len(shp.batches))))

    # Count total packets and vertices
    total_packets = sum(len(b.packets) for b in shp.batches)
    num_vertices = len(bmodel.vtx.positions) if hasattr(bmodel.vtx, 'positions') else 0

    # Find armature
    armature_obj = None
    if mesh_obj.parent and mesh_obj.parent.type == 'ARMATURE':
        armature_obj = mesh_obj.parent

    new_inf = Inf1.Inf1.Rebuild(
        batch_mat_indices, num_vertices, total_packets,
        old_inf=bmodel.inf,
        batch_info=batch_info, drw1=drw, armature_obj=armature_obj)

    log.info("Rebuilt INF1: %d batches, %d packets, %d vertices",
             len(shp.batches), total_packets, num_vertices)
    bmodel.inf = new_inf


def reconstruct_mesh_sections(bmodel):
    """Rebuild ALL sections from Blender data. No raw/cached import data used.

    This is the full reconstruction path — every section is rebuilt from the
    Blender scene (armature, mesh, vertex groups). This allows verification
    against the original BMD as a source of truth.

    MAT3 and TEX1 are still raw (no builders yet) but everything else is
    reconstructed from scratch.
    """
    mesh_obj = find_mesh_object(bmodel)
    if mesh_obj is None:
        log.warning("Cannot find Blender mesh object for reconstruction.")
        return

    log.info("Full reconstruction from Blender data: %s", mesh_obj.name)

    # Find armature
    armature_obj = None
    if mesh_obj.parent and mesh_obj.parent.type == 'ARMATURE':
        armature_obj = mesh_obj.parent

    # --- Rebuild JNT1 from Blender armature ---
    if armature_obj is not None:
        new_jnt = Jnt1.Jnt1.BuildFromArmature(armature_obj)
        bmodel.jnt = new_jnt

    # --- Rebuild EVP1 from mesh vertex groups + armature ---
    # If original EVP1 was loaded from file (has matrices and weightedIndices),
    # preserve it — the envelopes and inverse bind matrices must match exactly
    # for SHP1 matrix table references to work correctly.
    # Only rebuild from scratch if no original data exists.
    if armature_obj is not None:
        old_evp = bmodel.evp
        has_loaded_evp = (hasattr(old_evp, 'matrices') and old_evp.matrices
                          and hasattr(old_evp, 'weightedIndices') and old_evp.weightedIndices)
        if not has_loaded_evp:
            new_evp = Evp1.Evp1()
            new_evp.BuildFromMesh(armature_obj, mesh_obj, jnt=bmodel.jnt, inf=bmodel.inf)
            bmodel.evp = new_evp

    # --- Rebuild DRW1 from mesh vertex groups + EVP1 ---
    # Preserve original DRW1 if loaded from file (ordering must match SHP1 refs).
    if armature_obj is not None:
        old_drw = bmodel.drw
        has_loaded_drw = (hasattr(old_drw, 'data') and old_drw.data
                          and hasattr(old_drw, 'isWeighted') and old_drw.isWeighted)
        if not has_loaded_drw:
            new_drw = Drw1.Drw1()
            new_drw.BuildFromMesh(armature_obj, mesh_obj, bmodel.evp)
            bmodel.drw = new_drw

    jnt = bmodel.jnt
    drw = bmodel.drw
    evp = bmodel.evp

    # Extract batch ordering from INF1 scene graph (still using original INF1
    # for ordering, will be rebuilt after SHP1)
    batch_mat_order = _extract_batch_material_order(bmodel.inf)
    batch_mat_order.sort(key=lambda x: x[0])
    batch_order = [blender_mat for _, blender_mat in batch_mat_order]
    log.info("INF1 batch->material order: %s", batch_order)

    # Pre-compute per-vertex DRW assignments
    vert_drw, mat_classification = Shp1.Shp1.PrecomputeVertexDRW(
        mesh_obj, drw, evp, batch_order)
    log.info("Pre-computed DRW assignments for %d vertices", len(vert_drw))

    # --- Rebuild VTX1 ---
    new_vtx, loop_indices = Vtx1.Vtx1.FromBlenderMesh(
        mesh_obj, jnt=jnt, drw=drw, evp=evp, vert_drw=vert_drw)
    if hasattr(bmodel.vtx, 'arrayFormats') and bmodel.vtx.arrayFormats:
        new_vtx.arrayFormats = bmodel.vtx.arrayFormats
    if hasattr(bmodel.vtx, '_formatSentinel'):
        new_vtx._formatSentinel = bmodel.vtx._formatSentinel
    bmodel.vtx = new_vtx

    # --- Rebuild SHP1 ---
    new_shp = Shp1.Shp1.FromBlenderMesh(
        mesh_obj, new_vtx, loop_indices, drw, batch_order=batch_order, evp1=evp)
    bmodel.shp = new_shp

    # --- Rebuild INF1 from new SHP1 + armature ---
    _rebuild_inf1(bmodel, mesh_obj, new_shp, drw)


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
