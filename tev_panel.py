"""Blender Properties panel for GX TEV stage configuration.

Visual pipeline editor with human-readable summaries and editable properties.
"""

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
ALPHA_OP = {0: "AND", 1: "OR", 2: "XOR", 3: "XNOR"}

KONST_COLOR_SEL = {
    0x00: "1.0", 0x01: "7/8", 0x02: "3/4", 0x03: "5/8",
    0x04: "1/2", 0x05: "3/8", 0x06: "1/4", 0x07: "1/8",
    0x0C: "K0", 0x0D: "K1", 0x0E: "K2", 0x0F: "K3",
    0x10: "K0.R", 0x11: "K1.R", 0x12: "K2.R", 0x13: "K3.R",
    0x14: "K0.G", 0x15: "K1.G", 0x16: "K2.G", 0x17: "K3.G",
    0x18: "K0.B", 0x19: "K1.B", 0x1A: "K2.B", 0x1B: "K3.B",
    0x1C: "K0.A", 0x1D: "K1.A", 0x1E: "K2.A", 0x1F: "K3.A",
}

KONST_ALPHA_SEL = {
    0x00: "1.0", 0x01: "7/8", 0x02: "3/4", 0x03: "5/8",
    0x04: "1/2", 0x05: "3/8", 0x06: "1/4", 0x07: "1/8",
    0x10: "K0.R", 0x11: "K1.R", 0x12: "K2.R", 0x13: "K3.R",
    0x14: "K0.G", 0x15: "K1.G", 0x16: "K2.G", 0x17: "K3.G",
    0x18: "K0.B", 0x19: "K1.B", 0x1A: "K2.B", 0x1B: "K3.B",
    0x1C: "K0.A", 0x1D: "K1.A", 0x1E: "K2.A", 0x1F: "K3.A",
}

# Friendly names for display in summaries
_COLOR_FRIENDLY = {
    "cprev": "Prev.RGB", "aprev": "Prev.A", "c0": "Reg0.RGB", "a0": "Reg0.A",
    "c1": "Reg1.RGB", "a1": "Reg1.A", "c2": "Reg2.RGB", "a2": "Reg2.A",
    "texc": "Tex.RGB", "texa": "Tex.A", "rasc": "Ras.RGB", "rasa": "Ras.A",
    "one": "1.0", "half": "0.5", "konst": "Konst", "zero": "0",
}

_ALPHA_FRIENDLY = {
    "aprev": "Prev.A", "a0": "Reg0.A", "a1": "Reg1.A", "a2": "Reg2.A",
    "texa": "Tex.A", "rasa": "Ras.A", "konst": "Konst", "zero": "0",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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


def _friendly(enum_name, friendly_table):
    """Get a human-friendly name for a TEV input."""
    return friendly_table.get(enum_name, enum_name)


# ---------------------------------------------------------------------------
# TEV Stage Description (human-readable formula summary)
# ---------------------------------------------------------------------------

def describe_tev_combine(a_name, b_name, c_name, d_name, op_name, friendly_table):
    """Produce a one-line human-readable description of a TEV combiner stage.

    TEV formula: D + ((1-C)*A + C*B) for op=add, D - ((1-C)*A + C*B) for op=sub.
    """
    a = _friendly(a_name, friendly_table)
    b = _friendly(b_name, friendly_table)
    c = _friendly(c_name, friendly_table)
    d = _friendly(d_name, friendly_table)

    a_zero = a_name == "zero"
    b_zero = b_name == "zero"
    c_zero = c_name == "zero"
    d_zero = d_name == "zero"
    is_sub = (op_name == "sub")

    # Handle comparison ops specially
    if op_name not in ("add", "sub"):
        return "%s %s %s" % (a, op_name, b)

    op_sym = "-" if is_sub else "+"

    # Compute the blend term: (1-C)*A + C*B
    # When C=zero: blend = A (passthrough A)
    # When C=one:  blend = B (passthrough B)  [only for color, where "one" exists]
    # When A=zero: blend = C*B (multiply)
    # When B=zero: blend = (1-C)*A (multiply by inverse)
    # General case: Lerp(A, B, C)

    blend_part = None
    if a_zero and b_zero:
        blend_part = None  # blend term is zero
    elif c_zero:
        # (1-0)*A + 0*B = A
        blend_part = a
    elif c_name == "one":
        # (1-1)*A + 1*B = B
        blend_part = b
    elif a_zero:
        # C*B
        if c_name == "one":
            blend_part = b
        else:
            blend_part = "%s * %s" % (c, b)
    elif b_zero:
        # (1-C)*A
        blend_part = "%s * (1-%s)" % (a, c)
    else:
        # General lerp
        blend_part = "Lerp(%s, %s, %s)" % (a, b, c)

    # Combine with D
    if blend_part is None and d_zero:
        return "0 (black)"
    elif blend_part is None:
        return "Pass %s" % d
    elif d_zero:
        if is_sub:
            return "-(%s)" % blend_part
        return blend_part
    else:
        return "%s %s %s" % (d, op_sym, blend_part)


def describe_blend_mode(mode_val, src_val, dst_val):
    """Return human-readable blend mode string."""
    mode = _enum(BLEND_TYPE, mode_val)
    if mode == "none":
        return "Opaque (no blending)"
    elif mode == "subtract":
        return "Subtractive blending"
    elif mode == "logic":
        return "Logic op blending"

    src = _enum(BLEND_FACTOR, src_val)
    dst = _enum(BLEND_FACTOR, dst_val)

    # Common combos
    if src == "srcalpha" and dst == "invsrcalpha":
        return "Standard Alpha Blend"
    elif src == "one" and dst == "one":
        return "Additive Blend"
    elif src == "zero" and dst == "srcclr":
        return "Multiplicative Blend"
    elif src == "one" and dst == "zero":
        return "Opaque (overwrite)"

    return "%s * src + %s * dst" % (src, dst)


def describe_alpha_test(comp0_val, ref0_val, op_val, comp1_val, ref1_val):
    """Return human-readable alpha test string."""
    comp0 = _enum(COMPARE_FUNC, comp0_val)
    ref0 = str(ref0_val) if ref0_val is not None else "?"
    op = _enum(ALPHA_OP, op_val)
    comp1 = _enum(COMPARE_FUNC, comp1_val)
    ref1 = str(ref1_val) if ref1_val is not None else "?"

    def _test_str(comp, ref):
        if comp == "always":
            return "always"
        elif comp == "never":
            return "never"
        return "alpha %s %s" % (comp, ref)

    t0 = _test_str(comp0, ref0)
    t1 = _test_str(comp1, ref1)

    if t0 == "always" and t1 == "always":
        return "Always pass"
    elif t0 == "never" and t1 == "never":
        return "Never pass (invisible)"
    elif t1 == "always":
        return t0
    elif t0 == "always":
        return t1

    return "%s %s %s" % (t0, op, t1)


# ---------------------------------------------------------------------------
# Expand/Collapse State (per-stage, stored on WindowManager)
# ---------------------------------------------------------------------------

def _expand_prop_name(stage_idx):
    return "gx_tev_expand_%d" % stage_idx


def _is_expanded(context, stage_idx):
    wm = context.window_manager
    prop = _expand_prop_name(stage_idx)
    return getattr(wm, prop, False) if hasattr(wm, prop) else False


# ---------------------------------------------------------------------------
# Operators
# ---------------------------------------------------------------------------

class GX_TEV_OT_toggle_stage(bpy.types.Operator):
    """Toggle TEV stage detail visibility"""
    bl_idname = "gx_tev.toggle_stage"
    bl_label = "Toggle Stage"
    bl_options = {'INTERNAL'}

    stage: bpy.props.IntProperty()  # type: ignore

    def execute(self, context):
        wm = context.window_manager
        prop = _expand_prop_name(self.stage)
        if hasattr(wm, prop):
            setattr(wm, prop, not getattr(wm, prop))
        return {'FINISHED'}


# ---------------------------------------------------------------------------
# Panel
# ---------------------------------------------------------------------------

class MATERIAL_PT_gx_tev(bpy.types.Panel):
    bl_idname = "MATERIAL_PT_gx_tev"
    bl_label = "GX TEV Pipeline"
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

        # ---- Header ----
        header = layout.box()
        row = header.row()
        row.label(text=mat.name, icon='MATERIAL')
        sub = row.row(align=True)
        sub.alignment = 'RIGHT'
        sub.label(text="%d TEV Stages" % stage_count)
        sub.separator()
        sub.label(text="Cull: %s" % cull)

        # ---- Per-stage ----
        for i in range(stage_count):
            self._draw_stage(context, layout, mat, i)

        # ---- Footer: Render State ----
        self._draw_footer(layout, mat)

    def _draw_stage(self, context, layout, mat, i):
        prefix = "gc_tev_%d_" % i

        # Get all values for this stage
        ca = _enum(TEV_COLOR_IN, _get(mat, prefix + "colorInA"))
        cb = _enum(TEV_COLOR_IN, _get(mat, prefix + "colorInB"))
        cc = _enum(TEV_COLOR_IN, _get(mat, prefix + "colorInC"))
        cd = _enum(TEV_COLOR_IN, _get(mat, prefix + "colorInD"))
        cop = _enum(TEV_OP, _get(mat, prefix + "colorOp"))

        aa = _enum(TEV_ALPHA_IN, _get(mat, prefix + "alphaInA"))
        ab = _enum(TEV_ALPHA_IN, _get(mat, prefix + "alphaInB"))
        ac = _enum(TEV_ALPHA_IN, _get(mat, prefix + "alphaInC"))
        ad = _enum(TEV_ALPHA_IN, _get(mat, prefix + "alphaInD"))
        aop = _enum(TEV_OP, _get(mat, prefix + "alphaOp"))

        # Summary descriptions
        color_desc = describe_tev_combine(ca, cb, cc, cd, cop, _COLOR_FRIENDLY)
        alpha_desc = describe_tev_combine(aa, ab, ac, ad, aop, _ALPHA_FRIENDLY)

        tex_map = _get(mat, prefix + "texMap")
        has_tex = tex_map is not None and int(tex_map) != 0xFF

        # Stage box
        stage_box = layout.box()

        # Header row with expand toggle
        header_row = stage_box.row(align=True)

        expanded = _is_expanded(context, i)
        icon = 'DISCLOSURE_TRI_DOWN' if expanded else 'DISCLOSURE_TRI_RIGHT'
        toggle = header_row.operator("gx_tev.toggle_stage", text="", icon=icon, emboss=False)
        toggle.stage = i

        stage_icon = 'TEXTURE' if has_tex else 'NODE'
        header_row.label(text="Stage %d" % i, icon=stage_icon)

        # Destination register on the right
        dest_c = _enum(TEV_REGISTER, _get(mat, prefix + "colorRegId"))
        dest_a = _enum(TEV_REGISTER, _get(mat, prefix + "alphaRegId"))
        dest_sub = header_row.row()
        dest_sub.alignment = 'RIGHT'
        if dest_c == dest_a:
            dest_sub.label(text="-> %s" % dest_c)
        else:
            dest_sub.label(text="-> C:%s A:%s" % (dest_c, dest_a))

        # Summary lines (always visible)
        sum_col = stage_box.column(align=True)

        r = sum_col.row(align=True)
        r.label(text="", icon='COLOR')
        r.label(text="Color: %s" % color_desc)

        r = sum_col.row(align=True)
        r.label(text="", icon='RESTRICT_RENDER_ON')
        r.label(text="Alpha: %s" % alpha_desc)

        # Expanded details
        if not expanded:
            return

        # TEV Order
        tex_coord = _get(mat, prefix + "texCoordId")
        chan_id = _get(mat, prefix + "chanId")
        kc = _get(mat, prefix + "constColorSel")
        ka = _get(mat, prefix + "constAlphaSel")

        order_box = stage_box.box()
        order_box.label(text="Inputs", icon='LINKED')
        order_grid = order_box.grid_flow(row_major=True, columns=2, even_columns=True, align=True)
        order_grid.label(text="Tex Map: %s" % (_fmt_tex(tex_map)))
        order_grid.label(text="Tex Coord: %s" % (_fmt_val(tex_coord)))
        order_grid.label(text="Raster Chan: %s" % (_fmt_chan(chan_id)))
        order_grid.label(text="")
        order_grid.label(text="Konst Color: %s" % _enum(KONST_COLOR_SEL, kc))
        order_grid.label(text="Konst Alpha: %s" % _enum(KONST_ALPHA_SEL, ka))

        # Color Combine (detailed)
        self._draw_combine_detail(
            stage_box, "Color Combine", 'COLOR', prefix,
            TEV_COLOR_IN, mat,
            "colorInA", "colorInB", "colorInC", "colorInD",
            "colorOp", "colorBias", "colorScale", "colorClamp", "colorRegId"
        )

        # Alpha Combine (detailed)
        self._draw_combine_detail(
            stage_box, "Alpha Combine", 'RESTRICT_RENDER_ON', prefix,
            TEV_ALPHA_IN, mat,
            "alphaInA", "alphaInB", "alphaInC", "alphaInD",
            "alphaOp", "alphaBias", "alphaScale", "alphaClamp", "alphaRegId"
        )

    def _draw_combine_detail(self, parent, label, icon, prefix, in_table, mat,
                             inA, inB, inC, inD, op, bias, scale, clamp, regid):
        """Draw a detailed combiner section with editable integer fields."""
        box = parent.box()
        box.label(text=label, icon=icon)

        # Input row with editable integer props + enum name labels
        grid = box.grid_flow(row_major=True, columns=4, even_columns=True, align=True)

        for suffix, slot in [(inA, "A"), (inB, "B"), (inC, "C"), (inD, "D")]:
            key = prefix + suffix
            val = _get(mat, key)
            name = _enum(in_table, val)
            col = grid.column(align=True)
            col.label(text="%s: %s" % (slot, name))
            # Editable integer field
            if val is not None:
                col.prop(mat, '["%s"]' % key, text="")

        # Op / Bias / Scale row
        op_row = box.row(align=True)

        op_val = _get(mat, prefix + op)
        bias_val = _get(mat, prefix + bias)
        scale_val = _get(mat, prefix + scale)
        clamp_val = _get(mat, prefix + clamp)
        reg_val = _get(mat, prefix + regid)

        col = op_row.column(align=True)
        col.label(text="Op: %s" % _enum(TEV_OP, op_val))
        if op_val is not None:
            col.prop(mat, '["%s"]' % (prefix + op), text="")

        col = op_row.column(align=True)
        col.label(text="Bias: %s" % _enum(TEV_BIAS, bias_val))
        if bias_val is not None:
            col.prop(mat, '["%s"]' % (prefix + bias), text="")

        col = op_row.column(align=True)
        col.label(text="Scale: %s" % _enum(TEV_SCALE, scale_val))
        if scale_val is not None:
            col.prop(mat, '["%s"]' % (prefix + scale), text="")

        col = op_row.column(align=True)
        col.label(text="Clamp: %s" % ("Yes" if clamp_val else "No"))
        if clamp_val is not None:
            col.prop(mat, '["%s"]' % (prefix + clamp), text="")

        # Dest row
        dest_row = box.row()
        dest_row.label(text="Dest: %s" % _enum(TEV_REGISTER, reg_val))
        if reg_val is not None:
            dest_row.prop(mat, '["%s"]' % (prefix + regid), text="")

    def _draw_footer(self, layout, mat):
        """Draw render state footer with human-readable descriptions."""
        footer = layout.box()
        footer.label(text="Render State", icon='RENDERLAYERS')

        # Blend mode
        blend_mode = _get(mat, "gc_tev_blendMode")
        blend_src = _get(mat, "gc_tev_blendSrcFactor")
        blend_dst = _get(mat, "gc_tev_blendDstFactor")
        blend_desc = describe_blend_mode(blend_mode, blend_src, blend_dst)

        blend_box = footer.box()
        blend_box.label(text="Blend Mode: %s" % blend_desc, icon='GHOST_ENABLED')
        if blend_mode is not None and _enum(BLEND_TYPE, blend_mode) != "none":
            detail = blend_box.row(align=True)
            detail.label(text="Type: %s" % _enum(BLEND_TYPE, blend_mode))
            detail.label(text="Src: %s" % _enum(BLEND_FACTOR, blend_src))
            detail.label(text="Dst: %s" % _enum(BLEND_FACTOR, blend_dst))

        # Z-mode
        z_enable = _get(mat, "gc_tev_zEnable")
        z_func = _get(mat, "gc_tev_zFunc")
        z_update = _get(mat, "gc_tev_zEnableUpdate")

        z_box = footer.box()
        z_parts = []
        if z_enable:
            z_parts.append("Depth test: %s" % _enum(COMPARE_FUNC, z_func))
        else:
            z_parts.append("Depth test: OFF")
        z_parts.append("Write: %s" % ("ON" if z_update else "OFF"))
        z_box.label(text=" | ".join(z_parts), icon='EMPTY_SINGLE_ARROW')

        # Alpha compare
        ac_comp0 = _get(mat, "gc_tev_alphaComp0")
        ac_ref0 = _get(mat, "gc_tev_alphaRef0")
        ac_op = _get(mat, "gc_tev_alphaOp")
        ac_comp1 = _get(mat, "gc_tev_alphaComp1")
        ac_ref1 = _get(mat, "gc_tev_alphaRef1")

        alpha_desc = describe_alpha_test(ac_comp0, ac_ref0, ac_op, ac_comp1, ac_ref1)
        ac_box = footer.box()
        ac_box.label(text="Alpha Test: %s" % alpha_desc, icon='IMAGE_ALPHA')


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _fmt_tex(val):
    if val is None:
        return "?"
    v = int(val)
    if v == 0xFF:
        return "none"
    return "tex%d" % v


def _fmt_val(val):
    if val is None:
        return "?"
    v = int(val)
    if v == 0xFF:
        return "none"
    return str(v)


def _fmt_chan(val):
    if val is None:
        return "?"
    v = int(val)
    chan_names = {
        0: "Color0", 1: "Color1", 2: "Alpha0", 3: "Alpha1",
        4: "Color0A0", 5: "Color1A1", 6: "ColorZero", 7: "AlphaBump",
        8: "AlphaBumpN", 0xFF: "none",
    }
    return chan_names.get(v, "chan%d" % v)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

_expand_props_registered = False
MAX_TEV_STAGES = 16


def register():
    global _expand_props_registered
    bpy.utils.register_class(GX_TEV_OT_toggle_stage)
    bpy.utils.register_class(MATERIAL_PT_gx_tev)

    # Register expand/collapse booleans on WindowManager
    if not _expand_props_registered:
        for i in range(MAX_TEV_STAGES):
            setattr(
                bpy.types.WindowManager,
                _expand_prop_name(i),
                bpy.props.BoolProperty(default=False)
            )
        _expand_props_registered = True


def unregister():
    global _expand_props_registered
    bpy.utils.unregister_class(MATERIAL_PT_gx_tev)
    bpy.utils.unregister_class(GX_TEV_OT_toggle_stage)

    if _expand_props_registered:
        for i in range(MAX_TEV_STAGES):
            prop = _expand_prop_name(i)
            if hasattr(bpy.types.WindowManager, prop):
                delattr(bpy.types.WindowManager, prop)
        _expand_props_registered = False
