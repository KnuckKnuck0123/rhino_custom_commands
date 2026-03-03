import rhinoscriptsyntax as rs

def draw_i_beam_profile():
    """
    Creates a 2D I-Beam cross-section profile as a closed polyline.
    Prompts the user for dimensions and an insertion point.
    """
    print("=== 2D I-Beam Command ===")
    
    # Get insertion point
    insertion_point = rs.GetPoint("Select insertion point for I-Beam center")
    if not insertion_point:
        return

    # Get dimensions
    depth = rs.GetReal("Total depth of the I-Beam", 10.0, 0.1)
    if depth is None:
        return

    flange_width = rs.GetReal("Flange width", 5.0, 0.1)
    if flange_width is None:
        return

    flange_thickness = rs.GetReal("Flange thickness", 0.5, 0.01)
    if flange_thickness is None:
        return

    web_thickness = rs.GetReal("Web thickness", 0.5, 0.01)
    if web_thickness is None:
        return

    # Validate dimensions
    if 2 * flange_thickness >= depth:
        print("Error: Total flange thickness exceeds beam depth.")
        return

    if web_thickness >= flange_width:
        print("Error: Web thickness exceeds flange width.")
        return

    try:
        rs.EnableRedraw(False)

        # Calculate half-dimensions for coordinates relative to origin
        fw2 = flange_width / 2.0
        d2 = depth / 2.0
        wt2 = web_thickness / 2.0
        ft = flange_thickness

        # Define the 12 points of the I-beam (plus 1 to close the outline)
        points = [
            [-fw2, d2, 0],          # Top left outer
            [fw2, d2, 0],           # Top right outer
            [fw2, d2 - ft, 0],      # Top right inner
            [wt2, d2 - ft, 0],      # Web top right
            [wt2, -d2 + ft, 0],     # Web bottom right
            [fw2, -d2 + ft, 0],     # Bottom right inner
            [fw2, -d2, 0],          # Bottom right outer
            [-fw2, -d2, 0],         # Bottom left outer
            [-fw2, -d2 + ft, 0],    # Bottom left inner
            [-wt2, -d2 + ft, 0],    # Web bottom left
            [-wt2, d2 - ft, 0],     # Web top left
            [-fw2, d2 - ft, 0],     # Top left inner
            [-fw2, d2, 0]           # Close polyline at Top left outer
        ]

        # Translate points to user's selected insertion point
        translated_points = []
        for pt in points:
            translated_points.append([
                pt[0] + insertion_point.X,
                pt[1] + insertion_point.Y,
                pt[2] + insertion_point.Z
            ])

        # Create geometry
        curve_id = rs.AddPolyline(translated_points)
        
        # Organize into a layer
        layer_name = "2D_I_Beams"
        if not rs.IsLayer(layer_name):
            rs.AddLayer(layer_name) # You can add color too if desired
            
        if curve_id:
            rs.ObjectLayer(curve_id, layer_name)
            rs.SelectObject(curve_id)
            print("I-Beam profile created successfully.")

    except Exception as e:
        print("An error occurred: {}".format(e))
    finally:
        rs.EnableRedraw(True)

if __name__ == "__main__":
    draw_i_beam_profile()
