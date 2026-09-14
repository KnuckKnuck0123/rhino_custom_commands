import importlib.util
import pathlib
import unittest

path = pathlib.Path(__file__).parents[1] / 'src' / 'array_tools' / 'variation.py'
spec = importlib.util.spec_from_file_location('variation', path)
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)


class VariationTests(unittest.TestCase):
    def test_gradual_endpoints(self):
        s = v.validated({'variation': 'Gradual', 'uniform_scale': False, 'shift_end': (10, 20, 30), 'scale_end': (2, 3, 4)})
        self.assertEqual(v.values_at(s, 0, 0, (0, 0, 0)), ((0, 0, 0), (0, 0, 0), (1, 1, 1)))
        self.assertEqual(v.values_at(s, 9, 1, (0, 0, 0))[0], (10, 20, 30))
        self.assertEqual(v.values_at(s, 9, .5, (0, 0, 0))[2], (1.5, 2, 2.5))

    def test_seed_reproducibility_and_bounds(self):
        s = v.validated({'variation': 'Random', 'shift_start': (-4, -3, -2), 'shift_end': (2, 3, 4)})
        a = v.values_at(s, 8, .2, (0, 0, 0))
        self.assertEqual(a, v.values_at(s, 8, .9, (0, 0, 0)))
        self.assertNotEqual(a, v.values_at(s, 9, .2, (0, 0, 0)))
        for low, high, value in zip(s['shift_start'], s['shift_end'], a[0]):
            self.assertLessEqual(low, value)
            self.assertLessEqual(value, high)

    def test_falloff_blends_scale_to_identity(self):
        s = v.validated({'variation': 'Gradual', 'falloff_enabled': True, 'falloff_radius': 10,
                         'scale_end': (3, 3, 3), 'shift_end': (10, 0, 0)})
        self.assertEqual(v.values_at(s, 0, 1, (10, 0, 0))[2], (1, 1, 1))
        self.assertEqual(v.values_at(s, 0, 1, (0, 0, 0))[2], (3, 3, 3))
        self.assertEqual(v.values_at(s, 0, 1, (5, 0, 0))[2], (2, 2, 2))
        self.assertEqual(v.values_at(s, 0, 1, (5, 0, 0))[0], (5, 0, 0))

    def test_hard_falloff_and_strength(self):
        s = v.validated({'falloff_enabled': True, 'falloff_radius': 10,
                         'falloff_softness': 0, 'falloff_strength': .5})
        self.assertEqual(v.falloff_weight((9.9, 0, 0), s), .5)
        self.assertEqual(v.falloff_weight((10, 0, 0), s), 0)

    def test_uniform_random_scale(self):
        s = v.validated({'variation': 'Random', 'scale_start': (.5, .5, .5), 'scale_end': (2, 2, 2)})
        scale = v.values_at(s, 3, .5, (0, 0, 0))[2]
        self.assertEqual(scale[0], scale[1])
        self.assertEqual(scale[1], scale[2])
        s['uniform_scale'] = False
        scale = v.values_at(s, 3, .5, (0, 0, 0))[2]
        self.assertNotEqual(scale[0], scale[1])

    def test_plan_falloff_ignores_cplane_normal(self):
        s = v.validated({'falloff_enabled': True, 'falloff_radius': 10,
                         'falloff_center': (0, 100, 0)})
        # A vertical construction plane with normal Y: center projects to origin.
        self.assertEqual(v.falloff_weight((0, 0, 0), s, (0, 1, 0)), 1)
        self.assertEqual(v.falloff_weight((5, 0, 0), s, (0, 1, 0)), .5)
        self.assertEqual(v.falloff_weight((0, 0, 0), s), 0)

    def test_invalid_values(self):
        for settings in ({'scale_end': (0, 1, 1)}, {'count_x': 1.5}, {'count_x': 5001},
                         {'spacing_x': float('nan')}, {'falloff_radius': 0},
                         {'rotate_end': (0, float('inf'), 0)}):
            with self.assertRaises(ValueError):
                v.validated(settings)


if __name__ == '__main__':
    unittest.main()
