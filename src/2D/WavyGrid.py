import rhinoscriptsyntax as rs
import random

def create_wavy_grid():
    """
    Creates a 'wavy', irregular 2D grid of interpolated curves on the XY plane.
    Points are perturbed randomly to create a wobbly effect.
    """
    # 1. Get user inputs
    x_cells = rs.GetInteger("Number of cells in X", 10, 1)
    if x_cells is None: return

    y_cells = rs.GetInteger("Number of cells in Y", 10, 1)
    if y_cells is None: return

    spacing = rs.GetReal("Base grid spacing", 2.0, 0.001)
    if spacing is None: return

    # Randomness factor (0.0 = perfect grid, higher = more chaotic)
    jitter = rs.GetReal("Chaos Factor (Max offset)", 0.8, 0.0)
    if jitter is None: return

    # Thickness
    thickness = rs.GetReal("Grid line thickness (0 for none)", 0.0, 0.0)
    if thickness is None: return

    # Disable redraw for speed
    rs.EnableRedraw(False)

    grid_curves = []

    # 2. Generate the grid of points
    # We store them in a 2D list: points[x_index][y_index]
    points = []
    
    for i in range(x_cells + 1):
        col_points = []
        for j in range(y_cells + 1):
            # Calculate base position
            base_x = i * spacing
            base_y = j * spacing
            
            # Apply random jitter
            rx = random.uniform(-jitter, jitter)
            ry = random.uniform(-jitter, jitter)
            
            pt = [base_x + rx, base_y + ry, 0]
            col_points.append(pt)
        points.append(col_points)

    def add_curve_with_thickness(pts):
        curve_id = rs.AddInterpCurve(pts, degree=3, knotstyle=0)
        if not curve_id: return
        
        if thickness > 0:
            import Rhino, scriptcontext
            rh_crv = rs.coercecurve(curve_id)
            if rh_crv:
                tol = rs.UnitAbsoluteTolerance()
                off1 = rh_crv.Offset(Rhino.Geometry.Plane.WorldXY, thickness/2.0, tol, Rhino.Geometry.CurveOffsetCornerStyle.Sharp)
                off2 = rh_crv.Offset(Rhino.Geometry.Plane.WorldXY, -thickness/2.0, tol, Rhino.Geometry.CurveOffsetCornerStyle.Sharp)
                
                if off1:
                    for c in off1:
                        cid = scriptcontext.doc.Objects.AddCurve(c)
                        if cid: grid_curves.append(cid)
                if off2:
                    for c in off2:
                        cid = scriptcontext.doc.Objects.AddCurve(c)
                        if cid: grid_curves.append(cid)
                
                rs.DeleteObject(curve_id)
        else:
            grid_curves.append(curve_id)

    # 3. Create 'Horizontal' curves (along X direction)
    for j in range(y_cells + 1):
        row_pts = []
        for i in range(x_cells + 1):
            row_pts.append(points[i][j])
        add_curve_with_thickness(row_pts)

    # 4. Create 'Vertical' curves (along Y direction)
    for i in range(x_cells + 1):
        col_pts = points[i]
        add_curve_with_thickness(col_pts)

    # Group the result
    if grid_curves:
        group_name = rs.AddGroup("WavyGrid")
        rs.AddObjectsToGroup(grid_curves, group_name)

    rs.EnableRedraw(True)
    print("Created wavy grid: {}x{}, spacing {}, chaos {}".format(x_cells, y_cells, spacing, jitter))

if __name__ == "__main__":
    create_wavy_grid()
