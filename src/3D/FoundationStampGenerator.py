import rhinoscriptsyntax as rs
import Rhino
import Rhino.Geometry as rg
import scriptcontext as sc
import math
import random

def create_foundation_stamp():
    """
    Generates a 3D printable stamp for foundation walls.
    Includes a large 'U', decorative subdivision, and space for custom text.
    """
    
    # 1. User Input / Parameters
    base_size = 8.0 # inches
    thickness = 0.5 # thickness of the base plate
    emboss_depth = 0.25 # how far the text/pattern sticks out
    
    # Text Parameters
    main_char = rs.GetString("Main Letter", "U")
    if not main_char: main_char = "U"
    
    client_name = rs.GetString("Client Name / Address", "123 FOUNDATION ST")
    if client_name is None: client_name = ""
    
    complexity = rs.GetInteger("Decorative Complexity (1-5)", 3, 1, 5)
    
    # 2. Main Generation Loop for "Options"
    while True:
        seed = random.randint(0, 1000)
        random.seed(seed)
        
        # Setup
        rs.EnableRedraw(False)
        generated_objects = []
        
        # Create Base Plate
        pt0 = rg.Point3d(-base_size/2, -base_size/2, 0)
        pt1 = rg.Point3d(base_size/2, base_size/2, thickness)
        base_box = rg.BoundingBox(pt0, pt1)
        base_geo = rg.Brep.CreateFromBox(base_box)
        
        # 3. Generate Main "U" (Arial Black)
        font = "Arial Black"
        plane = rg.Plane.WorldXY
        plane.Origin = rg.Point3d(0, 0, thickness)
        text_height = 5.0
        
        curves = rg.Curve.CreateTextOutlines(main_char, font, text_height, 0, False, plane, 0.01, 0.0)
        
        main_geo = []
        if curves:
            bbox = rg.BoundingBox.Empty
            for c in curves: bbox.Union(c.GetBoundingBox(True))
            center = bbox.Center
            move_vec = rg.Vector3d(-center.X, -center.Y, 0)
            xf = rg.Transform.Translation(move_vec)
            
            for c in curves:
                c.Transform(xf)
                ext = rg.Surface.CreateExtrusion(c, rg.Vector3d(0, 0, emboss_depth))
                if ext:
                    brep = ext.ToBrep()
                    brep = brep.CapPlanarHoles(sc.doc.ModelAbsoluteTolerance)
                    main_geo.append(brep)

        # 4. Generate Secondary Text
        sec_text_height = 0.4
        sec_plane = rg.Plane.WorldXY
        sec_plane.Origin = rg.Point3d(0, -2.8, thickness)
        
        sec_curves = rg.Curve.CreateTextOutlines(client_name, "Arial", sec_text_height, 0, False, sec_plane, 0.01, 0.0)
        sec_geo = []
        if sec_curves:
            bbox = rg.BoundingBox.Empty
            for c in sec_curves: bbox.Union(c.GetBoundingBox(True))
            center = bbox.Center
            move_vec = rg.Vector3d(-center.X, 0, 0) 
            xf = rg.Transform.Translation(move_vec)
            for c in sec_curves:
                c.Transform(xf)
                ext = rg.Surface.CreateExtrusion(c, rg.Vector3d(0, 0, emboss_depth))
                if ext:
                    brep = ext.ToBrep()
                    brep = brep.CapPlanarHoles(sc.doc.ModelAbsoluteTolerance)
                    sec_geo.append(brep)

        # 5. Decorative Pattern
        dec_geo = []
        def recursive_subdivide(x0, x1, y0, y1, depth):
            if depth <= 0 or random.random() < 0.2:
                cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
                if abs(cx) > 1.8 or abs(cy) > 1.8: # Avoid central text
                    h = random.uniform(0.05, emboss_depth * 0.8)
                    p_box = rg.Brep.CreateFromBox(rg.BoundingBox(
                        rg.Point3d(x0 + 0.05, y0 + 0.05, thickness),
                        rg.Point3d(x1 - 0.05, y1 - 0.05, thickness + h)
                    ))
                    dec_geo.append(p_box)
                return
            if (x1 - x0) > (y1 - y0):
                mid = x0 + (x1 - x0) * random.uniform(0.3, 0.7)
                recursive_subdivide(x0, mid, y0, y1, depth - 1)
                recursive_subdivide(mid, x1, y0, y1, depth - 1)
            else:
                mid = y0 + (y1 - y0) * random.uniform(0.3, 0.7)
                recursive_subdivide(x0, x1, y0, mid, depth - 1)
                recursive_subdivide(x0, x1, mid, y1, depth - 1)

        recursive_subdivide(-3.8, 3.8, -3.8, 3.8, complexity + 2)

        # 6. Interlocking Tabs
        tab_size = 1.0
        tab_depth = 0.5
        
        # Male Tab (Left)
        l_tab = rg.Brep.CreateFromBox(rg.BoundingBox(
            rg.Point3d(-base_size/2 - tab_depth, -tab_size/2, 0),
            rg.Point3d(-base_size/2, tab_size/2, thickness)
        ))
        
        # Female Slot (Right - for cutout)
        r_tab_cut = rg.Brep.CreateFromBox(rg.BoundingBox(
            rg.Point3d(base_size/2 - tab_depth, -tab_size/2, -0.1),
            rg.Point3d(base_size/2 + 0.1, tab_size/2, thickness + 0.1)
        ))
        
        # 7. Final Boolean Assembly
        all_parts = [base_geo, l_tab] + main_geo + sec_geo + dec_geo
        final_union = rg.Brep.CreateBooleanUnion(all_parts, sc.doc.ModelAbsoluteTolerance)
        
        if final_union:
            final_geo = final_union[0]
            cut_result = rg.Brep.CreateBooleanDifference([final_geo], [r_tab_cut], sc.doc.ModelAbsoluteTolerance)
            if cut_result: final_geo = cut_result[0]
            
            final_id = sc.doc.Objects.AddBrep(final_geo)
            generated_objects.append(final_id)
        else:
            # Fallback for complex unions
            for b in all_parts: generated_objects.append(sc.doc.Objects.AddBrep(b))
            print("Boolean failed, baked individual parts.")

        rs.EnableRedraw(True)
        rs.UnselectAllObjects()
        rs.SelectObjects(generated_objects)
        
        # Option choice
        opt = rs.GetString("Option Generated (Seed {}). Accept?".format(seed), "Accept", ["Accept", "Regenerate", "Cancel"])
        if opt == "Accept" or opt is None:
            break
        elif opt == "Regenerate":
            rs.DeleteObjects(generated_objects)
            continue
        else:
            rs.DeleteObjects(generated_objects)
            return

    print("Foundation Stamp Generated.")

if __name__ == "__main__":
    create_foundation_stamp()
