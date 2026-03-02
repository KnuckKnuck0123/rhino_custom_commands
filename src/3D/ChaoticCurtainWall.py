import rhinoscriptsyntax as rs
import random

def create_chaotic_curtain_wall():
    """
    Creates a chaotic curtain wall on a selected surface.
    """
    srf_id = rs.GetObject("Select a Base Surface for the Curtain Wall", rs.filter.surface)
    if not srf_id: return
    
    u_divs = rs.GetInteger("Number of U Divisions (Columns)", 10, 1)
    if u_divs is None: return
    
    v_divs = rs.GetInteger("Number of V Divisions (Rows)", 10, 1)
    if v_divs is None: return
    
    mullion_radius = rs.GetReal("Mullion Radius (Thickness)", 1.0, 0.01)
    if mullion_radius is None: return
    
    grid_chaos = rs.GetReal("Grid Chaos (Distortion distance of mullion intersections)", 2.0, 0.0)
    if grid_chaos is None: return
    
    missing_prob = rs.GetReal("Missing Panel Probability (0.0 to 1.0)", 0.1, 0.0, 1.0)
    if missing_prob is None: return
    
    panel_depth_var = rs.GetReal("Panel Depth Variation (Random offset along normal)", 5.0, 0.0)
    if panel_depth_var is None: return

    rs.EnableRedraw(False)

    group_name = rs.AddGroup("ChaoticCurtainWall")
    created_objs = []
    
    # Analyze surface domain
    domain_u = rs.SurfaceDomain(srf_id, 0)
    domain_v = rs.SurfaceDomain(srf_id, 1)
    
    u_step = (domain_u[1] - domain_u[0]) / u_divs
    v_step = (domain_v[1] - domain_v[0]) / v_divs
    
    # Generate points grid
    grid_pts = []
    grid_normals = []
    
    for i in range(u_divs + 1):
        u_val = domain_u[0] + i * u_step
        col_pts = []
        col_norms = []
        for j in range(v_divs + 1):
            v_val = domain_v[0] + j * v_step
            # base point and normal
            pt = rs.EvaluateSurface(srf_id, u_val, v_val)
            norm = rs.SurfaceNormal(srf_id, [u_val, v_val])
            
            # Apply grid chaos (only internal points)
            if grid_chaos > 0 and 0 < i < u_divs and 0 < j < v_divs:
                # tangent plane to perturb
                plane = rs.PlaneFromNormal(pt, norm)
                x_offset = random.uniform(-grid_chaos, grid_chaos)
                y_offset = random.uniform(-grid_chaos, grid_chaos)
                pt = rs.PointAdd(pt, rs.VectorScale(plane.XAxis, x_offset))
                pt = rs.PointAdd(pt, rs.VectorScale(plane.YAxis, y_offset))
                
            col_pts.append(pt)
            col_norms.append(norm)
        grid_pts.append(col_pts)
        grid_normals.append(col_norms)
        
    unique_edges = set()
    
    # Create Panels and Mullion edges
    for i in range(u_divs):
        for j in range(v_divs):
            p1 = grid_pts[i][j]
            p2 = grid_pts[i+1][j]
            p3 = grid_pts[i+1][j+1]
            p4 = grid_pts[i][j+1]
            
            n1 = grid_normals[i][j]
            n2 = grid_normals[i+1][j]
            n3 = grid_normals[i+1][j+1]
            n4 = grid_normals[i][j+1]
            
            avg_n = rs.VectorAdd(rs.VectorAdd(n1, n2), rs.VectorAdd(n3, n4))
            avg_n = rs.VectorUnitize(avg_n)
            
            # Add segments to mullions
            unique_edges.add(frozenset(((i, j), (i+1, j))))
            unique_edges.add(frozenset(((i+1, j), (i+1, j+1))))
            unique_edges.add(frozenset(((i+1, j+1), (i, j+1))))
            unique_edges.add(frozenset(((i, j+1), (i, j))))
            
            # Check for missing panel
            if random.random() >= missing_prob:
                # Panel variation
                depth_offset = random.uniform(-panel_depth_var, panel_depth_var)
                
                op1 = rs.PointAdd(p1, rs.VectorScale(avg_n, depth_offset))
                op2 = rs.PointAdd(p2, rs.VectorScale(avg_n, depth_offset))
                op3 = rs.PointAdd(p3, rs.VectorScale(avg_n, depth_offset))
                op4 = rs.PointAdd(p4, rs.VectorScale(avg_n, depth_offset))
                
                # Shrink panel to fit inside mullions
                centroid = [(op1[0]+op2[0]+op3[0]+op4[0])/4, 
                            (op1[1]+op2[1]+op3[1]+op4[1])/4, 
                            (op1[2]+op2[2]+op3[2]+op4[2])/4]
                            
                diag1 = rs.Distance(op1, op3)
                diag2 = rs.Distance(op2, op4)
                avg_diag = (diag1 + diag2)/2.0
                
                # Ensure the panel size is larger than the mullion gap
                mullion_gap = mullion_radius * 2.5
                if avg_diag > mullion_gap:
                    scale_factor = (avg_diag - mullion_gap) / avg_diag
                    
                    sp1 = [centroid[k] + (op1[k]-centroid[k])*scale_factor for k in range(3)]
                    sp2 = [centroid[k] + (op2[k]-centroid[k])*scale_factor for k in range(3)]
                    sp3 = [centroid[k] + (op3[k]-centroid[k])*scale_factor for k in range(3)]
                    sp4 = [centroid[k] + (op4[k]-centroid[k])*scale_factor for k in range(3)]
                    
                    panel_srf = rs.AddSrfPt([sp1, sp2, sp3, sp4])
                    if panel_srf:
                        created_objs.append(panel_srf)

    culled_lines = []
    for edge in unique_edges:
        edge_list = list(edge)
        if len(edge_list) == 2:
            p_idx1, p_idx2 = edge_list
            p_a = grid_pts[p_idx1[0]][p_idx1[1]]
            p_b = grid_pts[p_idx2[0]][p_idx2[1]]
            line = rs.AddLine(p_a, p_b)
            if line:
                culled_lines.append(line)

    # Create pipes
    for line in culled_lines:
        if line:
            pipe = rs.AddPipe(line, 0, mullion_radius, cap=1)
            if pipe:
                created_objs.extend(pipe)
            rs.DeleteObject(line)
            
    if created_objs:
        rs.AddObjectsToGroup(created_objs, group_name)

    rs.EnableRedraw(True)
    print("Created Chaotic Curtain Wall with {} objects.".format(len(created_objs)))

if __name__ == '__main__':
    create_chaotic_curtain_wall()
