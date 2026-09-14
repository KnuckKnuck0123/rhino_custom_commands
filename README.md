<img src="assets/array-tools-icon.png" alt="Array Studio icon: an array of teal architectural blocks" width="128" />

# Array Studio

Array tools for Rhino 8 with shift, rotation, scale, random/gradual variation,
and spatial falloff. Built from scratch for architecture students on Windows and
macOS, with four focused interfaces and support for curves, polysurfaces, groups,
and block instances.

**Version 0.9.0.** The source tools have been tested on Rhino 8 for macOS and
Windows. The Package Manager build is being prepared for clean-install testing
before public release.

## Get the Windows testing branch

With Git installed, open PowerShell or your IDE terminal:

```powershell
git clone --branch array-tools --single-branch https://github.com/KnuckKnuck0123/rhino_custom_commands.git rhino-array-tools
cd rhino-array-tools
```

Open **`rhino-array-tools` itself** in VS Code or Antigravity. This is the folder
containing `.vscode`, `README.md`, and `src`. **Do not open only `src`**: the editor
will not discover the hotkey task from there.

If you already have the repository cloned and your working tree is clean:

```powershell
git fetch origin
git switch --track origin/array-tools
```

If the local `array-tools` branch already exists, use `git switch array-tools`
instead. For later updates on that branch, use `git pull --ff-only`. Keep any
Windows testing changes committed or otherwise preserved before switching branches.

## Start from the IDE

1. Open Rhino **8.11 or newer** and create/open a model.
2. In Rhino's command line, run **`StartScriptServer`**. This can also be added to
   Rhino startup commands. Keep one Rhino instance open for straightforward targeting.
3. Open the cloned project root in the IDE. Enable workspace trust for your own
   checkout if the IDE asks; tasks cannot run in restricted mode.
4. Open **`src/ArrayTools.py`**, save it, and press the build shortcut:

   | Windows | macOS |
   | --- | --- |
   | **Ctrl+Shift+B** | **Cmd+Shift+B** |

5. Choose **Profile Array**, **Along Curve**, **Surface Array**, or **Volume Array**.
   Select objects and respond to picking prompts in the Rhino viewport.

Use the IDE command **Tasks: Run Build Task** and select **Run Rhino 8 Script** if
another extension overrides the shortcut. Use this task rather than the editor's
ordinary Python Run/Debug button: the code needs Rhino's Python environment.
There are **no pip dependencies to install** for using the tools.

The task sends the active saved file to Rhino with `rhinocode script`. It needs
no plugin installation, PATH configuration, or manual `RunPythonScript` command.
For a harmless connection check, open `src/TestConnection.py` and use the same
shortcut; Rhino should print an Array Studio connection message.

Standard executable paths are already configured in `.vscode/tasks.json`:

- Windows: `C:\Program Files\Rhino 8\System\rhinocode.exe`
- macOS: `/Applications/Rhino 8.app/Contents/Resources/bin/rhinocode`

For a custom Rhino installation, change the corresponding task path. If no panel
appears, check the IDE task terminal and Rhino command history, confirm
`StartScriptServer` is running, and ensure the active editor file is an entry script.

[McNeel RhinoCode CLI documentation](https://developer.rhino3d.com/en/guides/scripting/advanced-cli/)

## Try the tools

Open one of these entry scripts and press the build hotkey:

| File | Tool |
| --- | --- |
| `src/ArrayStudio.py` | The packaged `ArrayStudio` command and tool chooser |
| `src/ArrayTools.py` | Development launcher with module reloading |
| `src/ProfileArray.py` | Linear or grid arrays on the construction plane |
| `src/ArrayAlongCurve.py` | Objects along a 2D or 3D curve |
| `src/SurfaceArray.py` | U/V samples on a surface or selected face |
| `src/VolumeArray.py` | Exterior-face placement or interior grid fill |

Each panel has **All array tools** to return to the chooser. Closing the chooser
returns to the previous panel. Switching tools retains the source selection and
variation settings; select a new target for the new use case.

1. Select source curves, polysurfaces, a group, or block instances as one unit.
2. Pick a base point if the default source bounding-box center is unsuitable.
3. For curve, surface, or volume tools, select the target.
4. Adjust placement. Choose Random or Gradual under Variation, then edit Shift,
   Rotate, or Scale. Random uses minimum/maximum; gradual uses start/end values.
5. Optionally enable Falloff and pick its center. Set radius, strength and softness.
6. Inspect the temporary preview. Choose **Wireframe** or **Shaded** and use the
   **Color** picker to change its appearance. **Create array** adds output in one undo
   operation and closes the panel. **Cancel / Close** clears the preview.

Preview style and color affect only temporary display; generated objects retain
their source attributes. Curves remain lines in Shaded mode. Preview preferences
are remembered for the current Rhino session.

Uniform scale is on by default; turn it off for independent axis scales.
Blocks stay instances. Grouped sources move together and each multi-object copy
gets its own group. Originals are preserved, and the final output is selected.

## Current scope and limits

- Rhino 8 Python 3, RhinoCommon, and Eto; no additional Python packages required.
- Curve copies are spaced by count along curve length; distance-spacing input is
  not implemented yet. Closed curves omit the duplicate endpoint.
- Surface/exterior counts are U/V samples **per face**, not physical distance.
  They do not rebuild the target. Trims can reduce the resulting count.
- Interior fill requires a closed manifold polysurface. It filters nominal copy
  base points; objects can overlap or extend outside, especially after variation.
  This is not a collision-free packing tool.
- Gradual progression uses curve order, surface U/V, or spatial construction-plane
  axes across a volume. Variation axes follow each placement frame.
- Falloff is circular in plan and spherical in 3D. It blends scale back to 1 and
  shift/rotation back to 0 outside the zone; it does not remove copies.
- A maximum of 5,000 candidate placements is enforced. The UI limits each count
  to 100 and samples large previews; creation uses all valid placements.
- A copied source and target are captured for the preview. Reselect after editing
  the source/target geometry in Rhino.
- The installed package still needs a final clean-start check on both platforms.

## Verification

Seven pure-Python variation checks pass. In Rhino on macOS, geometry smoke checks
pass for linear/grid, vertical curves, surface UV, exterior/interior volumes,
falloff, and candidate limits. Separate headless-document checks pass for preview
isolation, groups, and block instance preservation/composed transforms. All four
Eto panels construct and their contextual controls pass a runtime smoke check.
Noah reported successful curve and surface trials on Mac and all four source tools
working on Windows. The resizing layout was revised after feedback. The packaged
command still needs a final clean-start check on both platforms.

Run standalone checks with `python3 -m unittest discover -s tests -p 'test_*.py'`.
The `tests/rhino_*.py` scripts run inside Rhino, not system Python.

## Packaging

The Rhino Script Editor project is `ArrayStudio.rhproj`. It publishes one Rhino
command, `ArrayStudio`, containing the four modes in its chooser. The package is
version `0.9.0`, licensed under MIT, and targets Rhino 8 on Windows and macOS.
The Package Manager identifier is `ArrayStudio`; the plugin and interface display
the product name as Array Studio. Public upload follows clean-install testing.

[McNeel script plugin publishing guide](https://developer.rhino3d.com/guides/scripting/projects-publish/)

## Documentation

- [Windows/Mac testing checklist and bug report template](docs/TESTING.md)
- [Development architecture and release handoff](docs/DEVELOPMENT.md)
- [Design brief and feature intent](DESIGN.md)
- [Icon provenance and generation prompt](assets/README.md)
