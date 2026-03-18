# -*- coding: utf-8 -*-
"""
StairGenerator.py - Parametric stair generator for Rhino.
Supports: Straight Run, L-Shaped, Switchback (U-Shape), Spiral.
IBC compliant: auto-inserts landings every 12'-0" of rise,
plus required top and bottom landings.
"""
import Rhino
import Rhino.Geometry as rg
import scriptcontext as sc
import rhinoscriptsyntax as rs
import math

# IBC max vertical rise between landings: 12'-0" = 144"
MAX_RISE_BETWEEN_LANDINGS_IN = 144.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_unit_scale():
    """Scale factor so defaults (in inches) adapt to document units."""
    units = sc.doc.ModelUnitSystem
    lookup = {
        Rhino.UnitSystem.Inches: 1.0,
        Rhino.UnitSystem.Feet: 1.0 / 12.0,
        Rhino.UnitSystem.Millimeters: 25.4,
        Rhino.UnitSystem.Centimeters: 2.54,
        Rhino.UnitSystem.Meters: 0.0254,
    }
    return lookup.get(units, 1.0)


def extrude_profile(profile_pts, direction, tol):
    """Extrude a closed 2-D polyline profile into a capped solid Brep.

    Args:
        profile_pts: list of Point3d forming a closed polyline (last == first).
        direction:   Vector3d extrusion direction.
        tol:         document absolute tolerance.
    Returns:
        A Brep or None.
    """
    faces = []
    for i in range(len(profile_pts) - 1):
        seg = rg.LineCurve(profile_pts[i], profile_pts[i + 1])
        srf = rg.Surface.CreateExtrusion(seg, direction)
        if srf:
            faces.append(srf.ToBrep())
    if not faces:
        return None
    joined = rg.Brep.JoinBreps(faces, tol)
    if joined and len(joined) > 0:
        capped = joined[0].CapPlanarHoles(tol)
        return capped if capped else joined[0]
    return None


def straight_profile(n_risers, rh, td, slab, x0=0.0, z0=0.0):
    """Return a list of Point3d describing a closed stepped profile in XZ."""
    pts = []
    # Stepped top surface
    for i in range(n_risers):
        pts.append(rg.Point3d(x0 + i * td, 0, z0 + i * rh))
        pts.append(rg.Point3d(x0 + i * td, 0, z0 + (i + 1) * rh))
    # Underside (diagonal)
    last_x = x0 + (n_risers - 1) * td
    top_z  = z0 + n_risers * rh
    pts.append(rg.Point3d(last_x, 0, top_z - slab))
    pts.append(rg.Point3d(x0, 0, z0 - slab))
    # Close
    pts.append(rg.Point3d(pts[0].X, pts[0].Y, pts[0].Z))
    return pts


def add_brep(brep, objects_list):
    """Add a valid Brep to the document, appending the GUID to objects_list."""
    if brep and brep.IsValid:
        guid = sc.doc.Objects.AddBrep(brep)
        if guid:
            objects_list.append(guid)


def make_box(min_pt, max_pt):
    """Create a Brep box from two diagonal corner Point3d values."""
    bbox = rg.BoundingBox(min_pt, max_pt)
    return rg.Brep.CreateFromBox(bbox)


# ---------------------------------------------------------------------------
# Stair builders
# ---------------------------------------------------------------------------

def split_into_flights(n, rh, max_rise):
    """Split total risers into code-compliant flights (max rise each).

    Returns a list of riser-counts per flight.
    """
    max_risers = max(2, int(math.floor(max_rise / rh)))
    flights = []
    remaining = n
    while remaining > 0:
        flight_n = min(remaining, max_risers)
        flights.append(flight_n)
        remaining -= flight_n
    return flights


def build_straight(n, rh, td, w, slab, land_depth, max_rise):
    """Straight-run stair with auto-intermediate landings per IBC.

    Includes bottom landing, flight(s), intermediate landings, and top landing.
    """
    tol = sc.doc.ModelAbsoluteTolerance
    objs = []
    flights = split_into_flights(n, rh, max_rise)
    direction = rg.Vector3d(0, w, 0)

    x_cur = 0.0
    z_cur = 0.0

    # --- Bottom landing ---
    add_brep(make_box(
        rg.Point3d(x_cur - land_depth, 0, z_cur - slab),
        rg.Point3d(x_cur, w, z_cur)
    ), objs)

    for fi, flight_n in enumerate(flights):
        # Build this flight
        profile = straight_profile(flight_n, rh, td, slab, x0=x_cur, z0=z_cur)
        brep = extrude_profile(profile, direction, tol)
        add_brep(brep, objs)

        # Advance position to end of this flight
        x_cur += (flight_n - 1) * td
        z_cur += flight_n * rh

        # Intermediate landing (between flights)
        if fi < len(flights) - 1:
            add_brep(make_box(
                rg.Point3d(x_cur, 0, z_cur - slab),
                rg.Point3d(x_cur + land_depth, w, z_cur)
            ), objs)
            x_cur += land_depth

    # --- Top landing ---
    add_brep(make_box(
        rg.Point3d(x_cur, 0, z_cur - slab),
        rg.Point3d(x_cur + land_depth, w, z_cur)
    ), objs)

    num_flights = len(flights)
    if num_flights > 1:
        print("  -> {} flights with {} intermediate landing(s)".format(
            num_flights, num_flights - 1))

    return objs


def build_l_shaped(n, rh, td, w, slab, turn, landing_at, land_depth):
    """L-shaped stair with bottom landing, turn landing, and top landing."""
    tol = sc.doc.ModelAbsoluteTolerance
    objs = []

    run1_n = landing_at
    run2_n = n - landing_at

    # --- Bottom landing ---
    add_brep(make_box(
        rg.Point3d(-land_depth, 0, -slab),
        rg.Point3d(0, w, 0)
    ), objs)

    # --- Run 1 (along +X) ---
    p1 = straight_profile(run1_n, rh, td, slab)
    brep1 = extrude_profile(p1, rg.Vector3d(0, w, 0), tol)
    add_brep(brep1, objs)

    # Landing position
    land_x = (run1_n - 1) * td
    land_z = run1_n * rh

    # --- Turn landing box ---
    if turn == "Left":
        land_min = rg.Point3d(land_x, 0, land_z - slab)
        land_max = rg.Point3d(land_x + land_depth, w, land_z)
    else:
        land_min = rg.Point3d(land_x, 0, land_z - slab)
        land_max = rg.Point3d(land_x + land_depth, w, land_z)
    add_brep(make_box(land_min, land_max), objs)

    # --- Run 2 (turned 90 degrees) ---
    p2 = straight_profile(run2_n, rh, td, slab, z0=0.0)
    brep2 = extrude_profile(p2, rg.Vector3d(w, 0, 0), tol)
    if brep2:
        if turn == "Left":
            rot = rg.Transform.Rotation(-math.pi / 2, rg.Vector3d.ZAxis, rg.Point3d.Origin)
            mov = rg.Transform.Translation(rg.Vector3d(land_x + land_depth, w, land_z))
        else:
            rot = rg.Transform.Rotation(math.pi / 2, rg.Vector3d.ZAxis, rg.Point3d.Origin)
            mov = rg.Transform.Translation(rg.Vector3d(land_x, 0, land_z))
        brep2.Transform(rot)
        brep2.Transform(mov)
        add_brep(brep2, objs)

    # --- Top landing (at the end of run 2) ---
    top_z = n * rh
    if turn == "Left":
        top_x = land_x + land_depth
        top_y = w
        run2_end_y = top_y + (run2_n - 1) * td
        add_brep(make_box(
            rg.Point3d(top_x, run2_end_y, top_z - slab),
            rg.Point3d(top_x + w, run2_end_y + land_depth, top_z)
        ), objs)
    else:
        top_x = land_x
        run2_end_y = -(run2_n - 1) * td
        add_brep(make_box(
            rg.Point3d(top_x - w, run2_end_y - land_depth, top_z - slab),
            rg.Point3d(top_x, run2_end_y, top_z)
        ), objs)

    return objs


def build_switchback(n, rh, td, w, slab, land_depth):
    """Switchback (U-shape) stair with bottom, middle, and top landings."""
    tol = sc.doc.ModelAbsoluteTolerance
    objs = []

    run1_n = n // 2
    run2_n = n - run1_n

    # --- Bottom landing ---
    add_brep(make_box(
        rg.Point3d(-land_depth, 0, -slab),
        rg.Point3d(0, w, 0)
    ), objs)

    # --- Run 1 (along +X) ---
    p1 = straight_profile(run1_n, rh, td, slab)
    brep1 = extrude_profile(p1, rg.Vector3d(0, w, 0), tol)
    add_brep(brep1, objs)

    land_x = (run1_n - 1) * td
    land_z = run1_n * rh

    # --- Middle (switchback) landing ---
    total_y = 2 * w + land_depth
    land_min = rg.Point3d(land_x, 0, land_z - slab)
    land_max = rg.Point3d(land_x + td, total_y, land_z)
    add_brep(make_box(land_min, land_max), objs)

    # --- Run 2 (along -X, offset in Y) ---
    p2 = straight_profile(run2_n, rh, td, slab)
    brep2 = extrude_profile(p2, rg.Vector3d(0, w, 0), tol)
    if brep2:
        mirror = rg.Transform.Mirror(rg.Plane(rg.Point3d.Origin, rg.Vector3d.XAxis))
        brep2.Transform(mirror)
        move = rg.Transform.Translation(
            rg.Vector3d(land_x + td, w + land_depth, land_z)
        )
        brep2.Transform(move)
        add_brep(brep2, objs)

    # --- Top landing (at end of run 2) ---
    top_z = n * rh
    run2_end_x = land_x + td - (run2_n - 1) * td
    add_brep(make_box(
        rg.Point3d(run2_end_x - land_depth, w + land_depth, top_z - slab),
        rg.Point3d(run2_end_x, 2 * w + land_depth, top_z)
    ), objs)

    return objs


def build_spiral(n, rh, w, slab, inner_r, total_deg):
    """Spiral stair: wedge-shaped treads arranged around a center pole."""
    tol = sc.doc.ModelAbsoluteTolerance
    objs = []
    outer_r = inner_r + w
    step_angle = math.radians(total_deg) / n

    for i in range(n):
        a0 = i * step_angle
        a1 = a0 + step_angle
        z_top = (i + 1) * rh
        z_bot = z_top - slab

        # Four corners on the top surface, four on the bottom
        cos0, sin0 = math.cos(a0), math.sin(a0)
        cos1, sin1 = math.cos(a1), math.sin(a1)

        top = [
            rg.Point3d(inner_r * cos0, inner_r * sin0, z_top),
            rg.Point3d(outer_r * cos0, outer_r * sin0, z_top),
            rg.Point3d(outer_r * cos1, outer_r * sin1, z_top),
            rg.Point3d(inner_r * cos1, inner_r * sin1, z_top),
        ]
        bot = [
            rg.Point3d(inner_r * cos0, inner_r * sin0, z_bot),
            rg.Point3d(outer_r * cos0, outer_r * sin0, z_bot),
            rg.Point3d(outer_r * cos1, outer_r * sin1, z_bot),
            rg.Point3d(inner_r * cos1, inner_r * sin1, z_bot),
        ]

        # Build 6 faces (top, bottom, 4 sides) as planar breps
        faces = []
        # Top & bottom quads
        for quad in [top, bot]:
            crv = rg.PolylineCurve([quad[0], quad[1], quad[2], quad[3], quad[0]])
            face = rg.Brep.CreatePlanarBreps(crv, tol)
            if face:
                faces.extend(face)
        # Four side quads
        sides = [
            [top[0], top[1], bot[1], bot[0]],
            [top[1], top[2], bot[2], bot[1]],
            [top[2], top[3], bot[3], bot[2]],
            [top[3], top[0], bot[0], bot[3]],
        ]
        for sq in sides:
            crv = rg.PolylineCurve([sq[0], sq[1], sq[2], sq[3], sq[0]])
            face = rg.Brep.CreatePlanarBreps(crv, tol)
            if face:
                faces.extend(face)

        if faces:
            joined = rg.Brep.JoinBreps(faces, tol)
            if joined:
                for b in joined:
                    add_brep(b, objs)

    # Center pole
    axis = rg.Line(rg.Point3d(0, 0, 0), rg.Point3d(0, 0, n * rh))
    pole = rg.Brep.CreateFromCylinder(
        rg.Cylinder(rg.Circle(rg.Plane.WorldXY, inner_r * 0.3), n * rh),
        True, True
    )
    add_brep(pole, objs)

    return objs


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def create_stair():
    """Main entry point - prompts the user and builds the stair."""
    stair_types = ["Straight Run", "L-Shaped", "Switchback (U-Shape)", "Spiral"]
    stair_type = rs.ListBox(stair_types, "Select stair type:", "Stair Generator",
                            stair_types[0])
    if stair_type is None:
        return

    s = get_unit_scale()
    max_rise = MAX_RISE_BETWEEN_LANDINGS_IN * s  # 12'-0" in doc units

    # --- Common parameters ---
    floor_height = rs.GetReal("Floor-to-floor height", 120.0 * s, 1.0)
    if floor_height is None: return

    width = rs.GetReal("Stair width", 36.0 * s, 1.0)
    if width is None: return

    riser_target = rs.GetReal("Target riser height (auto-adjusts to fit)", 7.0 * s, 1.0)
    if riser_target is None: return

    tread_depth = rs.GetReal("Tread depth", 11.0 * s, 1.0)
    if tread_depth is None: return

    slab_thickness = rs.GetReal("Slab / tread thickness", 6.0 * s, 0.1)
    if slab_thickness is None: return

    # Landing depth - IBC requires >= stair width; default to width
    landing_depth = rs.GetReal("Landing depth (IBC min = stair width)", width, width)
    if landing_depth is None: return

    # Calculate risers
    num_risers = max(2, int(round(floor_height / riser_target)))
    riser_height = floor_height / num_risers

    # --- Type-specific parameters ---
    turn_dir = None
    landing_at = None
    inner_radius = None
    total_rotation = None

    if stair_type == "L-Shaped":
        turn_dir = rs.ListBox(["Left", "Right"], "Turn direction:", "L-Shaped", "Left")
        if turn_dir is None: return
        landing_at = rs.GetInteger("Landing at riser #", num_risers // 2, 2, num_risers - 2)
        if landing_at is None: return

    elif stair_type == "Spiral":
        inner_radius = rs.GetReal("Inner (pole) radius", 6.0 * s, 1.0)
        if inner_radius is None: return
        total_rotation = rs.GetReal("Total rotation (degrees)", 360.0, 90.0)
        if total_rotation is None: return

    # --- Build ---
    sc.doc.Views.RedrawEnabled = False
    stair_objects = []

    try:
        if stair_type == "Straight Run":
            stair_objects = build_straight(num_risers, riser_height,
                                           tread_depth, width, slab_thickness,
                                           landing_depth, max_rise)
        elif stair_type == "L-Shaped":
            stair_objects = build_l_shaped(num_risers, riser_height,
                                           tread_depth, width, slab_thickness,
                                           turn_dir, landing_at, landing_depth)
        elif stair_type == "Switchback (U-Shape)":
            stair_objects = build_switchback(num_risers, riser_height,
                                             tread_depth, width, slab_thickness,
                                             landing_depth)
        elif stair_type == "Spiral":
            stair_objects = build_spiral(num_risers, riser_height,
                                         width, slab_thickness,
                                         inner_radius, total_rotation)

        # Layer + group
        if stair_objects:
            layer = "Stairs"
            if not rs.IsLayer(layer):
                rs.AddLayer(layer)
            for obj in stair_objects:
                rs.ObjectLayer(obj, layer)
            grp = rs.AddGroup("Stair_{}".format(stair_type.replace(" ", "_")))
            rs.AddObjectsToGroup(stair_objects, grp)

        print("Stair created: {} | {} risers @ {:.3f} | tread {:.3f}".format(
            stair_type, num_risers, riser_height, tread_depth))

    except Exception as e:
        print("Error creating stair: {}".format(e))

    finally:
        sc.doc.Views.RedrawEnabled = True
        sc.doc.Views.Redraw()


if __name__ == "__main__":
    create_stair()
