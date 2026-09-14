"""Placement and transforms only; never mutates a Rhino document.

build_transforms returns (transforms, nominal placement points). Variation acts in
placement-frame axes, XYZ rotations in that order. Curve frame X follows tangent.
UV counts sample cell centers per face, independently of surface control points.
Interior counts sample the CPlane-aligned bounding box and filter contained points.
"""
import math
import Rhino.Geometry as rg
from .variation import DEFAULTS, MAX_CANDIDATES, validated, values_at


def _budget(count):
    if count > MAX_CANDIDATES:
        raise ValueError('This array requests {} candidate positions; limit is {}. Reduce counts.'.format(count, MAX_CANDIDATES))


def _fraction(index, count):
    return float(index) / (count - 1) if count > 1 else 0.0


def _copy_frame(base, point):
    return rg.Plane(point, base.XAxis, base.YAxis)


def _faces(target):
    if isinstance(target, rg.Brep):
        return list(target.Faces)
    if isinstance(target, rg.Surface):
        return [target]
    raise ValueError('Select a surface or polysurface as the placement target.')


def _placements(s, base, target, tolerance):
    nx, ny, nz = [s['count_' + a] for a in 'xyz']
    direction = 'XYZ'.index(s['progression'])
    mode = s['mode']
    if mode in ('Linear', 'Grid'):
        ny = ny if mode == 'Grid' else 1
        _budget(nx * ny)
        for j in range(ny):
            for i in range(nx):
                point = base.PointAt(i * s['spacing_x'], j * s['spacing_y'])
                progress = _fraction(i, nx) if mode == 'Linear' else (_fraction(i, nx), _fraction(j, ny), 0.)[direction]
                yield _copy_frame(base, point), progress
        return
    if mode == 'Curve':
        if not isinstance(target, rg.Curve) or not target.IsValid or target.GetLength() <= tolerance:
            raise ValueError('Select a valid curve longer than model tolerance.')
        _budget(nx)
        if nx == 1:
            parameters = [target.Domain.T0]
        else:
            parameters = list(target.DivideByCount(nx if target.IsClosed else nx - 1, True) or [])
            if target.IsClosed:
                parameters = parameters[:nx]
        if len(parameters) != nx:
            raise ValueError('Could not divide the selected curve.')
        frames = None
        if s['orient']:
            if nx == 1:
                ok, single = target.PerpendicularFrameAt(parameters[0])
                frames = [single] if ok else None
            else:
                frames = target.GetPerpendicularFrames(parameters)
            if frames is None or len(frames) != nx:
                raise ValueError('Could not calculate stable curve frames. Check the target curve.')
        for i, parameter in enumerate(parameters):
            point = target.PointAt(parameter)
            if frames is not None:
                # Zero-twisting frame normal is tangent; put tangent on local X.
                frame = rg.Plane(point, frames[i].ZAxis, frames[i].XAxis)
            else:
                frame = _copy_frame(base, point)
            yield frame, _fraction(i, nx)
        return
    if mode == 'Surface' or (mode == 'Volume' and s['volume_mode'] == 'Exterior'):
        faces = _faces(target)
        if mode == 'Surface' and len(faces) != 1:
            raise ValueError('Surface mode needs one face; use Volume / Exterior for a polysurface.')
        _budget(nx * ny * len(faces))
        if mode == 'Volume':
            to_local = rg.Transform.PlaneToPlane(base, rg.Plane.WorldXY)
            bounds = target.GetBoundingBox(to_local)
            if not bounds.IsValid:
                raise ValueError('Could not calculate exterior bounds.')
            lower = (bounds.Min.X, bounds.Min.Y, bounds.Min.Z)[direction]
            upper = (bounds.Max.X, bounds.Max.Y, bounds.Max.Z)[direction]
        for face in faces:
            du, dv = face.Domain(0), face.Domain(1)
            for j in range(ny):
                v = dv.ParameterAt((j + .5) / ny)
                for i in range(nx):
                    u = du.ParameterAt((i + .5) / nx)
                    if isinstance(face, rg.BrepFace) and face.IsPointOnFace(u, v) == rg.PointFaceRelation.Exterior:
                        continue
                    ok, frame = face.FrameAt(u, v)
                    if not ok or not frame.IsValid:
                        continue
                    if isinstance(face, rg.BrepFace) and face.OrientationIsReversed:
                        frame = rg.Plane(frame.Origin, frame.XAxis, -frame.YAxis)
                    if not s['orient']:
                        frame = _copy_frame(base, frame.Origin)
                    if mode == 'Volume':
                        local = rg.Point3d(frame.Origin)
                        local.Transform(to_local)
                        coordinate = (local.X, local.Y, local.Z)[direction]
                        progress = (coordinate - lower) / (upper - lower) if upper - lower > tolerance else 0.
                    else:
                        progress = (_fraction(i, nx), _fraction(j, ny), 0.)[direction]
                    yield frame, progress
        return
    if not isinstance(target, rg.Brep) or not target.IsSolid or not target.IsManifold or not target.IsValid:
        raise ValueError('Interior mode requires a valid closed, manifold polysurface.')
    _budget(nx * ny * nz)
    box = target.GetBoundingBox(rg.Transform.PlaneToPlane(base, rg.Plane.WorldXY))
    if not box.IsValid:
        raise ValueError('Could not calculate volume bounds.')
    for k in range(nz):
        z = box.Min.Z + (box.Max.Z - box.Min.Z) * (k + .5) / nz
        for j in range(ny):
            y = box.Min.Y + (box.Max.Y - box.Min.Y) * (j + .5) / ny
            for i in range(nx):
                x = box.Min.X + (box.Max.X - box.Min.X) * (i + .5) / nx
                point = base.PointAt(x, y, z)
                if target.IsPointInside(point, tolerance, True):
                    yield _copy_frame(base, point), (_fraction(i, nx), _fraction(j, ny), _fraction(k, nz))[direction]


def build_transforms(settings, base_plane, target=None, tolerance=0.001):
    """Return (list[Transform], list[Point3d]); sources must use this same base plane.

    Counts limit candidate sampling to 5000 before allocating previews. Interior
    containment applies to copy base points, not each object's entire bounding box.
    Falloff uses nominal world positions, so moving copies cannot alter its field.
    """
    s = validated(settings)
    if not base_plane.IsValid:
        raise ValueError('The source base plane is invalid.')
    if not math.isfinite(tolerance) or tolerance <= 0:
        raise ValueError('Model tolerance must be finite and positive.')
    plan_normal = None
    if s['mode'] in ('Linear', 'Grid'):
        n = base_plane.Normal
        plan_normal = (n.X, n.Y, n.Z)
    transforms, points = [], []
    for index, (frame, progress) in enumerate(_placements(s, base_plane, target, tolerance)):
        p = frame.Origin
        shift, rotate, scale = values_at(s, index, progress, (p.X, p.Y, p.Z), plan_normal)
        transform = rg.Transform.Scale(frame, *scale) * rg.Transform.PlaneToPlane(base_plane, frame)
        for angle, axis in zip(rotate, (frame.XAxis, frame.YAxis, frame.ZAxis)):
            if angle:
                transform = rg.Transform.Rotation(math.radians(angle), axis, p) * transform
        offset = frame.XAxis * shift[0] + frame.YAxis * shift[1] + frame.ZAxis * shift[2]
        transform = rg.Transform.Translation(offset) * transform
        if not transform.IsValid:
            raise ValueError('Variation produced an invalid transformation.')
        transforms.append(transform)
        points.append(p)
    if not transforms:
        raise ValueError('No placement points landed on the target. Increase sampling counts or choose another target.')
    return transforms, points
