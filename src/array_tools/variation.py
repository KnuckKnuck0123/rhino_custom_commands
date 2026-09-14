"""Rhino-independent deterministic variation and falloff mathematics."""
import math
import random

DEFAULTS = {
    'mode': 'Grid', 'count_x': 5, 'count_y': 5, 'count_z': 3,
    'spacing_x': 10.0, 'spacing_y': 10.0, 'spacing_z': 10.0,
    'volume_mode': 'Exterior', 'orient': True, 'variation': 'None',
    'shift_start': (0., 0., 0.), 'shift_end': (0., 0., 0.),
    'rotate_start': (0., 0., 0.), 'rotate_end': (0., 0., 0.),
    'scale_start': (1., 1., 1.), 'scale_end': (1., 1., 1.),
    'uniform_scale': True, 'seed': 1, 'progression': 'X', 'falloff_enabled': False,
    'falloff_center': (0., 0., 0.), 'falloff_radius': 50.,
    'falloff_strength': 1., 'falloff_softness': 1.,
}
MAX_CANDIDATES = 5000


def validated(settings):
    result = dict(DEFAULTS)
    result.update(settings)
    for key, choices in [('mode', ('Linear', 'Grid', 'Curve', 'Surface', 'Volume')),
                         ('volume_mode', ('Exterior', 'Interior')),
                         ('variation', ('None', 'Random', 'Gradual')),
                         ('progression', ('X', 'Y', 'Z'))]:
        if result[key] not in choices:
            raise ValueError('Invalid {}: {}'.format(key, result[key]))
    for axis in 'xyz':
        key = 'count_' + axis
        count = int(result[key])
        if count != float(result[key]) or not 1 <= count <= MAX_CANDIDATES:
            raise ValueError('Counts must be integers from 1 to {}.'.format(MAX_CANDIDATES))
        result[key] = count
        key = 'spacing_' + axis
        result[key] = float(result[key])
        if not math.isfinite(result[key]) or result[key] <= 0:
            raise ValueError('Spacing must be finite and positive.')
    for key in ('shift_start', 'shift_end', 'rotate_start', 'rotate_end',
                'scale_start', 'scale_end', 'falloff_center'):
        values = tuple(float(v) for v in result[key])
        if len(values) != 3 or not all(math.isfinite(v) for v in values):
            raise ValueError('{} needs three finite numbers.'.format(key))
        if key.startswith('scale') and min(values) <= 0:
            raise ValueError('Scale factors must be positive.')
        result[key] = values
    for key in ('falloff_radius', 'falloff_strength', 'falloff_softness'):
        result[key] = float(result[key])
        if not math.isfinite(result[key]):
            raise ValueError('{} must be finite.'.format(key))
    if result['falloff_radius'] <= 0:
        raise ValueError('Falloff radius must be positive.')
    if not 0 <= result['falloff_strength'] <= 1 or not 0 <= result['falloff_softness'] <= 1:
        raise ValueError('Falloff strength and softness must be between 0 and 1.')
    result['seed'] = int(result['seed'])
    return result


def falloff_weight(point, settings, plane_normal=None):
    if not settings['falloff_enabled']:
        return 1.0
    delta = tuple(a - b for a, b in zip(point, settings['falloff_center']))
    if plane_normal is not None:
        normal_length = math.sqrt(sum(v * v for v in plane_normal))
        normal = tuple(v / normal_length for v in plane_normal)
        height = sum(a * b for a, b in zip(delta, normal))
        delta = tuple(a - height * b for a, b in zip(delta, normal))
    distance = math.sqrt(sum(v * v for v in delta))
    fraction = distance / settings['falloff_radius']
    if fraction >= 1:
        return 0.0
    softness = settings['falloff_softness']
    if softness == 0 or fraction <= 1 - softness:
        return settings['falloff_strength']
    t = (1 - fraction) / softness
    return settings['falloff_strength'] * t * t * (3 - 2 * t)


def values_at(settings, index, progress, point, plane_normal=None):
    """Return (shift xyz, rotation xyz degrees, scale xyz); each seed/index is stable."""
    if settings['variation'] == 'None':
        return (0., 0., 0.), (0., 0., 0.), (1., 1., 1.)
    weight = falloff_weight(point, settings, plane_normal)
    rng = random.Random(settings['seed'] * 1000003 + index * 9176)
    result = []
    for name, identity in [('shift', 0.), ('rotate', 0.), ('scale', 1.)]:
        values = []
        for start, end in zip(settings[name + '_start'], settings[name + '_end']):
            amount = rng.random() if settings['variation'] == 'Random' else max(0., min(1., progress))
            value = start + (end - start) * amount
            values.append(identity + (value - identity) * weight)
        if name == 'scale' and settings['uniform_scale']:
            values = [values[0]] * 3
        result.append(tuple(values))
    return tuple(result)
