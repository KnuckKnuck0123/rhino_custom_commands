# -*- coding: utf-8 -*-
"""
CurtainWall.py - Parametric curtain wall generator for Rhino.
Works on surfaces OR closed curves (extruded to a given height).
Parameters: top/bottom sill, left/right jambs, H/V mullion spacing,
mullion profile, glass panel inset, and optional rotation.
"""
import rhinoscriptsyntax as rs
import Rhino
import Rhino.Geometry as rg
import scriptcontext as sc
import math


def measure_surface(srf_id, domain_u, domain_v, n_measure=50):
    """Measure physical size of a surface by sampling."""
    mid_v = (domain_v[0] + domain_v[1]) / 2.0
    u_length = 0.0
    prev = rs.EvaluateSurface(srf_id, domain_u[0], mid_v)
    for i in range(1, n_measure + 1):
        u = domain_u[0] + (domain_u[1] - domain_u[0]) * i / float(n_measure)
        pt = rs.EvaluateSurface(srf_id, u, mid_v)
        u_length += rs.Distance(prev, pt)
        prev = pt

    mid_u = (domain_u[0] + domain_u[1]) / 2.0
    v_length = 0.0
    prev = rs.EvaluateSurface(srf_id, mid_u, domain_v[0])
    for i in range(1, n_measure + 1):
        v = domain_v[0] + (domain_v[1] - domain_v[0]) * i / float(n_measure)
        pt = rs.EvaluateSurface(srf_id, mid_u, v)
        v_length += rs.Distance(prev, pt)
        prev = pt

    return u_length, v_length


def create_curtain_wall():
    """Parametric curtain wall on a surface or closed curve."""

    # --- 1. Select input ---
    obj_id = rs.GetObject("Select surface or closed curve for curtain wall",
                          rs.filter.surface | rs.filter.curve)
    if not obj_id:
        return

    srf_id = None
    is_closed_curve = False
    extrusion_id = None
    wall_height = None

    if rs.IsCurve(obj_id):
        if not rs.IsCurveClosed(obj_id):
            print("Curve must be closed. Please select a closed curve.")
            return
        is_closed_curve = True

        wall_height = rs.GetReal("Wall height", 120.0, 1.0)
        if wall_height is None:
            return

        # Extrude the curve to create the surface
        extrusion_path = rs.AddLine([0, 0, 0], [0, 0, wall_height])
        srf_id = rs.ExtrudeCurve(obj_id, extrusion_path)
        rs.DeleteObject(extrusion_path)

        if not srf_id:
            print("Failed to extrude curve.")
            return
    else:
        srf_id = obj_id

    # --- 2. Parameters ---
    num_v_mullions = rs.GetInteger("Number of vertical mullions", 5, 0)
    if num_v_mullions is None: return

    num_h_mullions = rs.GetInteger("Number of horizontal mullions", 3, 0)
    if num_h_mullions is None: return

    if is_closed_curve:
        # No jambs for closed curves - they wrap around
        top_sill = rs.GetReal("Top sill depth", 4.0, 0.0)
        if top_sill is None: return
        bottom_sill = rs.GetReal("Bottom sill depth", 6.0, 0.0)
        if bottom_sill is None: return
        left_jamb = 0.0
        right_jamb = 0.0
    else:
        top_sill = rs.GetReal("Top sill depth", 4.0, 0.0)
        if top_sill is None: return
        bottom_sill = rs.GetReal("Bottom sill depth", 6.0, 0.0)
        if bottom_sill is None: return
        left_jamb = rs.GetReal("Left jamb width", 3.0, 0.0)
        if left_jamb is None: return
        right_jamb = rs.GetReal("Right jamb width", 3.0, 0.0)
        if right_jamb is None: return

    mullion_width = rs.GetReal("Mullion width (face)", 2.0, 0.1)
    if mullion_width is None: return

    rotation_deg = rs.GetReal("Rotation angle (degrees, 0=none)", 0.0, -360.0, 360.0)
    if rotation_deg is None: return

    # --- 3. Analyze surface ---
    domain_u = rs.SurfaceDomain(srf_id, 0)
    domain_v = rs.SurfaceDomain(srf_id, 1)
    u_length, v_length = measure_surface(srf_id, domain_u, domain_v)

    print("Surface size: {:.1f} x {:.1f}".format(u_length, v_length))

    # Usable area after jambs/sills
    usable_u = u_length - left_jamb - right_jamb
    usable_v = v_length - top_sill - bottom_sill

    if usable_u <= 0 or usable_v <= 0:
        print("Error: Frame dimensions exceed surface size.")
        if extrusion_id:
            rs.DeleteObject(extrusion_id)
        return

    # Calculate mullion counts
    n_v_mullions_internal = num_v_mullions
    n_h_mullions_internal = num_h_mullions

    # For closed curves, we want mullions to wrap continuously
    if is_closed_curve:
        n_v_mullions_internal = max(1, num_v_mullions)

    print("Grid: {} vertical x {} horizontal mullions".format(
        n_v_mullions_internal, n_h_mullions_internal))

    # --- 4. Build geometry ---
    rs.EnableRedraw(False)

    parent_layer = "CurtainWall"
    if not rs.IsLayer(parent_layer):
        rs.AddLayer(parent_layer)

    frame_layer_name = "{}::Frame".format(parent_layer)
    if not rs.IsLayer(frame_layer_name):
        rs.AddLayer("Frame", rs.CreateColor(80, 80, 80), parent=parent_layer)

    mullion_layer_name = "{}::Mullions".format(parent_layer)
    if not rs.IsLayer(mullion_layer_name):
        rs.AddLayer("Mullions", rs.CreateColor(120, 120, 120), parent=parent_layer)

    panel_layer_name = "{}::Panels".format(parent_layer)
    if not rs.IsLayer(panel_layer_name):
        rs.AddLayer("Panels", rs.CreateColor(140, 200, 230), parent=parent_layer)

    created_objs = []
    group_name = rs.AddGroup("CurtainWall")
    panel_count = 0

    try:
        # UV fractions
        u_range = domain_u[1] - domain_u[0]
        v_range = domain_v[1] - domain_v[0]

        u_frac_left = left_jamb / u_length if u_length > 0 else 0
        u_frac_right = right_jamb / u_length if u_length > 0 else 0
        v_frac_bottom = bottom_sill / v_length if v_length > 0 else 0
        v_frac_top = top_sill / v_length if v_length > 0 else 0

        u_start = domain_u[0] + u_frac_left * u_range
        u_end = domain_u[1] - u_frac_right * u_range
        v_start = domain_v[0] + v_frac_bottom * v_range
        v_end = domain_v[1] - v_frac_top * v_range

        # Mullion positions
        if is_closed_curve:
            # For closed curves: evenly spaced around full perimeter
            u_positions = []
            for i in range(n_v_mullions_internal):
                u_positions.append(domain_u[0] + u_range * i / float(n_v_mullions_internal))
            u_positions.append(domain_u[1])  # wraps to start
        else:
            u_positions = [u_start]
            if n_v_mullions_internal > 0:
                u_step = (u_end - u_start) / (n_v_mullions_internal + 1)
                for i in range(1, n_v_mullions_internal + 1):
                    u_positions.append(u_start + i * u_step)
            u_positions.append(u_end)

        v_positions = [v_start]
        if n_h_mullions_internal > 0:
            v_step = (v_end - v_start) / (n_h_mullions_internal + 1)
            for i in range(1, n_h_mullions_internal + 1):
                v_positions.append(v_start + i * v_step)
        v_positions.append(v_end)

        # Rotation transform
        rot_xform = None
        if abs(rotation_deg) > 0.01:
            center_pt = rs.EvaluateSurface(srf_id, (domain_u[0] + domain_u[1]) / 2.0,
                                                     (domain_v[0] + domain_v[1]) / 2.0)
            center_normal = rs.SurfaceNormal(srf_id, [(domain_u[0] + domain_u[1]) / 2.0,
                                                       (domain_v[0] + domain_v[1]) / 2.0])
            rot_xform = rs.XformRotation2(rotation_deg, center_normal, center_pt)

        # --- Helper: create UV rectangle ---
        brep = rs.coercebrep(srf_id) if not is_closed_curve else None
        face = brep.Faces[0] if brep and brep.Faces.Count > 0 else None

        border_crvs = rs.DuplicateSurfaceBorder(srf_id) if not is_closed_curve else []
        border_geom = [rs.coercecurve(c) for c in border_crvs] if border_crvs else []

        def is_point_on_face(u, v):
            if not face: return True
            try:
                rel = face.IsPointOnFace(u, v)
                return rel != rg.PointFaceRelation.Exterior
            except:
                return True

        def make_uv_rect(u0, u1, v0, v1, layer_name):
            if u1 <= u0 or v1 <= v0:
                return False
            mid_u = (u0 + u1) / 2.0
            mid_v = (v0 + v1) / 2.0
            if not is_point_on_face(mid_u, mid_v):
                return False
            
            n = 5
            pts = []
            for k in range(n):
                pts.append(rs.EvaluateSurface(srf_id, u0 + (u1-u0)*k/float(n), v0))
            for k in range(n):
                pts.append(rs.EvaluateSurface(srf_id, u1, v0 + (v1-v0)*k/float(n)))
            for k in range(n):
                pts.append(rs.EvaluateSurface(srf_id, u1 - (u1-u0)*k/float(n), v1))
            for k in range(n):
                pts.append(rs.EvaluateSurface(srf_id, u0, v1 - (v1-v0)*k/float(n)))
            pts.append(pts[0])
            
            if any(p is None for p in pts):
                return False
                
            crv_id = rs.AddPolyline(pts)
            if not crv_id: return False
            
            crv_geom = rs.coercecurve(crv_id)
            if border_geom:
                tol = sc.doc.ModelAbsoluteTolerance
                try:
                    intersections = rg.Curve.CreateBooleanIntersection(crv_geom, border_geom, tol)
                    if intersections and len(intersections) > 0:
                        rs.DeleteObject(crv_id)
                        added = False
                        for ig in intersections:
                            new_crv = sc.doc.Objects.AddCurve(ig)
                            if new_crv:
                                rs.ObjectLayer(new_crv, layer_name)
                                if rot_xform: rs.TransformObject(new_crv, rot_xform)
                                created_objs.append(new_crv)
                                added = True
                        return added
                except:
                    pass
            
            rs.ObjectLayer(crv_id, layer_name)
            if rot_xform: rs.TransformObject(crv_id, rot_xform)
            created_objs.append(crv_id)
            return True

        total_work = 4 + len(u_positions) + len(v_positions) + \
                     (len(u_positions) - 1) * (len(v_positions) - 1)
        rs.StatusBarProgressMeterShow("Building curtain wall", 0, max(total_work, 1), True, True)
        prog = 0

        mu_u = (mullion_width / u_length) * u_range if u_length > 0 else 0
        mu_v = (mullion_width / v_length) * v_range if v_length > 0 else 0

        # --- Frame perimeter ---
        if not is_closed_curve:
            # Left jamb (full height)
            make_uv_rect(domain_u[0], u_start, domain_v[0], domain_v[1], frame_layer_name)
            prog += 1; rs.StatusBarProgressMeterUpdate(prog, True)

            # Right jamb (full height)
            make_uv_rect(u_end, domain_u[1], domain_v[0], domain_v[1], frame_layer_name)
            prog += 1; rs.StatusBarProgressMeterUpdate(prog, True)

        # Bottom sill (full width)
        make_uv_rect(u_start, u_end, domain_v[0], v_start, frame_layer_name)
        prog += 1; rs.StatusBarProgressMeterUpdate(prog, True)

        # Top sill (full width)
        make_uv_rect(u_start, u_end, v_end, domain_v[1], frame_layer_name)
        prog += 1; rs.StatusBarProgressMeterUpdate(prog, True)

        # --- Internal vertical mullions ---
        vm_u_list = u_positions[:-1] if is_closed_curve else u_positions[1:-1]
        for u in vm_u_list:
            make_uv_rect(u - mu_u/2.0, u + mu_u/2.0, v_start, v_end, mullion_layer_name)
            prog += 1; rs.StatusBarProgressMeterUpdate(prog, True)

        # --- Internal horizontal mullions ---
        for j in range(1, len(v_positions) - 1):
            v_pos = v_positions[j]
            for i in range(len(u_positions) - 1):
                bay_u0 = u_positions[i] + (mu_u/2.0 if i > 0 else 0)
                bay_u1 = u_positions[i+1] - (mu_u/2.0 if i < len(u_positions) - 2 else 0)
                make_uv_rect(bay_u0, bay_u1, v_pos - mu_v/2.0, v_pos + mu_v/2.0, mullion_layer_name)
            prog += 1; rs.StatusBarProgressMeterUpdate(prog, True)

        # --- Glass panels ---
        # For closed curves, wrap the u_positions list
        u_panel_positions = list(u_positions)

        for i in range(len(u_panel_positions) - 1):
            for j in range(len(v_positions) - 1):
                bay_u0 = u_panel_positions[i] + (mu_u/2.0 if i > 0 else 0)
                bay_u1 = u_panel_positions[i+1] - (mu_u/2.0 if i < len(u_panel_positions) - 2 else 0)
                bay_v0 = v_positions[j] + (mu_v/2.0 if j > 0 else 0)
                bay_v1 = v_positions[j+1] - (mu_v/2.0 if j < len(v_positions) - 2 else 0)

                if make_uv_rect(bay_u0, bay_u1, bay_v0, bay_v1, panel_layer_name):
                    panel_count += 1

                prog += 1; rs.StatusBarProgressMeterUpdate(prog, True)

        if border_crvs:
            rs.DeleteObjects(border_crvs)
            
        # Group everything
        if created_objs:
            rs.AddObjectsToGroup(created_objs, group_name)

        # Clean up temporary extrusion surface (hide it)
        if is_closed_curve and srf_id:
            rs.DeleteObject(srf_id)

    except Exception as e:
        print("Error: {}".format(e))
        import traceback
        traceback.print_exc()

    finally:
        rs.StatusBarProgressMeterHide()
        rs.EnableRedraw(True)
        sc.doc.Views.Redraw()

    mullion_count = len(created_objs) - panel_count
    print("Curtain wall complete: {} mullions + {} panels = {} objects".format(
        mullion_count, panel_count, len(created_objs)))


if __name__ == "__main__":
    create_curtain_wall()
