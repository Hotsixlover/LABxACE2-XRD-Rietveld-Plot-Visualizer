# SPDX-License-Identifier: GPL-2.0-or-later
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from xrd_rietveld_manager.data_loader import DataLoader
from xrd_rietveld_manager.profile_parsers import ProfileParseError
from xrd_rietveld_manager.layers_manager import LayersManagerMixin
from xrd_rietveld_manager.figure_set_manager import FigureSetManagerMixin

FIXTURES = ROOT / "tests" / "fixtures"


class ProfileParserTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def load_text(self, contents, suffix=".csv"):
        path = Path(self.tmp.name) / ("profile_\uc2dc\ud5d8" + suffix)
        path.write_text(contents, encoding="utf-8-sig")
        return DataLoader(str(path)).load()

    def fixture(self, name):
        return (FIXTURES / name).read_text(encoding="utf-8")

    def test_all_four_formats_produce_equivalent_curves(self):
        for name in ("profex_profile.dia", "gsas_ii_profile.csv", "gsas_liveplot.csv", "fullprof_profile.prf"):
            with self.subTest(name=name):
                loader = DataLoader(str(FIXTURES / name)).load()
                self.assertEqual(loader.x, [10, 11, 12])
                np.testing.assert_allclose(loader.obs_np, [.5, 1, .25])
                np.testing.assert_allclose(loader.calc_np, [.45, .875, .225])
                np.testing.assert_allclose(loader.back_np, [.05, .075, .025])
                np.testing.assert_allclose(loader.diff_np, [.05, .125, .025])
                self.assertEqual(loader.x_unit, "2theta")
                self.assertTrue(loader.source_format)

    def test_gsas_header_mapping_not_weight_or_position(self):
        loader = self.load_text('x,y_bkg,y_calc,weight,y_obs,Q\n10,2,18,999,20,1\n11,3,35,888,40,2')
        np.testing.assert_allclose(loader.calc, [.45, .875])
        np.testing.assert_allclose(loader.back, [.05, .075])

    def test_fortran_exponents_bom_and_unicode_path(self):
        loader = self.load_text('2Theta,I(obs),I(calc),I(bkg)\n10,2D1,1.8D1,2\n11,4D1,3.5D1,3')
        np.testing.assert_allclose(loader.obs, [.5, 1])

    def test_missing_background_is_not_fabricated(self):
        loader = self.load_text('x,y_obs,y_calc\n10,20,18\n11,40,35')
        self.assertEqual(loader.back, [])
        self.assertFalse(loader.visibility["Background"])
        loader.visibility["Background"] = True  # a saved template cannot re-add a missing layer
        order = LayersManagerMixin._get_loader_layer_order(None, loader)
        self.assertNotIn("Background", order)
        self.assertEqual(loader.phase_names, [])

    def test_fullprof_without_background_does_not_use_bragg_as_background(self):
        loader = self.load_text('Title\n1 2 1.54 1.54\n2Theta Yobs Ycal Yobs-Ycal Bragg Posr (hkl)\n10 20 18 -98 30 -100 (1 0 0)\n11 40 35 -95 35 -100 (1 1 0)\n', '.prf')
        self.assertEqual(loader.back, [])
        np.testing.assert_allclose(loader.diff, [.05, .125])

    def test_fullprof_declared_count_separates_numeric_reflections(self):
        text = self.fixture("fullprof_profile.prf") + '\n50 1 2 3 4\n'
        loader = self.load_text(text, '.prf')
        self.assertEqual(len(loader.x), 3)
        self.assertEqual(loader.source_metadata["declared_points"], 3)

    def test_fullprof_truncated_points_fail(self):
        text = self.fixture("fullprof_profile.prf").replace('1 3 1.5406', '1 5 1.5406')
        with self.assertRaises(ProfileParseError):
            self.load_text(text, '.prf')

    def test_fullprof_invalid_numeric_row_fails_without_skipping(self):
        text = self.fixture("fullprof_profile.prf").replace('11 40 35', '11 BAD 35')
        with self.assertRaisesRegex(ProfileParseError, "line"):
            self.load_text(text, '.prf')

    def test_nonangular_axes_rejected(self):
        cases = [(self.fixture('gsas_ii_profile.csv').replace('"PXC"', '"PNT"'), '.csv'),
                 (self.fixture('fullprof_profile.prf').replace('2Theta', 'T.O.F.'), '.prf'),
                 (self.fixture('gsas_liveplot.csv').replace('label 2-Theta', 'label Q'), '.csv'),
                 ('Q,y_obs,y_calc\n1,20,18\n2,40,35', '.csv')]
        for text, suffix in cases:
            with self.subTest(suffix=suffix, header=text[:70]), self.assertRaises(ProfileParseError):
                self.load_text(text, suffix)

    def test_liveplot_transformed_intensity_rejected(self):
        for label in ('log(Intensity)', 'Intensity/sigma(I)', 'sqrt(Intensity)'):
            with self.subTest(label=label), self.assertRaises(ProfileParseError):
                self.load_text(self.fixture('gsas_liveplot.csv').replace('y axis label Intensity', 'y axis label '+label))

    def test_liveplot_empty_background_and_reflection_tail(self):
        text = self.fixture('gsas_liveplot.csv')
        for old in (', 18, 2,', ', 35, 3,', ', 9, 1,'):
            text = text.replace(old, old.rsplit(',', 2)[0] + ', ,')
        loader = self.load_text(text)
        self.assertEqual(loader.back, [])
        self.assertEqual(len(loader.x), 3)

    def test_invalid_csv_not_silently_skipped(self):
        for row in ('11,BAD,35,3', '11,nan,35,3', '11,40,inf,3', '11,40', '10,40,35,3'):
            with self.subTest(row=row), self.assertRaises(ProfileParseError):
                self.load_text('x,y_obs,y_calc,y_bkg\n10,20,18,2\n'+row)

    def test_stacked_csv_has_actionable_error(self):
        with self.assertRaisesRegex(ProfileParseError, 'histogram CSV'):
            self.load_text('x,y_obs_A,y_obs_B\n10,20,18\n11,40,35')

    def test_project_or_unknown_format_fails(self):
        for suffix in ('.gpx', '.pcr', '.exp'):
            with self.subTest(suffix=suffix), self.assertRaises(ProfileParseError):
                self.load_text('not a profile', suffix)

    def test_descending_profile_reverses_all_columns(self):
        loader = self.load_text('x,y_obs,y_calc,y_bkg\n11,40,35,3\n10,20,18,2')
        self.assertEqual(loader.x, [10, 11])
        np.testing.assert_allclose(loader.obs, [.5, 1])
        np.testing.assert_allclose(loader.back, [.05, .075])

    def test_failed_reload_keeps_previous_valid_data(self):
        loader = self.load_text(self.fixture('gsas_ii_profile.csv'))
        before = loader.obs_np.copy()
        Path(loader.filepath).write_text('not a profile', encoding='utf-8')
        with self.assertRaises(ProfileParseError):
            loader.load()
        np.testing.assert_array_equal(loader.obs_np, before)

    def test_figureset_source_reloading_accepts_new_formats(self):
        app = SimpleNamespace(loaded_files={})
        for name in ('gsas_ii_profile.csv', 'gsas_liveplot.csv', 'fullprof_profile.prf'):
            path = str(FIXTURES / name)
            self.assertTrue(FigureSetManagerMixin._ensure_figure_set_source_loaded(app, path))
            self.assertEqual(len(app.loaded_files[path].x), 3)
            self.assertFalse(FigureSetManagerMixin._ensure_figure_set_source_loaded(app, path))


if __name__ == '__main__':
    unittest.main()
