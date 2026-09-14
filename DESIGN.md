# Array tools brief

Status: first development implementation is available; see README for current
behavior, tests, and limits. Items labeled proposed include future refinements.

## Purpose and delivery

Build new array tools from scratch for architecture students using Rhino 8 on
Windows and macOS. Publish the finished plugin through Rhino Package Manager.
Do not salvage the existing array scripts. Preserve the editor testing workflow:
Cmd+Shift+B on Mac and Ctrl+Shift+B on Windows.

The defining capability is variation through translation (shift), rotation, and
scale. These controls should support both ordered arrays and aggregations.
Expose parameters through a graphical interface with numeric inputs and sliders.

## Required placement modes

| Mode | Source and target | Required controls and behavior |
| --- | --- | --- |
| Plan | A profile drawn in plan, repeated linearly or in a grid | Counts and spacing; shift, rotation, and scale in the working plane. Other plan patterns can be added. |
| Curve | A polysurface, group, or block instance repeated along a 2D or 3D curve | Placement along the curve with shift, rotation, and scale variation. |
| Surface | Objects repeated over a surface | Adjustable U and V sampling density without rebuilding the surface; shared variation controls. |
| Polysurface / volume | Objects distributed on a polysurface or within a volume | An Interior / Exterior switch selects enclosed fill or outside-face placement. Both support the shared variation controls. |

Surface sampling counts are independent of the number of control points or
visible isocurves. Changing U/V counts changes placement samples, not the target
geometry. Equal parameter steps do not necessarily produce equal physical spacing.
A polysurface has separate face domains; do not treat it as one continuous UV grid.

## Confirmed interface structure

Four dedicated tools: Profile Array, Along Curve, Surface Array, and Volume Array.
Each has a focused panel and an All array tools back button to the chooser.
Profile Array exposes Linear/Grid; Volume Array exposes Interior/Exterior.
Hide irrelevant controls and use descriptive labels. Panels are resizable, with
scrolling for longer controls and persistent Create/Cancel actions. Random ranges
are labeled Minimum/Maximum; gradual ranges are labeled Start/End.
All tools accept curves and 3D sources (polysurfaces, groups, blocks).

## Proposed shared interaction

1. Choose a placement mode and select source objects as one repeatable unit.
2. Set a base point and orientation for that unit; choose a target where needed.
3. Adjust placement counts or spacing.
4. Adjust shift, rotation, and scale using paired numeric fields and sliders.
5. Preview changes in the viewport, then create the array or cancel.

Use a Rhino Eto interface for Windows and Mac. Keep the same controls and meanings
on both platforms. Build the plan mode first to establish the shared interface
and transformation behavior before adding target-specific modes.

## Variation requirements

Support both random values within limits and gradual progression. Include an
optional falloff zone to localize variation. The proposed UI keeps Random / Gradual
as the variation choice and Falloff as a separate enable/disable control, allowing
either kind of variation to fade spatially.

Proposed variation controls:

- Per-axis shift in document units and rotation in degrees.
- Uniform scale by default, with independent axis scales when needed; 1 means
  original size, and scale stays positive in the initial version.
- Zero shift, zero rotation, and scale 1 produce an ordinary array.
- Random: minimum/maximum values, an explicit seed and a separate reroll button,
  so adjusting one parameter does not unexpectedly reshuffle every copy.
- Gradual: start/end values and a direction of progression. Use distance along
  a curve, a chosen grid or U/V direction, or a selected spatial axis for volume
  and multi-face placement; do not depend on arbitrary face enumeration.
- Apply scale and rotation around each copy's own base point, then shift it in
  the selected coordinate frame. Never accidentally rotate the entire array
  around the world origin.

### Proposed falloff behavior

Start with one point-centered zone: circular in the plan's construction plane and
spherical for 3D placement. Expose Pick Center, Radius, Strength, and Softness
with a visible viewport guide. Changes update the array preview. Additional zone
shapes and multiple zones are possible later extensions, not initial requirements.

At full strength, variation has its full effect at the center, fades smoothly
toward the radius, and has no effect outside. Softness controls the width of the
fade; zero softness gives a hard boundary. Evaluate distance from each original
placement point before variation, so shifting a copy does not change its own
falloff weight. Apply one weight to the whole source unit, including every member
of a group.

For weight w between 0 and 1, multiply shift and rotation by w and blend scale
from 1 toward its requested value: effective scale = 1 + w * (requested scale - 1).
This returns copies to ordinary array placement outside the zone instead of
shrinking them to zero. Falloff controls variation, not the number of copies.
Keep random samples stable while moving or resizing the zone.

## Proposed geometry behavior

- Plan: use the active construction plane, with shift in its X/Y directions and
  rotation around its normal. Linear and rectangular grid are the initial patterns;
  radial and staggered grids are possible later additions.
- Curve: offer count or distance spacing along actual curve length, with an
  orientation choice between keeping the source orientation and following the
  curve. Handle vertical tangents and inflection points without arbitrary flips.
- Surface: sample the surface's parameter domain, honor trim boundaries and holes,
  and offer alignment to the local surface frame. Avoid duplicate seam placements.
- Polysurface exterior: sample selected faces and handle shared edges
  without duplicate copies. Face orientation and density need explicit treatment.
- Volume interior: require a closed volume and begin with a 3D grid
  filtered by containment. Distinguish keeping copy base points inside from
  containing entire transformed objects; do not silently claim collision-free
  packing or full-object containment.
- Groups: transform all members together, preserving relative positions; group
  each resulting copy separately. Blocks remain block instances.

## Proposed implementation and acceptance checks

Separate placement-frame generation, variation, viewport preview, and document
creation so all modes share transformation and UI behavior. Start with Python 3
and RhinoCommon, with Eto for the UI, retaining direct source-file testing.

- Preserve source objects. Preview does not add permanent document geometry.
- Cancel and closing the UI remove preview state and leave the document unchanged.
- Create all output in one undoable operation, selecting the final geometry.
- Respect document units and tolerance. Validate counts and values before preview.
- Keep the interface responsive for large arrays with an explicit preview budget.
- Test grouped sources, blocks, trimmed faces, closed curves, surface seams, and
  degenerate inputs as their modes are implemented.
- Verify repeatable random seeds, gradual progression independent of face order,
  and falloff at the center, boundary, and outside. Zero falloff strength must
  restore the ordinary array, including scale 1, without changing copy counts.
- Verify the UI and installed package on both Windows and Mac before release.

## Confirmed scope decisions

- Build from scratch; do not salvage the legacy array scripts.
- Volume mode supports both interior and exterior placement through a switch.
- Variation supports both random and gradual behavior, plus a falloff zone.
- Detailed falloff controls and geometry defaults above are proposed starting
  points that can be refined in the working prototype.

## Technical references

- [McNeel Eto guides: cross-platform UI in Rhino](https://developer.rhino3d.com/en/guides/eto/)
- [Rhino-specific Eto integration](https://developer.rhino3d.com/guides/eto/rhino-specific/)
- [BrepFace.IsPointOnFace: trim-aware parameter sampling](https://mcneel.github.io/rhinocommon-api-docs/api/RhinoCommon/html/M_Rhino_Geometry_BrepFace_IsPointOnFace_1.htm)
- [Publishing Rhino script plugins](https://developer.rhino3d.com/guides/scripting/projects-publish/)
