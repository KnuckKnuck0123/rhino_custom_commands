import rhinoscriptsyntax as rs
import random

def create_variable_grille_clean():
    """
    Creates a 'Variable Grille' of vertical slits, maintaining a clean border.
    Slots vary in height internally by splitting rather than shrinking the outer edges.
    """
    # 1. Select Boundary
    obj_id = rs.GetObject("Select Closed Curve or Surface for Clean Grille", rs.filter.curve | rs.filter.surface)
    if not obj_id: return

    # 2. Parameters
    slit_width = rs.GetReal("Slit Width", 3.0, 0.1)
    if slit_width is None: return

    gap_width = rs.GetReal("Gap between Slits", 3.0, 0.0)
    if gap_width is None: return

    margin = rs.GetReal("Clean Border Margin", 2.0, 0.0)
    if margin is None: return

    tab_width = rs.GetReal("Bridge/Tab Width between internal splits", 2.0, 0.1)
    if tab_width is None: return

    max_splits = rs.GetInteger("Max Number of Splits per Column (for height variation)", 3, 0)
    if max_splits is None: return

    rs.EnableRedraw(False)

    group_name = rs.AddGroup("VariableGrille_Clean")
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
        
        created_objs = process_curve_grille(obj_id, slit_width, gap_width, margin, tab_width, max_splits)
        
    elif rs.IsSurface(obj_id):
        created_objs = process_surface_grille(obj_id, slit_width, gap_width, margin, tab_width, max_splits)

    if created_objs:
        rs.AddObjectsToGroup(created_objs, group_name)
    
    rs.EnableRedraw(True)
    print("Created Clean Border Variable Grille with {} geometries.".format(len(created_objs)))

def process_curve_grille(curve_id, width, gap, margin, tab_width, max_splits):
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
    
    # Apply Margin to X Bounds
    start_x = min_pt[0] + margin
    end_x = max_pt[0] - margin
    min_y_bound = min_pt[1]
    max_y_bound = max_pt[1]
    
    # Safety Check
    if start_x >= end_x:
        rs.DeleteObject(crv_copy)
        return []

    # Step along X
    current_x = start_x 
    
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
                
                # Apply clean top and bottom margins
                if margin > 0:
                    if (y_top - y_bot) > margin * 2:
                        y_bot += margin
                        y_top -= margin
                    else:
                        continue
                        
                total_h = y_top - y_bot
                
                if total_h > 0.01:
                    # Determine how many times we will split this specific column
                    num_splits = random.randint(0, max_splits) if max_splits > 0 else 0
                    
                    # Make sure the tabs fit within the height
                    if num_splits * tab_width >= total_h * 0.5:
                        num_splits = int((total_h * 0.5) / tab_width)
                        
                    # Remaining space to be divided into individual holes
                    H = total_h - (num_splits * tab_width)
                    
                    if num_splits > 0 and H > 0.1:
                        # Pick random heights for the split centers
                        cuts = [random.uniform(0, H) for _ in range(num_splits)]
                        cuts.sort()
                        cuts = [0] + cuts + [H]
                        
                        current_y = y_bot
                        for j in range(len(cuts)-1):
                            hole_len = cuts[j+1] - cuts[j]
                            end_y = current_y + hole_len
                            
                            p1 = [current_x, current_y, 0]
                            p2 = [current_x + width, current_y, 0]
                            p3 = [current_x + width, end_y, 0]
                            p4 = [current_x, end_y, 0]
                            slits.append(rs.AddPolyline([p1, p2, p3, p4, p1]))
                            
                            current_y = end_y + tab_width
                    else:
                        # Full Slit
                        p1 = [current_x, y_bot, 0]
                        p2 = [current_x + width, y_bot, 0]
                        p3 = [current_x + width, y_top, 0]
                        p4 = [current_x, y_top, 0]
                        slits.append(rs.AddPolyline([p1, p2, p3, p4, p1]))

        current_x += width + gap

    inv_xform = rs.XformRotation1(rs.WorldXYPlane(), plane)
    rs.TransformObjects(slits, inv_xform)
    
    rs.DeleteObject(crv_copy)
    return slits

def process_surface_grille(srf_id, width, gap, margin, tab_width, max_splits):
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
    
    while current_u < domain_u[1]:
        u_center = current_u + param_width/2.0
        if u_center > domain_u[1]: break
        
        v_min = domain_v[0]
        v_max = domain_v[1]
        orig_v_range = v_max - v_min
        
        v_iso = rs.ExtractIsoCurve(srf_id, [u_center, domain_v[0]], 1)
        v_len = rs.CurveLength(v_iso)
        rs.DeleteObject(v_iso)

        if margin > 0:
            p_margin_v = (margin / v_len) * orig_v_range
            if (v_max - v_min) > p_margin_v * 2:
                v_min += p_margin_v
                v_max -= p_margin_v
            else:
                current_u += param_width + param_gap
                continue

        u1 = current_u
        u2 = current_u + param_width
        
        total_v = v_max - v_min
        p_tab_v = (tab_width / v_len) * orig_v_range if v_len > 0 else 0
        
        num_splits = random.randint(0, max_splits) if max_splits > 0 else 0
        
        if num_splits * p_tab_v >= total_v * 0.5:
            num_splits = int((total_v * 0.5) / p_tab_v) if p_tab_v > 0 else 0
            
        V_H = total_v - (num_splits * p_tab_v)
        
        if num_splits > 0 and V_H > 0.01:
            cuts = [random.uniform(0, V_H) for _ in range(num_splits)]
            cuts.sort()
            cuts = [0] + cuts + [V_H]
            
            current_v = v_min
            for j in range(len(cuts)-1):
                hole_len_v = cuts[j+1] - cuts[j]
                end_v = current_v + hole_len_v
                
                uv_pts = [ [u1, current_v], [u2, current_v], [u2, end_v], [u1, end_v], [u1, current_v] ]
                pts_3d = [rs.EvaluateSurface(srf_id, uv[0], uv[1]) for uv in uv_pts]
                slits.append(rs.AddPolyline(pts_3d))
                
                current_v = end_v + p_tab_v
        else:
            uv_pts = [ [u1, v_min], [u2, v_min], [u2, v_max], [u1, v_max], [u1, v_min] ]
            pts_3d = [rs.EvaluateSurface(srf_id, uv[0], uv[1]) for uv in uv_pts]
            slits.append(rs.AddPolyline(pts_3d))
                        
        current_u += param_width + param_gap
        
    return slits

if __name__ == "__main__":
    create_variable_grille_clean()
