import rhinoscriptsyntax as rs
import random
import math
import Rhino
import scriptcontext

def get_plane_and_bounds_from_curves(crv_ids):
    if not crv_ids: return None, None, None
    poly = rs.ConvertCurveToPolyline(crv_ids[0])
    if not poly: return None, None, None
    pts = rs.CurvePoints(poly)
    rs.DeleteObject(poly)
    if not pts: return None, None, None
    
    plane = rs.PlaneFitFromPoints(pts)
    if not plane: return None, None, None
    
    world_z = Rhino.Geometry.Vector3d(0, 0, 1)
    if abs(plane.ZAxis.Z) < 0.99:
        horiz_x = Rhino.Geometry.Vector3d.CrossProduct(plane.ZAxis, world_z)
        horiz_x.Unitize()
        horiz_y = Rhino.Geometry.Vector3d.CrossProduct(plane.ZAxis, horiz_x)
        horiz_y.Unitize()
        if horiz_y.Z < 0:
            horiz_y = -horiz_y
            horiz_x = -horiz_x
        plane = Rhino.Geometry.Plane(plane.Origin, horiz_x, horiz_y)
    
    xform_to_2d = Rhino.Geometry.Transform.ChangeBasis(Rhino.Geometry.Plane.WorldXY, plane)
    
    min_x, min_y = float('inf'), float('inf')
    max_x, max_y = float('-inf'), float('-inf')
    
    for cid in crv_ids:
        cg = rs.coercecurve(cid).Duplicate()
        cg.Transform(xform_to_2d)
        bbox = cg.GetBoundingBox(True)
        if bbox.Min.X < min_x: min_x = bbox.Min.X
        if bbox.Min.Y < min_y: min_y = bbox.Min.Y
        if bbox.Max.X > max_x: max_x = bbox.Max.X
        if bbox.Max.Y > max_y: max_y = bbox.Max.Y
        
    return plane, [min_x, min_y, 0], [max_x, max_y, 0]

def generate_preview(obj_id, outer_curves, p1, p2, is_non_planar_srf, len_u, len_v, params, plane=None):
    v_panels = params["v_panels"]
    h_panels = params["h_panels"]
    v_mullion = params["v_mullion"]
    h_mullion = params["h_mullion"]
    sill_width = params["sill_width"]
    jamb_width = params["jamb_width"]
    variation = params["variation"]
    angle = params["angle"]
    
    random.seed(42) # Keep random variation consistent during live preview
    
    created_objs = []
    
    # Sort coordinates
    min_x = min(p1[0], p2[0])
    max_x = max(p1[0], p2[0])
    min_y = min(p1[1], p2[1])
    max_y = max(p1[1], p2[1])
    z = p1[2]
    
    cw_width = max_x - min_x
    cw_height = max_y - min_y
    
    if cw_width <= 0 or cw_height <= 0:
        return []

    xform_to_3d = None
    xform_to_2d = None
    if plane:
        xform_to_3d = Rhino.Geometry.Transform.ChangeBasis(plane, Rhino.Geometry.Plane.WorldXY)
        xform_to_2d = Rhino.Geometry.Transform.ChangeBasis(Rhino.Geometry.Plane.WorldXY, plane)

    # Draw the boundary limits
    if outer_curves:
        for cid in outer_curves:
            c = rs.CopyObject(cid)
            if c:
                created_objs.append(c)
    else:
        rect = rs.AddPolyline([[min_x, min_y, z], [max_x, min_y, z], 
                                     [max_x, max_y, z], [min_x, max_y, z], [min_x, min_y, z]])
        if rect:
            if xform_to_3d:
                rg = rs.coercecurve(rect).Duplicate()
                rg.Transform(xform_to_3d)
                rs.DeleteObject(rect)
                rect = scriptcontext.doc.Objects.AddCurve(rg)
            created_objs.append(rect)

    # Bounding box inner dimension for basic grid math
    inner_min_x = min_x + jamb_width
    inner_max_x = max_x - jamb_width
    inner_min_y = min_y + sill_width
    inner_max_y = max_y - sill_width
    
    # Prevent inside-out scaling
    if inner_min_x >= inner_max_x:
        jamb_width = cw_width * 0.1
        inner_min_x = min_x + jamb_width
        inner_max_x = max_x - jamb_width

    if inner_min_y >= inner_max_y:
        sill_width = cw_height * 0.1
        inner_min_y = min_y + sill_width
        inner_max_y = max_y - sill_width

    # Generate an inner rectangle to represent the bounding frame minus jambs/sills
    inner_rect = rs.AddPolyline([[inner_min_x, inner_min_y, z], [inner_max_x, inner_min_y, z], 
                                 [inner_max_x, inner_max_y, z], [inner_min_x, inner_max_y, z], [inner_min_x, inner_min_y, z]])
    
    inner_crv_geom = None
    if inner_rect:
        inner_crv_geom = rs.coercecurve(inner_rect).Duplicate()
        if xform_to_3d:
            rg = rs.coercecurve(inner_rect).Duplicate()
            rg.Transform(xform_to_3d)
            rs.DeleteObject(inner_rect)
            inner_rect = scriptcontext.doc.Objects.AddCurve(rg)
        created_objs.append(inner_rect)
    else:
        return created_objs

    inner_width = inner_max_x - inner_min_x
    inner_height = inner_max_y - inner_min_y
    
    glass_panels = []
    raw_panels = []
    
    # Grid logic
    if angle == 0.0:
        # Standard unrotated
        # Calculate grid lines over bounding box
        xs = [inner_min_x]
        ys = [inner_min_y]
        
        x_weights = [1.0] * v_panels
        if variation > 0:
            for i in range(v_panels):
                x_weights[i] += (random.random() * 2 - 1.0) * variation * 0.9
                if x_weights[i] < 0.1: x_weights[i] = 0.1
        x_total_weight = sum(x_weights)
        
        current_x = inner_min_x
        for i in range(v_panels - 1):
            panel_w = (x_weights[i] / x_total_weight) * inner_width
            current_x += panel_w
            xs.append(current_x)
        xs.append(inner_max_x)

        y_weights = [1.0] * h_panels
        if variation > 0:
            for i in range(h_panels):
                y_weights[i] += (random.random() * 2 - 1.0) * variation * 0.9
                if y_weights[i] < 0.1: y_weights[i] = 0.1
        y_total_weight = sum(y_weights)
        
        current_y = inner_min_y
        for i in range(h_panels - 1):
            panel_h = (y_weights[i] / y_total_weight) * inner_height
            current_y += panel_h
            ys.append(current_y)
        ys.append(inner_max_y)
        
        for i in range(v_panels):
            for j in range(h_panels):
                px_min = xs[i] + (v_mullion / 2.0 if i > 0 else 0)
                px_max = xs[i+1] - (v_mullion / 2.0 if i < v_panels - 1 else 0)
                
                py_min = ys[j] + (h_mullion / 2.0 if j > 0 else 0)
                py_max = ys[j+1] - (h_mullion / 2.0 if j < h_panels - 1 else 0)
                
                if px_min < px_max and py_min < py_max:
                    panel = rs.AddPolyline([[px_min, py_min, z], [px_max, py_min, z],
                                            [px_max, py_max, z], [px_min, py_max, z], [px_min, py_min, z]])
                    if panel:
                        raw_panels.append(panel)
    else:
        # Build an oversized grid and rotate it
        center_x = (min_x + max_x) / 2.0
        center_y = (min_y + max_y) / 2.0
        center_pt = [center_x, center_y, z]
        
        diag = math.sqrt(cw_width**2 + cw_height**2)
        oversize_min_x = center_x - diag
        oversize_max_x = center_x + diag
        oversize_min_y = center_y - diag
        oversize_max_y = center_y + diag
        
        avg_w = inner_width / v_panels if v_panels > 0 else inner_width
        avg_h = inner_height / h_panels if h_panels > 0 else inner_height
        
        # Hard cap to prevent infinite or extreme iteration crashing
        if avg_w < diag * 0.02: avg_w = diag * 0.02
        if avg_h < diag * 0.02: avg_h = diag * 0.02
        
        big_xs = []
        cx = oversize_min_x
        while cx < oversize_max_x:
            big_xs.append(cx)
            jitter = (random.random() * 2 - 1.0) * variation * 0.9 * avg_w if variation > 0 else 0
            step = avg_w + jitter
            if step < avg_w * 0.1: step = avg_w * 0.1
            cx += step
        big_xs.append(oversize_max_x)
        
        big_ys = []
        cy = oversize_min_y
        while cy < oversize_max_y:
            big_ys.append(cy)
            jitter = (random.random() * 2 - 1.0) * variation * 0.9 * avg_h if variation > 0 else 0
            step = avg_h + jitter
            if step < avg_h * 0.1: step = avg_h * 0.1
            cy += step
        big_ys.append(oversize_max_y)
        
        for i in range(len(big_xs)-1):
            for j in range(len(big_ys)-1):
                px_min = big_xs[i] + v_mullion / 2.0
                px_max = big_xs[i+1] - v_mullion / 2.0
                py_min = big_ys[j] + h_mullion / 2.0
                py_max = big_ys[j+1] - h_mullion / 2.0
                
                if px_min < px_max and py_min < py_max:
                    panel = rs.AddPolyline([[px_min, py_min, z], [px_max, py_min, z],
                                            [px_max, py_max, z], [px_min, py_max, z], [px_min, py_min, z]])
                    if panel:
                        rs.RotateObject(panel, center_pt, angle)
                        raw_panels.append(panel)
                    
    # Intersect raw panels with inner bounding frame (inner_rect)
    framed_panels_geom = []
    
    tol = scriptcontext.doc.ModelAbsoluteTolerance
    if inner_crv_geom:
        for p in raw_panels:
            p_geom = rs.coercecurve(p)
            if p_geom:
                try:
                    out_crvs = Rhino.Geometry.Curve.CreateBooleanIntersection(p_geom, inner_crv_geom, tol)
                    if out_crvs:
                        framed_panels_geom.extend(out_crvs)
                except:
                    pass
            if p: rs.DeleteObject(p)

    # Secondary intersection against true surface bounds (holes, irregular shapes)
    final_panels_geom = []
    srf_curves_geom = []
    if outer_curves:
        for c in outer_curves:
            cg = rs.coercecurve(c).Duplicate()
            if cg:
                if xform_to_2d: cg.Transform(xform_to_2d)
                srf_curves_geom.append(cg)

    if srf_curves_geom:
        # Intersect all generated frame panels with the surface region to correctly clip holes
        for p_geom in framed_panels_geom:
            try:
                # CreateBooleanIntersection accepts (IEnumerable curvesA, IEnumerable curvesB, tol)
                out_crvs = Rhino.Geometry.Curve.CreateBooleanIntersection([p_geom], srf_curves_geom, tol)
                if out_crvs:
                    final_panels_geom.extend(out_crvs)
            except:
                pass
    else:
        final_panels_geom = framed_panels_geom

    # Bake final panels to the doc
    for crv in final_panels_geom:
        if crv:
            if xform_to_3d: crv.Transform(xform_to_3d)
            crv_id = scriptcontext.doc.Objects.AddCurve(crv)
            if crv_id:
                glass_panels.append(crv_id)

    created_objs.extend(glass_panels)

    # Transform to 3D surface if required
    if is_non_planar_srf and obj_id:
        domain_u = rs.SurfaceDomain(obj_id, 0)
        domain_v = rs.SurfaceDomain(obj_id, 1)
        mapped_objs = []
        for obj in created_objs:
            pts = []
            if rs.IsCurve(obj):
                pl_obj = rs.ConvertCurveToPolyline(obj)
                if pl_obj:
                    pts = rs.CurvePoints(pl_obj)
                    rs.DeleteObject(pl_obj)
                else:
                    pts = rs.CurvePoints(obj)
            
            if pts:
                sub_pts = [pts[0]]
                for idx in range(1, len(pts)):
                    pA = pts[idx-1]
                    pB = pts[idx]
                    dist = rs.Distance(pA, pB)
                    divs = int(dist / 1.0) # Subdivide every 1 unit max
                    for i in range(1, divs + 1):
                        f = float(i) / (divs + 1)
                        sub_pts.append([pA[0] + f*(pB[0]-pA[0]), pA[1] + f*(pB[1]-pA[1]), pA[2] + f*(pB[2]-pA[2])])
                    sub_pts.append(pB)
                
                new_pts = []
                for pt in sub_pts:
                    u_t = pt[0] / len_u if len_u > 0 else 0
                    v_t = pt[1] / len_v if len_v > 0 else 0
                    u = domain_u[0] + u_t * (domain_u[1] - domain_u[0])
                    v = domain_v[0] + v_t * (domain_v[1] - domain_v[0])
                    srf_pt = rs.EvaluateSurface(obj_id, u, v)
                    
                    target_pt = srf_pt if srf_pt else pt
                    if not new_pts or rs.Distance(new_pts[-1], target_pt) > 0.005:
                        new_pts.append(target_pt)
                
                if rs.IsCurveClosed(obj) and len(new_pts) > 1:
                    if rs.Distance(new_pts[0], new_pts[-1]) > 0.005:
                        new_pts.append(new_pts[0])
                
                if len(new_pts) >= 2:
                    try:
                        mapped = rs.AddPolyline(new_pts)
                        if mapped:
                            mapped_objs.append(mapped)
                    except:
                        pass
                    
            if obj: rs.DeleteObject(obj)
            
        created_objs = mapped_objs

    return created_objs

def create_2d_curtain_wall():
    obj_id = rs.GetObject("Select a surface or closed curve for the curtain wall (Press Enter to draw)", rs.filter.surface | rs.filter.polysurface | rs.filter.curve)
    
    is_non_planar_srf = False
    len_u = 0
    len_v = 0
    p1 = None
    p2 = None
    outer_curves = []
    plane = None
    
    if obj_id:
        if rs.IsCurve(obj_id):
            if not rs.IsCurvePlanar(obj_id) or not rs.IsCurveClosed(obj_id):
                print("Selected curve must be planar and closed.")
                return
            outer_curves = [rs.CopyObject(obj_id)]
            plane, p1, p2 = get_plane_and_bounds_from_curves(outer_curves)
            if not plane:
                bbox = rs.BoundingBox(obj_id)
                if not bbox: return
                p1 = bbox[0]
                p2 = bbox[2]
        else:
            if not rs.IsSurfacePlanar(obj_id):
                is_non_planar_srf = True
                
                if rs.IsPolysurface(obj_id):
                    print("Please select a single Surface, not a Polysurface, for non-planar mapping.")
                    return
                
                domain_u = rs.SurfaceDomain(obj_id, 0)
                domain_v = rs.SurfaceDomain(obj_id, 1)
                mid_v = (domain_v[0] + domain_v[1])/2.0
                crv_u = rs.ExtractIsoCurve(obj_id, [domain_u[0], mid_v], 0)
                len_u = rs.CurveLength(crv_u)
                rs.DeleteObject(crv_u)
                
                mid_u = (domain_u[0] + domain_u[1])/2.0
                crv_v = rs.ExtractIsoCurve(obj_id, [mid_u, domain_v[0]], 1)
                len_v = rs.CurveLength(crv_v)
                rs.DeleteObject(crv_v)
                
                p1 = [0, 0, 0]
                p2 = [len_u, len_v, 0]
                
                rect_crv = rs.AddPolyline([[0,0,0], [len_u,0,0], [len_u,len_v,0], [0,len_v,0], [0,0,0]])
                if rect_crv:
                    outer_curves = [rect_crv]
                
            else:
                border_crvs = rs.DuplicateSurfaceBorder(obj_id)
                if not border_crvs: return
                outer_curves = border_crvs
                plane, p1, p2 = get_plane_and_bounds_from_curves(outer_curves)
                if not plane:
                    bbox = rs.BoundingBox(obj_id)
                    if not bbox: return
                    p1 = bbox[0]
                    p2 = bbox[2]
    else:
        rect_pts = rs.GetRectangle()
        if not rect_pts: return
        p1 = rect_pts[0]
        p2 = rect_pts[2]

    params = {
        "v_panels": 5,
        "h_panels": 3,
        "v_mullion": 2.0,
        "h_mullion": 2.0,
        "sill_width": 4.0,
        "jamb_width": 4.0,
        "variation": 0.2,
        "angle": 0.0
    }
    
    labels = [
        "V Panels", "H Panels",
        "V Mullion", "H Mullion",
        "Sill Width", "Jamb Width",
        "Variation (0.0-1.0)", "Rotation Angle"
    ]
    
    defaults = [
        str(params["v_panels"]), str(params["h_panels"]),
        str(params["v_mullion"]), str(params["h_mullion"]),
        str(params["sill_width"]), str(params["jamb_width"]),
        str(params["variation"]), str(params["angle"])
    ]
    
    title = "2D Curtain Wall Parameters"
    msg = "Configure the grid parameters."
    
    preview_ids = []
    
    while True:
        if preview_ids:
            rs.DeleteObjects(preview_ids)
            preview_ids = []
            
        rs.EnableRedraw(False)
        preview_ids = generate_preview(obj_id, outer_curves, p1, p2, is_non_planar_srf, len_u, len_v, params, plane)
        rs.EnableRedraw(True)
        
        results = rs.PropertyListBox(labels, defaults, title, msg)
        
        if not results:
            if preview_ids: rs.DeleteObjects(preview_ids)
            
            # Clean up copied outer boundary items if aborting
            for cid in outer_curves:
                if cid and cid != obj_id:
                    rs.DeleteObject(cid)
                    
            print("Curtain Wall generation cancelled.")
            break
            
        defaults = results
        
        try:
            params["v_panels"] = max(1, int(results[0]))
            params["h_panels"] = max(1, int(results[1]))
            params["v_mullion"] = max(0.0, float(results[2]))
            params["h_mullion"] = max(0.0, float(results[3]))
            params["sill_width"] = max(0.0, float(results[4]))
            params["jamb_width"] = max(0.0, float(results[5]))
            params["variation"] = max(0.0, min(1.0, float(results[6])))
            params["angle"] = float(results[7])
        except:
            rs.MessageBox("Invalid input values. Please try again.")
            continue
            
        res = rs.MessageBox("Accept Current Layout?\nYes = Apply\nNo = Edit again\nCancel = Quit", 3 | 32)
        
        if res == 6: # Yes
            group_name = rs.AddGroup("2DCurtainWall")
            if preview_ids:
                rs.AddObjectsToGroup(preview_ids, group_name)
                rs.SelectObjects(preview_ids)
                
            for cid in outer_curves:
                if cid and cid != obj_id:
                    rs.DeleteObject(cid)
                    
            print("Created 2D Curtain Wall successfully.")
            break
        elif res == 2: # Cancel
            if preview_ids: rs.DeleteObjects(preview_ids)
            
            for cid in outer_curves:
                if cid and cid != obj_id:
                    rs.DeleteObject(cid)
            break

if __name__ == "__main__":
    create_2d_curtain_wall()
