import rhinoscriptsyntax as rs
import Rhino
import scriptcontext
import math
import random

def get_surfaces_info(srf_ids):
    srfs_info = []
    centroids = []
    
    for s_id in srf_ids:
        c = rs.SurfaceAreaCentroid(s_id)
        if c:
            centroids.append(c[0])
        else:
            centroids.append(rs.BoundingBox(s_id)[0]) # fallback
            
    for i, srf_id in enumerate(srf_ids):
        crvs = rs.DuplicateSurfaceBorder(srf_id)
        if not crvs: continue
        
        # Merge border curves to one boolean
        border_geom = rs.coercecurve(crvs[0])
        for j in range(1, len(crvs)):
            next_geom = rs.coercecurve(crvs[j])
            joined = Rhino.Geometry.Curve.JoinCurves([border_geom, next_geom])
            if joined:
                border_geom = joined[0]
                
        poly = rs.ConvertCurveToPolyline(crvs[0])
        pts = rs.CurvePoints(poly)
        for c in crvs: rs.DeleteObject(c)
        if poly: rs.DeleteObject(poly)
        
        plane = rs.PlaneFitFromPoints(pts)
        if not plane: continue
        
        world_z = Rhino.Geometry.Vector3d(0,0,1)
        normal = plane.ZAxis
        if abs(normal.Z) < 0.99: 
            horiz_x = Rhino.Geometry.Vector3d.CrossProduct(normal, world_z)
            horiz_x.Unitize()
            horiz_y = Rhino.Geometry.Vector3d.CrossProduct(normal, horiz_x)
            horiz_y.Unitize()
            if horiz_y.Z < 0:
                horiz_y = -horiz_y
                horiz_x = -horiz_x
            plane = Rhino.Geometry.Plane(plane.Origin, horiz_x, horiz_y)
        
        # Orient XAxis along the sequence to form a ribbon
        if len(srf_ids) > 1:
            if i < len(srf_ids) - 1:
                flow_vec = centroids[i+1] - centroids[i]
            else:
                flow_vec = centroids[i] - centroids[i-1]
            
            flow_vec.Z = 0
            if flow_vec.Length > 0.001:
                flow_vec.Unitize()
                horiz_v = Rhino.Geometry.Vector3d(plane.XAxis)
                horiz_v.Z = 0
                if horiz_v.Length > 0.001:
                    horiz_v.Unitize()
                    if horiz_v * flow_vec < -0.1:
                        plane = Rhino.Geometry.Plane(plane.Origin, -plane.XAxis, plane.YAxis)
                        
        # Get 2D bounds to shift origin
        min_u, max_u = float('inf'), float('-inf')
        min_v, max_v = float('inf'), float('-inf')
        
        for pt in pts:
            b, u, v = plane.ClosestParameter(pt)
            if u < min_u: min_u = u
            if u > max_u: max_u = u
            if v < min_v: min_v = v
            if v > max_v: max_v = v
            
        width = max_u - min_u
        height = max_v - min_v
        
        origin = plane.PointAt(min_u, min_v)
        plane = Rhino.Geometry.Plane(origin, plane.XAxis, plane.YAxis)
        
        srfs_info.append({
            "id": srf_id,
            "plane": plane,
            "width": width,
            "height": height,
            "border_geom": border_geom
        })
        
    return srfs_info

def generate_preview(srfs_info, params):
    target_width = params["panel_width"]
    target_height = params["panel_height"]
    mullion = params["mullion_width"]
    break_up_chance = params["break_up"]
    seed = params.get("seed", 42)
    
    random.seed(seed)
    
    total_L = sum([info["width"] for info in srfs_info])
    max_H = max([info["height"] for info in srfs_info]) if srfs_info else 0
    
    if total_L <= 0 or max_H <= 0: return []
    
    nv = max(1, int(round(total_L / target_width)))
    nh = max(1, int(round(max_H / target_height)))
    
    actual_w = total_L / nv
    actual_h = max_H / nh
    
    global_xs = [i * actual_w for i in range(nv + 1)]
    global_ys = [i * actual_h for i in range(nh + 1)]
    
    # Pre-generate global grid
    panels = []
    for i in range(nv):
        for j in range(nh):
            panels.append({
                'col': i,
                'row': j,
                'x1': global_xs[i],
                'x2': global_xs[i+1],
                'y1': global_ys[j],
                'y2': global_ys[j+1],
                'active': True
            })
            
    # Break up panels
    if break_up_chance > 0:
        for p in panels:
            if not p['active']: continue
            if random.random() < break_up_chance:
                # 50% chance to merge right, 50% to merge up
                if random.choice([True, False]):
                    neighbors = [n for n in panels if n['active'] and n['col'] == p['col']+1 and n['row'] == p['row'] and abs(n['y1'] - p['y1']) < 0.001 and abs(n['y2'] - p['y2']) < 0.001]
                    if neighbors:
                        n = neighbors[0]
                        p['x2'] = n['x2']
                        n['active'] = False
                else:
                    neighbors = [n for n in panels if n['active'] and n['row'] == p['row']+1 and n['col'] == p['col'] and abs(n['x1'] - p['x1']) < 0.001 and abs(n['x2'] - p['x2']) < 0.001]
                    if neighbors:
                        n = neighbors[0]
                        p['y2'] = n['y2']
                        n['active'] = False

    created_objs = []
    tol = scriptcontext.doc.ModelAbsoluteTolerance
    
    current_x = 0.0
    
    for info in srfs_info:
        plane = info["plane"]
        width = info["width"]
        border_geom = info["border_geom"]
        
        start_u = current_x
        end_u = current_x + width
        
        # Transform 3D border to local 2D space for clean intersection
        xform_to_2d = Rhino.Geometry.Transform.ChangeBasis(Rhino.Geometry.Plane.WorldXY, plane)
        xform_to_3d = Rhino.Geometry.Transform.ChangeBasis(plane, Rhino.Geometry.Plane.WorldXY)
        
        border_2d = border_geom.Duplicate()
        border_2d.Transform(xform_to_2d)
        
        # Collect panel curves in 2D
        local_panels_2d = []
        
        for p in panels:
            if not p['active']: continue
            
            # Intersection of panel with this surface's U slice
            cx1 = max(p['x1'], start_u) - start_u
            cx2 = min(p['x2'], end_u) - start_u
            cy1 = p['y1']
            cy2 = p['y2']
            
            if cx1 < cx2 and cy1 < cy2:
                # Apply local mullion offsets
                px_min = cx1 + mullion / 2.0
                px_max = cx2 - mullion / 2.0
                py_min = cy1 + mullion / 2.0
                py_max = cy2 - mullion / 2.0
                
                if px_min < px_max and py_min < py_max:
                    rect = rs.AddPolyline([
                        [px_min, py_min, 0],
                        [px_max, py_min, 0],
                        [px_max, py_max, 0],
                        [px_min, py_max, 0],
                        [px_min, py_min, 0]
                    ])
                    if rect:
                        rect_geom = rs.coercecurve(rect)
                        local_panels_2d.append(rect_geom)
                        rs.DeleteObject(rect)
                        
        # Intersect all panels collectively (or individually) with surface boundary
        if local_panels_2d and border_2d:
            for p_geom in local_panels_2d:
                try:
                    intersections = Rhino.Geometry.Curve.CreateBooleanIntersection(p_geom, border_2d, tol)
                    if intersections:
                        for inter in intersections:
                            inter.Transform(xform_to_3d) # Map back to 3D
                            obj_id = scriptcontext.doc.Objects.AddCurve(inter)
                            if obj_id: created_objs.append(obj_id)
                except Exception as e:
                    pass
        
        current_x += width

    return created_objs

def create_continuous_curtain_wall():
    srf_ids = rs.GetObjects("Select continuous planar surfaces in sequence", rs.filter.surface | rs.filter.polysurface)
    if not srf_ids: return
    
    srfs_info = get_surfaces_info(srf_ids)
    if not srfs_info:
        print("Could not extract valid planes from selected surfaces.")
        return
        
    params = {
        "panel_width": 4.0,
        "panel_height": 8.0,
        "mullion_width": 0.2,
        "break_up": 0.2,
        "seed": 42
    }
    
    labels = [
        "Target Panel Width",
        "Target Panel Height",
        "Mullion Width",
        "Break Up Chance (0.0-1.0)",
        "Random Seed"
    ]
    
    defaults = [
        str(params["panel_width"]),
        str(params["panel_height"]),
        str(params["mullion_width"]),
        str(params["break_up"]),
        str(params["seed"])
    ]
    
    title = "Continuous Curtain Wall Parameter"
    msg = "Configure uniform panel constraints and break up chance."
    
    preview_ids = []
    
    while True:
        if preview_ids:
            rs.DeleteObjects(preview_ids)
            preview_ids = []
            
        rs.EnableRedraw(False)
        preview_ids = generate_preview(srfs_info, params)
        rs.EnableRedraw(True)
        
        results = rs.PropertyListBox(labels, defaults, title, msg)
        
        if not results:
            if preview_ids: rs.DeleteObjects(preview_ids)
            print("Operation cancelled.")
            break
            
        defaults = results
        
        try:
            params["panel_width"] = max(0.1, float(results[0]))
            params["panel_height"] = max(0.1, float(results[1]))
            params["mullion_width"] = max(0.0, float(results[2]))
            params["break_up"] = max(0.0, min(1.0, float(results[3])))
            params["seed"] = int(results[4])
        except:
            rs.MessageBox("Invalid inputs.")
            continue
            
        res = rs.MessageBox("Accept Layout?\nYes = Apply\nNo = Edit again\nCancel = Quit", 3 | 32)
        
        if res == 6: # Yes
            group = rs.AddGroup("ContinuousCurtainWall")
            if preview_ids:
                rs.AddObjectsToGroup(preview_ids, group)
                rs.SelectObjects(preview_ids)
            print("Curtain wall applied to {} surfaces.".format(len(srf_ids)))
            break
        elif res == 2: # Cancel
            if preview_ids: rs.DeleteObjects(preview_ids)
            break

if __name__ == "__main__":
    create_continuous_curtain_wall()
