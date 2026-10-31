import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

import dataset_generator
import inference

ROOT = Path(__file__).resolve().parents[1]


class ProjectTests(unittest.TestCase):
    def cli(self, script, *args):
        return subprocess.run([sys.executable, str(ROOT / script), *map(str, args)],
                              cwd=ROOT, capture_output=True, text=True, timeout=60)

    def test_invalid_arrays(self):
        rng = np.random.default_rng(0)
        valid = rng.integers(0, 255, (100, 100), dtype=np.uint8)
        for bad in (None, np.empty((0, 0)), np.ones((100, 100, 3)),
                    np.full((100, 100), np.nan), np.zeros((100, 100))):
            with self.subTest(value=type(bad)):
                with self.assertRaises(ValueError):
                    inference.locate(bad, valid)
                with self.assertRaises(ValueError):
                    inference.locate(valid, bad)

    def test_incompatible_sizes(self):
        rng = np.random.default_rng(1)
        with self.assertRaisesRegex(ValueError, 'too small'):
            inference.locate(rng.random((10, 10)), rng.random((100, 100)))
        with self.assertRaisesRegex(ValueError, 'too small'):
            inference.locate(rng.random((1000, 1000)), rng.random((20, 20)))

    def test_cli_errors(self):
        for script, args in [('inference.py', []), ('inference.py', ['missing.png', 'missing2.png']),
                             ('dataset_generator.py', ['--num-pairs', '0']),
                             ('dataset_generator.py', ['--seed', '-1'])]:
            result = self.cli(script, *args)
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn('Traceback', result.stderr)

    def test_empty_or_malformed_dataset(self):
        with tempfile.TemporaryDirectory() as folder:
            csv_path = Path(folder) / 'ground_truth.csv'
            for content in ('reference,search,x_true,y_true\n', 'wrong,columns\n1,2\n',
                            'reference,search,x_true,y_true\nmissing.png,missing.png,1,1\n'):
                csv_path.write_text(content)
                result = self.cli('evaluate.py', folder)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('error:', result.stderr)
                self.assertNotIn('Traceback', result.stderr)

    def test_dram_end_to_end(self):
        with tempfile.TemporaryDirectory() as folder:
            generated = self.cli('dataset_generator.py', '--num-pairs', '1', '--seed', '0', '--out', folder)
            self.assertEqual(generated.returncode, 0, generated.stderr)
            with open(Path(folder) / 'ground_truth.csv') as handle:
                row = next(csv.DictReader(handle))
            reference = Path(folder) / row['reference']
            search = Path(folder) / row['search']
            self.assertEqual(cv2.imread(str(reference), 0).shape, (1000, 1000))
            result = self.cli('inference.py', reference, search)
            self.assertEqual(result.returncode, 0, result.stderr)
            x, y = map(float, result.stdout.strip().splitlines()[-1].split(','))
            self.assertLess(np.hypot(x - float(row['x_true']), y - float(row['y_true'])), 3)
            result = self.cli('evaluate.py', folder)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('pairs evaluated       : 1', result.stdout)
            self.assertTrue((Path(folder) / 'overlays/_SLIDE_success.png').exists())

    def test_finfet_generation(self):
        reference, search, center = dataset_generator.make_pair(style='finfet', seed=2)
        self.assertEqual(reference.shape, (1000, 1000))
        self.assertEqual(search.shape, (1000, 1000))
        self.assertTrue(all(0 <= value < 1000 for value in center))


if __name__ == '__main__':
    unittest.main()
