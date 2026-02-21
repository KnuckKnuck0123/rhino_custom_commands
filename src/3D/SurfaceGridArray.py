import rhinoscriptsyntax as rs
import Rhino.Geometry as rg
import random
import math

def get_counts(params):
    labels = ["Count U", "Count V"]
    defaults = [str(params["u_count"]), str(params["v_count"])]
    results = rs.PropertyListBox(labels, defaults, "Grid Counts", "Set UV grid counts")
    if results:
        try:
            return {
                "u_count": max(1, int(results[0])),
                "v_count": max(1, int(results[1]))
            }
        except:
            pass
    return None

def get_jitter(params):
    labels = [
        "Jitter U (0.0-1.0 cell size)", 
        "Jitter V (0.0-1.0 cell size)",
        "Offset Normal Min", "Offset Normal Max"
    ]
    defaults = [
        "{:.2f}".format(params["u_jit"]), 
        "{:.2f}".format(params["v_jit"]),
        "{:.2f}".format(params["off_min"]),
        "{:.2f}".format(params["off_max"])
    ]
    results = rs.PropertyListBox(labels, defaults, "Position Variation", "Set grid jitter and offset")
    if results:
        try:
            return {
                "u_jit": float(results[0]),
                "v_jit": float(results[1]),
                "off_min": float(results[2]),
                "off_max": float(results[3])
            }
        except:
            pass
    return None

def get_rotation(params):
    labels = [
        "Rot X Min (Deg)", "Rot X Max (Deg)",
        "Rot Y Min (Deg)", "Rot Y Max (Deg)",
        "Rot Z Min (Deg)", "Rot Z Max (Deg)"
    ]
    defaults = [
        "{:.2f}".format(params["rx_min"]), "{:.2f}".format(params["rx_max"]),
        "{:.2f}".format(params["ry_min"]), "{:.2f}".format(params["ry_max"]),
        "{:.2f}".format(params["rz_min"]), "{:.2f}".format(params["rz_max"])
    ]
    results = rs.PropertyListBox(labels, defaults, "Rotation Variation", "Rotate around surface frame axes")
    if results:
        try:
            return {
                "rx_min": float(results[0]), "rx_max": float(results[1]),
                "ry_min": float(results[2]), "ry_max": float(results[3]),
                "rz_min": float(results[4]), "rz_max": float(results[5])
            }
        except:
            pass
    return None

def get_scale(params):
    labels = ["Scale Min", "Scale Max"]
    defaults = ["{:.2f}".format(params["s_min"]), "{:.2f}".format(params["s_max"])]
    results = rs.PropertyListBox(labels, defaults, "Scale Variation", "Set uniform scale range")
    if results:
        try:
            return {
                "s_min": float(results[0]),
                "s_max": float(results[1])
            }
        except:
            pass
    return None

def get_seed(params):
    res = rs.GetInteger("Random Seed", params["seed"])
    if res is not None:
        return {"seed": res}
    return None

def get_geometry_brep(obj_id):
    """
    Converts the Rhino Object to a Brep or list of faces.
    Returns a Rhino.Geometry.Brep or None.
    """
    rh_obj = rs.coercerhinoobject(obj_id)
    if not rh_obj: return None
    
    geom = rh_obj.Geometry
    
    # 1. Surface / Polysrf (Brep)
    if isinstance(geom, rg.Brep):
        return geom
        
    # 2. SubD -> Brep
    if isinstance(geom, rg.SubD):
        return geom.ToBrep(rg.SubDToBrepOptions.Default)
        
    # 3. Mesh -> Brep (Faces) 
    # Warning: High poly meshes will result in massive Breps
    if isinstance(geom, rg.Mesh):
        # Check face count to prevent freezing
        if geom.Faces.Count > 500:
            res = rs.MessageBox("Mesh has {} faces. This will create a grid on EVERY face.\nContinue?".format(geom.Faces.Count), 4 | 48)
            if res != 6: return None
            
        return rg.Brep.CreateFromMesh(geom, True)
        
    return None

def generate_preview(source_id, target_brep, params, source_plane):
    # Unpack
    uc, vc = params["u_count"], params["v_count"]
    seed = params["seed"]
    
    # Ranges
    u_jit, v_jit = params["u_jit"], params["v_jit"]
    off_min, off_max = params["off_min"], params["off_max"]
    
    rx_min, rx_max = params["rx_min"], params["rx_max"]
    ry_min, ry_max = params["ry_min"], params["ry_max"]
    rz_min, rz_max = params["rz_min"], params["rz_max"]
    
    s_min, s_max = params["s_min"], params["s_max"]
    
    random.seed(seed)
    
    preview_objs = []
    
    # Helper to clamp
    def clamp(val, mn, mx):
        return max(mn, min(val, mx))

    # Iterate over ALL faces in the Brep (Surface, Polysrf, Converted Mesh/SubD)
    for face_idx in range(target_brep.Faces.Count):
        face = target_brep.Faces[face_idx]
        
        # Reparameterize face for easy 0-1 math logic locally?
        # Actually, let's just read the domain.
        dom_u = face.Domain(0)
        dom_v = face.Domain(1)
        du = dom_u[1] - dom_u[0]
        dv = dom_v[1] - dom_v[0]

        for i in range(uc):
            for j in range(vc):
                # 1. Base UV
                # Determine normalized 0..1 param
                if uc > 1: u_norm = float(i) / float(uc - 1)
                else: u_norm = 0.5
                
                if vc > 1: v_norm = float(j) / float(vc - 1)
                else: v_norm = 0.5
                
                # 2. Jitter
                # Jitter is fraction of cell size
                # Cell size approx = 1.0 / count
                u_cell = 1.0 / float(uc) if uc > 0 else 1.0
                v_cell = 1.0 / float(vc) if vc > 0 else 1.0
                
                u_j = 0
                v_j = 0
                if u_jit > 0: u_j = random.uniform(-u_jit, u_jit) * u_cell
                if v_jit > 0: v_j = random.uniform(-v_jit, v_jit) * v_cell
                
                final_u_norm = clamp(u_norm + u_j, 0.0, 1.0)
                final_v_norm = clamp(v_norm + v_j, 0.0, 1.0)
                
                # Map back to real domain
                u_param = dom_u[0] + final_u_norm * du
                v_param = dom_v[0] + final_v_norm * dv
                
                # 3. Get Frame
                # FrameAt gives a plane tangent to surface
                rc, frame = face.FrameAt(u_param, v_param)
                if not rc: continue
                
                # 4. Apply Offset
                off_val = 0
                if off_min != 0 or off_max != 0:
                    off_val = random.uniform(off_min, off_max)
                
                # Move frame origin along Z (Normal)
                frame.Origin = frame.Origin + (frame.ZAxis * off_val)
                
                # 5. Calculate Transform
                # Orient Source Plane -> Target Frame
                # But first, we might want to apply local rotation to the Target Frame
                
                # Rotation
                rot_x = random.uniform(rx_min, rx_max)
                rot_y = random.uniform(ry_min, ry_max)
                rot_z = random.uniform(rz_min, rz_max)
                
                # Rotate the frame itself? 
                # If we rotate the frame, the orientation changes suitable for OrientPlane
                if rot_x != 0: frame.Rotate(math.radians(rot_x), frame.XAxis, frame.Origin)
                if rot_y != 0: frame.Rotate(math.radians(rot_y), frame.YAxis, frame.Origin)
                if rot_z != 0: frame.Rotate(math.radians(rot_z), frame.ZAxis, frame.Origin)
                
                # Scale
                s = random.uniform(s_min, s_max)
                
                # 6. Transform Object
                # We copy and transform
                new_obj = rs.CopyObject(source_id)
                
                # Initial Orientation
                xform = rg.Transform.PlaneToPlane(source_plane, frame)
                rs.TransformObject(new_obj, xform)
                
                # Scale (local to the new placement)
                if s != 1.0:
                    rs.ScaleObject(new_obj, frame.Origin, [s, s, s])
                    
                preview_objs.append(new_obj)

    return preview_objs

def create_surface_grid_array():
    # 1. Select Source
    source_id = rs.GetObject("Select object to array", preselect=True)
    if not source_id: return
    
    # 2. Select Target Surface
    # Filter 8=Surface, 16=Polysurface, 32=Mesh, 262144=SubD (if available) -> Just use 0 for all
    target_id = rs.GetObject("Select target Surface, Polysurface, Mesh, or SubD", 0) 
    if not target_id: return
    
    # Convert to Brep for unified handling
    target_brep = get_geometry_brep(target_id)
    if not target_brep:
        rs.MessageBox("Object type not supported or conversion failed.")
        return

    # 3. Base Plane Calculation
    bbox = rs.BoundingBox(source_id)
    if not bbox: return
    
    # Bottom Center
    corn_min = bbox[0]
    corn_max = bbox[6]
    anchor_pt = rg.Point3d((corn_min.X + corn_max.X)/2.0, (corn_min.Y + corn_max.Y)/2.0, corn_min.Z)
    source_plane = rg.Plane(anchor_pt, rg.Vector3d.ZAxis)

    # 4. Parameters
    # Default counts
    params = {
        "u_count": 5, "v_count": 5,
        "u_jit": 0.0, "v_jit": 0.0,
        "off_min": 0.0, "off_max": 0.0,
        "rx_min": 0.0, "rx_max": 0.0,
        "ry_min": 0.0, "ry_max": 0.0,
        "rz_min": 0.0, "rz_max": 0.0, # Rotation around Normal
        "s_min": 1.0, "s_max": 1.0,
        "seed": 1234
    }
    
    preview_ids = []
    
    try:
        while True:
            # Update Preview
            if preview_ids:
                rs.DeleteObjects(preview_ids)
                preview_ids = []
                
            rs.EnableRedraw(False)
            preview_ids = generate_preview(source_id, target_brep, params, source_plane)
            rs.EnableRedraw(True)
            
            # Prompt
            # Update msg to indicate if multiple faces
            f_count = target_brep.Faces.Count
            s_grid = "Grid" if f_count == 1 else "Grid(x{})".format(f_count)
            
            msg = "{}: {}x{} | Jitter: {:.2f}/{:.2f}".format(s_grid, params["u_count"], params["v_count"], params["u_jit"], params["v_jit"])
            opts = ["Counts", "Position", "Rotation", "Scale", "Seed", "Apply"]
            
            selected = rs.GetString(msg, "Apply", opts)
            
            if selected is None: # Escape
                rs.DeleteObjects(preview_ids)
                return
            
            selected = selected.upper()
            
            if selected == "APPLY" or selected == "":
                rs.SelectObjects(preview_ids)
                print("Created {} objects.".format(len(preview_ids)))
                break
                
            elif selected.startswith("C"):
                updates = get_counts(params)
                if updates: params.update(updates)
                
            elif selected.startswith("P"): # Position / Jitter
                updates = get_jitter(params)
                if updates: params.update(updates)
                
            elif selected.startswith("R"):
                updates = get_rotation(params)
                if updates: params.update(updates)
                
            elif selected.startswith("SC"):
                updates = get_scale(params)
                if updates: params.update(updates)
                
            elif selected.startswith("SE"):
                updates = get_seed(params)
                if updates: params.update(updates)
                
    except Exception as e:
        rs.EnableRedraw(True)
        rs.MessageBox("Error: " + str(e))
        if preview_ids: rs.DeleteObjects(preview_ids)

if __name__ == "__main__":
    create_surface_grid_array()
