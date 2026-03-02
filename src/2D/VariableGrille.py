import rhinoscriptsyntax as rs
import random

def create_variable_grille():
    """
    Creates a 'Variable Grille' of vertical slits with a tab/bridge.
    Bridge can either interrupt the slit or connect between slits.
    """
    # 1. Select Boundary
    obj_id = rs.GetObject("Select Closed Curve or Surface for Grille", rs.filter.curve | rs.filter.surface)
    if not obj_id: return

    # 2. Parameters
    slit_width = rs.GetReal("Slit Width", 3.0, 0.1)
    if slit_width is None: return

    gap_width = rs.GetReal("Gap between Slits", 3.0, 0.0)
    if gap_width is None: return

    variation = rs.GetReal("Height Variation (Max random shortening)", 0.0, 0.0)
    if variation is None: return

    margin = rs.GetReal("Border Margin", 0.0, 0.0)
    if margin is None: return

    tab_width = rs.GetReal("Tab Width (Bridge thickness, 0 for pure grille)", 1.0, 0.0)
    if tab_width is None: return

    bridge_pattern = 0
    if tab_width > 0:
        bridge_pattern = rs.GetInteger("Bridge Pattern (0=Middle, 1=Alternating, 2=Random)", 1, 0, 2)
        if bridge_pattern is None: return

    rs.EnableRedraw(False)

    group_name = rs.AddGroup("VariableGrille")
    created_objs = []

    if rs.IsCurve(obj_id):
        if not rs.IsCurveClosed(obj_id):
            print("Selected curve must be closed.")
            rs.EnableRedraw(True)
            return
        if not rs.IsCurvePlanar(obj_id):
            print("Selected curve must be planar.")
            rs.EnableRedraw(True)
            return
        
        created_objs = process_curve_grille(obj_id, slit_width, gap_width, variation, margin, tab_width, bridge_pattern)
        
    elif rs.IsSurface(obj_id):
        created_objs = process_surface_grille(obj_id, slit_width, gap_width, variation, margin, tab_width, bridge_pattern)

    if created_objs:
        rs.AddObjectsToGroup(created_objs, group_name)
    
    rs.EnableRedraw(True)
    print("Created Variable Grille with {} geometries.".format(len(created_objs)))

def process_curve_grille(curve_id, width, gap, variation, margin, tab_width, bridge_pattern):
    slits = []
    
    # Coordinate system: Use the plane of the curve
    plane = rs.CurvePlane(curve_id)
    if not plane: return []
    
    # Get bounding box in plane coordinates
    xform = rs.XformRotation1(plane, rs.WorldXYPlane())
    
    # Work on a copy
    crv_copy = rs.CopyObject(curve_id)
    rs.TransformObject(crv_copy, xform)
    
    bbox = rs.BoundingBox(crv_copy)
    if not bbox:
        rs.DeleteObject(crv_copy)
        return []

    min_pt = bbox[0]
    max_pt = bbox[2]
    
    # Apply Margin to Bounds
    start_x = min_pt[0] + margin
    end_x = max_pt[0] - margin
    min_y_bound = min_pt[1]
    max_y_bound = max_pt[1]
    
    # Safety Check
    if start_x >= end_x:
        rs.DeleteObject(crv_copy)
        return []

    # Step along X
    current_x = start_x # Start at edge + margin
    slit_index = 0
    
    while current_x < end_x:
        center_x = current_x + width/2.0
        
        if center_x > end_x: break
        
        line_start = [center_x, min_y_bound - 10.0, 0]
        line_end = [center_x, max_y_bound + 10.0, 0]
        line_id = rs.AddLine(line_start, line_end)
        
        events = rs.CurveCurveIntersection(line_id, crv_copy)
        rs.DeleteObject(line_id)
        
        if events:
            y_coords = []
            for e in events:
                y_coords.append(e[1][1])
            y_coords.sort()
            
            for i in range(0, len(y_coords), 2):
                if i+1 >= len(y_coords): break
                y_bot = y_coords[i]
                y_top = y_coords[i+1]
                
                total_h = y_top - y_bot
                
                if total_h > 0.01:
                    max_var = min(variation, total_h * 0.9) if variation > 0 else 0
                    
                    if max_var > 0:
                        shrink = random.uniform(0, max_var)
                        shrink_bot = random.uniform(0, shrink)
                        shrink_top = shrink - shrink_bot
                        
                        y_bot += shrink_bot
                        y_top -= shrink_top
                    
                    if margin > 0:
                        if (y_top - y_bot) > margin * 2:
                            y_bot += margin
                            y_top -= margin
                        else:
                             continue
                    
                    if tab_width > 0 and (y_top - y_bot) > tab_width:
                        # Determine vertical position of the bridge
                        y_range = (y_top - y_bot) - tab_width
                        if bridge_pattern == 0: # Middle
                            y_bot_bridge = y_bot + y_range / 2.0
                        elif bridge_pattern == 1: # Alternating
                            if slit_index % 2 == 0:
                                y_bot_bridge = y_bot + y_range * 0.75 # High
                            else:
                                y_bot_bridge = y_bot + y_range * 0.25 # Low
                        else: # Random
                            y_bot_bridge = y_bot + random.uniform(0, y_range)
                            
                        y_mid = y_bot_bridge + tab_width / 2.0
                        
                        p1_b = [current_x, y_bot, 0]
                        p2_b = [current_x + width, y_bot, 0]
                        p3_b = [current_x + width, y_mid - tab_width/2.0, 0]
                        p4_b = [current_x, y_mid - tab_width/2.0, 0]
                        rect_id_b = rs.AddPolyline([p1_b, p2_b, p3_b, p4_b, p1_b])
                        slits.append(rect_id_b)
                        
                        p1_t = [current_x, y_mid + tab_width/2.0, 0]
                        p2_t = [current_x + width, y_mid + tab_width/2.0, 0]
                        p3_t = [current_x + width, y_top, 0]
                        p4_t = [current_x, y_top, 0]
                        rect_id_t = rs.AddPolyline([p1_t, p2_t, p3_t, p4_t, p1_t])
                        slits.append(rect_id_t)
                    else:
                        # Full Slit
                        p1 = [current_x, y_bot, 0]
                        p2 = [current_x + width, y_bot, 0]
                        p3 = [current_x + width, y_top, 0]
                        p4 = [current_x, y_top, 0]
                        rect_id = rs.AddPolyline([p1, p2, p3, p4, p1])
                        slits.append(rect_id)

        current_x += width + gap
        slit_index += 1

    inv_xform = rs.XformRotation1(rs.WorldXYPlane(), plane)
    rs.TransformObjects(slits, inv_xform)
    
    rs.DeleteObject(crv_copy)
    return slits

def process_surface_grille(srf_id, width, gap, variation, margin, tab_width, bridge_pattern):
    slits = []
    domain_u = rs.SurfaceDomain(srf_id, 0)
    domain_v = rs.SurfaceDomain(srf_id, 1)
    
    mid_v = (domain_v[0] + domain_v[1]) / 2.0
    u_iso = rs.ExtractIsoCurve(srf_id, [domain_u[0], mid_v], 0) 
    u_len = rs.CurveLength(u_iso)
    rs.DeleteObject(u_iso)
    
    if u_len == 0: return []
    
    u_range = domain_u[1] - domain_u[0]
    param_width = (width / u_len) * u_range
    param_gap = (gap / u_len) * u_range
    
    param_margin_u = (margin / u_len) * u_range if u_len > 0 else 0
    
    current_u = domain_u[0] + param_margin_u
    slit_index = 0
    
    while current_u < domain_u[1]:
        u_center = current_u + param_width/2.0
        if u_center > domain_u[1]: break
        
        v_min = domain_v[0]
        v_max = domain_v[1]
        orig_v_range = v_max - v_min
        
        v_iso = rs.ExtractIsoCurve(srf_id, [u_center, domain_v[0]], 1)
        v_len = rs.CurveLength(v_iso)
        rs.DeleteObject(v_iso)
        
        max_var = min(variation, v_len * 0.9) if variation > 0 else 0
        
        if max_var > 0:
            shrink = random.uniform(0, max_var)
            shrink_bot = random.uniform(0, shrink)
            shrink_top = shrink - shrink_bot
            
            p_shrink_bot = (shrink_bot / v_len) * orig_v_range
            p_shrink_top = (shrink_top / v_len) * orig_v_range
            
            v_min += p_shrink_bot
            v_max -= p_shrink_top

        if margin > 0:
            p_margin_v = (margin / v_len) * orig_v_range
            if (v_max - v_min) > p_margin_v * 2:
                v_min += p_margin_v
                v_max -= p_margin_v
            else:
                continue

        u1 = current_u
        u2 = current_u + param_width
        
        if tab_width > 0:
            p_tab_v = (tab_width / v_len) * orig_v_range if v_len > 0 else 0
            if (v_max - v_min) > p_tab_v:
                v_range_b = (v_max - v_min) - p_tab_v
                if bridge_pattern == 0:
                    v_bot_bridge = v_min + v_range_b / 2.0
                elif bridge_pattern == 1:
                    if slit_index % 2 == 0:
                        v_bot_bridge = v_min + v_range_b * 0.75
                    else:
                        v_bot_bridge = v_min + v_range_b * 0.25
                else:
                    v_bot_bridge = v_min + random.uniform(0, v_range_b)
                    
                v_mid = v_bot_bridge + p_tab_v / 2.0
                
                uv_pts_b = [ [u1, v_min], [u2, v_min], [u2, v_mid - p_tab_v/2.0], [u1, v_mid - p_tab_v/2.0], [u1, v_min] ]
                pts_3d_b = [rs.EvaluateSurface(srf_id, uv[0], uv[1]) for uv in uv_pts_b]
                slit_id_b = rs.AddPolyline(pts_3d_b)
                slits.append(slit_id_b)
                
                uv_pts_t = [ [u1, v_mid + p_tab_v/2.0], [u2, v_mid + p_tab_v/2.0], [u2, v_max], [u1, v_max], [u1, v_mid + p_tab_v/2.0] ]
                pts_3d_t = [rs.EvaluateSurface(srf_id, uv[0], uv[1]) for uv in uv_pts_t]
                slit_id_t = rs.AddPolyline(pts_3d_t)
                slits.append(slit_id_t)
            else:
                uv_pts = [ [u1, v_min], [u2, v_min], [u2, v_max], [u1, v_max], [u1, v_min] ]
                pts_3d = [rs.EvaluateSurface(srf_id, uv[0], uv[1]) for uv in uv_pts]
                slit_id = rs.AddPolyline(pts_3d)
                slits.append(slit_id)
        else:
            uv_pts = [ [u1, v_min], [u2, v_min], [u2, v_max], [u1, v_max], [u1, v_min] ]
            pts_3d = [rs.EvaluateSurface(srf_id, uv[0], uv[1]) for uv in uv_pts]
            slit_id = rs.AddPolyline(pts_3d)
            slits.append(slit_id)
                        
        current_u += param_width + param_gap
        slit_index += 1
        
    return slits

if __name__ == "__main__":
    create_variable_grille()
