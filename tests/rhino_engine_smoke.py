#! python 3
"""Run in Rhino 8 ScriptEditor; asserts geometry without changing the document."""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))
import Rhino.Geometry as rg
from array_tools.engine import build_transforms


def run():
    base = rg.Plane.WorldXY
    transforms, points = build_transforms({'mode': 'Grid', 'count_x': 3, 'count_y': 2}, base)
    assert len(transforms) == 6
    moved = rg.Point3d(0, 0, 0)
    moved.Transform(transforms[-1])
    assert moved.DistanceTo(rg.Point3d(20, 10, 0)) < 1e-8
    transforms, _ = build_transforms({'mode': 'Linear', 'count_x': 2, 'variation': 'Gradual',
                                      'scale_end': (2, 2, 2), 'shift_end': (5, 0, 0)}, base)
    moved = rg.Point3d(1, 0, 0)
    moved.Transform(transforms[-1])
    assert moved.DistanceTo(rg.Point3d(17, 0, 0)) < 1e-8
    curve = rg.LineCurve(rg.Point3d(0, 0, 0), rg.Point3d(0, 0, 20))
    transforms, points = build_transforms({'mode': 'Curve', 'count_x': 5}, base, curve)
    assert len(points) == 5 and points[-1].DistanceTo(rg.Point3d(0, 0, 20)) < 1e-8
    x = rg.Vector3d.XAxis
    x.Transform(transforms[0])
    assert x.IsParallelTo(rg.Vector3d.ZAxis) == 1
    surface = rg.NurbsSurface.CreateFromCorners(rg.Point3d(0, 0, 0), rg.Point3d(20, 0, 0),
                                                rg.Point3d(20, 20, 0), rg.Point3d(0, 20, 0))
    _, points = build_transforms({'mode': 'Surface', 'count_x': 3, 'count_y': 4}, base, surface)
    assert len(points) == 12
    brep = rg.Brep.CreateFromBox(rg.BoundingBox(rg.Point3d(0, 0, 0), rg.Point3d(20, 20, 20)))
    _, points = build_transforms({'mode': 'Volume', 'volume_mode': 'Interior',
                                  'count_x': 3, 'count_y': 3, 'count_z': 3}, base, brep)
    assert len(points) == 27 and all(brep.IsPointInside(p, .001, True) for p in points)
    _, points = build_transforms({'mode': 'Volume', 'volume_mode': 'Exterior',
                                  'count_x': 2, 'count_y': 2}, base, brep)
    assert len(points) == 24
    # A global Z progression must be constant on the bottom/top faces,
    # regardless of each face's UV directions.
    transforms, points = build_transforms({'mode': 'Volume', 'volume_mode': 'Exterior',
        'count_x': 2, 'count_y': 2, 'orient': False, 'variation': 'Gradual',
        'progression': 'Z', 'shift_end': (10, 0, 0)}, base, brep)
    for transform, point in zip(transforms, points):
        moved = rg.Point3d(0, 0, 0)
        moved.Transform(transform)
        assert abs(moved.X - point.X - point.Z / 2) < 1e-8
    transforms, _ = build_transforms({'mode': 'Linear', 'count_x': 1,
        'variation': 'Gradual', 'shift_start': (5, 0, 0),
        'falloff_enabled': True, 'falloff_center': (0, 0, 100), 'falloff_radius': 10}, base)
    moved = rg.Point3d(0, 0, 0)
    moved.Transform(transforms[0])
    assert abs(moved.X - 5) < 1e-8
    try:
        build_transforms({'mode': 'Grid', 'count_x': 100, 'count_y': 100}, base)
    except ValueError:
        pass
    else:
        raise AssertionError('Candidate budget was not enforced')
    print('ArrayTools engine: all Rhino geometry smoke checks passed.')


if __name__ == '__main__':
    run()
