# SPDX-License-Identifier: GPL-2.0-or-later
import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from xrd_rietveld_manager.plotter import PlotterMixin
from xrd_rietveld_manager import reference_peaks


class PhaseReferencePeakTests(unittest.TestCase):
    def setUp(self):
        self.plotter = object.__new__(PlotterMixin)
        self.plotter.phase_name_overrides = {}

    def test_form_factors_are_loaded_from_xraydb_cache(self):
        class FakeXrayDB:
            def get_cache(self, name):
                self.requested_table = name
                return [SimpleNamespace(
                    ion="Fe",
                    scale=json.dumps([1, 2, 3, 4, 5]),
                    exponents=json.dumps([0.1, 0.2, 0.3, 0.4, 0.5]),
                    offset=6,
                )]

        fake_db = FakeXrayDB()
        fake_module = SimpleNamespace(get_xraydb=lambda: fake_db)
        original = reference_peaks._RIETAN_FORM_FACTORS
        reference_peaks._RIETAN_FORM_FACTORS = None
        sys.modules["xraydb"] = fake_module
        try:
            factors = reference_peaks._rietan_form_factor_table()
        finally:
            sys.modules.pop("xraydb", None)
            reference_peaks._RIETAN_FORM_FACTORS = original

        self.assertEqual(fake_db.requested_table, "Waasmaier")
        self.assertEqual(factors["Fe"], {
            "a": (1, 2, 3, 4, 5),
            "c": 6.0,
            "b": (0.1, 0.2, 0.3, 0.4, 0.5),
        })

    def test_phase_matches_reference_formula(self):
        self.plotter.reference_peaks = [
            {
                "label": "Li Fe P O4",
                "visible": True,
                "peaks": [(20.0, 100.0, (1, 0, 0))],
                "structure": {"formula": "Li Fe P O4"},
                "path": "C:/references/LiFePO4-Pnma.cif",
            }
        ]
        loader = SimpleNamespace(
            phase_names=["database_phase"],
            display_names={"database_phase": "LiFePO4"},
        )

        matched = self.plotter._reference_for_phase("database_phase", [loader])

        self.assertIs(matched, self.plotter.reference_peaks[0])

    def test_reduced_phase_formula_matches_reference_supercell_formula(self):
        self.plotter.reference_peaks = [
            {
                "label": "Fe2 Na4 O14 P4",
                "visible": True,
                "peaks": [(30.0, 100.0, (1, 1, 1))],
                "structure": {"formula": "Fe2 Na4 O14 P4"},
                "path": "C:/references/Na2FeP2O7-4001802-2014.cif",
            }
        ]
        loader = SimpleNamespace(
            phase_names=["database_phase"],
            display_names={"database_phase": "Na2FeP2O7"},
        )

        matched = self.plotter._reference_for_phase("database_phase", [loader])

        self.assertIs(matched, self.plotter.reference_peaks[0])

    def test_hidden_reference_is_not_used(self):
        self.plotter.reference_peaks = [
            {
                "label": "Fe2O3",
                "visible": False,
                "peaks": [(33.0, 100.0, (1, 0, 4))],
            }
        ]
        loader = SimpleNamespace(
            phase_names=["Fe2O3"],
            display_names={"Fe2O3": "Fe2O3"},
        )

        self.assertIsNone(self.plotter._reference_for_phase("Fe2O3", [loader]))

    def test_only_main_in_range_reference_peaks_are_returned(self):
        reference = {
            "peaks": [
                (9.0, 100.0, (1, 0, 0)),
                (20.0, 4.9, (0, 1, 0)),
                (30.0, 5.0, (0, 0, 1)),
                (40.0, 70.0, (1, 1, 0)),
                (61.0, 80.0, (1, 0, 1)),
            ]
        }

        positions = self.plotter._main_reference_peak_positions(
            reference, 10.0, 60.0
        )

        self.assertEqual(positions, [30.0, 40.0])


if __name__ == "__main__":
    unittest.main()
