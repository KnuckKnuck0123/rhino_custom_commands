import rhinoscriptsyntax as rs
import math

def create_polygonal_pipe():
    """
    Creates a pipe along curves with options for Round, Triangle, or Rectangle profiles.
    Supports multiple curves and groups.
    """
    # 1. Select Path Curves
    crv_ids = rs.GetObjects("Select path curves", rs.filter.curve, group=True, preselect=True)
    if not crv_ids: return

    # 2. Select Mode
    # Allow user to type R, T, or Box/Rec
    mode = rs.GetString("Pipe Shape", "Round", ["Round", "Triangle", "Rectangle"])
    if not mode: return
    mode = mode.lower()

    # 3. Gather Parameters based on mode
    pipe_params = {}
    
    if mode.startswith("rou"):
        radius = rs.GetReal("Pipe Radius", 1.0)
        if radius is None: return
        pipe_params['radius'] = radius

    elif mode.startswith("tri"):
        radius = rs.GetReal("Triangle Radius (Distance to corners)", 1.0)
        if radius is None: return
        pipe_params['radius'] = radius

    elif mode.startswith("rec") or mode.startswith("box") or mode.startswith("squ"):
        width = rs.GetReal("Width", 1.0)
        if width is None: return
        height = rs.GetReal("Height", width) # Defaults to square
        if height is None: return
        pipe_params['width'] = width
        pipe_params['height'] = height

    rs.EnableRedraw(False)
    
    all_created_objs = []
    
    try:
        for crv_id in crv_ids:
            new_objs = process_curve_pipe(crv_id, mode, pipe_params)
            if new_objs:
                all_created_objs.extend(new_objs)

        if all_created_objs:
            # Group them
            group_name = rs.AddGroup()
            if group_name:
                rs.AddObjectsToGroup(all_created_objs, group_name)
            
            # Select them (behaves like SelLast)
            rs.SelectObjects(all_created_objs)

    except Exception as e:
        print("Error creating pipe: {}".format(e))
        
    finally:
        rs.EnableRedraw(True)

def process_curve_pipe(crv_id, mode, params):
    """
    Internal function to process a single curve.
    Returns a list of created object IDs.
    """
    created_ids = []
    
    if mode.startswith("rou"):
        # --- ROUND PIPE ---
        radius = params['radius']
        
        # To ensure constant radius, we typically specify param 0 and param 1
        domain = rs.CurveDomain(crv_id)
        # AddPipe(curve_id, parameters, radii, blend_type=0, cap=0, fit=False)
        # Cap: 0=none, 1=flat, 2=round
        pipes = rs.AddPipe(crv_id, [domain[0], domain[1]], [radius, radius], cap=1)
        if pipes:
            created_ids.extend(pipes)

    else:
        # --- SWEEP BASED (Triangle/Rect) ---
        
        # 1. Get profile plane at start of curve
        start_param = rs.CurveDomain(crv_id)[0]
        plane = rs.CurvePerpFrame(crv_id, start_param)
        if not plane: return []
        
        profile_crv = None

        if mode.startswith("tri"):
            # --- TRIANGLE ---
            radius = params['radius']

            # Calculate 3 points for triangle polygon
            points = []
            # Angles: 90, 210, 330 degrees for a balanced triangle pointing 'up' relative to rail normal
            angles_deg = [90, 210, 330] 
            
            for deg in angles_deg:
                ang = math.radians(deg)
                local_x = radius * math.cos(ang)
                local_y = radius * math.sin(ang)
                
                pt = plane.Origin + (plane.XAxis * local_x) + (plane.YAxis * local_y)
                points.append(pt)
            
            # Close the loop
            points.append(points[0])
            profile_crv = rs.AddPolyline(points)

        elif mode.startswith("rec") or mode.startswith("box") or mode.startswith("squ"):
            # --- RECTANGLE ---
            width = params['width']
            height = params['height']
            
            # Draw manually to ensure centering
            w2 = width / 2.0
            h2 = height / 2.0
            
            corners = [
                (-w2, -h2), (w2, -h2), (w2, h2), (-w2, h2), (-w2, -h2)
            ]
            
            points = []
            for (cx, cy) in corners:
                pt = plane.Origin + (plane.XAxis * cx) + (plane.YAxis * cy)
                points.append(pt)
                
            profile_crv = rs.AddPolyline(points)
        
        if profile_crv:
            # Sweep
            sweeps = rs.AddSweep1(crv_id, [profile_crv], closed=True)
            if sweeps:
                for s_id in sweeps:
                    rs.CapPlanarHoles(s_id)
                created_ids.extend(sweeps)
            
            # Cleanup profile
            rs.DeleteObject(profile_crv)
            
    return created_ids

if __name__ == "__main__":
    create_polygonal_pipe()
