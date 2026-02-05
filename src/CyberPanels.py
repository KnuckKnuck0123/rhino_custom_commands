import rhinoscriptsyntax as rs
import random

def create_cyber_panels():
    """
    Applies a recursive subdivision (quadtree-like) to a selected surface,
    creating irregular panels with varying extrusion heights for a 'Cyberpunk' / Greeble effect.
    """
    # 1. Select Target Surface
    srf = rs.GetObject("Select a surface to panelize", rs.filter.surface)
    if not srf: return

    # 2. Parameters
    generations = rs.GetInteger("Recursion Depth (Complexity)", 4, 1, 8)
    if generations is None: return

    max_height = rs.GetReal("Max Panel Extrusion Height", 1.0, 0.0)
    if max_height is None: return

    gap_percent = rs.GetReal("Panel Gap % (0.0 - 0.5)", 0.05, 0.0, 0.5)
    if gap_percent is None: return

    # 3. Recursive Logic
    # Returns list of tuples: (u_min, u_max, v_min, v_max)
    def recursive_split(u0, u1, v0, v1, depth):
        # Stop condition: Max depth reached OR Random early stop (for variation)
        # We start stopping early only after depth 2 to ensure some density
        if depth <= 0:
            return [(u0, u1, v0, v1)]
        
        if depth < generations - 1 and random.random() < 0.15:
             return [(u0, u1, v0, v1)]

        # Split Logic
        # Determine 0=Split U, 1=Split V
        # If one dimension is much larger, favor splitting that one to keep panels roughly square
        du = u1 - u0
        dv = v1 - v0
        
        # Simple heuristic: Split the longest side, or random if close
        if du > dv * 1.5:  split_dir = 0
        elif dv > du * 1.5: split_dir = 1
        else: split_dir = random.choice([0, 1])

        # Split parameter t (0.3 to 0.7 to avoid slivers)
        t = random.uniform(0.3, 0.7)

        if split_dir == 0: # U split
            u_split = u0 + (u1 - u0) * t
            return recursive_split(u0, u_split, v0, v1, depth-1) + \
                   recursive_split(u_split, u1, v0, v1, depth-1)
        else: # V split
            v_split = v0 + (v1 - v0) * t
            return recursive_split(u0, u1, v0, v_split, depth-1) + \
                   recursive_split(u0, u1, v_split, v1, depth-1)

    # 4. Execution
    rs.EnableRedraw(False)
    
    # Get surface domain boundaries
    u_domain = rs.SurfaceDomain(srf, 0)
    v_domain = rs.SurfaceDomain(srf, 1)
    
    # Generate the UV rectangles
    panels_uv = recursive_split(u_domain[0], u_domain[1], v_domain[0], v_domain[1], generations)
    
    generated_objs = []

    for p_uv in panels_uv:
        u0, u1, v0, v1 = p_uv

        # Skip random panels to create "missing" hull plating (damage/variety)
        if random.random() < 0.05:
            continue

        # Apply Gap (Shrink UV)
        du = u1 - u0
        dv = v1 - v0
        u_gap = du * gap_percent
        v_gap = dv * gap_percent
        
        nu0, nu1 = u0 + u_gap, u1 - u_gap
        nv0, nv1 = v0 + v_gap, v1 - v_gap
        
        # Evaluate 4 corners
        # (Using EvaluateSurface handles curved surfaces, though strictly planar panels 
        # on curved surfaces might clip. This is 'good enough' for greebles).
        corners_uv = [(nu0, nv0), (nu1, nv0), (nu1, nv1), (nu0, nv1)]
        corners_3d = [rs.EvaluateSurface(srf, uv[0], uv[1]) for uv in corners_uv]
        
        # Create base panel
        # Adding a 5th point (first point) to close the polyline
        corners_3d.append(corners_3d[0])
        
        # Create the planar curve for the panel
        # Note: If surface is non-planar, these 4 points might not be planar.
        # rs.AddSrfPt is robust for 3-4 points.
        panel_srf = rs.AddSrfPt(corners_3d[:-1]) # Remove duplicate for AddSrfPt
        
        if panel_srf:
            # Calculate Normal for extrusion
            center_u = (nu0 + nu1) / 2
            center_v = (nv0 + nv1) / 2
            normal = rs.SurfaceNormal(srf, [center_u, center_v])
            normal = rs.VectorUnitize(normal)
            
            # Determine Extrusion Height
            # Varied height for texture
            h = random.uniform(max_height * 0.1, max_height)
            
            # 50% chance to be "flush" (very thin) vs "protruding"
            if random.random() < 0.3:
                h = max_height * 0.05
                
            vec = rs.VectorScale(normal, h)
            
            # Create Extrusion Path
            # We can't use ExtrudeSurface simply without a curve, 
            # and automating "ExtrudeSurface" via rs.ExtrudeSurface(srf, curve) works best.
            # We need a line curve representing the vector.
            start_pt = corners_3d[0]
            end_pt = rs.PointAdd(start_pt, vec)
            path_crv = rs.AddLine(start_pt, end_pt)
            
            if path_crv:
                extrusion = rs.ExtrudeSurface(panel_srf, path_crv)
                rs.DeleteObject(path_crv)
                
                if extrusion:
                    rs.CapPlanarHoles(extrusion)
                    generated_objs.append(extrusion)
            
            # Clean up the base surface
            rs.DeleteObject(panel_srf)

    # Group
    if generated_objs:
        grp = rs.AddGroup("CyberPanels")
        rs.AddObjectsToGroup(generated_objs, grp)
        
    rs.EnableRedraw(True)
    print("Generated {} cyber panels.".format(len(generated_objs)))

if __name__ == "__main__":
    create_cyber_panels()
