import rhinoscriptsyntax as rs
import random

def create_variable_grille():
    """
    Creates a 'Variable Grille' of vertical slits with specified width and height variation.
    Can be generated inside a closed planar curve (filling it) or distributed across a surface.
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
        
        created_objs = process_curve_grille(obj_id, slit_width, gap_width, variation, margin)
        
    elif rs.IsSurface(obj_id):
        created_objs = process_surface_grille(obj_id, slit_width, gap_width, variation, margin)

    if created_objs:
        rs.AddObjectsToGroup(created_objs, group_name)
    
    rs.EnableRedraw(True)
    print("Created Variable Grille with {} slits.".format(len(created_objs)))

def process_curve_grille(curve_id, width, gap, variation, margin):
    slits = []
    
    # Coordinate system: Use the plane of the curve
    plane = rs.CurvePlane(curve_id)
    if not plane: return []
    
    # Get bounding box in plane coordinates
    # We can transform curve to XY, do logic, transform back
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
    
    while current_x < end_x:
        # Define a vertical line slice at the CENTER of the proposed slit
        # or check both edges? 
        # Efficient approach: Intersection at center X
        center_x = current_x + width/2.0
        
        # Check if center is within X bounds
        if center_x > end_x: break
        
        # Vertical ray (Line)
        line_start = [center_x, min_y_bound - 10.0, 0]
        line_end = [center_x, max_y_bound + 10.0, 0]
        line_id = rs.AddLine(line_start, line_end)
        
        # Intersect
        events = rs.CurveCurveIntersection(line_id, crv_copy)
        rs.DeleteObject(line_id)
        
        if events:
            # Sort intersection points by Y
            y_coords = []
            for e in events:
                # e[1] is point on first curve (line)
                y_coords.append(e[1][1])
            y_coords.sort()
            
            # Create slits for intervals
            # Assume closed curve -> even number of intersections
            for i in range(0, len(y_coords), 2):
                if i+1 >= len(y_coords): break
                y_bot = y_coords[i]
                y_top = y_coords[i+1]
                
                # Apply variation
                # Reduce height by random amount, but keep centered or random shift?
                # User asked for "variation in their height".
                # Let's perform a random shrink from both ends
                
                total_h = y_top - y_bot
                
                if total_h > 0.01: # Filter tiny slivers
                    # If variation is set, reduce height
                    # Limit variation to total_height * 0.9 to avoid inversion
                    max_var = min(variation, total_h * 0.9) if variation > 0 else 0
                    
                    if max_var > 0:
                        shrink = random.uniform(0, max_var)
                        # Distribute shrink randomly between top and bottom
                        shrink_bot = random.uniform(0, shrink)
                        shrink_top = shrink - shrink_bot
                        
                        y_bot += shrink_bot
                        y_top -= shrink_top
                    
                    # Apply Margin vertically as well
                    if margin > 0:
                        if (y_top - y_bot) > margin * 2:
                            y_bot += margin
                            y_top -= margin
                        else:
                             # If margin consumes the whole slit, skip it?
                             continue
                    
                    # Create Rectangle
                    # (x, y_bot) to (x+w, y_top)
                    p1 = [current_x, y_bot, 0]
                    p2 = [current_x + width, y_bot, 0]
                    p3 = [current_x + width, y_top, 0]
                    p4 = [current_x, y_top, 0]
                    
                    rect_id = rs.AddPolyline([p1, p2, p3, p4, p1])
                    slits.append(rect_id)

        current_x += width + gap

    # Transform slits back to original plane
    inv_xform = rs.XformRotation1(rs.WorldXYPlane(), plane)
    rs.TransformObjects(slits, inv_xform)
    
    rs.DeleteObject(crv_copy)
    return slits

def process_surface_grille(srf_id, width, gap, variation, margin):
    # This maps the grid onto the surface UV domain directly.
    # Note: 'width' and 'gap' in UV space might distort if surface is not uniform.
    # To do this accurately in physical units, we would need to measure surface.
    # For now, we'll try to estimate UV step based on domain size/length.
    
    slits = []
    domain_u = rs.SurfaceDomain(srf_id, 0)
    domain_v = rs.SurfaceDomain(srf_id, 1)
    
    # Estimate length in U direction to calibrate steps
    mid_v = (domain_v[0] + domain_v[1]) / 2.0
    u_iso = rs.ExtractIsoCurve(srf_id, [domain_u[0], mid_v], 0) 
    u_len = rs.CurveLength(u_iso)
    rs.DeleteObject(u_iso)
    
    if u_len == 0: return []
    
    # Param width
    # If total length is u_len, then param_width = (width / u_len) * (u_max - u_min)
    u_range = domain_u[1] - domain_u[0]
    param_width = (width / u_len) * u_range
    param_gap = (gap / u_len) * u_range
    
    # Param margin (approximate in U)
    param_margin_u = (margin / u_len) * u_range if u_len > 0 else 0
    
    current_u = domain_u[0] + param_margin_u
    
    while current_u < domain_u[1]:
        # We will create an Isocurve (vertical) or construct the rectangle in UV space and map?
        # Creating curves on surface is cleaner.
        
        # Center of slit
        u_center = current_u + param_width/2.0
        if u_center > domain_u[1]: break
        
        # Slit V range
        v_min = domain_v[0]
        v_max = domain_v[1]
        
        # Apply Variation to V (height)
        # Using V-domain directly might be tricky if V-length varies.
        # But assuming relatively uniform surface:
        
        # Get approx V length at this U
        v_iso = rs.ExtractIsoCurve(srf_id, [u_center, domain_v[0]], 1)
        v_len = rs.CurveLength(v_iso)
        rs.DeleteObject(v_iso)
        
        max_var = min(variation, v_len * 0.9) if variation > 0 else 0
        
        if max_var > 0:
            shrink = random.uniform(0, max_var)
            shrink_bot = random.uniform(0, shrink)
            shrink_top = shrink - shrink_bot
            
            # Convert physical shrink to param shrink (approx)
            # param_shrink = (shrink / v_len) * v_range
            v_range = v_max - v_min
            
            p_shrink_bot = (shrink_bot / v_len) * v_range
            p_shrink_top = (shrink_top / v_len) * v_range
            
            v_min += p_shrink_bot
            v_max -= p_shrink_top

        if margin > 0:
            # Approx parameter for margin
            p_margin_v = (margin / v_len) * v_range
            if (v_max - v_min) > p_margin_v * 2:
                v_min += p_margin_v
                v_max -= p_margin_v
            else:
                continue

        # Create Surface Curve (Rectangle equivalent)
        # Rectangle in UV space:
        # (u, v_min), (u+w, v_min), (u+w, v_max), (u, v_max)
        
        u1 = current_u
        u2 = current_u + param_width
        
        # 4 corners in UV
        uv_pts = [ [u1, v_min], [u2, v_min], [u2, v_max], [u1, v_max], [u1, v_min] ]
        
        # Evaluate 3D points
        pts_3d = []
        for uv in uv_pts:
            pts_3d.append(rs.EvaluateSurface(srf_id, uv[0], uv[1]))
            
        # Create Polyline on surface?
        # A flat polyline might not lie on surface.
        # rs.AddInterpCurveOnSurface(srf_id, points)
        # But sharp corners? AddCurveOnSurface uses control points.
        # Maybe just create the 3D Polyline (chord approximation).
        # "Drawn on a surface" usually means geometry projected or mapped.
        # A simple polyline connecting evaluated points works well for "visual" grille unless it needs to be strictly geodesic.
        
        slit_id = rs.AddPolyline(pts_3d)
        slits.append(slit_id)
        
        current_u += param_width + param_gap
        
    return slits

if __name__ == "__main__":
    create_variable_grille()
