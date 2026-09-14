# Development

## Runtime and launch

The tools run in **Rhino 8 Python 3**, using RhinoCommon and Eto. There are no
third-party Python dependencies. Python installed outside Rhino is useful only
for the Rhino-independent unit tests.

Open the repository root in the IDE, start Rhino 8.11+ and run
`StartScriptServer`, then save an entry script and press **Ctrl+Shift+B** on
Windows or **Cmd+Shift+B** on Mac. See [the testing guide](TESTING.md) for setup,
troubleshooting, and acceptance cases.

The default build task runs `rhinocode script` on `${file}` using:

| OS | Executable |
| --- | --- |
| Windows | `C:\Program Files\Rhino 8\System\rhinocode.exe` |
| macOS | `/Applications/Rhino 8.app/Contents/Resources/bin/rhinocode` |

Keep `src` intact: the entry scripts import neighboring modules. Running a shared
module directly will not open a tool. Source execution does not register Rhino
plugin commands or require package installation.

## Code map

| Path | Responsibility |
| --- | --- |
| `src/ArrayStudio.py` | Published `ArrayStudio` Rhino command entry point |
| `src/ArrayTools.py` | Development launcher with implementation reloads |
| `src/array_tools/app.py` | Tool chooser, window lifecycle, and switching state |
| `src/ProfileArray.py` | Dedicated plan linear/grid launcher |
| `src/ArrayAlongCurve.py` | Dedicated curve launcher |
| `src/SurfaceArray.py` | Dedicated surface launcher |
| `src/VolumeArray.py` | Dedicated exterior/interior launcher |
| `src/TestConnection.py` | Harmless IDE-to-Rhino connection check |
| `src/array_tools/variation.py` | Defaults, validation, deterministic random/gradual variation, falloff math; no Rhino imports |
| `src/array_tools/engine.py` | Placement frames and transforms; does not mutate documents |
| `src/array_tools/objects.py` | Source capture, group expansion, block-aware preview, output creation and cleanup |
| `src/array_tools/ui.py` | Shared Eto panels, contextual controls, picking, preview refresh, Create/Cancel |
| `.vscode/tasks.json` | OS-specific IDE test task |

Launchers reload the shared implementation during development. The active window
and chooser use Rhino's `scriptcontext.sticky`; switching tools transfers source
state and settings. Source and target geometry are captured for the current run:
reselect them after editing the underlying Rhino objects.

The panel's TableLayout keeps its header and action buttons fixed while settings
scroll. The revised layout has been exercised on macOS and Windows; additional
display-scaling reports remain welcome.

## Geometry contract

- A selected source set is one repeatable unit. The default base point is its
  bounding-box center; its frame uses the active construction plane.
- Placement generation returns transforms and nominal points. Scale, then XYZ
  rotations, then shift apply in each placement frame around the copy's base point.
- Curve mode divides by length using a count; local X follows the tangent when
  orientation following is enabled. Distance-spacing input is not implemented.
- Surface and exterior modes sample UV cell centers per face and reject trimmed
  regions. Counts do not alter control points and are not equal-distance spacing.
- Interior mode filters a construction-plane-aligned bounding-box grid with solid
  containment. Only nominal base points are constrained, before variation.
- Randomness is deterministic per seed and placement index. Falloff weights use
  nominal points, blending shift/rotation to 0 and scale to 1. Plan falloff ignores
  distance normal to the construction plane; 3D falloff uses spherical distance.
- The engine caps candidate placements at 5,000 before filtering. The UI caps
  individual counts at 100; preview can sample output while Create uses all valid
  placements. Neither preview nor creation implements collision avoidance.
- Preview is transient. Create adds output in one undo record, preserving source
  objects and block definitions; every multi-object copy receives its own group.

## Checks

From the repository root, run the standalone suite:

```sh
python3 -m unittest discover -s tests -p 'test_*.py'
```

On Windows with the Python launcher:

```powershell
py -3 -m unittest discover -s tests -p "test_*.py"
```

These seven tests cover variation bounds/reproducibility, gradual endpoints,
uniform scaling, falloff behavior, and validation. They cannot test Rhino geometry
or Eto.

Run the following **inside Rhino Python 3**, through ScriptEditor or the IDE task:

- `tests/rhino_engine_smoke.py`: placement/transformation checks, vertical curve
  frames, surface counts, box volume counts, volume progression, falloff, and limits.
  It constructs in-memory geometry without changing the model.
- `tests/rhino_objects_checks.py`: preview isolation, group capture/creation, and
  block preservation/composed transforms in a separate headless document. Select
  Python 3 if running it in ScriptEditor.

Live viewport appearance, Undo, panel navigation, window resizing, irregular target
geometry, and OS-specific behavior require [manual testing](TESTING.md).

## Package Manager releases

`ArrayStudio.rhproj` builds Array Studio as one `ArrayStudio` Rhino command.
The embedded `array_tools` Python library contains the chooser and four modes.
The project is MIT licensed and targets Rhino 8 on Windows and macOS. Build the
distributable, inspect its contents, and test a clean installation without this
source checkout before publishing a new version to the public Package Manager server.

On macOS, build the final package from the repository root with:

```sh
sh scripts/build_package.sh
```

The script first uses RhinoCode to compile the `.rhp`, removes generated solution
sources, then replaces the minimal manifest with `package/manifest.yml` and adds
the 64 px package icon, MIT license, and README before Yak creates the final
`rh8-any` package. The output is written under `build/package/rh8/` and is
intentionally excluded from Git.

See McNeel's [RhinoCode CLI guide](https://developer.rhino3d.com/en/guides/scripting/advanced-cli/)
and [script plugin publishing guide](https://developer.rhino3d.com/guides/scripting/projects-publish/).
The [design brief](../DESIGN.md) includes proposed refinements; the implementation
and README describe what is available now.
