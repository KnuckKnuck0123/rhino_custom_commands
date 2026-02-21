import rhinoscriptsyntax as rs
import random
import Rhino.Geometry as rg

def get_counts(params):
    labels = ["Count X", "Count Y", "Count Z"]
    defaults = [str(params["cx"]), str(params["cy"]), str(params["cz"])]
    results = rs.PropertyListBox(labels, defaults, "Array Counts", "Set grid counts")
    if results:
        try:
            return {
                "cx": max(1, int(results[0])),
                "cy": max(1, int(results[1])),
                "cz": max(1, int(results[2]))
            }
        except:
            pass
    return None

def get_spacing(params):
    labels = ["Spacing X", "Spacing Y", "Spacing Z"]
    defaults = ["{:.2f}".format(params["sx"]), "{:.2f}".format(params["sy"]), "{:.2f}".format(params["sz"])]
    results = rs.PropertyListBox(labels, defaults, "Array Spacing", "Set grid spacing")
    if results:
        try:
            return {
                "sx": float(results[0]),
                "sy": float(results[1]),
                "sz": float(results[2])
            }
        except:
            pass
    return None

def get_translation(params):
    labels = [
        "Trans X Min", "Trans X Max",
        "Trans Y Min", "Trans Y Max",
        "Trans Z Min", "Trans Z Max"
    ]
    defaults = [
        "{:.2f}".format(params["tx_min"]), "{:.2f}".format(params["tx_max"]),
        "{:.2f}".format(params["ty_min"]), "{:.2f}".format(params["ty_max"]),
        "{:.2f}".format(params["tz_min"]), "{:.2f}".format(params["tz_max"])
    ]
    results = rs.PropertyListBox(labels, defaults, "Translation Range", "Set translation min/max")
    if results:
        try:
            return {
                "tx_min": float(results[0]), "tx_max": float(results[1]),
                "ty_min": float(results[2]), "ty_max": float(results[3]),
                "tz_min": float(results[4]), "tz_max": float(results[5])
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
    results = rs.PropertyListBox(labels, defaults, "Rotation Range", "Set rotation min/max (degrees)")
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
    results = rs.PropertyListBox(labels, defaults, "Scale Range", "Set scale min/max factor")
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

def generate_preview(obj_id, params, bbox):
    cx, cy, cz = params["cx"], params["cy"], params["cz"]
    sx, sy, sz = params["sx"], params["sy"], params["sz"]
    seed = params["seed"]
    mode = params["mode"] # 0=Linear, 1=Random
    
    # Ranges
    tx_min, tx_max = params["tx_min"], params["tx_max"]
    ty_min, ty_max = params["ty_min"], params["ty_max"]
    tz_min, tz_max = params["tz_min"], params["tz_max"]
    
    rx_min, rx_max = params["rx_min"], params["rx_max"]
    ry_min, ry_max = params["ry_min"], params["ry_max"]
    rz_min, rz_max = params["rz_min"], params["rz_max"]
    
    s_min, s_max = params["s_min"], params["s_max"]
    
    total_count = cx * cy * cz
    random.seed(seed)
    
    # Center for Scale/Rotate
    # bbox is a list of 8 points. 
    # 0 = bottom-left-front, 6 = top-right-back
    center = (bbox[0] + bbox[6]) / 2.0
    
    created_ids = []
    
    for z in range(cz):
        for y in range(cy):
            for x in range(cx):
                # 1. Base Grid Position
                base_vec = rs.VectorAdd([x * sx, y * sy, z * sz], [0,0,0])
                
                # 2. Variable Calculation
                # Calculate t (0.0 to 1.0) for Linear mode
                flat_idx = x + y*cx + z*(cx*cy)
                if total_count > 1:
                    t = float(flat_idx) / float(total_count - 1)
                else:
                    t = 0.0
                
                # Calculate Values
                if mode == 0: # Linear (Intepolate Min -> Max)
                    curr_tx = tx_min + (tx_max - tx_min) * t
                    curr_ty = ty_min + (ty_max - ty_min) * t
                    curr_tz = tz_min + (tz_max - tz_min) * t
                    
                    curr_rx = rx_min + (rx_max - rx_min) * t
                    curr_ry = ry_min + (ry_max - ry_min) * t
                    curr_rz = rz_min + (rz_max - rz_min) * t
                    
                    curr_s = s_min + (s_max - s_min) * t
                    
                else: # Random (Uniform Min, Max)
                    curr_tx = random.uniform(tx_min, tx_max)
                    curr_ty = random.uniform(ty_min, ty_max)
                    curr_tz = random.uniform(tz_min, tz_max)
                    
                    curr_rx = random.uniform(rx_min, rx_max)
                    curr_ry = random.uniform(ry_min, ry_max)
                    curr_rz = random.uniform(rz_min, rz_max)
                    
                    curr_s = random.uniform(s_min, s_max)
                
                # 3. Transform
                # We copy the object for every instance
                # Optimized: If count is high, we might want to use blocks, but for now simple copy
                new_obj = rs.CopyObject(obj_id)
                
                # Scale
                # Note: rs.ScaleObject scales from the center. 
                # If we want each object to scale 'individually' but stay in grid, we scale BEFORE move?
                # Usually we want object to scale around its OWN center.
                # The 'center' variable derived from bbox is the center of the Original Object.
                # Since we haven't moved it yet, this is correct.
                rs.ScaleObject(new_obj, center, [curr_s, curr_s, curr_s])
                
                # Rotate
                if curr_rx != 0: rs.RotateObject(new_obj, center, curr_rx, [1, 0, 0])
                if curr_ry != 0: rs.RotateObject(new_obj, center, curr_ry, [0, 1, 0])
                if curr_rz != 0: rs.RotateObject(new_obj, center, curr_rz, [0, 0, 1])
                
                # Translate
                # Grid Move + Random/Linear Move
                total_move = rs.VectorAdd(base_vec, [curr_tx, curr_ty, curr_tz])
                rs.MoveObject(new_obj, total_move)
                
                created_ids.append(new_obj)

    return created_ids

def create_wild_array():
    # 1. Select Object
    obj_id = rs.GetObject("Select object to array", preselect=True)
    if not obj_id:
        return

    # Calculate initial defaults based on object size
    bbox = rs.BoundingBox(obj_id)
    if not bbox:
        return
    
    # Dimensions
    width_x = abs(bbox[0][0] - bbox[1][0])
    width_y = abs(bbox[0][1] - bbox[3][1])
    width_z = abs(bbox[0][2] - bbox[4][2])
    
    def_space_x = width_x if width_x > 0 else 10.0
    def_space_y = width_y if width_y > 0 else 10.0
    def_space_z = width_z if width_z > 0 else 10.0
    
    # Initial Params
    params = {
        "cx": 5, "cy": 1, "cz": 1,
        "sx": def_space_x, "sy": def_space_y, "sz": def_space_z,
        "mode": 1, # 0=Linear, 1=Random
        "seed": 1234,
        
        # Ranges (Default 0 variation, Scale 1)
        "tx_min": 0.0, "tx_max": 0.0,
        "ty_min": 0.0, "ty_max": 0.0,
        "tz_min": 0.0, "tz_max": 0.0,
        
        "rx_min": 0.0, "rx_max": 0.0,
        "ry_min": 0.0, "ry_max": 0.0,
        "rz_min": 0.0, "rz_max": 0.0,
        
        "s_min": 1.0, "s_max": 1.0
    }
    
    preview_ids = []
    
    try:
        while True:
            # 1. Update Preview
            if preview_ids:
                rs.DeleteObjects(preview_ids)
                preview_ids = []
            
            rs.EnableRedraw(False)
            preview_ids = generate_preview(obj_id, params, bbox)
            rs.EnableRedraw(True)
            
            # 2. Prompt options
            mode_str = "Random" if params["mode"] == 1 else "Linear"
            
            # Command line options
            opts = ["Counts", "Spacing", "Translation", "Rotation", "Scale", "Mode", "Seed", "Apply"]
            
            # Construct a clear message
            msg = "Mode: {} | Count: {}x{}x{} | Spacing: {:.1f}/{:.1f}/{:.1f}".format(
                mode_str, params["cx"], params["cy"], params["cz"], 
                params["sx"], params["sy"], params["sz"]
            )
            
            selected = rs.GetString(msg, "Apply", opts)
            
            if selected is None: # Escape
                rs.DeleteObjects(preview_ids)
                return
            
            selected = selected.upper()
            
            if selected == "APPLY" or selected == "":
                # Keep objects, Exit
                rs.SelectObjects(preview_ids)
                print("Array created with {} objects.".format(len(preview_ids)))
                break
                
            elif selected.startswith("C"): # Counts
                updates = get_counts(params)
                if updates: params.update(updates)
                
            elif selected.startswith("SP"): # Spacing
                updates = get_spacing(params)
                if updates: params.update(updates)
                
            elif selected.startswith("T"): # Translation
                updates = get_translation(params)
                if updates: params.update(updates)
                
            elif selected.startswith("R"): # Rotation
                updates = get_rotation(params)
                if updates: params.update(updates)
                
            elif selected.startswith("SC"): # Scale
                updates = get_scale(params)
                if updates: params.update(updates)
                
            elif selected.startswith("SE"): # Seed
                updates = get_seed(params)
                if updates: params.update(updates)
                
            elif selected.startswith("M"): # Mode
                # Toggle
                params["mode"] = 1 - params["mode"]
                
    except Exception as e:
        rs.MessageBox("Error: " + str(e))
        if preview_ids:
            rs.DeleteObjects(preview_ids)

if __name__ == "__main__":
    create_wild_array()
