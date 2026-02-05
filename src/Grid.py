import rhinoscriptsyntax as rs

def create_grid():
    """
    Creates a 2D grid of lines on the XY plane based on user inputs.
    """
    # 1. Get user input for grid dimensions
    # Number of cells in X
    x_cells = rs.GetInteger("Number of cells in X direction", 10, 1)
    if x_cells is None: return

    # Number of cells in Y
    y_cells = rs.GetInteger("Number of cells in Y direction", 10, 1)
    if y_cells is None: return

    # Spacing
    spacing = rs.GetReal("Grid cell spacing", 1.0, 0.001)
    if spacing is None: return

    # Group the grid lines for easier management? Optional, but nice.
    # Let's just make lines for now.

    # Disable redraw for performance
    rs.EnableRedraw(False)

    grid_lines = []

    # 2. Create vertical lines (along Y axis, varying X)
    # To have N cells, we need N+1 lines
    total_width = x_cells * spacing
    total_height = y_cells * spacing

    for i in range(x_cells + 1):
        x_pos = i * spacing
        start = (x_pos, 0, 0)
        end = (x_pos, total_height, 0)
        line = rs.AddLine(start, end)
        if line: grid_lines.append(line)

    # 3. Create horizontal lines (along X axis, varying Y)
    for j in range(y_cells + 1):
        y_pos = j * spacing
        start = (0, y_pos, 0)
        end = (total_width, y_pos, 0)
        line = rs.AddLine(start, end)
        if line: grid_lines.append(line)
    
    # Optional: Group the created objects
    if grid_lines:
        group_name = rs.AddGroup("GeneratedGrid")
        rs.AddObjectsToGroup(grid_lines, group_name)

    rs.EnableRedraw(True)
    print("Created grid: {}x{} cells, spacing {}".format(x_cells, y_cells, spacing))

if __name__ == "__main__":
    create_grid()
