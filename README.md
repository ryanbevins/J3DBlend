# J3DBlend

Blender 5.0 addon for importing and exporting Nintendo GameCube J3D formats -BMD/BDL models and BCK skeletal animations.

Fork of [blemd](https://github.com/niacdoial/blemd) by niacdoial, updated for Blender 5.0 with a fully working BCK animation export pipeline.

## What's New (vs blemd)

- **Blender 5.0 support** -uses the new layered action API for animation import/export
- **Working BCK export** -animations round-trip perfectly: import → edit in Blender → export → game
- **Fixed coordinate conversion** -GC Y-up ↔ Blender Z-up transform uses exact JNT1 rest pose data stored as bone custom properties, not Blender's internal matrix representation
- **Fixed translation export** -proper GC-space rotation matrix + rest position offset for all bones including deep hierarchy children
- **Robust export** -handles bones with missing keyframe channels (location/rotation/scale)

## Supported Formats

| Format | Import | Export |
|--------|--------|--------|
| BMD (Binary Model) | ✅ | ❌ (planned) |
| BDL (Binary Display List) | ✅ | ❌ |
| BCK (Bone Animation) | ✅ | ✅ |
| BTK (Texture Animation) | ✅ | ❌ |
| BTP (Texture Pattern) | ✅ | ❌ |

## Installation

1. Download this repo as a ZIP
2. In Blender: Edit → Preferences → Add-ons → Install from Disk
3. Select the ZIP file
4. Enable "Import-Export: BleMD" in the addon list

**Or** manually copy the folder to:
```
Windows: %APPDATA%/Blender Foundation/Blender/5.0/scripts/addons/
Linux:   ~/.config/blender/5.0/scripts/addons/
```

The addon folder **must** be named `blemd-master` or `blemd`.

## Usage

### Import BMD + Animations

1. File → Import → Nintendo BMD/BDL
2. Select a `.bmd` file
3. BCK animations are auto-detected from sibling `bck/` folder

Expected directory structure:
```
root/
  bmd/
    model.bmd
  bck/
    animation1.bck
    animation2.bck
```

### Export BCK Animation

1. Select the armature (must have been imported via BMD import -the GC rest pose data is stored on the bones)
2. File → Export → Nintendo BCK
3. The active action or NLA strip will be exported

**For new animations:** Duplicate an existing imported animation action, then modify the poses. This ensures all bones have keyframes on all channels. If creating from scratch, make sure every bone has Location + Rotation + Scale keyframes.

### Repacking into the Game

1. Export your BCK from Blender
2. Open the game's `.szs` archive in [GCFT](https://github.com/LagoLunatic/GCFT)
3. Replace the original BCK with your exported one
4. Save the archive
5. Rebuild the ISO with [pyisotools](https://github.com/JoshuaMKW/pyisotools)

## How the BCK Export Works

BCK files store **absolute** joint rotations (not deltas from rest pose). The game's J3D engine reads BCK values and directly replaces the rest pose -there's no additive blending.

The export pipeline:
1. Reads Blender fcurves (bone rotation mode: XZY)
2. Applies axis un-swap: Blender (x, -z, y) → GC (x, y, z)
3. Rotates by GC rest pose quaternion (stored during import as bone custom properties `gc_rest_rx/ry/rz`)
4. For translation: applies GC rest rotation matrix then adds rest position (`gc_rest_tx/ty/tz`)
5. Converts radians to s16 fixed-point and writes BCK binary

## Credits

- **niacdoial** - original blemd addon

## License

GPL v3 -same as the original blemd. See [LICENSE](LICENSE).
