import rhinoscriptsyntax as rs
import Rhino
import scriptcontext

def get_plane_and_bounds_from_curves(crv_ids):
    if not crv_ids: return None, None, None
    poly = rs.ConvertCurveToPolyline(crv_ids[0])
    if not poly: return None, None, None
    pts = rs.CurvePoints(poly)
    rs.DeleteObject(poly)
    if not pts: return None, None, None
    
    plane = rs.PlaneFitFromPoints(pts)
    if not plane: return None, None, None
    
    # Check if normals are reversed
    world_z = Rhino.Geometry.Vector3d(0, 0, 1)
    if abs(plane.ZAxis.Z) < 0.99:
        horiz_x = Rhino.Geometry.Vector3d.CrossProduct(plane.ZAxis, world_z)
        horiz_x.Unitize()
        horiz_y = Rhino.Geometry.Vector3d.CrossProduct(plane.ZAxis, horiz_x)
        horiz_y.Unitize()
        if horiz_y.Z < 0:
            horiz_y = -horiz_y
            horiz_x = -horiz_x
        plane = Rhino.Geometry.Plane(plane.Origin, horiz_x, horiz_y)
    
    xform_to_2d = Rhino.Geometry.Transform.ChangeBasis(Rhino.Geometry.Plane.WorldXY, plane)
    
    min_x, min_y = float('inf'), float('inf')
    max_x, max_y = float('-inf'), float('-inf')
    
    for cid in crv_ids:
        cg = rs.coercecurve(cid).Duplicate()
        cg.Transform(xform_to_2d)
        bbox = cg.GetBoundingBox(True)
        if bbox.Min.X < min_x: min_x = bbox.Min.X
        if bbox.Min.Y < min_y: min_y = bbox.Min.Y
        if bbox.Max.X > max_x: max_x = bbox.Max.X
        if bbox.Max.Y > max_y: max_y = bbox.Max.Y
        
    return plane, [min_x, min_y, 0], [max_x, max_y, 0]

def generate_preview(obj_id, outer_curves, p1, p2, is_non_planar_srf, len_u, len_v, params, plane=None):
    target_bay = params["target_bay_width"]
    transom_drop = params["transom_drop"]
    frame = params["frame_width"]
    mullion = params["mullion_width"]
    
    created_objs = []
    
    min_x = min(p1[0], p2[0])
    max_x = max(p1[0], p2[0])
    min_y = min(p1[1], p2[1])
    max_y = max(p1[1], p2[1])
    z = p1[2]
    
    cw_width = max_x - min_x
    cw_height = max_y - min_y
    
    if cw_width <= 0 or cw_height <= 0: return []
    
    xform_to_3d = None
    xform_to_2d = None
    if plane:
        xform_to_3d = Rhino.Geometry.Transform.ChangeBasis(plane, Rhino.Geometry.Plane.WorldXY)
        xform_to_2d = Rhino.Geometry.Transform.ChangeBasis(Rhino.Geometry.Plane.WorldXY, plane)
    
    if outer_curves:
        for cid in outer_curves:
            c = rs.CopyObject(cid)
            if c: created_objs.append(c)
    else:
        rect = rs.AddPolyline([[min_x, min_y, z], [max_x, min_y, z], 
                               [max_x, max_y, z], [min_x, max_y, z], [min_x, min_y, z]])
        if rect:
            if xform_to_3d:
                rg = rs.coercecurve(rect).Duplicate()
                rg.Transform(xform_to_3d)
                rs.DeleteObject(rect)
                rect = scriptcontext.doc.Objects.AddCurve(rg)
            created_objs.append(rect)

    inner_min_x = min_x + frame
    inner_max_x = max_x - frame
    inner_min_y = min_y + frame
    inner_max_y = max_y - frame
    
    if inner_min_x >= inner_max_x or inner_min_y >= inner_max_y:
        frame = min(cw_width, cw_height) * 0.05
        inner_min_x = min_x + frame
        inner_max_x = max_x - frame
        inner_min_y = min_y + frame
        inner_max_y = max_y - frame
        
    inner_rect = rs.AddPolyline([[inner_min_x, inner_min_y, z], [inner_max_x, inner_min_y, z], 
                                 [inner_max_x, inner_max_y, z], [inner_min_x, inner_max_y, z], [inner_min_x, inner_min_y, z]])
                                 
    inner_crv_geom = None
    if inner_rect:
        inner_crv_geom = rs.coercecurve(inner_rect).Duplicate()
        if xform_to_3d:
            rg = rs.coercecurve(inner_rect).Duplicate()
            rg.Transform(xform_to_3d)
            rs.DeleteObject(inner_rect)
            inner_rect = scriptcontext.doc.Objects.AddCurve(rg)
        created_objs.append(inner_rect)
    
    if not inner_crv_geom: return created_objs
    
    inner_w = inner_max_x - inner_min_x
    inner_h = inner_max_y - inner_min_y
    
    bays = max(1, int(round(inner_w / target_bay))) if target_bay > 0 else 1
    actual_bay_w = inner_w / bays
    xs = [inner_min_x + i * actual_bay_w for i in range(bays + 1)]
    split_y = inner_max_y - transom_drop
    if split_y <= inner_min_y: split_y = inner_min_y + inner_h * 0.8
    ys = [inner_min_y, split_y, inner_max_y]
    
    raw_panels = []
    for i in range(bays):
        for j in range(2): 
            px_min = xs[i] + (mullion / 2.0 if i > 0 else 0)
            px_max = xs[i+1] - (mullion / 2.0 if i < bays - 1 else 0)
            py_min = ys[j] + (mullion / 2.0 if j > 0 else 0)
            py_max = ys[j+1] - (mullion / 2.0 if j < 1 else 0)
            
            if px_min < px_max and py_min < py_max:
                panel = rs.AddPolyline([[px_min, py_min, z], [px_max, py_min, z],
                                        [px_max, py_max, z], [px_min, py_max, z], [px_min, py_min, z]])
                if panel: raw_panels.append(panel)
                
    framed_panels_geom = []
    tol = scriptcontext.doc.ModelAbsoluteTolerance
    
    for p in raw_panels:
        p_geom = rs.coercecurve(p)
        if p_geom:
            try:
                out = Rhino.Geometry.Curve.CreateBooleanIntersection(p_geom, inner_crv_geom, tol)
                if out: framed_panels_geom.extend(out)
            except:
                pass
        if p: rs.DeleteObject(p)
            
    final_panels_geom = []
    if outer_curves:
        srf_curves_geom = []
        for c in outer_curves:
            cg = rs.coercecurve(c).Duplicate()
            if xform_to_2d: cg.Transform(xform_to_2d)
            srf_curves_geom.append(cg)
            
        if srf_curves_geom:
            for p_geom in framed_panels_geom:
                try:
                    out = Rhino.Geometry.Curve.CreateBooleanIntersection([p_geom], srf_curves_geom, tol)
                    if out: final_panels_geom.extend(out)
                except:
                    pass
        else:
            final_panels_geom = framed_panels_geom
    else:
        final_panels_geom = framed_panels_geom
        
    glass_panels = []
    for crv in final_panels_geom:
        if crv:
            if xform_to_3d: crv.Transform(xform_to_3d)
            crv_id = scriptcontext.doc.Objects.AddCurve(crv)
            if crv_id: glass_panels.append(crv_id)
            
    created_objs.extend(glass_panels)
    
    if is_non_planar_srf and obj_id:
        domain_u = rs.SurfaceDomain(obj_id, 0)
        domain_v = rs.SurfaceDomain(obj_id, 1)
        mapped_objs = []
        for obj in created_objs:
            pts = []
            if rs.IsCurve(obj):
                pl_obj = rs.ConvertCurveToPolyline(obj)
                if pl_obj:
                    pts = rs.CurvePoints(pl_obj)
                    rs.DeleteObject(pl_obj)
                else:
                    pts = rs.CurvePoints(obj)
            
            if pts:
                sub_pts = [pts[0]]
                for idx in range(1, len(pts)):
                    pA = pts[idx-1]
                    pB = pts[idx]
                    dist = rs.Distance(pA, pB)
                    divs = int(dist / 1.0)
                    for k in range(1, divs + 1):
                        f = float(k) / (divs + 1)
                        sub_pts.append([pA[0] + f*(pB[0]-pA[0]), pA[1] + f*(pB[1]-pA[1]), pA[2] + f*(pB[2]-pA[2])])
                    sub_pts.append(pB)
                
                new_pts = []
                for pt in sub_pts:
                    u_t = pt[0] / len_u if len_u > 0 else 0
                    v_t = pt[1] / len_v if len_v > 0 else 0
                    u = domain_u[0] + u_t * (domain_u[1] - domain_u[0])
                    v = domain_v[0] + v_t * (domain_v[1] - domain_v[0])
                    srf_pt = rs.EvaluateSurface(obj_id, u, v)
                    target_pt = srf_pt if srf_pt else pt
                    if not new_pts or rs.Distance(new_pts[-1], target_pt) > 0.005:
                        new_pts.append(target_pt)
                
                if rs.IsCurveClosed(obj) and len(new_pts) > 1:
                    if rs.Distance(new_pts[0], new_pts[-1]) > 0.005: new_pts.append(new_pts[0])
                
                if len(new_pts) >= 2:
                    try:
                        mapped = rs.AddPolyline(new_pts)
                        if mapped: mapped_objs.append(mapped)
                    except: pass
            if obj: rs.DeleteObject(obj)
        created_objs = mapped_objs
        
    return created_objs

def create_storefront():
    obj_id = rs.GetObject("Select a surface or closed curve for the Storefront (Press Enter to draw)", rs.filter.surface | rs.filter.polysurface | rs.filter.curve)
    
    is_non_planar_srf = False
    len_u = 0
    len_v = 0
    p1 = None
    p2 = None
    outer_curves = []
    plane = None
    
    if obj_id:
        if rs.IsCurve(obj_id):
            if not rs.IsCurvePlanar(obj_id) or not rs.IsCurveClosed(obj_id):
                print("Selected curve must be planar and closed.")
                return
            outer_curves = [rs.CopyObject(obj_id)]
            plane, p1, p2 = get_plane_and_bounds_from_curves(outer_curves)
            if not plane:
                bbox = rs.BoundingBox(obj_id)
                p1 = bbox[0]
                p2 = bbox[2]
        else:
            if not rs.IsSurfacePlanar(obj_id):
                is_non_planar_srf = True
                if rs.IsPolysurface(obj_id):
                    print("Please select a single Surface, not a Polysurface, for non-planar mapping.")
                    return
                domain_u = rs.SurfaceDomain(obj_id, 0)
                domain_v = rs.SurfaceDomain(obj_id, 1)
                mid_v = (domain_v[0] + domain_v[1])/2.0
                crv_u = rs.ExtractIsoCurve(obj_id, [domain_u[0], mid_v], 0)
                len_u = rs.CurveLength(crv_u)
                rs.DeleteObject(crv_u)
                
                mid_u = (domain_u[0] + domain_u[1])/2.0
                crv_v = rs.ExtractIsoCurve(obj_id, [mid_u, domain_v[0]], 1)
                len_v = rs.CurveLength(crv_v)
                rs.DeleteObject(crv_v)
                
                p1 = [0, 0, 0]
                p2 = [len_u, len_v, 0]
                
                rect_crv = rs.AddPolyline([[0,0,0], [len_u,0,0], [len_u,len_v,0], [0,len_v,0], [0,0,0]])
                if rect_crv: outer_curves = [rect_crv]
            else:
                border_crvs = rs.DuplicateSurfaceBorder(obj_id)
                if not border_crvs: return
                outer_curves = border_crvs
                plane, p1, p2 = get_plane_and_bounds_from_curves(outer_curves)
                if not plane:
                    bbox = rs.BoundingBox(obj_id)
                    p1 = bbox[0]
                    p2 = bbox[2]
    else:
        rect_pts = rs.GetRectangle()
        if not rect_pts: return
        p1 = rect_pts[0]
        p2 = rect_pts[2]

    params = {
        "target_bay_width": 4.0,
        "transom_drop": 2.0,
        "frame_width": 0.4,
        "mullion_width": 0.2
    }
    
    labels = ["Target Bay Width", "Transom Drop", "Outer Frame Width", "Inner Mullion Width"]
    defaults = [str(params["target_bay_width"]), str(params["transom_drop"]), str(params["frame_width"]), str(params["mullion_width"])]
    title = "Storefront Parameters"
    msg = "Configure the storefront details."
    
    preview_ids = []
    
    while True:
        if preview_ids:
            rs.DeleteObjects(preview_ids)
            preview_ids = []
            
        rs.EnableRedraw(False)
        preview_ids = generate_preview(obj_id, outer_curves, p1, p2, is_non_planar_srf, len_u, len_v, params, plane)
        rs.EnableRedraw(True)
        
        results = rs.PropertyListBox(labels, defaults, title, msg)
        
        if not results:
            if preview_ids: rs.DeleteObjects(preview_ids)
            for cid in outer_curves:
                if cid and cid != obj_id: rs.DeleteObject(cid)
            break
            
        defaults = results
        
        try:
            params["target_bay_width"] = max(0.1, float(results[0]))
            params["transom_drop"] = max(0.1, float(results[1]))
            params["frame_width"] = max(0.0, float(results[2]))
            params["mullion_width"] = max(0.0, float(results[3]))
        except:
            rs.MessageBox("Invalid input.")
            continue
            
        res = rs.MessageBox("Accept Layout?", 3 | 32)
        
        if res == 6: # Yes
            group = rs.AddGroup("Storefront")
            if preview_ids:
                rs.AddObjectsToGroup(preview_ids, group)
                rs.SelectObjects(preview_ids)
            for cid in outer_curves:
                if cid and cid != obj_id: rs.DeleteObject(cid)
            print("Storefront created.")
            break
        elif res == 2: # Cancel
            if preview_ids: rs.DeleteObjects(preview_ids)
            for cid in outer_curves:
                if cid and cid != obj_id: rs.DeleteObject(cid)
            break

if __name__ == "__main__":
    create_storefront()
