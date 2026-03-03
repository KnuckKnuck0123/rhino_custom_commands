import rhinoscriptsyntax as rs

def create_metal_deck():
    """
    Creates a 2D Metal Decking profile based on real-world dimensions
    and maps it along the edge of a selected surface using surface normals.
    Defaults represent a standard 1.5" B-Deck.
    """
    print("=== 2D Metal Decking on Surface ===")
    
    # 1. Get parameters (Defaults based on 1.5" B-Deck)
    depth = rs.GetReal("Deck Depth (e.g. 1.5 for 1.5in B-Deck)", 1.5, 0.1)
    if depth is None: return
    
    pitch = rs.GetReal("Rib Pitch (e.g. 6.0 for B-Deck)", 6.0, 0.1)
    if pitch is None: return
    
    top_flange = rs.GetReal("Top Flange Width", 1.75, 0.1)
    if top_flange is None: return
    
    bot_flange = rs.GetReal("Bottom Flange Width", 1.75, 0.1)
    if bot_flange is None: return
    
    if top_flange + bot_flange >= pitch:
        print("Error: Combined flange widths exceed rib pitch.")
        return
        
    srf_id = rs.GetObject("Select a surface to map the decking onto", rs.filter.surface)
    if not srf_id:
        print("No surface selected.")
        return
        
    dir_choice = rs.GetString("Decking direction along surface?", "U", ["U", "V"])
    if not dir_choice: return
    dir_choice = dir_choice.upper()
    
    rs.EnableRedraw(False)
    
    try:
        domain_u = rs.SurfaceDomain(srf_id, 0)
        domain_v = rs.SurfaceDomain(srf_id, 1)
        
        # Calculate length along the selected surface direction
        if dir_choice == "U":
            mid_v = (domain_v[0] + domain_v[1]) / 2.0
            crv = rs.ExtractIsoCurve(srf_id, [domain_u[0], mid_v], 0)
            length = rs.CurveLength(crv)
            rs.DeleteObject(crv)
        else:
            mid_u = (domain_u[0] + domain_u[1]) / 2.0
            crv = rs.ExtractIsoCurve(srf_id, [mid_u, domain_v[0]], 1)
            length = rs.CurveLength(crv)
            rs.DeleteObject(crv)
            
        num_pitches = int(length / pitch)
        if num_pitches == 0:
            num_pitches = 1
            pitch = length # stretch to fit if length is smaller than a single pitch
            
        web_w = (pitch - top_flange - bot_flange) / 2.0
        
        # 2. Build 1D profile sequence points (length and depth)
        base_points = []
        for i in range(num_pitches):
            offset = i * pitch
            base_points.append([offset, 0, 0])
            base_points.append([offset + bot_flange / 2.0, 0, 0])
            base_points.append([offset + bot_flange / 2.0 + web_w, depth, 0])
            base_points.append([offset + bot_flange / 2.0 + web_w + top_flange, depth, 0])
            base_points.append([offset + bot_flange + 2 * web_w + top_flange, 0, 0])
        # Close out the final pitch precisely at the end of the profile
        base_points.append([num_pitches * pitch, 0, 0])
        
        # 3. Map the 1D points strictly to the edge of the surface using evaluated normals
        mapped_points = []
        for pt in base_points:
            x_val = pt[0] # Progress along the surface
            z_val = pt[1] # Corrugation depth projected via surface normal
            
            # Parametric value from 0.0 to 1.0 along the surface dimension
            t = x_val / (num_pitches * pitch)
            
            if dir_choice == "U":
                u = domain_u[0] + t * (domain_u[1] - domain_u[0])
                v = domain_v[0] # Locked to one edge of V
                srf_pt = rs.EvaluateSurface(srf_id, u, v)
                normal = rs.SurfaceNormal(srf_id, [u, v])
            else:
                u = domain_u[0] # Locked to one edge of U
                v = domain_v[0] + t * (domain_v[1] - domain_v[0])
                srf_pt = rs.EvaluateSurface(srf_id, u, v)
                normal = rs.SurfaceNormal(srf_id, [u, v])
                
            if srf_pt and normal:
                # Displace the point along the positive normal vector by the required depth magnitude
                final_pt = [
                    srf_pt[0] + normal[0] * z_val,
                    srf_pt[1] + normal[1] * z_val,
                    srf_pt[2] + normal[2] * z_val
                ]
                mapped_points.append(final_pt)
                
        # 4. Generate geometry and apply project rules 
        if len(mapped_points) > 1:
            crv_id = rs.AddPolyline(mapped_points)
            
            layer_name = "2D_Metal_Decking"
            if not rs.IsLayer(layer_name):
                rs.AddLayer(layer_name)
                
            rs.ObjectLayer(crv_id, layer_name)
            rs.SelectObject(crv_id)
            print("Metal decking profile generated and mapped to surface successfully.")
            
    except Exception as e:
        print("An error occurred: {}".format(e))
    finally:
        rs.EnableRedraw(True)

if __name__ == "__main__":
    create_metal_deck()
