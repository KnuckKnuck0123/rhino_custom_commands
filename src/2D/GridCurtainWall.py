import rhinoscriptsyntax as rs
import random
import math
import Rhino
import scriptcontext

def create_2d_curtain_wall():
    """
    Creates a clean 2D curtain wall with sill/jamb frames, glass panels, 
    and optional grid rotation and variation.
    """
    # 1. Get bounds
    obj_id = rs.GetObject("Select a surface or closed curve for the curtain wall (Press Enter to draw)", rs.filter.surface | rs.filter.polysurface | rs.filter.curve)
    
    is_non_planar_srf = False
    len_u = 0
    len_v = 0
    
    if obj_id:
        if rs.IsCurve(obj_id):
            if not rs.IsCurvePlanar(obj_id) or not rs.IsCurveClosed(obj_id):
                print("Selected curve must be planar and closed.")
                return
            bbox = rs.BoundingBox(obj_id)
            if not bbox: return
            p1 = bbox[0]
            p2 = bbox[2]
            outer_crv_id = rs.CopyObject(obj_id)
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
                
                outer_crv_id = rs.AddPolyline([[0,0,0], [len_u,0,0], [len_u,len_v,0], [0,len_v,0], [0,0,0]])
                
            else:
                bbox = rs.BoundingBox(obj_id)
                if not bbox: return
                p1 = bbox[0]
                p2 = bbox[2]
                
                # Extract the border curve for boolean operations later
                border_crvs = rs.DuplicateSurfaceBorder(obj_id)
                if not border_crvs: return
                if len(border_crvs) == 1:
                    outer_crv_id = border_crvs[0]
                else:
                    outer_crv_id = rs.JoinCurves(border_crvs, delete_input=True)[0]
    else:
        rect_pts = rs.GetRectangle()
        if not rect_pts: return
        p1 = rect_pts[0]
        p2 = rect_pts[2]
        outer_crv_id = None
    
    # 2. Parameters
    v_panels = rs.GetInteger("Number of vertical panels (Columns)", 5, 1)
    if v_panels is None: return
    
    h_panels = rs.GetInteger("Number of horizontal panels (Rows)", 3, 1)
    if h_panels is None: return
    
    v_mullion = rs.GetReal("Vertical mullion width", 2.0, 0.0)
    if v_mullion is None: return
    
    h_mullion = rs.GetReal("Horizontal mullion width", 2.0, 0.0)
    if h_mullion is None: return
    
    sill_width = rs.GetReal("Top and Bottom Sill width", 4.0, 0.0)
    if sill_width is None: return
    
    jamb_width = rs.GetReal("Left and Right Jamb width", 4.0, 0.0)
    if jamb_width is None: return
    
    variation = rs.GetReal("Panel Size Variation (0.0 to 1.0)", 0.2, 0.0, 1.0)
    if variation is None: return
    
    angle = rs.GetReal("Grid Rotation Angle (degrees)", 0.0)
    if angle is None: return

    rs.EnableRedraw(False)
    
    created_objs = []
    
    # Sort coordinates
    min_x = min(p1[0], p2[0])
    max_x = max(p1[0], p2[0])
    min_y = min(p1[1], p2[1])
    max_y = max(p1[1], p2[1])
    z = p1[2]
    
    cw_width = max_x - min_x
    cw_height = max_y - min_y
    
    # Outer curve handling
    if outer_crv_id:
        outer_rect = outer_crv_id
    else:
        outer_rect = rs.AddPolyline([[min_x, min_y, z], [max_x, min_y, z], 
                                     [max_x, max_y, z], [min_x, max_y, z], [min_x, min_y, z]])
    created_objs.append(outer_rect)
                                 
    # Using bounding box inner dimension for math calculation
    inner_min_x = min_x + jamb_width
    inner_max_x = max_x - jamb_width
    inner_min_y = min_y + sill_width
    inner_max_y = max_y - sill_width
    
    if inner_min_x >= inner_max_x or inner_min_y >= inner_max_y:
        print("Sill or Jamb widths are too large for the bounding box.")
        rs.EnableRedraw(True)
        return
        
    # Generate the inner cut geometry based on whether it is a custom shape or rectangle
    if outer_crv_id:
        # For arbitrary surfaces, we use rs.OffsetCurve (assuming avg. offset for simplicity if jamb != sill)
        # Offset curve inward. We will pick a point inside the bounding box.
        center_pt = [(min_x + max_x)/2.0, (min_y + max_y)/2.0, z]
        avg_offset = (jamb_width + sill_width) / 2.0
        
        if avg_offset > 0:
            inner_crvs = rs.OffsetCurve(outer_rect, center_pt, avg_offset)
            if inner_crvs:
                inner_rect = inner_crvs[0]
            else:
                inner_rect = rs.CopyObject(outer_rect) # fallback
        else:
            inner_rect = rs.CopyObject(outer_rect)
    else:
        inner_rect = rs.AddPolyline([[inner_min_x, inner_min_y, z], [inner_max_x, inner_min_y, z], 
                                     [inner_max_x, inner_max_y, z], [inner_min_x, inner_max_y, z], [inner_min_x, inner_min_y, z]])
    
    created_objs.append(inner_rect)
    
    inner_width = inner_max_x - inner_min_x
    inner_height = inner_max_y - inner_min_y
    
    glass_panels = []
    
    raw_panels = []
    
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
                    raw_panels.append(panel)
    else:
        # Build an oversized grid and rotate it around the center, then intersect with inner bound.
        center_x = (min_x + max_x) / 2.0
        center_y = (min_y + max_y) / 2.0
        center_pt = [center_x, center_y, z]
        
        diag = math.sqrt(cw_width**2 + cw_height**2)
        oversize_min_x = center_x - diag
        oversize_max_x = center_x + diag
        oversize_min_y = center_y - diag
        oversize_max_y = center_y + diag
        
        avg_w = inner_width / v_panels
        avg_h = inner_height / h_panels
        
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
                    rs.RotateObject(panel, center_pt, angle)
                    raw_panels.append(panel)
                    
    # Intersect raw panels with inner_rect
    inner_crv_geom = rs.coercecurve(inner_rect)
    tol = scriptcontext.doc.ModelAbsoluteTolerance
    for p in raw_panels:
        p_geom = rs.coercecurve(p)
        out_crvs = Rhino.Geometry.Curve.CreateBooleanIntersection(p_geom, inner_crv_geom, tol)
        if out_crvs:
            for crv in out_crvs:
                crv_id = scriptcontext.doc.Objects.AddCurve(crv)
                if crv_id:
                    glass_panels.append(crv_id)
        rs.DeleteObject(p)

    created_objs.extend(glass_panels)

    # If it was a non-planar surface, map all 2D shapes back to the varying 3D surface
    if is_non_planar_srf:
        domain_u = rs.SurfaceDomain(obj_id, 0)
        domain_v = rs.SurfaceDomain(obj_id, 1)
        mapped_objs = []
        for obj in created_objs:
            # Extract points (convert curved boundaries to straight segments first if needed)
            pts = []
            if rs.IsCurve(obj):
                pl_obj = rs.ConvertCurveToPolyline(obj)
                if pl_obj:
                    pts = rs.CurvePoints(pl_obj)
                    rs.DeleteObject(pl_obj)
                else:
                    pts = rs.CurvePoints(obj)
            
            if pts:
                # Subdivide long segments so they gracefully drape over the 3D surface curvature
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
                    # Cull duplicate identical points
                    if not new_pts or rs.Distance(new_pts[-1], target_pt) > 0.005:
                        new_pts.append(target_pt)
                
                # Make sure completely closed profiles map seamlessly
                if rs.IsCurveClosed(obj) and len(new_pts) > 1:
                    if rs.Distance(new_pts[0], new_pts[-1]) > 0.005:
                        new_pts.append(new_pts[0])
                
                # Only construct if valid polyline
                if len(new_pts) >= 2:
                    try:
                        mapped = rs.AddPolyline(new_pts)
                        if mapped:
                            mapped_objs.append(mapped)
                    except:
                        pass
                    
            rs.DeleteObject(obj)
            
        created_objs = mapped_objs
        glass_panels = []

    # Group everything
    group_name = rs.AddGroup("2DCurtainWall")
    if created_objs:
        rs.AddObjectsToGroup(created_objs, group_name)

    rs.EnableRedraw(True)
    print("Created 2D Curtain Wall with {} glass panels.".format(len(glass_panels)))

if __name__ == "__main__":
    create_2d_curtain_wall()
