import rhinoscriptsyntax as rs
import Rhino
import System.Collections.Generic
import random
import math

def create_rigid_brick_pile():
    """
    Creates a pile of bricks by simulating dropping them vertically.
    Prevents floating and overlapping by raycasting against previously placed bricks.
    """
    # 1. User Inputs
    num_bricks = rs.GetInteger("Number of bricks", 50, 1, 1000)
    if num_bricks is None: return False

    # Dimensions
    l = 20.0
    w = 10.0
    h = 5.0
    
    # Pile Radius
    pile_radius = rs.GetReal("Pile Radius", 50.0)
    if pile_radius is None: return False

    center = rs.GetPoint("Select center point")
    if not center: return False

    rs.EnableRedraw(False)
    rs.StatusBarProgressMeterShow("Stacking Bricks", 0, num_bricks, True, True)

    placed_meshes = []
    
    # Create the base mesh (box) geometry once to clone
    # We use Meshes for faster intersection calculations than Breps
    base_box = Rhino.Geometry.Mesh.CreateFromBox(
        Rhino.Geometry.Box(Rhino.Geometry.Plane.WorldXY, 
        Rhino.Geometry.Interval(-l/2, l/2),
        Rhino.Geometry.Interval(-w/2, w/2),
        Rhino.Geometry.Interval(-h/2, h/2)),
        1, 1, 1
    )

    try:
        for i in range(num_bricks):
            rs.StatusBarProgressMeterUpdate(i, True)
            
            if i % 5 == 0:
                rs.Prompt("Stacking brick {} of {}...".format(i+1, num_bricks))

            # 1. Spawn Position
            # Improve randomness: biased towards center?
            # Random angle and distance
            angle = random.uniform(0, 2*math.pi)
            # Square root of random for uniform disk distribution, or pure random for center clump
            # User wants a "pile", usually means conical.
            # Let's use a Gaussian distribution for natural piling
            r_dist = abs(random.gauss(0, pile_radius/2.0)) 
            
            dx = r_dist * math.cos(angle)
            dy = r_dist * math.sin(angle)
            
            spawn_x = center.X + dx
            spawn_y = center.Y + dy
            
            # 2. Orientation
            rot_z = random.uniform(0, 360)
            
            # 3. Create Candidate Mesh
            temp_mesh = base_box.Duplicate()
            
            # Rotate
            xform_rot = Rhino.Geometry.Transform.Rotation(math.radians(rot_z), Rhino.Geometry.Vector3d.ZAxis, Rhino.Geometry.Point3d.Origin)
            temp_mesh.Transform(xform_rot)
            
            # Move to XY position (at Z=0 initially)
            xform_move = Rhino.Geometry.Transform.Translation(spawn_x, spawn_y, 0)
            temp_mesh.Transform(xform_move)
            
            # 4. Collision Detection (The Drop)
            # practical z-offset to ensure we are above everything?
            # No, we just want to find the highest point BELOW this brick.
            
            highest_hit_z = center.Z # Ground level
            
            if len(placed_meshes) > 0:
                # To find where it sits, we raycast DOWN from the bottom of the new brick
                # We need significant sample points to catch corners of bricks below.
                # Just corners of the new brick might miss a brick below if the new brick is huge.
                # But here bricks are same size.
                
                # Sample points: Vertices of bottom face + center + maybe midpoints
                # For a box mesh: 
                # Vertices 0-3 are usually bottom, 4-7 top (depends on creation)
                # Let's inspect vertices.
                # Safest way: Get bounding box, take 4 corners of bottom face, + center.
                
                bbox = temp_mesh.GetBoundingBox(True)
                # corners
                corners = bbox.GetCorners() # 8 corners. 0-3 bottom usually.
                
                # Filter to find actual bottom vertices of the mesh (transformed)
                # Or just use the mesh vertices.
                # Mesh vertices are low count for a box (8).
                
                test_points = []
                for v in temp_mesh.Vertices:
                    # We might want to raycast from *every* vertex? 
                    # Actually we only care about vertices that are "bottom-ish"
                    # But since it's flat, all vertices are candidates if we rotated?
                    # Wait, we only rotated Z. So flat bottom is preserved.
                    # So vertices with lower Z are the bottom ones.
                    if v.Z < 1.0: # Close to 0
                        test_points.append(Rhino.Geometry.Point3d(v))
                
                # Add Center of bottom face
                # average of bottom vertices
                if len(test_points) > 0:
                    avg_x = sum([p.X for p in test_points])/len(test_points)
                    avg_y = sum([p.Y for p in test_points])/len(test_points)
                    test_points.append(Rhino.Geometry.Point3d(avg_x, avg_y, 0)) # Center
                    
                    # Add midpoints of edges for better coverage?
                    # 5 points (corners + center) is decent for roughly same sized bricks.
                    # 9 points is safer.
                    # Lets add points between center and corners.
                    
                
                # Raycast Vector: Down
                down_vec = Rhino.Geometry.Vector3d(0, 0, -1)
                
                # 4a. Check rays from NEW brick DOWN to OLD piles
                for pt in test_points:
                    # Start ray high up?
                    # RayShoot intersects geometry.
                    ray = Rhino.Geometry.Ray3d(Rhino.Geometry.Point3d(pt.X, pt.Y, 10000), down_vec)
                    
                    # Shoot against all placed meshes
                    # Optimization: Only check meshes roughly within bounding box range? 
                    # Spatial grid is complex for python script. 
                    # RayShoot is fast enough for <1000 meshes usually.
                    
                    hits = Rhino.Geometry.Intersect.Intersection.RayShoot(ray, placed_meshes, 1)
                    if hits and len(hits) > 0:
                        # hit: Point3d
                        hit_pt = hits[0]
                        # The ray started at 10000. 
                        # We want the surface Z.
                        if hit_pt.Z > highest_hit_z:
                            highest_hit_z = hit_pt.Z

                # 4b. Check rays from OLD bricks UP to NEW brick?
                # This prevents a sharp corner of an old brick from penetrating the *face* of the new brick 
                # if the new brick lands 'between' the user's sample points.
                # This is computationally expensive (Checking all old vertices against new mesh).
                # Optimization: Only check old bricks that we successfully hit in 4a? 
                # Or meshes whose bounding box overlaps the new brick's XY.
                
                # Let's do a bounding box filter for "Old vertices UP" check.
                new_bbox_xy = temp_mesh.GetBoundingBox(True)
                # Expand slightly
                
                up_vec = Rhino.Geometry.Vector3d(0,0,1)
                
                # Filter candidates
                close_meshes = []
                for pm in placed_meshes:
                    pm_bbox = pm.GetBoundingBox(True)
                    if pm_bbox.Max.X < new_bbox_xy.Min.X or pm_bbox.Min.X > new_bbox_xy.Max.X: continue
                    if pm_bbox.Max.Y < new_bbox_xy.Min.Y or pm_bbox.Min.Y > new_bbox_xy.Max.Y: continue
                    close_meshes.append(pm)
                    
                for pm in close_meshes:
                    # check its top vertices
                    # For a box rotated around Z, top vertices are the ones with Z > 0 (relative to its center)
                    # But here meshes are transformed to world.
                    # Just check all 8 vertices.
                    for v in pm.Vertices:
                        # Raycast UP from this vertex to the new mesh
                        ray = Rhino.Geometry.Ray3d(Rhino.Geometry.Point3d(v.X, v.Y, v.Z - 0.1), up_vec) # start slightly below
                        
                        # Intersect with NEW mesh (positioned at Z=0 currently)
                        # We want to know if this vertex is *under* the new mesh's footprint.
                        # Using RayShoot against the new mesh.
                        
                        # Temp mesh is at Z=0.
                        # If the old vertex is at Z=50.
                        # We shoot up from 50.
                        # If we hit the new mesh (at 0), it won't hit essentially?
                        # Actually we need to check if the vertex is inside the XY outline of the new mesh.
                        
                        # Simplified check:
                        # Raycast DOWN from high Z at (v.X, v.Y) against NEW mesh.
                        ray_check = Rhino.Geometry.Ray3d(Rhino.Geometry.Point3d(v.X, v.Y, 1000), down_vec)
                        hits = Rhino.Geometry.Intersect.Intersection.MeshRay(temp_mesh, ray_check)
                        if hits >= 0.0:
                            # It hit. That means this old vertex is strictly under the new brick.
                            # The hit point Z on the new brick is ~0 (if flat) or whatever.
                            # We need to raise the new brick so that its hit point is ABOVE the old vertex.
                            
                            # The new brick is currently at Z=0.
                            # The intersection point on the new brick is `hit_pt_on_mesh`.
                            hit_pt_on_mesh = ray_check.PointAt(hits)
                            # hit_pt_on_mesh.Z is likely near 0 or -h/2 etc.
                            
                            # The GAP required is v.Z - hit_pt_on_mesh.Z
                            required_z = v.Z + (0 - hit_pt_on_mesh.Z) # adjust for local offset
                            if required_z > highest_hit_z:
                                highest_hit_z = required_z

            # 5. Place it
            # The bottom of the brick should be at highest_hit_z
            # Our temp_mesh has its bottom at Z = -h/2 (if centered) or 0? 
            # We created box -h/2 to h/2.
            # So bottom is at -2.5.
            # We want bottom to be at highest_hit_z + epsilon
            
            # The mesh is currently at Z Translation 0 -> Center is 0 -> Bottom is -2.5
            # We want Bottom to be Highest_Z.
            # So Center must be Highest_Z + 2.5
            
            target_center_z = highest_hit_z + (h/2.0)
            
            xform_final = Rhino.Geometry.Transform.Translation(0, 0, target_center_z)
            temp_mesh.Transform(xform_final)
            
            placed_meshes.append(temp_mesh)
            
            # Add to document periodically or at end?
            # Adding meshes is fast.
            # But let's add at end to allow Cancel to be clean?
            # Actually showing progress is fun. Let's add every 10 or so? 
            # No, keep list for speed, add all at once.
            
    except Exception as e:
        print("Error: {}".format(e))
        
    finally:
        # Bake meshes
        rs.StatusBarProgressMeterShow("Baking Meshes", 0, len(placed_meshes), True, True)
        
        for i, m in enumerate(placed_meshes):
            rs.StatusBarProgressMeterUpdate(i, True)
            sc.doc.Objects.AddMesh(m)
        
        rs.StatusBarProgressMeterHide()
        rs.EnableRedraw(True)
        sc.doc.Views.Redraw()
        print("Stacked {} bricks.".format(len(placed_meshes)))

    return True

# Need to import scriptcontext to access doc if we strictly follow RhinoCommon
import scriptcontext as sc
import rhinoscriptsyntax as rs

if "scriptcontext" not in locals():
    import scriptcontext as sc
# Ensure doc is active
if not sc.doc: sc.doc = Rhino.RhinoDoc.ActiveDoc

if __name__ == "__main__":
    # Loop to allow re-running easily
    while True:
        # Check for escape key or cancellation inside the function
        # We need the function to return status. 
        # Modifying the function to return False on cancel would be ideal, 
        # but catching the None returns is enough if we check carefully.
        
        # To make this robust without rewriting all returns:
        # We just ask "Run again?" at the end if successful?
        # Or simply loop and if inputs are cancelled, we break.
        
        result = create_rigid_brick_pile()
        
        # If result is None (inputs cancelled), break
        if result is False or result is None:
            print("Script cancelled.")
            break
        
        # Optional: Explicit Prompt to continue
        # rs.GetBoolean or GetString
        # Just looping into inputs is usually the standard Rhino command flow (Repeat command).
        # We will assume if they Cancel inputs, they want to stop.

