"""Read-only Blender Properties panel for GX TEV stage configuration."""

import bpy

# ---------------------------------------------------------------------------
# GX enum display names
# ---------------------------------------------------------------------------

TEV_COLOR_IN = {
    0: "cprev", 1: "aprev", 2: "c0", 3: "a0", 4: "c1", 5: "a1",
    6: "c2", 7: "a2", 8: "texc", 9: "texa", 10: "rasc", 11: "rasa",
    12: "one", 13: "half", 14: "konst", 15: "zero",
}

TEV_ALPHA_IN = {
    0: "aprev", 1: "a0", 2: "a1", 3: "a2",
    4: "texa", 5: "rasa", 6: "konst", 7: "zero",
}

TEV_OP = {
    0: "add", 1: "sub",
    8: "comp_r8_gt", 9: "comp_r8_eq",
    10: "comp_gr16_gt", 11: "comp_gr16_eq",
    12: "comp_bgr24_gt", 13: "comp_bgr24_eq",
    14: "comp_rgb8_gt", 15: "comp_rgb8_eq",
}

TEV_BIAS = {0: "zero", 1: "+0.5", 2: "-0.5"}
TEV_SCALE = {0: "1x", 1: "2x", 2: "4x", 3: "0.5x"}
TEV_REGISTER = {0: "prev", 1: "reg0", 2: "reg1", 3: "reg2"}

CULL_MODE = {0: "none", 1: "front", 2: "back", 3: "all"}
BLEND_TYPE = {0: "none", 1: "blend", 2: "logic", 3: "subtract"}
BLEND_FACTOR = {
    0: "zero", 1: "one", 2: "srcclr", 3: "invsrcclr",
    4: "srcalpha", 5: "invsrcalpha", 6: "dstalpha", 7: "invdstalpha",
}
COMPARE_FUNC = {
    0: "never", 1: "less", 2: "equal", 3: "lequal",
    4: "greater", 5: "nequal", 6: "gequal", 7: "always",
}
ALPHA_OP = {0: "and", 1: "or", 2: "xor", 3: "xnor"}


def _get(mat, key, default=None):
    """Safe custom-property getter."""
    try:
        return mat[key]
    except KeyError:
        return default


def _enum(table, val):
    """Look up an enum value, return string."""
    if val is None:
        return "?"
    return table.get(int(val), "0x%02X" % int(val))


# ---------------------------------------------------------------------------
# Panel
# ---------------------------------------------------------------------------

class MATERIAL_PT_gx_tev(bpy.types.Panel):
    bl_idname = "MATERIAL_PT_gx_tev"
    bl_label = "GX TEV Stages"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "material"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        mat = context.material
        if mat is None:
            return False
        return _get(mat, "gc_tev_stageCount") is not None

    def draw(self, context):
        layout = self.layout
        mat = context.material

        stage_count = int(_get(mat, "gc_tev_stageCount", 0))
        cull = _enum(CULL_MODE, _get(mat, "gc_tev_cullMode"))

        # Header
        header = layout.box()
        header.label(text="Material: %s" % mat.name, icon='MATERIAL')
        row = header.row()
        row.label(text="TEV Stages: %d" % stage_count)
        row.label(text="Cull: %s" % cull)

        # Per-stage boxes
        for i in range(stage_count):
            prefix = "gc_tev_%d_" % i
            stage_box = layout.box()
            stage_box.label(text="Stage %d" % i, icon='NODE')

            # TEV Order
            tex_map = _get(mat, prefix + "texMap")
            tex_coord = _get(mat, prefix + "texCoordId")
            chan_id = _get(mat, prefix + "chanId")
            order_row = stage_box.row()
            order_row.label(text="Order:")
            order_row.label(text="tex=%s" % (str(tex_map) if tex_map is not None else "?"))
            order_row.label(text="coord=%s" % (str(tex_coord) if tex_coord is not None else "?"))
            order_row.label(text="chan=%s" % (str(chan_id) if chan_id is not None else "?"))

            # Color combine
            color_box = stage_box.box()
            color_box.label(text="Color Combine")
            r1 = color_box.row()
            r1.label(text="A: %s" % _enum(TEV_COLOR_IN, _get(mat, prefix + "colorInA")))
            r1.label(text="B: %s" % _enum(TEV_COLOR_IN, _get(mat, prefix + "colorInB")))
            r1.label(text="C: %s" % _enum(TEV_COLOR_IN, _get(mat, prefix + "colorInC")))
            r1.label(text="D: %s" % _enum(TEV_COLOR_IN, _get(mat, prefix + "colorInD")))
            r2 = color_box.row()
            r2.label(text="Op: %s" % _enum(TEV_OP, _get(mat, prefix + "colorOp")))
            r2.label(text="Bias: %s" % _enum(TEV_BIAS, _get(mat, prefix + "colorBias")))
            r2.label(text="Scale: %s" % _enum(TEV_SCALE, _get(mat, prefix + "colorScale")))
            r3 = color_box.row()
            clamp = _get(mat, prefix + "colorClamp")
            r3.label(text="Clamp: %s" % ("yes" if clamp else "no"))
            r3.label(text="Dest: %s" % _enum(TEV_REGISTER, _get(mat, prefix + "colorRegId")))

            # Alpha combine
            alpha_box = stage_box.box()
            alpha_box.label(text="Alpha Combine")
            r1 = alpha_box.row()
            r1.label(text="A: %s" % _enum(TEV_ALPHA_IN, _get(mat, prefix + "alphaInA")))
            r1.label(text="B: %s" % _enum(TEV_ALPHA_IN, _get(mat, prefix + "alphaInB")))
            r1.label(text="C: %s" % _enum(TEV_ALPHA_IN, _get(mat, prefix + "alphaInC")))
            r1.label(text="D: %s" % _enum(TEV_ALPHA_IN, _get(mat, prefix + "alphaInD")))
            r2 = alpha_box.row()
            r2.label(text="Op: %s" % _enum(TEV_OP, _get(mat, prefix + "alphaOp")))
            r2.label(text="Bias: %s" % _enum(TEV_BIAS, _get(mat, prefix + "alphaBias")))
            r2.label(text="Scale: %s" % _enum(TEV_SCALE, _get(mat, prefix + "alphaScale")))
            r3 = alpha_box.row()
            aclamp = _get(mat, prefix + "alphaClamp")
            r3.label(text="Clamp: %s" % ("yes" if aclamp else "no"))
            r3.label(text="Dest: %s" % _enum(TEV_REGISTER, _get(mat, prefix + "alphaRegId")))

            # Konst selections
            konst_row = stage_box.row()
            kc = _get(mat, prefix + "constColorSel")
            ka = _get(mat, prefix + "constAlphaSel")
            konst_row.label(text="Konst Color Sel: 0x%02X" % int(kc) if kc is not None else "Konst Color Sel: ?")
            konst_row.label(text="Konst Alpha Sel: 0x%02X" % int(ka) if ka is not None else "Konst Alpha Sel: ?")

        # Footer: blend, z-mode, alpha compare
        footer = layout.box()
        footer.label(text="Render State", icon='RENDERLAYERS')

        # Blend mode
        blend_row = footer.row()
        blend_mode = _get(mat, "gc_tev_blendMode")
        blend_src = _get(mat, "gc_tev_blendSrcFactor")
        blend_dst = _get(mat, "gc_tev_blendDstFactor")
        blend_row.label(text="Blend: %s" % _enum(BLEND_TYPE, blend_mode))
        blend_row.label(text="Src: %s" % _enum(BLEND_FACTOR, blend_src))
        blend_row.label(text="Dst: %s" % _enum(BLEND_FACTOR, blend_dst))

        # Z-mode
        z_row = footer.row()
        z_enable = _get(mat, "gc_tev_zEnable")
        z_func = _get(mat, "gc_tev_zFunc")
        z_update = _get(mat, "gc_tev_zEnableUpdate")
        z_row.label(text="Z-Test: %s" % ("on" if z_enable else "off"))
        z_row.label(text="Z-Func: %s" % _enum(COMPARE_FUNC, z_func))
        z_row.label(text="Z-Write: %s" % ("on" if z_update else "off"))

        # Alpha compare
        ac_row = footer.row()
        ac_comp0 = _get(mat, "gc_tev_alphaComp0")
        ac_ref0 = _get(mat, "gc_tev_alphaRef0")
        ac_op = _get(mat, "gc_tev_alphaOp")
        ac_comp1 = _get(mat, "gc_tev_alphaComp1")
        ac_ref1 = _get(mat, "gc_tev_alphaRef1")
        ac_row.label(text="Alpha: %s(%s)" % (
            _enum(COMPARE_FUNC, ac_comp0),
            str(ac_ref0) if ac_ref0 is not None else "?",
        ))
        ac_row.label(text=_enum(ALPHA_OP, ac_op))
        ac_row.label(text="%s(%s)" % (
            _enum(COMPARE_FUNC, ac_comp1),
            str(ac_ref1) if ac_ref1 is not None else "?",
        ))


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def register():
    bpy.utils.register_class(MATERIAL_PT_gx_tev)


def unregister():
    bpy.utils.unregister_class(MATERIAL_PT_gx_tev)
