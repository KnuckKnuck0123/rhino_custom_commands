import rhinoscriptsyntax as rs
import Rhino
import Rhino.Geometry as rg
import scriptcontext as sc
import random
import math

# ============================================================
# SUBDIVISION ALGORITHMS
# Each returns {'cuts': [((u0,v0),(u1,v1)),...], 'panels': [(u0,u1,v0,v1),...]}
# ============================================================

def mondrian_subdivide(u_dom, v_dom, max_depth, min_ratio, split_min, split_max):
    """Recursive Mondrian-style subdivision."""
    cuts = []
    panels = []
    u_total = u_dom[1] - u_dom[0]
    v_total = v_dom[1] - v_dom[0]

    def recurse(u0, u1, v0, v1, depth):
        u_frac = (u1 - u0) / u_total if u_total > 0 else 0
        v_frac = (v1 - v0) / v_total if v_total > 0 else 0

        if depth >= max_depth or (u_frac < min_ratio and v_frac < min_ratio):
            panels.append((u0, u1, v0, v1))
            return
        if depth > 1 and random.random() < 0.12 * depth:
            panels.append((u0, u1, v0, v1))
            return

        can_u = u_frac >= min_ratio * 2
        can_v = v_frac >= min_ratio * 2
        if not can_u and not can_v:
            panels.append((u0, u1, v0, v1))
            return

        if can_u and can_v:
            d = random.choice(['u', 'v'])
        elif can_u:
            d = 'u'
        else:
            d = 'v'

        r = random.uniform(split_min, split_max)
        if d == 'u':
            s = u0 + r * (u1 - u0)
            cuts.append(((s, v0), (s, v1)))
            recurse(u0, s, v0, v1, depth + 1)
            recurse(s, u1, v0, v1, depth + 1)
        else:
            s = v0 + r * (v1 - v0)
            cuts.append(((u0, s), (u1, s)))
            recurse(u0, u1, v0, s, depth + 1)
            recurse(u0, u1, s, v1, depth + 1)

    recurse(u_dom[0], u_dom[1], v_dom[0], v_dom[1], 0)
    return {'cuts': cuts, 'panels': panels}


def attractor_grid_subdivide(u_dom, v_dom, attractor_uv, u_count, v_count, contrast):
    """Non-uniform grid that densifies near an attractor point."""

    def generate_spacing(dom, count, attr_p, c):
        d_min, d_max = dom
        d_range = d_max - d_min
        if d_range < 1e-12:
            return [d_min, d_max]

        n = 500
        density = []
        for i in range(n):
            t = d_min + d_range * i / (n - 1)
            dist = abs(t - attr_p) / d_range
            # Clamp density to avoid extreme spikes
            raw = 1.0 + c * (1.0 / (dist + 0.1) - 1.0)
            density.append(max(0.2, min(raw, 50.0)))

        cdf = [0.0]
        for i in range(1, n):
            cdf.append(cdf[-1] + density[i] * d_range / (n - 1))
        total = cdf[-1]
        if total < 1e-12:
            # Fallback to uniform
            return [d_min + d_range * k / float(count) for k in range(count + 1)]
        cdf = [x / total for x in cdf]

        vals = [d_min]
        for k in range(1, count):
            target = k / float(count)
            lo, hi = 0, n - 1
            while lo < hi:
                mid = (lo + hi) // 2
                if cdf[mid] < target:
                    lo = mid + 1
                else:
                    hi = mid
            vals.append(d_min + d_range * lo / (n - 1))
        vals.append(d_max)
        return vals

    u_vals = generate_spacing(u_dom, u_count, attractor_uv[0], contrast)
    v_vals = generate_spacing(v_dom, v_count, attractor_uv[1], contrast)

    cuts = []
    for u in u_vals[1:-1]:
        cuts.append(((u, v_dom[0]), (u, v_dom[1])))
    for v in v_vals[1:-1]:
        cuts.append(((u_dom[0], v), (u_dom[1], v)))

    panels = []
    for i in range(len(u_vals) - 1):
        for j in range(len(v_vals) - 1):
            panels.append((u_vals[i], u_vals[i + 1], v_vals[j], v_vals[j + 1]))

    return {'cuts': cuts, 'panels': panels}


def staggered_strips_subdivide(u_dom, v_dom, num_strips, min_cross, max_cross, stagger, use_v):
    """Variable-width strips with staggered cross-cuts (brick bond)."""
    cuts = []
    panels = []

    if use_v:
        p_dom, s_dom = v_dom, u_dom
    else:
        p_dom, s_dom = u_dom, v_dom

    p_range = p_dom[1] - p_dom[0]
    s_range = s_dom[1] - s_dom[0]

    weights = [random.uniform(0.6, 1.4) for _ in range(num_strips)]
    total_w = sum(weights)
    edges = [p_dom[0]]
    for w in weights[:-1]:
        edges.append(edges[-1] + (w / total_w) * p_range)
    edges.append(p_dom[1])

    for p in edges[1:-1]:
        if use_v:
            cuts.append(((s_dom[0], p), (s_dom[1], p)))
        else:
            cuts.append(((p, s_dom[0]), (p, s_dom[1])))

    for si in range(num_strips):
        n_cross = random.randint(min_cross, max_cross)
        positions = sorted([random.uniform(s_dom[0] + 0.04 * s_range,
                                           s_dom[1] - 0.04 * s_range) for _ in range(n_cross)])

        if si % 2 == 1 and stagger > 0 and n_cross > 0:
            avg_sp = s_range / (n_cross + 1)
            offset = stagger * avg_sp
            positions = [p + offset for p in positions]
            positions = [p for p in positions
                         if s_dom[0] + 0.02 * s_range < p < s_dom[1] - 0.02 * s_range]

        p0 = edges[si]
        p1 = edges[si + 1]

        for s in positions:
            if use_v:
                cuts.append(((s, p0), (s, p1)))
            else:
                cuts.append(((p0, s), (p1, s)))

        all_s = [s_dom[0]] + sorted(positions) + [s_dom[1]]
        for k in range(len(all_s) - 1):
            if use_v:
                panels.append((all_s[k], all_s[k + 1], p0, p1))
            else:
                panels.append((p0, p1, all_s[k], all_s[k + 1]))

    return {'cuts': cuts, 'panels': panels}


def quadtree_subdivide(u_dom, v_dom, max_depth, probability, attractor_uv=None):
    """Quadtree with optional attractor-biased subdivision probability."""
    cuts = []
    panels = []
    u_range = u_dom[1] - u_dom[0]
    v_range = v_dom[1] - v_dom[0]

    def recurse(u0, u1, v0, v1, depth):
        if depth >= max_depth:
            panels.append((u0, u1, v0, v1))
            return

        p = probability
        if attractor_uv:
            cu = (u0 + u1) / 2.0
            cv = (v0 + v1) / 2.0
            dist = math.sqrt(((cu - attractor_uv[0]) / max(u_range, 1e-12)) ** 2 +
                             ((cv - attractor_uv[1]) / max(v_range, 1e-12)) ** 2)
            p = min(1.0, probability * (1.5 / (dist + 0.3)))

        if depth > 0 and random.random() > p:
            panels.append((u0, u1, v0, v1))
            return

        mu = (u0 + u1) / 2.0
        mv = (v0 + v1) / 2.0
        cuts.append(((mu, v0), (mu, v1)))
        cuts.append(((u0, mv), (u1, mv)))

        recurse(u0, mu, v0, mv, depth + 1)
        recurse(mu, u1, v0, mv, depth + 1)
        recurse(u0, mu, mv, v1, depth + 1)
        recurse(mu, u1, mv, v1, depth + 1)

    recurse(u_dom[0], u_dom[1], v_dom[0], v_dom[1], 0)
    return {'cuts': cuts, 'panels': panels}


def fracture_subdivide(u_dom, v_dom, num_lines, angle_min, angle_max):
    """Random fracture lines across the UV domain (cracked glass)."""
    cuts = []
    u_range = u_dom[1] - u_dom[0]
    v_range = v_dom[1] - v_dom[0]

    for _ in range(num_lines):
        angle = random.uniform(angle_min, angle_max)
        rad = math.radians(angle)
        du = math.cos(rad)
        dv = math.sin(rad)
        ou = random.uniform(u_dom[0], u_dom[1])
        ov = random.uniform(v_dom[0], v_dom[1])

        t_cands = []
        if abs(du) > 1e-10:
            t_cands.append((u_dom[0] - ou) / du)
            t_cands.append((u_dom[1] - ou) / du)
        if abs(dv) > 1e-10:
            t_cands.append((v_dom[0] - ov) / dv)
            t_cands.append((v_dom[1] - ov) / dv)

        eps = 1e-6 * max(u_range, v_range)
        valid = []
        for t in t_cands:
            u_t = ou + t * du
            v_t = ov + t * dv
            if (u_dom[0] - eps <= u_t <= u_dom[1] + eps and
                    v_dom[0] - eps <= v_t <= v_dom[1] + eps):
                valid.append(t)

        if len(valid) >= 2:
            valid.sort()
            start = (max(u_dom[0], min(u_dom[1], ou + valid[0] * du)),
                     max(v_dom[0], min(v_dom[1], ov + valid[0] * dv)))
            end = (max(u_dom[0], min(u_dom[1], ou + valid[-1] * du)),
                   max(v_dom[0], min(v_dom[1], ov + valid[-1] * dv)))
            cuts.append((start, end))

    return {'cuts': cuts, 'panels': []}


# ============================================================
# GEOMETRY HELPERS
# ============================================================

def uv_to_curve(surface, uv0, uv1, samples=20):
    """Map a UV line segment to a 3D interpolated curve on the surface."""
    pts = []
    for i in range(samples + 1):
        t = i / float(samples)
        u = uv0[0] + t * (uv1[0] - uv0[0])
        v = uv0[1] + t * (uv1[1] - uv0[1])
        pt = surface.PointAt(u, v)
        if pt and pt.IsValid:
            pts.append(pt)
    if len(pts) < 2:
        return None
    crv = rg.Curve.CreateInterpolatedCurve(pts, 3)
    return crv


def panel_outline(surface, u0, u1, v0, v1, samples=8):
    """Create a closed curve for a UV rectangle on the surface."""
    edges = [
        uv_to_curve(surface, (u0, v0), (u1, v0), samples),
        uv_to_curve(surface, (u1, v0), (u1, v1), samples),
        uv_to_curve(surface, (u1, v1), (u0, v1), samples),
        uv_to_curve(surface, (u0, v1), (u0, v0), samples),
    ]
    valid = [e for e in edges if e is not None]
    if len(valid) >= 3:
        joined = rg.Curve.JoinCurves(valid, sc.doc.ModelAbsoluteTolerance * 10)
        if joined and len(joined) > 0:
            return joined[0]
    return None


def ensure_child_layer(parent_name, child_name, color=None):
    """Create a child layer under a parent. Returns the full layer path."""
    full_path = "{}::{}".format(parent_name, child_name)
    if not rs.IsLayer(full_path):
        # Ensure parent exists first
        if not rs.IsLayer(parent_name):
            rs.AddLayer(parent_name)
        rs.AddLayer(child_name, color, parent=parent_name)
    return full_path


def get_attractor_uv(srf, prompt="Pick attractor point on or near surface"):
    """Robustly pick a 3D point and map it to UV on the surface."""
    pt = rs.GetPoint(prompt)
    if pt is None:
        return None
    pt3d = rg.Point3d(pt.X, pt.Y, pt.Z)
    rc, u, v = srf.ClosestPoint(pt3d)
    if not rc:
        print("Could not map point to surface UV.")
        return None
    return (u, v)


def get_surfaces_from_selection(obj_id):
    """Extract surfaces from a surface or polysurface selection.
    Returns a list of (surface, face_index) tuples.
    face_index is -1 for single surfaces.
    """
    surfaces = []

    if rs.IsPolysurface(obj_id):
        brep = rs.coercebrep(obj_id)
        if brep:
            for i in range(brep.Faces.Count):
                face = brep.Faces[i]
                srf = face.UnderlyingSurface()
                if srf:
                    surfaces.append((srf, i))
            print("Polysurface with {} faces detected.".format(brep.Faces.Count))
    elif rs.IsSurface(obj_id):
        srf = rs.coercesurface(obj_id)
        if srf:
            surfaces.append((srf, -1))
    else:
        # Try as brep (single-face brep)
        brep = rs.coercebrep(obj_id)
        if brep and brep.Faces.Count > 0:
            for i in range(brep.Faces.Count):
                face = brep.Faces[i]
                srf = face.UnderlyingSurface()
                if srf:
                    surfaces.append((srf, i))

    return surfaces


# ============================================================
# MAIN
# ============================================================

def surface_subdivider():
    """Unified surface subdivision tool with 5 methods.
    Supports both surfaces and polysurfaces.
    """

    # --- Select surface or polysurface ---
    obj_id = rs.GetObject("Select surface or polysurface to subdivide",
                          rs.filter.surface | rs.filter.polysurface)
    if not obj_id:
        return False

    surfaces = get_surfaces_from_selection(obj_id)
    if not surfaces:
        print("No valid surfaces found in selection.")
        return False

    print("Processing {} surface(s)...".format(len(surfaces)))

    # --- Choose method ---
    methods = [
        "1 - Mondrian (Recursive)",
        "2 - Attractor Grid",
        "3 - Staggered Strips",
        "4 - Quadtree",
        "5 - Fracture Lines",
    ]
    choice = rs.ListBox(methods, "Choose subdivision method", "Surface Subdivider")
    if not choice:
        return False

    idx = int(choice[0]) - 1

    # --- Collect method-specific parameters ONCE ---
    params = {}

    if idx == 0:  # Mondrian
        params['depth'] = rs.GetInteger("Max recursion depth", 5, 1, 10)
        if params['depth'] is None: return False
        params['min_r'] = rs.GetReal("Min panel ratio", 0.08, 0.02, 0.4)
        if params['min_r'] is None: return False
        params['sp_lo'] = rs.GetReal("Split ratio min", 0.25, 0.1, 0.5)
        if params['sp_lo'] is None: return False
        params['sp_hi'] = rs.GetReal("Split ratio max", 0.75, 0.5, 0.9)
        if params['sp_hi'] is None: return False

    elif idx == 1:  # Attractor Grid
        # Pick attractor as 3D point, will be projected onto each face
        params['attr_pt'] = rs.GetPoint("Pick attractor point on or near surface")
        if params['attr_pt'] is None: return False
        params['u_n'] = rs.GetInteger("U divisions", 10, 2, 50)
        if params['u_n'] is None: return False
        params['v_n'] = rs.GetInteger("V divisions", 10, 2, 50)
        if params['v_n'] is None: return False
        params['ctr'] = rs.GetReal("Contrast (0=uniform, 5=extreme)", 2.0, 0.0, 10.0)
        if params['ctr'] is None: return False

    elif idx == 2:  # Staggered Strips
        params['n_strips'] = rs.GetInteger("Number of strips", 8, 2, 50)
        if params['n_strips'] is None: return False
        params['mn_c'] = rs.GetInteger("Min cross-cuts per strip", 3, 1, 30)
        if params['mn_c'] is None: return False
        params['mx_c'] = rs.GetInteger("Max cross-cuts per strip", 8, params['mn_c'], 50)
        if params['mx_c'] is None: return False
        params['stg'] = rs.GetReal("Stagger (0=aligned, 0.5=brick bond)", 0.5, 0.0, 1.0)
        if params['stg'] is None: return False
        d_choice = rs.ListBox(["U (horizontal strips)", "V (vertical strips)"],
                              "Strip direction", "Direction")
        if not d_choice: return False
        params['use_v'] = d_choice.startswith("V")

    elif idx == 3:  # Quadtree
        params['depth'] = rs.GetInteger("Max depth", 4, 1, 8)
        if params['depth'] is None: return False
        params['prob'] = rs.GetReal("Subdivision probability", 0.7, 0.1, 1.0)
        if params['prob'] is None: return False
        use_attr = rs.GetBoolean("Use attractor?",
                                 ("NoAttractor", "UseAttractor"), (False,))
        params['use_attr'] = use_attr and use_attr[0]
        if params['use_attr']:
            params['attr_pt'] = rs.GetPoint("Pick attractor point on or near surface")
            if params['attr_pt'] is None:
                params['use_attr'] = False

    elif idx == 4:  # Fracture Lines
        params['n_lines'] = rs.GetInteger("Number of fracture lines", 12, 1, 100)
        if params['n_lines'] is None: return False
        params['a_min'] = rs.GetReal("Min angle (degrees)", 0.0, 0.0, 180.0)
        if params['a_min'] is None: return False
        params['a_max'] = rs.GetReal("Max angle (degrees)", 180.0, params['a_min'], 180.0)
        if params['a_max'] is None: return False

    # --- Process each surface ---
    rs.EnableRedraw(False)

    parent = "SurfaceSubdivision"
    if not rs.IsLayer(parent):
        rs.AddLayer(parent)
    cut_layer = ensure_child_layer(parent, "Cuts", rs.CreateColor(255, 80, 80))
    panel_layer = ensure_child_layer(parent, "Panels", rs.CreateColor(80, 180, 255))

    total_cuts = 0
    total_panels = 0

    try:
        for face_idx, (srf, fi) in enumerate(surfaces):
            u_dom = (srf.Domain(0).Min, srf.Domain(0).Max)
            v_dom = (srf.Domain(1).Min, srf.Domain(1).Max)

            face_label = "face {}".format(fi) if fi >= 0 else "surface"
            rs.Prompt("Subdividing {} ({}/{})...".format(face_label, face_idx + 1, len(surfaces)))

            # Run the algorithm for this face
            result = None

            if idx == 0:
                result = mondrian_subdivide(u_dom, v_dom, params['depth'],
                                            params['min_r'], params['sp_lo'], params['sp_hi'])

            elif idx == 1:
                pt = params['attr_pt']
                pt3d = rg.Point3d(pt.X, pt.Y, pt.Z)
                rc, au, av = srf.ClosestPoint(pt3d)
                if not rc:
                    print("Skipping {} - could not map attractor.".format(face_label))
                    continue
                result = attractor_grid_subdivide(u_dom, v_dom, (au, av),
                                                  params['u_n'], params['v_n'], params['ctr'])

            elif idx == 2:
                result = staggered_strips_subdivide(u_dom, v_dom, params['n_strips'],
                                                    params['mn_c'], params['mx_c'],
                                                    params['stg'], params['use_v'])

            elif idx == 3:
                a_uv = None
                if params['use_attr']:
                    pt = params['attr_pt']
                    pt3d = rg.Point3d(pt.X, pt.Y, pt.Z)
                    rc, au, av = srf.ClosestPoint(pt3d)
                    if rc:
                        a_uv = (au, av)
                result = quadtree_subdivide(u_dom, v_dom, params['depth'],
                                            params['prob'], a_uv)

            elif idx == 4:
                result = fracture_subdivide(u_dom, v_dom, params['n_lines'],
                                            params['a_min'], params['a_max'])

            if not result:
                continue

            # Create geometry for this face
            rs.StatusBarProgressMeterShow("Creating geometry",
                                          0, max(len(result['cuts']) + len(result['panels']), 1),
                                          True, True)
            progress = 0

            for uv0, uv1 in result['cuts']:
                crv = uv_to_curve(srf, uv0, uv1)
                if crv:
                    guid = sc.doc.Objects.AddCurve(crv)
                    if guid:
                        rs.ObjectLayer(guid, cut_layer)
                        total_cuts += 1
                progress += 1
                rs.StatusBarProgressMeterUpdate(progress, True)

            for (u0, u1, v0, v1) in result['panels']:
                outline = panel_outline(srf, u0, u1, v0, v1)
                if outline:
                    guid = sc.doc.Objects.AddCurve(outline)
                    if guid:
                        rs.ObjectLayer(guid, panel_layer)
                        total_panels += 1
                progress += 1
                rs.StatusBarProgressMeterUpdate(progress, True)

    except Exception as e:
        print("Error: {}".format(e))
        import traceback
        traceback.print_exc()

    finally:
        rs.StatusBarProgressMeterHide()
        rs.EnableRedraw(True)
        sc.doc.Views.Redraw()
        print("Done! {} cut curves, {} panel outlines across {} face(s).".format(
            total_cuts, total_panels, len(surfaces)))

    return True


if __name__ == "__main__":
    surface_subdivider()
