import rhinoscriptsyntax as rs
import random
import Rhino.Geometry as rg
import math

def create_wild_array():
    # 1. Select Object
    obj_id = rs.GetObject("Select object to array", preselect=True)
    if not obj_id:
        return

    # Calculate initial defaults based on object size
    bbox = rs.BoundingBox(obj_id)
    if not bbox:
        return
    
    # Calculate dimensions
    width_x = abs(bbox[0][0] - bbox[1][0])
    width_y = abs(bbox[0][1] - bbox[3][1])
    width_z = abs(bbox[0][2] - bbox[4][2])
    
    # Defaults: Exact width without extra padding (User: "Overlapping is okay")
    def_space_x = width_x if width_x > 0 else 10.0
    def_space_y = width_y if width_y > 0 else 10.0
    def_space_z = width_z if width_z > 0 else 10.0

    # Labels for the unified inputs
    # Sections: Grid Logic | Wild/Gradual Logic
    labels = [
        "Count X", "Count Y", "Count Z",         # 0, 1, 2
        "Spacing X", "Spacing Y", "Spacing Z",   # 3, 4, 5
        "Mode (0=Linear, 1=Random)",             # 6
        "Rand/Grad Trans X (Max)",               # 7 
        "Rand/Grad Trans Y (Max)",               # 8
        "Rand/Grad Trans Z (Max)",               # 9
        "Rand/Grad Rot X (Max Deg)",             # 10
        "Rand/Grad Rot Y (Max Deg)",             # 11
        "Rand/Grad Rot Z (Max Deg)",             # 12
        "Rand/Grad Scale (Var)",                 # 13 (e.g 0.5 means 1.0 +/- 0.5 or 1.0 -> 1.5)
        "Seed"                                   # 14
    ]
    
    # Initial Defaults
    defaults = [
        "5", "1", "1",                                  # Counts
        "{:.2f}".format(def_space_x), "{:.2f}".format(def_space_y), "{:.2f}".format(def_space_z), # Spacing
        "1",                                            # Mode (Default to Random/Wild as per name)
        "0.0", "0.0", "0.0",                            # Trans Max 
        "0.0", "0.0", "0.0",                            # Rot Max
        "0.0",                                          # Scale
        "1234"                                          # Seed
    ]

    title = "Wild Grid Array"
    msg = "Step 1: Define Grid & Wildness.\nAccept/Edit loop follows."

    while True:
        # Show Dialog
        results = rs.PropertyListBox(labels, defaults, title, msg)
        if not results:
            return # Cancelled

        # Use the entered values as next defaults
        defaults = results
        
        # Parse
        try:
            cx, cy, cz = int(results[0]), int(results[1]), int(results[2])
            sx, sy, sz = float(results[3]), float(results[4]), float(results[5])
            mode = int(results[6])
            
            # Wild/Gradual Mods
            t_mod_x, t_mod_y, t_mod_z = float(results[7]), float(results[8]), float(results[9])
            r_mod_x, r_mod_y, r_mod_z = float(results[10]), float(results[11]), float(results[12])
            s_mod = float(results[13])
            seed = int(results[14])
        except:
             rs.MessageBox("Invalid inputs.")
             continue

        if cx < 1: cx = 1
        if cy < 1: cy = 1
        if cz < 1: cz = 1
        
        total_count = cx * cy * cz
        rs.EnableRedraw(False)
        random.seed(seed)
        
        # Center for Rotation/Scale
        center = (bbox[0] + bbox[6]) / 2.0
        
        created_objs = []
        
        # Generate Grid
        for z in range(cz):
            for y in range(cy):
                for x in range(cx):
                    # 1. Grid Position (Base)
                    base_vec = rs.VectorAdd(
                        [x * sx, y * sy, z * sz], 
                        [0,0,0] # Origin offset if needed, redundant here
                    )
                    
                    # 2. Wild/Gradual Calculation
                    # Calculate 't' (0.0 to 1.0) based on index in total array
                    flat_idx = x + y*cx + z*(cx*cy)
                    if total_count > 1:
                        t = float(flat_idx) / float(total_count - 1)
                    else:
                        t = 0.0
                        
                    # Calculate Mods
                    if mode == 0: # Linear (Gradual 0 -> Mod)
                        tx = t_mod_x * t
                        ty = t_mod_y * t
                        tz = t_mod_z * t
                        
                        rx = r_mod_x * t
                        ry = r_mod_y * t
                        rz = r_mod_z * t
                        
                        # Scale: 1.0 + (Mod * t)
                        s = 1.0 + (s_mod * t)
                        
                    else: # Random (Wild +/- Mod)
                        # Center around 0
                        tx = random.uniform(-t_mod_x, t_mod_x) if t_mod_x != 0 else 0
                        ty = random.uniform(-t_mod_y, t_mod_y) if t_mod_y != 0 else 0
                        tz = random.uniform(-t_mod_z, t_mod_z) if t_mod_z != 0 else 0
                        
                        rx = random.uniform(-r_mod_x, r_mod_x) if r_mod_x != 0 else 0
                        ry = random.uniform(-r_mod_y, r_mod_y) if r_mod_y != 0 else 0
                        rz = random.uniform(-r_mod_z, r_mod_z) if r_mod_z != 0 else 0
                        
                        # Scale: 1.0 +/- Mod
                        s = 1.0 + random.uniform(-s_mod, s_mod) if s_mod != 0 else 1.0

                    # 3. Create & Transform
                    new_obj = rs.CopyObject(obj_id)
                    
                    # Order: Scale -> Rotate -> Translate (Base + Mod)
                    
                    # Scale
                    rs.ScaleObject(new_obj, center, [s, s, s])
                    
                    # Rotate
                    if rx != 0: rs.RotateObject(new_obj, center, rx, [1, 0, 0])
                    if ry != 0: rs.RotateObject(new_obj, center, ry, [0, 1, 0])
                    if rz != 0: rs.RotateObject(new_obj, center, rz, [0, 0, 1])
                    
                    # Translate
                    total_move = rs.VectorAdd(base_vec, [tx, ty, tz])
                    rs.MoveObject(new_obj, total_move)
                    
                    created_objs.append(new_obj)
        
        rs.EnableRedraw(True)
        
        # Interactive Loop Check
        # 6 = Yes, 7 = No (Rhino MessageBox buttons: YesNo=4. Return: Yes=6, No=7)
        # We want "Accept" (Yes), "Edit" (No/Cancel logic?)
        user_response = rs.MessageBox(
            "Array Created with {} objects.\n\nAccept Result?\nYes = Finish\nNo = Edit Settings\nCancel = Quit".format(total_count), 
            3 | 32 # YesNoCancel | IconQuestion
        )
        
        if user_response == 6: # Yes -> Accept
            group = rs.AddGroup()
            rs.AddObjectsToGroup(created_objs, group)
            break
        elif user_response == 7: # No -> Edit
            rs.DeleteObjects(created_objs)
            continue # Loop again with preserved 'defaults'
        else: # Cancel (2)
            rs.DeleteObjects(created_objs)
            break

if __name__ == "__main__":
    create_wild_array()
