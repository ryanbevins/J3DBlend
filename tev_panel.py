"""GX Material Editor panel for Blender.

Provides a user-friendly material preset editor that translates to/from
raw GX TEV combiner configurations under the hood.
"""

import bpy


# ---------------------------------------------------------------------------
# GX enum tables
# ---------------------------------------------------------------------------

TEV_COLOR_IN = {
    0: "cprev", 1: "aprev", 2: "c0", 3: "a0", 4: "c1", 5: "a1",
    6: "c2", 7: "a2", 8: "texc", 9: "texa", 10: "rasc", 11: "rasa",
    12: "one", 13: "half", 14: "konst", 15: "zero",
}
TEV_COLOR_IN_REV = {v: k for k, v in TEV_COLOR_IN.items()}

TEV_ALPHA_IN = {
    0: "aprev", 1: "a0", 2: "a1", 3: "a2",
    4: "texa", 5: "rasa", 6: "konst", 7: "zero",
}
TEV_ALPHA_IN_REV = {v: k for k, v in TEV_ALPHA_IN.items()}

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

# Friendly names for TEV summaries
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


def _set(mat, key, value):
    """Set a custom property on the material."""
    mat[key] = value


def _enum(table, val):
    """Look up an enum value, return string."""
    if val is None:
        return "?"
    return table.get(int(val), "0x%02X" % int(val))


def _friendly(enum_name, friendly_table):
    return friendly_table.get(enum_name, enum_name)


# ---------------------------------------------------------------------------
# Material Preset Definitions
# ---------------------------------------------------------------------------

PRESETS = {
    "Solid Color": {
        "name": "Solid Color",
        "description": "Output = material register color. No texture.",
        "stages": [
            {
                "colorInA": 15, "colorInB": 15, "colorInC": 15, "colorInD": 2,  # zero,zero,zero,c0
                "colorOp": 0, "colorBias": 0, "colorScale": 0, "colorClamp": 1, "colorRegId": 0,
                "alphaInA": 7, "alphaInB": 7, "alphaInC": 7, "alphaInD": 1,   # zero,zero,zero,a0
                "alphaOp": 0, "alphaBias": 0, "alphaScale": 0, "alphaClamp": 1, "alphaRegId": 0,
                "texMap": 0xFF, "texCoordId": 0xFF, "chanId": 0xFF,
                "constColorSel": 0x00, "constAlphaSel": 0x00,
            },
        ],
        "blend_mode": {"mode": 0, "src": 0, "dst": 0},
        "alpha_test": {"comp0": 7, "ref0": 0, "op": 0, "comp1": 7, "ref1": 0},
        "z_mode": {"enable": 1, "func": 3, "update": 1},
    },
    "Textured": {
        "name": "Textured",
        "description": "Output = texture sample.",
        "stages": [
            {
                "colorInA": 15, "colorInB": 15, "colorInC": 15, "colorInD": 8,  # zero,zero,zero,texc
                "colorOp": 0, "colorBias": 0, "colorScale": 0, "colorClamp": 1, "colorRegId": 0,
                "alphaInA": 7, "alphaInB": 7, "alphaInC": 7, "alphaInD": 4,   # zero,zero,zero,texa
                "alphaOp": 0, "alphaBias": 0, "alphaScale": 0, "alphaClamp": 1, "alphaRegId": 0,
                "texMap": 0, "texCoordId": 0, "chanId": 0xFF,
                "constColorSel": 0x00, "constAlphaSel": 0x00,
            },
        ],
        "blend_mode": {"mode": 0, "src": 0, "dst": 0},
        "alpha_test": {"comp0": 7, "ref0": 0, "op": 0, "comp1": 7, "ref1": 0},
        "z_mode": {"enable": 1, "func": 3, "update": 1},
    },
    "Textured + Vertex Color": {
        "name": "Textured + Vertex Color",
        "description": "Output = texture * vertex color.",
        "stages": [
            {
                "colorInA": 15, "colorInB": 8, "colorInC": 10, "colorInD": 15,  # zero,texc,rasc,zero
                "colorOp": 0, "colorBias": 0, "colorScale": 0, "colorClamp": 1, "colorRegId": 0,
                "alphaInA": 7, "alphaInB": 4, "alphaInC": 5, "alphaInD": 7,   # zero,texa,rasa,zero
                "alphaOp": 0, "alphaBias": 0, "alphaScale": 0, "alphaClamp": 1, "alphaRegId": 0,
                "texMap": 0, "texCoordId": 0, "chanId": 4,  # Color0A0
                "constColorSel": 0x00, "constAlphaSel": 0x00,
            },
        ],
        "blend_mode": {"mode": 0, "src": 0, "dst": 0},
        "alpha_test": {"comp0": 7, "ref0": 0, "op": 0, "comp1": 7, "ref1": 0},
        "z_mode": {"enable": 1, "func": 3, "update": 1},
    },
    "Textured + Konst Color": {
        "name": "Textured + Konst Color",
        "description": "Output = texture * konst color.",
        "stages": [
            {
                "colorInA": 15, "colorInB": 8, "colorInC": 14, "colorInD": 15,  # zero,texc,konst,zero
                "colorOp": 0, "colorBias": 0, "colorScale": 0, "colorClamp": 1, "colorRegId": 0,
                "alphaInA": 7, "alphaInB": 4, "alphaInC": 6, "alphaInD": 7,   # zero,texa,konst,zero
                "alphaOp": 0, "alphaBias": 0, "alphaScale": 0, "alphaClamp": 1, "alphaRegId": 0,
                "texMap": 0, "texCoordId": 0, "chanId": 0xFF,
                "constColorSel": 0x0C, "constAlphaSel": 0x10,  # K0, K0.R
            },
        ],
        "blend_mode": {"mode": 0, "src": 0, "dst": 0},
        "alpha_test": {"comp0": 7, "ref0": 0, "op": 0, "comp1": 7, "ref1": 0},
        "z_mode": {"enable": 1, "func": 3, "update": 1},
    },
    "Vertex Color Only": {
        "name": "Vertex Color Only",
        "description": "Output = vertex color (raster).",
        "stages": [
            {
                "colorInA": 15, "colorInB": 15, "colorInC": 15, "colorInD": 10,  # zero,zero,zero,rasc
                "colorOp": 0, "colorBias": 0, "colorScale": 0, "colorClamp": 1, "colorRegId": 0,
                "alphaInA": 7, "alphaInB": 7, "alphaInC": 7, "alphaInD": 5,   # zero,zero,zero,rasa
                "alphaOp": 0, "alphaBias": 0, "alphaScale": 0, "alphaClamp": 1, "alphaRegId": 0,
                "texMap": 0xFF, "texCoordId": 0xFF, "chanId": 4,  # Color0A0
                "constColorSel": 0x00, "constAlphaSel": 0x00,
            },
        ],
        "blend_mode": {"mode": 0, "src": 0, "dst": 0},
        "alpha_test": {"comp0": 7, "ref0": 0, "op": 0, "comp1": 7, "ref1": 0},
        "z_mode": {"enable": 1, "func": 3, "update": 1},
    },
    "Textured + Lighting": {
        "name": "Textured + Lighting",
        "description": "Output = texture * vertex color with lighting (2 stages).",
        "stages": [
            {
                # Stage 0: sample texture -> prev
                "colorInA": 15, "colorInB": 15, "colorInC": 15, "colorInD": 8,  # zero,zero,zero,texc
                "colorOp": 0, "colorBias": 0, "colorScale": 0, "colorClamp": 1, "colorRegId": 0,
                "alphaInA": 7, "alphaInB": 7, "alphaInC": 7, "alphaInD": 4,   # zero,zero,zero,texa
                "alphaOp": 0, "alphaBias": 0, "alphaScale": 0, "alphaClamp": 1, "alphaRegId": 0,
                "texMap": 0, "texCoordId": 0, "chanId": 0xFF,
                "constColorSel": 0x00, "constAlphaSel": 0x00,
            },
            {
                # Stage 1: prev * raster -> prev
                "colorInA": 15, "colorInB": 0, "colorInC": 10, "colorInD": 15,  # zero,cprev,rasc,zero
                "colorOp": 0, "colorBias": 0, "colorScale": 0, "colorClamp": 1, "colorRegId": 0,
                "alphaInA": 7, "alphaInB": 0, "alphaInC": 5, "alphaInD": 7,   # zero,aprev,rasa,zero
                "alphaOp": 0, "alphaBias": 0, "alphaScale": 0, "alphaClamp": 1, "alphaRegId": 0,
                "texMap": 0xFF, "texCoordId": 0xFF, "chanId": 4,  # Color0A0
                "constColorSel": 0x00, "constAlphaSel": 0x00,
            },
        ],
        "blend_mode": {"mode": 0, "src": 0, "dst": 0},
        "alpha_test": {"comp0": 7, "ref0": 0, "op": 0, "comp1": 7, "ref1": 0},
        "z_mode": {"enable": 1, "func": 3, "update": 1},
    },
}

PRESET_ORDER = [
    "Solid Color",
    "Textured",
    "Textured + Vertex Color",
    "Textured + Konst Color",
    "Vertex Color Only",
    "Textured + Lighting",
    "Custom",
]

# Alpha mode constants
ALPHA_MODES = [
    ("OPAQUE", "Opaque", "No blending, no alpha test"),
    ("ALPHA_TEST", "Alpha Test", "Alpha compare enabled, no blending"),
    ("TRANSLUCENT", "Translucent", "Source alpha blending"),
]


# ---------------------------------------------------------------------------
# Preset Detection (pattern matching)
# ---------------------------------------------------------------------------

def _stage_color_inputs(mat, stage_idx):
    """Return (A, B, C, D) color input enum names for a stage."""
    prefix = "gc_tev_%d_" % stage_idx
    a = _enum(TEV_COLOR_IN, _get(mat, prefix + "colorInA"))
    b = _enum(TEV_COLOR_IN, _get(mat, prefix + "colorInB"))
    c = _enum(TEV_COLOR_IN, _get(mat, prefix + "colorInC"))
    d = _enum(TEV_COLOR_IN, _get(mat, prefix + "colorInD"))
    return (a, b, c, d)


def _stage_alpha_inputs(mat, stage_idx):
    """Return (A, B, C, D) alpha input enum names for a stage."""
    prefix = "gc_tev_%d_" % stage_idx
    a = _enum(TEV_ALPHA_IN, _get(mat, prefix + "alphaInA"))
    b = _enum(TEV_ALPHA_IN, _get(mat, prefix + "alphaInB"))
    c = _enum(TEV_ALPHA_IN, _get(mat, prefix + "alphaInC"))
    d = _enum(TEV_ALPHA_IN, _get(mat, prefix + "alphaInD"))
    return (a, b, c, d)


def detect_preset(mat):
    """Detect which preset best matches the material's TEV config.

    Returns the preset name string, or "Custom" if no match.
    """
    stage_count = int(_get(mat, "gc_tev_stageCount", 0))
    if stage_count == 0:
        return "Custom"

    ca, cb, cc, cd = _stage_color_inputs(mat, 0)
    aa, ab, ac, ad = _stage_alpha_inputs(mat, 0)

    if stage_count == 1:
        # Solid Color: D=c0 (or similar register color), rest zero
        if ca == "zero" and cb == "zero" and cc == "zero" and cd in ("c0", "a0", "c1", "c2"):
            if aa == "zero" and ab == "zero" and ac == "zero" and ad in ("a0", "a1", "a2"):
                return "Solid Color"

        # Textured: D=texc, rest zero
        if ca == "zero" and cb == "zero" and cc == "zero" and cd == "texc":
            return "Textured"

        # Vertex Color Only: D=rasc, rest zero
        if ca == "zero" and cb == "zero" and cc == "zero" and cd == "rasc":
            return "Vertex Color Only"

        # Textured + Vertex Color (multiply): A=zero, B=texc, C=rasc, D=zero
        if ca == "zero" and cb == "texc" and cc == "rasc" and cd == "zero":
            return "Textured + Vertex Color"

        # Textured + Vertex Color (alt multiply): A=texc, B=zero, C=rasc, D=zero
        if ca == "texc" and cb == "zero" and cc == "rasc" and cd == "zero":
            return "Textured + Vertex Color"

        # Textured + Vertex Color: other common patterns
        # B=rasc, C=texc is equivalent (commutative multiply)
        if ca == "zero" and cb == "rasc" and cc == "texc" and cd == "zero":
            return "Textured + Vertex Color"
        if ca == "rasc" and cb == "zero" and cc == "texc" and cd == "zero":
            return "Textured + Vertex Color"

        # Textured + Konst Color: A=zero, B=texc, C=konst, D=zero
        if ca == "zero" and cb == "texc" and cc == "konst" and cd == "zero":
            return "Textured + Konst Color"
        if ca == "texc" and cb == "zero" and cc == "konst" and cd == "zero":
            return "Textured + Konst Color"
        if ca == "zero" and cb == "konst" and cc == "texc" and cd == "zero":
            return "Textured + Konst Color"

    elif stage_count == 2:
        ca1, cb1, cc1, cd1 = _stage_color_inputs(mat, 1)

        # Textured + Lighting: stage0 = passthrough tex, stage1 = prev * raster
        is_tex_pass_s0 = (ca == "zero" and cb == "zero" and cc == "zero" and cd == "texc")
        is_mul_s1 = (
            (ca1 == "zero" and cb1 == "cprev" and cc1 == "rasc" and cd1 == "zero") or
            (ca1 == "zero" and cb1 == "rasc" and cc1 == "cprev" and cd1 == "zero") or
            (ca1 == "cprev" and cb1 == "zero" and cc1 == "rasc" and cd1 == "zero") or
            (ca1 == "rasc" and cb1 == "zero" and cc1 == "cprev" and cd1 == "zero")
        )
        if is_tex_pass_s0 and is_mul_s1:
            return "Textured + Lighting"

    return "Custom"


def detect_alpha_mode(mat):
    """Detect the alpha mode from blend and alpha test settings."""
    blend_mode = int(_get(mat, "gc_tev_blendMode", 0))
    blend_src = int(_get(mat, "gc_tev_blendSrcFactor", 0))
    blend_dst = int(_get(mat, "gc_tev_blendDstFactor", 0))

    # Translucent: blend mode with srcalpha/invsrcalpha
    if blend_mode == 1 and blend_src == 4 and blend_dst == 5:
        return "TRANSLUCENT"

    # Alpha test: check if alpha compare is non-trivial
    comp0 = int(_get(mat, "gc_tev_alphaComp0", 7))
    comp1 = int(_get(mat, "gc_tev_alphaComp1", 7))
    if comp0 != 7 or comp1 != 7:  # not both "always"
        return "ALPHA_TEST"

    return "OPAQUE"


# ---------------------------------------------------------------------------
# Apply preset / alpha mode to material properties
# ---------------------------------------------------------------------------

def _get_current_tex_info(mat):
    """Extract texture map and UV coord from the current material (to preserve)."""
    tex_map = _get(mat, "gc_tev_0_texMap", 0)
    tex_coord = _get(mat, "gc_tev_0_texCoordId", 0)
    return int(tex_map), int(tex_coord)


def apply_preset(mat, preset_name):
    """Write all gc_tev_* properties from a preset definition."""
    if preset_name == "Custom" or preset_name not in PRESETS:
        return

    preset = PRESETS[preset_name]
    stages = preset["stages"]

    # Preserve existing texture/UV if present
    old_tex, old_coord = _get_current_tex_info(mat)

    # Stage count
    _set(mat, "gc_tev_stageCount", len(stages))

    # Write each stage
    for i, stage in enumerate(stages):
        prefix = "gc_tev_%d_" % i
        for key, val in stage.items():
            _set(mat, prefix + key, val)

    # Restore texture/UV on stages that use texture
    for i, stage in enumerate(stages):
        prefix = "gc_tev_%d_" % i
        if stage.get("texMap", 0xFF) != 0xFF:
            if old_tex != 0xFF:
                _set(mat, prefix + "texMap", old_tex)
                _set(mat, prefix + "texCoordId", old_coord)

    # Blend mode
    bm = preset.get("blend_mode", {})
    _set(mat, "gc_tev_blendMode", bm.get("mode", 0))
    _set(mat, "gc_tev_blendSrcFactor", bm.get("src", 0))
    _set(mat, "gc_tev_blendDstFactor", bm.get("dst", 0))

    # Alpha test
    at = preset.get("alpha_test", {})
    _set(mat, "gc_tev_alphaComp0", at.get("comp0", 7))
    _set(mat, "gc_tev_alphaRef0", at.get("ref0", 0))
    _set(mat, "gc_tev_alphaOp", at.get("op", 0))
    _set(mat, "gc_tev_alphaComp1", at.get("comp1", 7))
    _set(mat, "gc_tev_alphaRef1", at.get("ref1", 0))

    # Z-mode
    zm = preset.get("z_mode", {})
    _set(mat, "gc_tev_zEnable", zm.get("enable", 1))
    _set(mat, "gc_tev_zFunc", zm.get("func", 3))
    _set(mat, "gc_tev_zEnableUpdate", zm.get("update", 1))

    # Store detected preset
    _set(mat, "gc_tev_preset", preset_name)


def apply_alpha_mode(mat, mode):
    """Apply alpha mode settings to blend/alpha-test properties."""
    if mode == "OPAQUE":
        _set(mat, "gc_tev_blendMode", 0)
        _set(mat, "gc_tev_blendSrcFactor", 0)
        _set(mat, "gc_tev_blendDstFactor", 0)
        _set(mat, "gc_tev_alphaComp0", 7)  # always
        _set(mat, "gc_tev_alphaRef0", 0)
        _set(mat, "gc_tev_alphaOp", 0)
        _set(mat, "gc_tev_alphaComp1", 7)  # always
        _set(mat, "gc_tev_alphaRef1", 0)
    elif mode == "ALPHA_TEST":
        _set(mat, "gc_tev_blendMode", 0)
        _set(mat, "gc_tev_blendSrcFactor", 0)
        _set(mat, "gc_tev_blendDstFactor", 0)
        _set(mat, "gc_tev_alphaComp0", 4)  # greater
        _set(mat, "gc_tev_alphaRef0", 128)
        _set(mat, "gc_tev_alphaOp", 0)
        _set(mat, "gc_tev_alphaComp1", 7)  # always
        _set(mat, "gc_tev_alphaRef1", 0)
    elif mode == "TRANSLUCENT":
        _set(mat, "gc_tev_blendMode", 1)       # blend
        _set(mat, "gc_tev_blendSrcFactor", 4)   # srcalpha
        _set(mat, "gc_tev_blendDstFactor", 5)   # invsrcalpha
        _set(mat, "gc_tev_alphaComp0", 7)  # always
        _set(mat, "gc_tev_alphaRef0", 0)
        _set(mat, "gc_tev_alphaOp", 0)
        _set(mat, "gc_tev_alphaComp1", 7)  # always
        _set(mat, "gc_tev_alphaRef1", 0)


# ---------------------------------------------------------------------------
# TEV Stage Description (human-readable formula summary) - kept for Advanced
# ---------------------------------------------------------------------------

def describe_tev_combine(a_name, b_name, c_name, d_name, op_name, friendly_table):
    """Produce a one-line human-readable description of a TEV combiner stage."""
    a = _friendly(a_name, friendly_table)
    b = _friendly(b_name, friendly_table)
    c = _friendly(c_name, friendly_table)
    d = _friendly(d_name, friendly_table)

    a_zero = a_name == "zero"
    b_zero = b_name == "zero"
    c_zero = c_name == "zero"
    d_zero = d_name == "zero"
    is_sub = (op_name == "sub")

    if op_name not in ("add", "sub"):
        return "%s %s %s" % (a, op_name, b)

    op_sym = "-" if is_sub else "+"

    blend_part = None
    if a_zero and b_zero:
        blend_part = None
    elif c_zero:
        blend_part = a
    elif c_name == "one":
        blend_part = b
    elif a_zero:
        if c_name == "one":
            blend_part = b
        else:
            blend_part = "%s * %s" % (c, b)
    elif b_zero:
        blend_part = "%s * (1-%s)" % (a, c)
    else:
        blend_part = "Lerp(%s, %s, %s)" % (a, b, c)

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
    mode = _enum(BLEND_TYPE, mode_val)
    if mode == "none":
        return "Opaque (no blending)"
    elif mode == "subtract":
        return "Subtractive blending"
    elif mode == "logic":
        return "Logic op blending"

    src = _enum(BLEND_FACTOR, src_val)
    dst = _enum(BLEND_FACTOR, dst_val)

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
# Expand/Collapse State (per-stage + advanced section, on WindowManager)
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


class GX_MAT_OT_apply_preset(bpy.types.Operator):
    """Apply a material preset, overwriting TEV stages"""
    bl_idname = "gx_mat.apply_preset"
    bl_label = "Apply Preset"
    bl_options = {'REGISTER', 'UNDO'}

    preset_name: bpy.props.StringProperty()  # type: ignore

    def execute(self, context):
        mat = context.material
        if mat is None:
            self.report({'ERROR'}, "No active material")
            return {'CANCELLED'}

        apply_preset(mat, self.preset_name)
        return {'FINISHED'}


class GX_MAT_OT_simplify_preset(bpy.types.Operator):
    """Simplify TEV stages to the closest matching preset"""
    bl_idname = "gx_mat.simplify_preset"
    bl_label = "Simplify to Preset"
    bl_options = {'REGISTER', 'UNDO'}

    def invoke(self, context, event):
        mat = context.material
        if mat is None:
            return {'CANCELLED'}

        detected = detect_preset(mat)
        if detected == "Custom":
            self.report({'WARNING'}, "No matching preset found for %s" % mat.name)
            return {'CANCELLED'}

        # Store for confirm dialog
        self._detected = detected
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        mat = context.material
        if mat is None:
            return {'CANCELLED'}

        detected = detect_preset(mat)
        if detected == "Custom":
            self.report({'WARNING'}, "No matching preset found")
            return {'CANCELLED'}

        apply_preset(mat, detected)
        self.report({'INFO'}, "Simplified %s to '%s'" % (mat.name, detected))
        return {'FINISHED'}

    @classmethod
    def description(cls, context, properties):
        mat = context.material
        if mat is None:
            return "Simplify TEV stages to preset"
        detected = detect_preset(mat)
        return "Simplify %s to '%s'? This will overwrite TEV stages." % (mat.name, detected)


class GX_MAT_OT_set_alpha_mode(bpy.types.Operator):
    """Set alpha mode (Opaque / Alpha Test / Translucent)"""
    bl_idname = "gx_mat.set_alpha_mode"
    bl_label = "Set Alpha Mode"
    bl_options = {'REGISTER', 'UNDO'}

    mode: bpy.props.StringProperty()  # type: ignore

    def execute(self, context):
        mat = context.material
        if mat is None:
            return {'CANCELLED'}
        apply_alpha_mode(mat, self.mode)
        return {'FINISHED'}


# ---------------------------------------------------------------------------
# Property Group (for UI enum dropdown state on WindowManager)
# ---------------------------------------------------------------------------

def _preset_items(self, context):
    """Generate enum items for the preset dropdown."""
    items = []
    for name in PRESET_ORDER:
        items.append((name, name, PRESETS[name]["description"] if name in PRESETS else "Raw TEV stages"))
    return items


def _alpha_mode_items(self, context):
    return ALPHA_MODES


class GXMatEditorProps(bpy.types.PropertyGroup):
    preset_enum: bpy.props.EnumProperty(
        name="Preset",
        items=_preset_items,
        description="Material preset",
    )  # type: ignore

    alpha_mode_enum: bpy.props.EnumProperty(
        name="Alpha Mode",
        items=_alpha_mode_items,
        description="Alpha transparency mode",
    )  # type: ignore


# ---------------------------------------------------------------------------
# Main Panel
# ---------------------------------------------------------------------------

class MATERIAL_PT_gx_tev(bpy.types.Panel):
    bl_idname = "MATERIAL_PT_gx_tev"
    bl_label = "GX Material Editor"
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
        wm = context.window_manager
        props = wm.gx_mat_editor

        stage_count = int(_get(mat, "gc_tev_stageCount", 0))
        detected = detect_preset(mat)
        alpha_mode = detect_alpha_mode(mat)

        # ---- Material Name ----
        header = layout.box()
        header.label(text="Material: %s" % mat.name, icon='MATERIAL')

        # ---- Preset Row ----
        preset_box = layout.box()

        # Display detected preset
        row = preset_box.row(align=True)
        row.label(text="Preset:")
        row.label(text=detected, icon='PRESET' if detected != "Custom" else 'QUESTION')

        # Preset selector dropdown + apply button
        row = preset_box.row(align=True)
        row.prop(props, "preset_enum", text="")
        op = row.operator("gx_mat.apply_preset", text="Apply", icon='CHECKMARK')
        op.preset_name = props.preset_enum

        # Simplify button
        if detected != "Custom":
            row = preset_box.row()
            row.operator("gx_mat.simplify_preset", text="Simplify to Preset", icon='FILE_REFRESH')

        # ---- Settings ----
        settings_box = layout.box()
        settings_box.label(text="Settings", icon='PREFERENCES')

        # Texture info (from stage 0)
        tex_map = _get(mat, "gc_tev_0_texMap")
        tex_coord = _get(mat, "gc_tev_0_texCoordId")
        has_texture = tex_map is not None and int(tex_map) != 0xFF

        row = settings_box.row()
        row.label(text="Texture:")
        if has_texture:
            row.label(text=_fmt_tex(tex_map))
            if tex_map is not None:
                row.prop(mat, '["gc_tev_0_texMap"]', text="idx")
        else:
            row.label(text="None")

        if has_texture:
            row = settings_box.row()
            row.label(text="UV Channel:")
            row.label(text=_fmt_val(tex_coord))
            if tex_coord is not None:
                row.prop(mat, '["gc_tev_0_texCoordId"]', text="idx")

        # Cull mode
        cull_val = _get(mat, "gc_tev_cullMode")
        row = settings_box.row()
        row.label(text="Cull Mode:")
        row.label(text=_enum(CULL_MODE, cull_val))
        if cull_val is not None:
            row.prop(mat, '["gc_tev_cullMode"]', text="")

        # ---- Alpha Mode ----
        alpha_box = layout.box()
        alpha_box.label(text="Alpha Mode: %s" % dict(ALPHA_MODES).get(alpha_mode, alpha_mode), icon='IMAGE_ALPHA')

        row = alpha_box.row(align=True)
        for mode_id, mode_label, _ in ALPHA_MODES:
            sub = row.row(align=True)
            sub.active = (alpha_mode != mode_id)
            op = sub.operator("gx_mat.set_alpha_mode", text=mode_label,
                              depress=(alpha_mode == mode_id))
            op.mode = mode_id

        # Alpha Test settings (visible if not opaque)
        if alpha_mode == "ALPHA_TEST":
            at_box = alpha_box.box()
            at_box.label(text="Alpha Test", icon='FILTER')

            comp0 = _get(mat, "gc_tev_alphaComp0")
            ref0 = _get(mat, "gc_tev_alphaRef0")

            row = at_box.row(align=True)
            row.label(text="Compare:")
            row.label(text=_enum(COMPARE_FUNC, comp0))
            if comp0 is not None:
                row.prop(mat, '["gc_tev_alphaComp0"]', text="")

            row = at_box.row(align=True)
            row.label(text="Ref:")
            if ref0 is not None:
                row.prop(mat, '["gc_tev_alphaRef0"]', text="")
            else:
                row.label(text="?")

        elif alpha_mode == "TRANSLUCENT":
            bl_box = alpha_box.box()
            bl_box.label(text="Blend: Standard Alpha Blend", icon='GHOST_ENABLED')
            blend_src = _get(mat, "gc_tev_blendSrcFactor")
            blend_dst = _get(mat, "gc_tev_blendDstFactor")
            row = bl_box.row(align=True)
            row.label(text="Src: %s" % _enum(BLEND_FACTOR, blend_src))
            row.label(text="Dst: %s" % _enum(BLEND_FACTOR, blend_dst))

        # ---- Z Mode ----
        z_enable = _get(mat, "gc_tev_zEnable")
        z_func = _get(mat, "gc_tev_zFunc")
        z_update = _get(mat, "gc_tev_zEnableUpdate")

        z_box = layout.box()
        z_box.label(text="Depth", icon='EMPTY_SINGLE_ARROW')
        row = z_box.row(align=True)
        row.label(text="Test: %s" % ("ON" if z_enable else "OFF"))
        if z_enable:
            row.label(text="Func: %s" % _enum(COMPARE_FUNC, z_func))
        row.label(text="Write: %s" % ("ON" if z_update else "OFF"))

        # ---- Advanced: Raw TEV Stages (collapsible) ----
        adv_box = layout.box()

        # Toggle for advanced section
        expanded = getattr(wm, "gx_tev_advanced_expand", False)
        icon = 'DISCLOSURE_TRI_DOWN' if expanded else 'DISCLOSURE_TRI_RIGHT'
        row = adv_box.row(align=True)
        row.prop(wm, "gx_tev_advanced_expand", text="Advanced: TEV Stages (%d)" % stage_count,
                 icon=icon, emboss=False)

        if expanded:
            for i in range(stage_count):
                self._draw_stage(context, adv_box, mat, i)

            # Render state footer
            self._draw_footer(adv_box, mat)

    def _draw_stage(self, context, layout, mat, i):
        """Draw a raw TEV stage (same as old panel, for Advanced section)."""
        prefix = "gc_tev_%d_" % i

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

        color_desc = describe_tev_combine(ca, cb, cc, cd, cop, _COLOR_FRIENDLY)
        alpha_desc = describe_tev_combine(aa, ab, ac, ad, aop, _ALPHA_FRIENDLY)

        tex_map = _get(mat, prefix + "texMap")
        has_tex = tex_map is not None and int(tex_map) != 0xFF

        stage_box = layout.box()

        # Header row with expand toggle
        header_row = stage_box.row(align=True)

        expanded = _is_expanded(context, i)
        icon = 'DISCLOSURE_TRI_DOWN' if expanded else 'DISCLOSURE_TRI_RIGHT'
        toggle = header_row.operator("gx_tev.toggle_stage", text="", icon=icon, emboss=False)
        toggle.stage = i

        stage_icon = 'TEXTURE' if has_tex else 'NODE'
        header_row.label(text="Stage %d" % i, icon=stage_icon)

        # Destination register
        dest_c = _enum(TEV_REGISTER, _get(mat, prefix + "colorRegId"))
        dest_a = _enum(TEV_REGISTER, _get(mat, prefix + "alphaRegId"))
        dest_sub = header_row.row()
        dest_sub.alignment = 'RIGHT'
        if dest_c == dest_a:
            dest_sub.label(text="-> %s" % dest_c)
        else:
            dest_sub.label(text="-> C:%s A:%s" % (dest_c, dest_a))

        # Summary lines
        sum_col = stage_box.column(align=True)

        r = sum_col.row(align=True)
        r.label(text="", icon='COLOR')
        r.label(text="Color: %s" % color_desc)

        r = sum_col.row(align=True)
        r.label(text="", icon='RESTRICT_RENDER_ON')
        r.label(text="Alpha: %s" % alpha_desc)

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

        grid = box.grid_flow(row_major=True, columns=4, even_columns=True, align=True)

        for suffix, slot in [(inA, "A"), (inB, "B"), (inC, "C"), (inD, "D")]:
            key = prefix + suffix
            val = _get(mat, key)
            name = _enum(in_table, val)
            col = grid.column(align=True)
            col.label(text="%s: %s" % (slot, name))
            if val is not None:
                col.prop(mat, '["%s"]' % key, text="")

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

        dest_row = box.row()
        dest_row.label(text="Dest: %s" % _enum(TEV_REGISTER, reg_val))
        if reg_val is not None:
            dest_row.prop(mat, '["%s"]' % (prefix + regid), text="")

    def _draw_footer(self, layout, mat):
        """Draw render state footer."""
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
# Registration
# ---------------------------------------------------------------------------

_expand_props_registered = False
MAX_TEV_STAGES = 16

_classes = (
    GXMatEditorProps,
    GX_TEV_OT_toggle_stage,
    GX_MAT_OT_apply_preset,
    GX_MAT_OT_simplify_preset,
    GX_MAT_OT_set_alpha_mode,
    MATERIAL_PT_gx_tev,
)


def register():
    global _expand_props_registered

    for cls in _classes:
        bpy.utils.register_class(cls)

    bpy.types.WindowManager.gx_mat_editor = bpy.props.PointerProperty(type=GXMatEditorProps)

    # Advanced section expand toggle
    bpy.types.WindowManager.gx_tev_advanced_expand = bpy.props.BoolProperty(
        name="Advanced TEV Stages",
        default=False,
    )

    # Per-stage expand/collapse booleans
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

    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)

    if hasattr(bpy.types.WindowManager, "gx_mat_editor"):
        del bpy.types.WindowManager.gx_mat_editor

    if hasattr(bpy.types.WindowManager, "gx_tev_advanced_expand"):
        del bpy.types.WindowManager.gx_tev_advanced_expand

    if _expand_props_registered:
        for i in range(MAX_TEV_STAGES):
            prop = _expand_prop_name(i)
            if hasattr(bpy.types.WindowManager, prop):
                delattr(bpy.types.WindowManager, prop)
        _expand_props_registered = False
