# SPDX-License-Identifier: GPL-2.0-or-later
import os
import random

import numpy as np

from xrd_rietveld_manager.chemical_formula import (
    assign_distinct_formula_colors,
    extract_chemical_formula,
    generate_formula_color,
)
from xrd_rietveld_manager.native_backend import try_load_dia_numeric
from xrd_rietveld_manager.profile_parsers import parse_profile

# ========================================================
# 1. Data Loader
# ========================================================
class DataLoader:
    def __init__(self, filepath=None):
        self.filepath = filepath
        self.filename = os.path.basename(filepath) if filepath else "Untitled"
        self.project_color = self._random_vivid_color()
        self.default_project_color = self.project_color
        self.global_visible = True 
        
        # Layer control state
        self.is_expanded = True
        
        self.x = []       
        self.obs = []     
        self.calc = []    
        self.back = []    
        self.diff = []    
        self.phases = {} 
        self.x_np = np.array([], dtype=float)
        self.obs_np = np.array([], dtype=float)
        self.calc_np = np.array([], dtype=float)
        self.back_np = np.array([], dtype=float)
        self.diff_np = np.array([], dtype=float)
        self.phases_np = {}
        self.phase_names = []
        self.layer_order = []
        self.phase_auto_stack_order = []
        # Automatic Split-layout positions are kept separately so the layer
        # sliders can apply a manual delta without disabling auto stacking.
        self.phase_auto_stack_offsets = {}
        
        self.depth_3d_main = None
        self.depth_3d_phases = {}
        
        # Per-sample visibility state
        self.visibility = {
            "Observed": True, "Calculated": True, 
            "Background": True, "Difference": True
        }
        
        self.offsets = {}
        self.display_names = {}
        # Per-sample style state
        self.styles = {}
        self.default_styles = {}

    def sync_numpy_cache(self):
        """Build array caches once after parsing.

        The UI keeps list fields for compatibility with existing dialogs and
        truth checks, while plotting/stacking can use the cached arrays to avoid
        repeated np.array(...) calls on every redraw.
        """
        self.x_np = np.asarray(self.x, dtype=float)
        self.obs_np = np.asarray(self.obs, dtype=float)
        self.calc_np = np.asarray(self.calc, dtype=float)
        self.back_np = np.asarray(self.back, dtype=float)
        self.diff_np = np.asarray(self.diff, dtype=float)
        self.phases_np = {name: np.asarray(values, dtype=float) for name, values in self.phases.items()}

    def array_for(self, key, fallback=None):
        if key == "Observed":
            return self.obs_np
        if key == "Calculated":
            return self.calc_np
        if key == "Background":
            return self.back_np
        if key == "Difference":
            return self.diff_np
        if key in self.phases_np:
            return self.phases_np[key]
        if fallback is None:
            return np.array([], dtype=float)
        return np.asarray(fallback, dtype=float)
        
    def _random_vivid_color(self):
        colors = [
            '#E6194B', '#3CB44B', '#FFE119', '#4363D8', '#F58231', 
            '#911EB4', '#46F0F0', '#F032E6', '#BCF60C', '#FABEBE', 
            '#008080', '#E6BEFF', '#9A6324', '#FFFAC8', '#800000'
        ]
        return random.choice(colors)

    def _get_default_style(self, key, color=None):
        base = {"mode": "line", "marker": "o", "size": 3, "linewidth": 1.0, "color": "black", "linestyle": "-"}
        if color: base["color"] = color
        if key == "Observed":
            base["mode"] = "symbol"
            # Raw/observed DIA points start in black in the source program.
            base["color"] = "black"
            base["observed_custom_color"] = False
        elif key == "Calculated":
            base["color"] = "red"
        elif key == "Background":
            base["color"] = "green"
            base["linestyle"] = "--"
        elif key == "Difference":
            base["color"] = "gray"
        return base
        
    def load(self, format_hint=None):
        """Parse and validate completely before replacing the loader state."""
        if not self.filepath:
            raise ValueError("No profile file selected.")
        profile = parse_profile(self.filepath, native_reader=try_load_dia_numeric,
                                format_hint=format_hint)
        x, arrays = profile.normalized()
        self.source_format = profile.source_format
        self.source_metadata = dict(profile.metadata)
        self.x_unit = "2theta"
        self.x = x.tolist()
        self.obs = arrays["Observed"].tolist()
        self.calc = arrays["Calculated"].tolist()
        self.back = arrays["Background"].tolist()
        self.diff = arrays["Difference"].tolist()
        self.phase_names = list(profile.phases)
        self.phases = {name: arrays[name].tolist() for name in self.phase_names}
        self.available_layers = {key for key, values in arrays.items() if values.size}
        self.visibility = {key: key in self.available_layers
                           for key in ["Observed", "Calculated", "Background", "Difference"]}
        self.offsets = {}
        self.styles = {}
        self.display_names = {}
        self.depth_3d_phases = {}
        self.layer_order = []
        self.phase_auto_stack_order = []
        self.phase_auto_stack_offsets = {}
        for name in self.phase_names:
            self.visibility[name] = True
            self.offsets[name] = 0.0
            self.display_names[name] = extract_chemical_formula(name)
            self.depth_3d_phases[name] = None
        self.x_min, self.x_max = min(self.x), max(self.x)

        self.offsets["Observed"] = 0.0
        self.offsets["Calculated"] = 0.0
        self.offsets["Background"] = 0.0
        self.offsets["Difference"] = 0.0

        self.display_names["Observed"] = self.filename 
        self.display_names["Calculated"] = "Calculated"
        self.display_names["Background"] = "Background"
        self.display_names["Difference"] = "Difference"
        
        self.styles["Observed"] = self._get_default_style("Observed")
        self.styles["Calculated"] = self._get_default_style("Calculated")
        self.styles["Background"] = self._get_default_style("Background")
        self.styles["Difference"] = self._get_default_style("Difference")
        
        phase_formulas = [
            self.display_names.get(phase_name, phase_name)
            for phase_name in self.phase_names
        ]
        distinct_phase_colors = assign_distinct_formula_colors(
            phase_formulas
        )
        for phase_name in self.phase_names:
            phase_formula = self.display_names.get(
                phase_name,
                phase_name,
            )
            auto_phase_color = distinct_phase_colors.get(
                phase_formula
            )
            if auto_phase_color is None:
                auto_phase_color = generate_formula_color(
                    phase_formula
                )
            self.styles[phase_name] = self._get_default_style(
                phase_name,
                auto_phase_color,
            )

        # Keep immutable reset targets separate from the live styles.
        # Templates, palettes, and Color Setting can freely modify
        # ``styles`` without losing the colors assigned at file load.
        self.default_styles = {
            key: dict(style) for key, style in self.styles.items()
        }

        self.sync_numpy_cache()
        return self

    def load_dia(self):
        """Compatibility entry point for existing DIA callers."""
        return self.load(format_hint="dia")
