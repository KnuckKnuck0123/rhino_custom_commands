# Testing Array Studio

This guide covers source testing in Rhino 8. The source hotkey does not test the
installed Package Manager command.

## Start on Windows or Mac

1. Clone the repository and open the **repository root** in VS Code
   or a compatible IDE. `.vscode/tasks.json` must be inside the opened workspace;
   opening only `src` will hide the task.
2. Start Rhino **8.11 or newer**, open a scratch model, and run `StartScriptServer`
   in Rhino. Use one Rhino instance while testing.
3. Open and save `src/TestConnection.py`. Press **Ctrl+Shift+B on Windows** or
   **Cmd+Shift+B on Mac**. Look for its connection message in Rhino.
4. Open `src/ArrayTools.py` and use the same hotkey for the chooser, or run a
   dedicated launcher: `ProfileArray.py`, `ArrayAlongCurve.py`, `SurfaceArray.py`,
   or `VolumeArray.py` in `src`.

The task runs the **active saved file**. Do not use the IDE's ordinary Python Run
button or install `Rhino`, `Eto`, or `scriptcontext` with pip; Rhino supplies them.
If the IDE requests workspace trust, review and trust your own checkout to enable
its task. If the command is missing, use **Tasks: Run Build Task** and select
**Run Rhino 8 Script**. Custom Rhino installation paths require an edit to the
appropriate OS entry in `.vscode/tasks.json`.

## Current evidence

| Area | Current evidence |
| --- | --- |
| macOS interactive curve array | Noah's first test worked well |
| macOS interactive surface array | Noah's initial test worked; complex targets still need coverage |
| Pure Python variation checks | Seven checks previously passed |
| Rhino geometry smoke checks | Previously passed, including box interior/exterior placement |
| Rhino source/group/block checks | Previously passed in a separate headless document |
| Volume interactive use | Noah reports all four source tools working on Windows |
| Window sizing | Revised layout exercised on macOS and Windows; broader display-scaling coverage welcome |
| Windows source workflow and UI | Noah reports all tools working |
| Installed package on macOS | Clean-start `ArrayStudio` command check passed |
| Public Package Manager | `ArrayStudio (0.9.0)` verified on McNeel's server |

Automated checks do not establish interactive acceptance. Record platform, Rhino
version, and the cases tested when updating this table.

## Volume: first manual test

Use a small, asymmetric source so orientation is visible: a polysurface, a group
of two different objects, or the existing block. Keep the source separate from
the target. For predictable counts, use a plain closed box target without split
faces, an unrotated World Top construction plane, and Variation set to **None**.

1. Run `src/VolumeArray.py`, select the source, and select the box as target.
2. Choose **Interior**, set X/Y/Z counts to **3/3/3**, and inspect the preview.
   Expect **27 copies**, with nominal base points inside the box.
3. Create the array. Confirm the source and target remain, then run Undo once:
   the created array should disappear together.
4. Reopen, reselect, choose **Exterior**, and set U/V counts to **2/2**. A plain
   six-face box should produce **24 copies**, four per face. Toggle orientation
   following and inspect all sides, including the bottom face.
5. Repeat with a curved closed solid. Interior filters a construction-plane grid;
   exterior samples each face independently, so spacing and counts vary by face.
6. Try an open polysurface in Interior. Expect a closed/manifold target error and
   no created output. Exterior should still accept suitable open polysurfaces.

Interior containment applies to **base points before variation**. Copies may
overlap or extend beyond the solid; this is not full-object containment or packing.
For a multi-object source, “27 copies” means 27 repeated units, not 27 individual
Rhino objects.

## Shared acceptance checklist

- **Source types:** repeat with a curve, polysurface, group, and block. Members of
  a group should keep their relative positions and each copy should be grouped
  separately. Blocks should remain instances of the original definition.
- **Random:** set nonzero shift/rotation ranges and scale 0.7–1.3. The same seed
  and placement settings should reproduce the arrangement; **New random
  arrangement** should change it. Test both uniform and independent axis scale.
- **Gradual:** use scale 1–2 or rotation 0–90 degrees and inspect progression.
  Curve uses path order; surface uses U/V; volume uses the selected spatial axis.
- **Falloff:** enable a zone with a center among the placements. Change radius,
  strength, and softness. Outside the zone, copies should return to ordinary
  placement and scale 1. Strength 0 should remove variation without removing
  copies. Confirm this for both Random and Gradual.
- **Preview appearance:** switch Wireframe/Shaded and change Color for a solid,
  group, and block. Curves should remain lines. Create output and verify that its
  source object colors/materials are preserved.
- **Cancel:** after changing preview settings, use Cancel / Close and the window
  close button. Preview and zone guides should disappear without adding objects.
- **Undo:** Create should preserve originals, select output, and undo as one
  operation. Test this with grouped and block sources too.
- **Navigation:** use **All array tools**, choose another panel, and return.
  Source and variation settings should carry over; select a target for the new
  use case. Closing the chooser should restore the preceding panel.
- **Sizing:** shrink and enlarge every panel, including each Variation subtab.
  Scroll to every field; Create/Cancel and navigation must remain reachable.
  Repeat at Windows display scaling such as 125%/150% and on the smaller display.
- **Surface shapes:** test a doubly curved surface, an irregular trimmed outline,
  a surface with a hole, and a selected polysurface face. No nominal placements
  should land in trimmed-out regions. UV sampling can have uneven physical
  spacing; increasing counts must not rebuild the target.
- **Curve shapes:** test an open planar path, a closed path, a vertical path, and
  a 3D curve. Check end placement and orientation; closed paths should not double
  up the seam endpoint.
- **Limits:** a 100×100 grid should show the candidate-limit error rather than
  create output. Start ordinary tests with low counts and small source geometry.

## Report a problem

Include the branch commit (`git rev-parse --short HEAD`), OS, Rhino version,
display scaling for UI issues, launcher, source/target types, placement counts,
variation/falloff values, expected result, actual result, and Rhino command-history
error text. A small `.3dm` reproducer is useful when the behavior depends on geometry.
