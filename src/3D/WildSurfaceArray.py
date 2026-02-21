import rhinoscriptsyntax as rs
import Rhino.Geometry as rg
import Rhino
import random
import math
import bisect

def create_wild_surface_array():
    # 1. Select Source Object
    source_id = rs.GetObject("Select object to scatter (Greeble)", preselect=True)
    if not source_id: 
        return
    
    # 2. Select Target Surface/Mesh/SubD
    # Filter: Surface(8) + Polysurface(16) + Mesh(32) + SubD(262144 - though often passed via other filters depending on API version)
    # providing 0 usually allows all, but let's try to be specific or allow generic selection
    target_id = rs.GetObject("Select target Surface, Polysurface, Mesh, or SubD", 8 | 16 | 32)
    if not target_id: 
        return

    # Calculate initial defaults from Source (Bottom Center)
    bbox = rs.BoundingBox(source_id)
    if not bbox: 
        return
    
    # Bbox 0=Min, 6=Max (approx). We want center of bottom face.
    min_pt = bbox[0]
    max_pt = bbox[6]
    
    # Default to placing the object's bottom center on the surface
    source_base_center = rg.Point3d((min_pt.X + max_pt.X)/2.0, (min_pt.Y + max_pt.Y)/2.0, min_pt.Z)

    # 3. Setup Inputs
    # Labels
    labels = [
        "Total Count",                     # 0
        "Scale Base (1.0 = Original)",     # 1
        "Scale Var (0.5 = +/- 0.5)",       # 2
        "Offset Z (Base)",                 # 3
        "Offset Z Var (+/-)",              # 4
        "Rot Z (Spin Max Deg)",            # 5
        "Rot X/Y (Tilt Max Deg)",          # 6
        "Seed"                             # 7
    ]
    
    # Initial Defaults
    defaults = [
        "50",                              # Count
        "1.0",                             # Scale Base
        "0.2",                             # Scale Var
        "0.0",                             # Offset Base
        "0.0",                             # Offset Var
        "360",                             # Spin (Full random)
        "5",                               # Tilt (Slight wobble)
        "1234"                             # Seed
    ]
    
    title = "Wild Surface Array"
    msg = "Step 2: Define Scatter Parameters."
    
    # 4. Preparation: Get Target Mesh (Robust Conversion)
    target_obj = rs.coercerhinoobject(target_id)
    mesh = None
    
    # Strategy: Try to get existing render meshes, otherwise generate new mesh from geometry
    existing_meshes = target_obj.GetMeshes(rg.MeshType.Preview)
    if existing_meshes and existing_meshes.Count > 0:
        mesh = existing_meshes[0]
        # Copy to avoid modifying original document mesh if that's a thing
        mesh = mesh.Duplicate()
        for i in range(1, existing_meshes.Count):
            mesh.Append(existing_meshes[i])
    else:
        # Generate new mesh
        mp = Rhino.Geometry.MeshingParameters.FastRenderMesh
        if isinstance(target_obj.Geometry, rg.Brep):
            m_arr = rg.Mesh.CreateFromBrep(target_obj.Geometry, mp)
            if m_arr: 
                mesh = m_arr[0]
                for i in range(1, len(m_arr)): mesh.Append(m_arr[i])
        elif isinstance(target_obj.Geometry, rg.SubD):
            mesh = rg.Mesh.CreateFromSubD(target_obj.Geometry, 1) # 1 = Smooth
        elif isinstance(target_obj.Geometry, rg.Mesh):
            mesh = target_obj.Geometry.Duplicate()
            
    if not mesh:
        rs.MessageBox("Could not convert target to mesh for calculation.")
        return

    # Prepare Mesh for Random Distribution
    # Convert to triangles to make barycentric picking easier
    mesh.Faces.ConvertQuadsToTriangles()
    
    # Ensure normals
    if mesh.Normals.Count == 0:
        mesh.Normals.ComputeNormals()
    
    # Calculate Areas for Weighted Distribution
    face_areas = []
    total_area = 0.0
    
    for i in range(mesh.Faces.Count):
        f = mesh.Faces[i]
        # MeshFace indices
        pA = mesh.Vertices[f.A]
        pB = mesh.Vertices[f.B]
        pC = mesh.Vertices[f.C]
        
        # Area = 0.5 * length(CrossProduct)
        vAB = pB - pA
        vAC = pC - pA
        area = 0.5 * (rs.VectorCrossProduct(vAB, vAC).Length)
        
        face_areas.append(area)
        total_area += area
        
    # CDF for weighted random choice
    cdf = []
    curr = 0.0
    for a in face_areas:
        curr += a
        cdf.append(curr)

    # 5. Interactive Loop
    while True:
        results = rs.PropertyListBox(labels, defaults, title, msg)
        if not results: 
            break
        
        defaults = results # Persist values for next loop
        
        try:
            count = int(results[0])
            s_base = float(results[1])
            s_var = float(results[2])
            z_base = float(results[3])
            z_var = float(results[4])
            r_spin_max = float(results[5])
            r_tilt_max = float(results[6])
            seed = int(results[7])
        except:
            rs.MessageBox("Invalid input values. Please try again.")
            continue

        if count < 1: count = 1
        
        rs.EnableRedraw(False)
        random.seed(seed)
        
        created_objs = []
        
        # Define Source Plane (Base of object)
        plane_source = rg.Plane.WorldXY
        plane_source.Origin = source_base_center
        
        # Generate Limit (prevent infinite loops if mesh broken)
        # We can just iterate 'count' times
        
        for _ in range(count):
            # A. Pick Random Face Weighted
            r_val = random.uniform(0, total_area)
            face_idx = bisect.bisect_left(cdf, r_val)
            if face_idx >= len(cdf): face_idx = len(cdf) - 1
            
            # B. Pick Random Point in Triangle (Face)
            r1 = random.random()
            r2 = random.random()
            # Fold back if outside triangle
            if r1 + r2 > 1.0:
                r1 = 1.0 - r1
                r2 = 1.0 - r2
            
            f = mesh.Faces[face_idx]
            # Explicit Casts to Point3d to avoid Point3f ambiguities
            pA = rg.Point3d(mesh.Vertices[f.A])
            pB = rg.Point3d(mesh.Vertices[f.B])
            pC = rg.Point3d(mesh.Vertices[f.C])
            
            vecAB = pB - pA
            vecAC = pC - pA
            
            # Barycentric Point
            pt_loc = pA + (vecAB * r1) + (vecAC * r2)
            
            # C. Interpolate Normal
            # We want smooth normals if available
            wA = 1.0 - r1 - r2
            # Weights match vertices A, B, C
            
            if mesh.Normals.Count == mesh.Vertices.Count:
                nA = rg.Vector3d(mesh.Normals[f.A])
                nB = rg.Vector3d(mesh.Normals[f.B])
                nC = rg.Vector3d(mesh.Normals[f.C])
                n_loc = (nA * wA) + (nB * r1) + (nC * r2)
            else:
                # Fallback to Face Normal
                n_loc = rs.VectorCrossProduct(vecAB, vecAC)
            
            n_loc = rg.Vector3d(n_loc) # Ensure Vector3d
            n_loc.Unitize()
            
            # D. Transform Object
            new_obj = rs.CopyObject(source_id)
            
            # Create Target Plane
            # We apply Offset Z here
            offset_final = z_base + random.uniform(-z_var, z_var)
            origin_final = pt_loc + (n_loc * offset_final)
            
            # rg.Plane(origin, normal) creates a valid plane with arbitrary X/Y
            # Explicit cast to Point3d to prevent any 'bool' TypeError confusion
            plane_target = rg.Plane(rg.Point3d(origin_final), n_loc)
            
            # Orient
            xform = rg.Transform.PlaneToPlane(plane_source, plane_target)
            rs.TransformObject(new_obj, xform)
            
            # E. Local Randoms (Scale, Spin, Tilt)
            
            # Scale
            s_final = s_base + random.uniform(-s_var, s_var)
            if s_final <= 0: s_final = 0.01 # Prevent zero/negative scale issues
            rs.ScaleObject(new_obj, origin_final, [s_final, s_final, s_final])
            
            # Spin (Rotation around Normal)
            r_spin = random.uniform(-r_spin_max, r_spin_max)
            if r_spin != 0:
                rs.RotateObject(new_obj, origin_final, r_spin, n_loc)
                
            # Tilt (Rotation around local X or Y)
            # plane_target X and Y are now valid local axes for the object
            r_tilt_x = random.uniform(-r_tilt_max, r_tilt_max)
            r_tilt_y = random.uniform(-r_tilt_max, r_tilt_max)
            
            if r_tilt_x != 0:
                rs.RotateObject(new_obj, origin_final, r_tilt_x, plane_target.XAxis)
            if r_tilt_y != 0:
                rs.RotateObject(new_obj, origin_final, r_tilt_y, plane_target.YAxis)
                
            created_objs.append(new_obj)
            
        rs.EnableRedraw(True)
        
        # 6. Accept/Edit UI
        # 6=Yes(Accept), 7=No(Edit), 2=Cancel
        user_response = rs.MessageBox(
            "Scatter Created with {} objects.\n\nAccept Result?\nYes = Finish\nNo = Edit Settings\nCancel = Quit".format(len(created_objs)), 
            3 | 32
        )
        
        if user_response == 6: # Yes
            group = rs.AddGroup()
            rs.AddObjectsToGroup(created_objs, group)
            break
        elif user_response == 7: # Edit
            rs.DeleteObjects(created_objs)
            continue
        else: # Cancel
            rs.DeleteObjects(created_objs)
            break

if __name__ == "__main__":
    create_wild_surface_array()
