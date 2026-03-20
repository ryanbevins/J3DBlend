"""Test BuildFromArmature: create a 2-bone armature and verify JNT1 output.

Run with:
  "C:\Program Files\Blender Foundation\Blender 5.0\blender.exe" --background --python test_build_jnt1.py
"""
import sys
import os
import math
import bpy
from mathutils import Vector, Matrix, Euler

# Create a fresh scene
bpy.ops.wm.read_factory_settings(use_empty=True)

# Create armature with 2 bones
arm_data = bpy.data.armatures.new("TestArmature")
arm_obj = bpy.data.objects.new("TestArmature", arm_data)
bpy.context.collection.objects.link(arm_obj)
bpy.context.view_layer.objects.active = arm_obj

bpy.ops.object.mode_set(mode='EDIT')

# Root bone: at origin, pointing up Z (Blender convention)
root = arm_data.edit_bones.new("root")
root.head = (0, 0, 0)
root.tail = (0, 0, 1)

# Child bone: offset along Z, pointing up Z
child = arm_data.edit_bones.new("child")
child.head = (0, 0, 1)
child.tail = (0, 0, 2)
child.parent = root

bpy.ops.object.mode_set(mode='OBJECT')

# Import BuildFromArmature from the addon package
addon_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(addon_dir)
addon_name = os.path.basename(addon_dir)

if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Enable the addon so relative imports work
import importlib
pkg = importlib.import_module(addon_name)
Jnt1_mod = importlib.import_module(addon_name + '.Jnt1')

jnt = Jnt1_mod.Jnt1.BuildFromArmature(arm_obj)

print("\n========== BuildFromArmature Test Results ==========")

# Test 1: correct bone count and order
assert len(jnt.frames) == 2, f"Expected 2 frames, got {len(jnt.frames)}"
assert jnt.frames[0].name == 'root'
assert jnt.frames[1].name == 'child'
print("PASS: Bone count and order correct")

# Test 2: matrices/isMatrixValid lists match
assert len(jnt.matrices) == 2
assert len(jnt.isMatrixValid) == 2
assert all(v is None for v in jnt.matrices)
assert all(v is False for v in jnt.isMatrixValid)
print("PASS: matrices and isMatrixValid initialized correctly")

# Test 3: rawSectionData is None (forces DumpData reconstruction)
assert jnt._rawSectionData is None
print("PASS: _rawSectionData is None")

# Test 4: Root bone values
r = jnt.frames[0]
assert abs(r.t.x) < 1e-4 and abs(r.t.y) < 1e-4 and abs(r.t.z) < 1e-4, \
    f"Root translation should be ~zero, got ({r.t.x}, {r.t.y}, {r.t.z})"
assert abs(r.sx - 1.0) < 1e-4 and abs(r.sy - 1.0) < 1e-4 and abs(r.sz - 1.0) < 1e-4
print(f"PASS: Root t=({r.t.x:.4f}, {r.t.y:.4f}, {r.t.z:.4f}), s=({r.sx:.4f}, {r.sy:.4f}, {r.sz:.4f})")
print(f"      Root r=({math.degrees(r.rx):.2f}, {math.degrees(r.ry):.2f}, {math.degrees(r.rz):.2f}) deg")

# Test 5: Child bone has unit-length translation
c = jnt.frames[1]
t_mag = math.sqrt(c.t.x**2 + c.t.y**2 + c.t.z**2)
assert abs(t_mag - 1.0) < 1e-3, f"Child translation magnitude should be ~1.0, got {t_mag}"
assert abs(c.sx - 1.0) < 1e-4
print(f"PASS: Child t=({c.t.x:.4f}, {c.t.y:.4f}, {c.t.z:.4f}) mag={t_mag:.4f}")
print(f"      Child r=({math.degrees(c.rx):.2f}, {math.degrees(c.ry):.2f}, {math.degrees(c.rz):.2f}) deg")

# Test 6: Default JntEntry fields
assert r.matrix_type == 0
assert r.jnt_pad == 0x00ff
assert r.jnt_pad2 == 0xffff
assert r.jnt_unknown2 == 0.0
assert r._bbMin == [0.0, 0.0, 0.0]
assert r._bbMax == [0.0, 0.0, 0.0]
print("PASS: Default JntEntry fields correct")

# Test 7: DumpData doesn't crash (round-trip through JntEntry)
from io import BytesIO
BW = importlib.import_module(addon_name + '.BinaryWriter')
bw = BW.BinaryWriter()
bw._f = BytesIO()
jnt.DumpData(bw)
data = bw._f.getvalue()
assert len(data) > 0, "DumpData produced no output"
# JNT1 header tag
assert data[:4] == b'JNT1', f"Expected JNT1 tag, got {data[:4]}"
print(f"PASS: DumpData produced {len(data)} bytes with JNT1 tag")

print("\n========== All tests passed! ==========\n")
