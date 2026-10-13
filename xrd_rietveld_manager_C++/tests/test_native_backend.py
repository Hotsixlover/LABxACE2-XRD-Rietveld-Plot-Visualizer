# SPDX-License-Identifier: GPL-2.0-or-later
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from matplotlib.figure import Figure


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from xrd_rietveld_manager.data_loader import DataLoader
from xrd_rietveld_manager import data_loader, native_backend
from xrd_rietveld_manager import reference_peaks
from xrd_rietveld_manager.plotter import PlotterMixin


class NativeBackendTests(unittest.TestCase):
    def test_backend_status_contract(self):
        status = native_backend.backend_status()
        self.assertIn("available", status)
        self.assertIn("version", status)
        self.assertIn("error", status)

    def test_data_loader_keeps_public_list_and_numpy_interfaces(self):
        contents = "\n".join([
            "TITLE=x STRUC[1]=Fe2O3 STRUC[2]=LiFePO4",
            "10 20 18 2 4 6",
            "11 40 35 3 8 10",
            "12 invalid 1 1 1 1",
            "13 10 9 1 2",
        ])
        handle, path = tempfile.mkstemp(suffix=".dia")
        os.close(handle)
        try:
            Path(path).write_text(contents, encoding="latin1")
            loader = DataLoader(path)
            loader.load_dia()
            self.assertEqual(loader.default_project_color, loader.project_color)
            self.assertEqual(loader.default_styles["Calculated"]["color"], "red")
            original_phase_color = loader.default_styles["Fe2O3"]["color"]
            loader.styles["Fe2O3"]["color"] = "#ffffff"
            self.assertEqual(loader.default_styles["Fe2O3"]["color"], original_phase_color)
            self.assertEqual(loader.phase_names, ["Fe2O3", "LiFePO4"])
            self.assertEqual(loader.x, [10.0, 11.0, 13.0])
            np.testing.assert_allclose(loader.obs_np, [0.5, 1.0, 0.25])
            np.testing.assert_allclose(loader.calc_np, [0.45, 0.875, 0.225])
            np.testing.assert_allclose(loader.diff_np, [0.05, 0.125, 0.025])
            np.testing.assert_allclose(loader.phases_np["Fe2O3"], [0.1, 0.2, 0.05])
            np.testing.assert_allclose(loader.phases_np["LiFePO4"], [0.15, 0.25, 0.0])
            self.assertIsInstance(loader.obs, list)
            self.assertIsInstance(loader.obs_np, np.ndarray)

            original = data_loader.try_load_dia_numeric
            data_loader.try_load_dia_numeric = lambda *args, **kwargs: None
            try:
                fallback = DataLoader(path)
                fallback.load_dia()
            finally:
                data_loader.try_load_dia_numeric = original
            self.assertEqual(loader.x, fallback.x)
            np.testing.assert_allclose(loader.obs_np, fallback.obs_np)
            np.testing.assert_allclose(loader.calc_np, fallback.calc_np)
            np.testing.assert_allclose(loader.back_np, fallback.back_np)
            np.testing.assert_allclose(loader.diff_np, fallback.diff_np)
            for phase_name in loader.phase_names:
                np.testing.assert_allclose(
                    loader.phases_np[phase_name],
                    fallback.phases_np[phase_name],
                )
        finally:
            Path(path).unlink(missing_ok=True)

    def test_local_maximum_equivalence_when_native_is_available(self):
        values = np.array([0.0, 2.0, 1.0, 5.0, 4.0, 7.0, 0.0, 1.0, 0.0])
        native = native_backend.try_local_maxima(values, threshold_fraction=0.05)
        if native is None:
            self.skipTest("native library is not built")
        threshold = np.max(values) * 0.05
        expected = np.where(
            (values[1:-1] > values[:-2])
            & (values[1:-1] > values[2:])
            & (values[1:-1] > threshold)
        )[0] + 1
        np.testing.assert_array_equal(native, expected)

    def test_reference_pattern_equivalence_when_native_is_available(self):
        structure = {
            "cell": {
                "a": 4.0,
                "b": 4.0,
                "c": 4.0,
                "alpha": 90.0,
                "beta": 90.0,
                "gamma": 90.0,
            },
            "atoms": [{
                "element": "Fe",
                "species": "Fe",
                "x": 0.0,
                "y": 0.0,
                "z": 0.0,
                "occ": 1.0,
                "b_iso": 0.0,
            }],
        }
        if native_backend._get_library() is None:
            self.skipTest("native library is not built")
        native = native_backend.try_calculate_reference_pattern(
            structure,
            reference_peaks._rietan_form_factor_table(),
            reference_peaks.ATOMIC_Z,
            wavelength=1.5406,
            include_kalpha2=True,
        )
        if native is None:
            self.skipTest("native library is not built")

        calculator = object.__new__(reference_peaks.ReferencePeaksMixin)
        calculator.reference_kalpha2 = True
        original = reference_peaks.try_calculate_reference_pattern
        reference_peaks.try_calculate_reference_pattern = lambda *args, **kwargs: None
        try:
            expected = calculator._calculate_reference_pattern(structure, wavelength=1.5406)
        finally:
            reference_peaks.try_calculate_reference_pattern = original

        self.assertEqual(len(native), len(expected))
        np.testing.assert_allclose(
            [item[0] for item in native],
            [item[0] for item in expected],
            rtol=1e-11,
            atol=1e-10,
        )
        np.testing.assert_allclose(
            [item[1] for item in native],
            [item[1] for item in expected],
            rtol=1e-10,
            atol=1e-9,
        )
        self.assertEqual([item[2] for item in native], [item[2] for item in expected])

    def test_layer_offset_preview_moves_existing_artists(self):
        class CanvasStub:
            def __init__(self):
                self.draw_idle_calls = 0

            def draw_idle(self):
                self.draw_idle_calls += 1

        plotter = object.__new__(PlotterMixin)
        plotter._layer_offset_artists = {}
        plotter.canvas = CanvasStub()
        loader = SimpleNamespace(offsets={"Observed": 1.0})
        figure = Figure()
        axes = figure.add_subplot(111)
        x_values = np.array([0.0, 1.0, 2.0])
        y_values = np.array([2.0, 3.0, 4.0])
        line, = axes.plot(x_values, y_values)
        scatter = axes.scatter(x_values, y_values)
        fill = axes.fill_between(x_values, 1.0, y_values)
        label = axes.text(2.0, 4.0, "Observed")
        fill_before = [path.vertices.copy() for path in fill.get_paths()]

        plotter._register_layer_offset_artist(loader, "Observed", "line", line)
        plotter._register_layer_offset_artist(loader, "Observed", "scatter", scatter)
        plotter._register_layer_offset_artist(loader, "Observed", "fill", fill)
        plotter._register_layer_offset_artist(loader, "Observed", "text", label)

        self.assertTrue(plotter._preview_layer_offset(loader, "Observed", 1.75))
        np.testing.assert_allclose(line.get_ydata(), y_values + 0.75)
        np.testing.assert_allclose(scatter.get_offsets()[:, 1], y_values + 0.75)
        for path, original in zip(fill.get_paths(), fill_before):
            np.testing.assert_allclose(path.vertices[:, 1], original[:, 1] + 0.75)
        self.assertEqual(label.get_position(), (2.0, 4.75))
        self.assertEqual(plotter.canvas.draw_idle_calls, 1)


if __name__ == "__main__":
    unittest.main()
