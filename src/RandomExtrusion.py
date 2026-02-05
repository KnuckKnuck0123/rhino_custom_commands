
import rhinoscriptsyntax as rs
import Rhino
import scriptcontext as sc
import random

def random_extrusion():
    """
    Randomly extrudes selected curves, surfaces, polysurfaces, or SubD objects.
    Each object gets a random extrusion height between a user-defined min and max.
    """
    # 1. Select Objects
    # Object types: 4=Curve, 8=Surface, 16=Polysurface, 262144=SubD (approx logic, usually 0 selects all but we can filter)
    # We allow everything initially and filter in loop or let command fail gracefully?
    # Better to filter: 4 + 8 + 16 (Polysrf) 
    # SubD type filter in rs.GetObjects might rely on the integer. 
    # 0 = All. Let's use 0 and check Is... later.
    
    ids = rs.GetObjects("Select curves, surfaces, polysurfaces, or SubD to extrude", 0, preselect=True)
    if not ids:
        return

    # 2. Get Parameters
    h_min = rs.GetReal("Minimum Extrusion Height", 5.0)
    if h_min is None: return
    
    h_max = rs.GetReal("Maximum Extrusion Height", 15.0)
    if h_max is None: return

    # Ensure Min <= Max
    if h_min > h_max:
        h_min, h_max = h_max, h_min

    rs.EnableRedraw(False)
    
    # 3. Iterate and Extrude
    count = 0
    new_objects = []
    
    # Start Undo Record
    undo_record_id = sc.doc.BeginUndoRecord("Random Extrusion")
    
    try:
        for obj_id in ids:
            # Determine correct command
            cmd = None
            
            # Check Types
            obj_type = rs.ObjectType(obj_id)
            
            if obj_type == 4: # Curve
                cmd = "ExtrudeCrv"
            elif obj_type == 8 or obj_type == 16: # Surface or Polysurface
                cmd = "ExtrudeSrf"
            elif obj_type == 262144: # SubD
                cmd = "ExtrudeSubD"
            else:
                # Fallback check
                if rs.IsCurve(obj_id):
                    cmd = "ExtrudeCrv"
                elif rs.IsSurface(obj_id) or rs.IsPolysurface(obj_id):
                    cmd = "ExtrudeSrf"
                elif hasattr(rs, "IsSubD") and rs.IsSubD(obj_id):
                     cmd = "ExtrudeSubD"
                # Check directly via RhinoCommon if rs.IsSubD missing
                elif sc.doc.Objects.Find(obj_id).Geometry.ObjectType == Rhino.DocObjects.ObjectType.SubD:
                    cmd = "ExtrudeSubD"
            
            if not cmd:
                continue

            # Calculate random height
            dist = random.uniform(h_min, h_max)
            
            # Select object for command
            rs.UnselectAllObjects()
            rs.SelectObject(obj_id)
            
            # Construct command
            macro = ""
            if cmd == "ExtrudeCrv":
                macro = "-_ExtrudeCrv _Solid=_Yes {}".format(dist)
            elif cmd == "ExtrudeSrf":
                macro = "-_ExtrudeSrf _Solid=_Yes {}".format(dist)
            elif cmd == "ExtrudeSubD":
                macro = "-_ExtrudeSubD _Direction=_Normal {}".format(dist)
            
            # Execute
            success = rs.Command(macro, False)
            if success:
                count += 1
                # Capture created objects
                last_objs = rs.LastCreatedObjects()
                if last_objs:
                    new_objects.extend(last_objs)

    except Exception as e:
        print("An error occurred: {}".format(e))
    
    finally:
        # End Undo Record
        if undo_record_id != 0:
            sc.doc.EndUndoRecord(undo_record_id)

        rs.EnableRedraw(True)
        rs.UnselectAllObjects() # Clean up selection
        
        # Select newly created objects for user convenience (fixes SelLast/Selection issue)
        if new_objects:
            rs.SelectObjects(new_objects)
            
        print("Randomly extruded {} objects.".format(count))

if __name__ == "__main__":
    random_extrusion()
