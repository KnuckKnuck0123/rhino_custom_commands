# -*- coding: utf-8 -*-
"""
VariableOffset - Offset curves and surfaces with a varying distance.
Works like Rhino's built-in offset but interpolates between a min and max distance.
Curves: offsets in the CPlane (like native offset).
Surfaces/Polysurfaces: offsets along normals.
"""
import rhinoscriptsyntax as rs
import Rhino
import Rhino.Geometry as rg
import scriptcontext as sc
import math


def variable_offset_curve(curve, cplane, dist_start, dist_end, num_waves, num_samples, both_sides):
    """Offset a curve in the CPlane with variable distance."""
    divs = curve.DivideByCount(num_samples, True)
    if not divs or len(divs) < 2:
        return []

    curve_length = curve.GetLength()
    if curve_length < 1e-10:
        return []

    results = []
    sides = [1, -1] if both_sides else [1]

    for side in sides:
        offset_pts = []
        for t in divs:
            pt = curve.PointAt(t)

            # Normalized position along curve (0 to 1)
            sub_len = curve.GetLength(rg.Interval(curve.Domain.Min, t))
            t_norm = sub_len / curve_length

            # Compute variable distance
            if num_waves <= 1:
                # Linear gradient from start to end
                d = dist_start + t_norm * (dist_end - dist_start)
            else:
                # Sine wave between min and max
                mid = (dist_start + dist_end) / 2.0
                amp = (dist_end - dist_start) / 2.0
                d = mid + amp * math.sin(2.0 * math.pi * num_waves * t_norm)

            # Offset direction: perpendicular in the CPlane
            tangent = curve.TangentAt(t)
            offset_dir = rg.Vector3d.CrossProduct(tangent, cplane.Normal)
            if offset_dir.Length < 1e-10:
                # Fallback if tangent is parallel to CPlane normal
                offset_dir = rg.Vector3d.CrossProduct(tangent, rg.Vector3d.ZAxis)
            offset_dir.Unitize()

            offset_pts.append(pt + offset_dir * d * side)

        if len(offset_pts) >= 2:
            crv = rg.Curve.CreateInterpolatedCurve(offset_pts, 3)
            if crv:
                results.append(crv)

    return results


def variable_offset_surface(surface, dist_start, dist_end, num_waves, samples):
    """Offset a surface along its normals with variable distance."""
    u_dom = surface.Domain(0)
    v_dom = surface.Domain(1)
    u_range = u_dom.Max - u_dom.Min
    v_range = v_dom.Max - v_dom.Min

    if u_range < 1e-12 or v_range < 1e-12:
        return None

    points = []
    for j in range(samples):
        v_norm = j / float(samples - 1)
        v = v_dom.Min + v_norm * v_range
        for i in range(samples):
            u_norm = i / float(samples - 1)
            u = u_dom.Min + u_norm * u_range

            pt = surface.PointAt(u, v)
            normal = surface.NormalAt(u, v)
            if not normal.IsValid or normal.Length < 1e-10:
                normal = rg.Vector3d.ZAxis
            normal.Unitize()

            # Vary distance along U direction
            if num_waves <= 1:
                d = dist_start + u_norm * (dist_end - dist_start)
            else:
                mid = (dist_start + dist_end) / 2.0
                amp = (dist_end - dist_start) / 2.0
                d = mid + amp * math.sin(2.0 * math.pi * num_waves * u_norm)

            points.append(pt + normal * d)

    # Try NURBS surface
    try:
        srf = rg.NurbsSurface.CreateThroughPoints(
            points, samples, samples, 3, 3, False, False)
        if srf:
            return srf
    except:
        pass

    # Fallback: mesh
    mesh = rg.Mesh()
    for pt in points:
        mesh.Vertices.Add(pt)
    for j in range(samples - 1):
        for i in range(samples - 1):
            a = j * samples + i
            b = a + 1
            c = (j + 1) * samples + i + 1
            dd = (j + 1) * samples + i
            mesh.Faces.AddFace(a, b, c, dd)
    mesh.Normals.ComputeNormals()
    mesh.Compact()
    return mesh


def ensure_child_layer(parent_name, child_name, color=None):
    full_path = "{}::{}".format(parent_name, child_name)
    if not rs.IsLayer(full_path):
        if not rs.IsLayer(parent_name):
            rs.AddLayer(parent_name)
        rs.AddLayer(child_name, color, parent=parent_name)
    return full_path


def variable_offset():
    """Variable offset: select geometry, set min/max distance, done."""

    # 1. Select geometry
    obj_ids = rs.GetObjects("Select curves, surfaces, or polysurfaces to offset",
                            rs.filter.curve | rs.filter.surface | rs.filter.polysurface)
    if not obj_ids:
        return

    # 2. Min and max offset
    dist_min = rs.GetReal("Minimum offset distance", 0.5)
    if dist_min is None:
        return
    dist_max = rs.GetReal("Maximum offset distance", 5.0)
    if dist_max is None:
        return

    # 3. Variation - simple choice
    num_waves = rs.GetReal("Variation waves (1=linear gradient, 2+=wave pattern)", 1.0, 0.5, 50.0)
    if num_waves is None:
        return

    # 4. Classify geometry
    curves = []
    surfaces = []

    for oid in obj_ids:
        if rs.IsCurve(oid):
            crv = rs.coercecurve(oid)
            if crv:
                curves.append(crv)
        elif rs.IsPolysurface(oid):
            brep = rs.coercebrep(oid)
            if brep:
                for i in range(brep.Faces.Count):
                    srf = brep.Faces[i].UnderlyingSurface()
                    if srf:
                        surfaces.append(srf)
        elif rs.IsSurface(oid):
            srf = rs.coercesurface(oid)
            if srf:
                surfaces.append(srf)

    # 5. Options for curves
    both_sides = False
    if curves:
        sides_opt = rs.GetBoolean("Offset both sides?",
                                  ("OneSide", "BothSides"), (True,))
        if sides_opt:
            both_sides = sides_opt[0]

    # Surface resolution
    srf_samples = 25
    if surfaces:
        srf_samples = rs.GetInteger("Surface resolution", 25, 10, 80)
        if srf_samples is None:
            srf_samples = 25

    # 6. Process
    rs.EnableRedraw(False)
    cplane = rs.ViewCPlane()

    parent_layer = "VariableOffset"
    if not rs.IsLayer(parent_layer):
        rs.AddLayer(parent_layer)
    crv_layer = ensure_child_layer(parent_layer, "Curves", rs.CreateColor(255, 160, 40))
    srf_layer = ensure_child_layer(parent_layer, "Surfaces", rs.CreateColor(40, 180, 255))

    total = 0

    try:
        for crv in curves:
            results = variable_offset_curve(crv, cplane, dist_min, dist_max,
                                             num_waves, 100, both_sides)
            for oc in results:
                guid = sc.doc.Objects.AddCurve(oc)
                if guid:
                    rs.ObjectLayer(guid, crv_layer)
                    total += 1

        for srf in surfaces:
            result = variable_offset_surface(srf, dist_min, dist_max,
                                              num_waves, srf_samples)
            if result:
                if isinstance(result, rg.NurbsSurface):
                    guid = sc.doc.Objects.AddSurface(result)
                elif isinstance(result, rg.Mesh):
                    guid = sc.doc.Objects.AddMesh(result)
                else:
                    guid = None
                if guid:
                    rs.ObjectLayer(guid, srf_layer)
                    total += 1

    except Exception as e:
        print("Error: {}".format(e))
        import traceback
        traceback.print_exc()

    finally:
        rs.EnableRedraw(True)
        sc.doc.Views.Redraw()
        print("Created {} offset object(s).".format(total))


variable_offset()
