import rhinoscriptsyntax as rs
import random

def create_diag_grid():
    """
    Creates a grid that interpolates between straight (orthogonal) and diagonal lines.
    Offers modes: Diagonal Only, Hybrid (Both), or Random Mix.
    """
    # 1. Inputs
    x_cells = rs.GetInteger("Number of cells in X", 10, 1)
    if x_cells is None: return

    y_cells = rs.GetInteger("Number of cells in Y", 10, 1)
    if y_cells is None: return

    spacing = rs.GetReal("Cell spacing", 2.0, 0.001)
    if spacing is None: return

    # Mode Selection
    # 0 = Diagonal Only (Diamonds)
    # 1 = Hybrid (Star/Union Jack - Both Rect and Diag)
    # 2 = Random Mix (Some cells Rect, some Diag, some Both)
    mode_items = ["Diagonal", "Hybrid_All", "Random_Mix"]
    mode = rs.GetInteger("Grid Mode (0=Diagonal, 1=Hybrid, 2=Random)", 1, 0, 2)
    if mode is None: return

    rs.EnableRedraw(False)
    
    lines = []

    # Helper to add line
    def add(p1, p2):
        ln = rs.AddLine(p1, p2)
        if ln: lines.append(ln)

    # We iterate through the "cells" (squares defined by i,j to i+1,j+1)
    for i in range(x_cells):
        for j in range(y_cells):
            
            # Cell corners
            # p0 -- p3
            # |     |
            # p1 -- p2
            #
            # Order: 
            # p0 = (i, j)
            # p1 = (i, j+1)  <-- Wait, usually Y goes up.
            # Let's map cartesian: 
            # BL = (i, j)
            # BR = (i+1, j)
            # TR = (i+1, j+1)
            # TL = (i, j+1)
            
            x0, y0 = i * spacing, j * spacing
            x1, y1 = (i + 1) * spacing, (j + 1) * spacing
            
            p_bl = [x0, y0, 0]
            p_br = [x1, y0, 0]
            p_tr = [x1, y1, 0]
            p_tl = [x0, y1, 0]

            # Determine what to draw for this cell
            # cell_mode: 0=Diag, 1=Rect, 2=Both
            cell_type = 2 # Default to Both (Hybrid)

            if mode == 0: # Diagonal Only
                cell_type = 0
            elif mode == 1: # Hybrid All
                cell_type = 2
            elif mode == 2: # Random Mix
                # Randomly choose what this cell has
                # 33% Rect, 33% Diag, 33% Both? 
                # Or maybe 50% Diag, 50% Hybrid?
                r = random.random()
                if r < 0.33: cell_type = 0 # Diag
                elif r < 0.66: cell_type = 1 # Rect
                else: cell_type = 2 # Both

            # DRAWING 
            
            # Rectangular Lines (Orthogonal)
            # Note: If we simply add rect lines for every cell, we duplicate shared edges.
            # For a "Smart" grid, we might only draw Bottom and Left edges, then close the top/right at the end.
            # But since we are doing per-cell randomness, we might WANT double lines or unconnected lines? 
            # If "Random", we probably treat each cell as a unit.
            # If "Uniform", we should avoid duplicates. 
            # For simplicity in this script (V1), duplicates are acceptable or we can just ignore them (Rhino handles them okay visually).
            # Let's try to be slightly smart: Only draw Bottom and Left if they match the neighbor? Too complex for V1.
            # let's just draw the lines. 'rs.CurveBooleanUnion' or similar could clean up later if needed.
            
            if cell_type == 1 or cell_type == 2:
                # Add Rect (verify duplicates?)
                # Actually, simpler logic:
                # A cell owns its Bottom and Left edge? 
                # Let's just draw the full box for the cell to ensure it looks 'complete' in Random mode
                add(p_bl, p_br) # Bottom
                add(p_br, p_tr) # Right
                add(p_tr, p_tl) # Top
                add(p_tl, p_bl) # Left
            
            # Diagonal Lines
            if cell_type == 0 or cell_type == 2:
                add(p_bl, p_tr) # /
                add(p_tl, p_br) # \

    if lines:
        grp = rs.AddGroup("DiagGrid")
        rs.AddObjectsToGroup(lines, grp)

    rs.EnableRedraw(True)
    print("Created DiagGrid Mode {}".format(mode))

if __name__ == "__main__":
    create_diag_grid()
