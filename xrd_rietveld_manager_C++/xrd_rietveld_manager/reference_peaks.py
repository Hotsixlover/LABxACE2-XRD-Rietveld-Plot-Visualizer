# SPDX-License-Identifier: GPL-2.0-or-later
from xrd_rietveld_manager.common import *
from pathlib import Path
import cmath
import json
import shlex

from xrd_rietveld_manager.native_backend import try_calculate_reference_pattern


ATOMIC_Z = {
    "H": 1, "Li": 3, "Be": 4, "B": 5, "C": 6, "N": 7, "O": 8, "F": 9,
    "Na": 11, "Mg": 12, "Al": 13, "Si": 14, "P": 15, "S": 16, "Cl": 17,
    "K": 19, "Ca": 20, "Ti": 22, "V": 23, "Cr": 24, "Mn": 25, "Fe": 26,
    "Co": 27, "Ni": 28, "Cu": 29, "Zn": 30, "Ga": 31, "Ge": 32, "As": 33,
    "Se": 34, "Br": 35, "Rb": 37, "Sr": 38, "Y": 39, "Zr": 40, "Nb": 41,
    "Mo": 42, "Ru": 44, "Rh": 45, "Pd": 46, "Ag": 47, "Cd": 48, "In": 49,
    "Sn": 50, "Sb": 51, "Te": 52, "I": 53, "Ba": 56, "La": 57, "Ce": 58,
    "W": 74, "Pt": 78, "Au": 79, "Pb": 82, "Bi": 83,
}

_RIETAN_FORM_FACTORS = None


def _rietan_form_factor_table():
    """Load Waasmaier-Kirfel coefficients from the separately installed XrayDB package."""
    global _RIETAN_FORM_FACTORS
    if _RIETAN_FORM_FACTORS is not None:
        return _RIETAN_FORM_FACTORS

    try:
        from xraydb import get_xraydb

        rows = get_xraydb().get_cache("Waasmaier")
        table = {
            str(row.ion): {
                "a": tuple(float(value) for value in json.loads(row.scale)),
                "c": float(row.offset),
                "b": tuple(float(value) for value in json.loads(row.exponents)),
            }
            for row in rows
        }
    except Exception as exc:
        raise RuntimeError(
            "Reference-peak calculations require the xraydb package. "
            "Install project dependencies with: python -m pip install -r requirements.txt"
        ) from exc

    if not table:
        raise RuntimeError("XrayDB did not provide Waasmaier-Kirfel scattering factors.")
    _RIETAN_FORM_FACTORS = table
    return table
class ReferencePeaksMixin:
    def _init_reference_peaks(self):
        self.reference_cif_dir = Path(__file__).resolve().parent / "CIF file"
        self.reference_peaks = []
        self.reference_peaks_enabled = False
        self.reference_wavelength = 1.5406
        self.reference_kalpha2 = True
        self.reference_panel_height = 0.75
        self.reference_label_size = 8
        self.reference_label_bold = True
        self.reference_label_position = "left"
        self.reference_stick_width = 1.0
        self._reference_palette = ["#4a4a4a"]
        self._load_default_reference_cifs(refresh_ui=False, redraw=False, silent=True)

    def _sync_reference_controls(self):
        if hasattr(self, "var_reference_peaks_enabled"):
            self.reference_peaks_enabled = bool(self.var_reference_peaks_enabled.get())
        if hasattr(self, "var_reference_wavelength"):
            try:
                self.reference_wavelength = max(0.2, min(5.0, float(self.var_reference_wavelength.get())))
            except Exception:
                pass
        if hasattr(self, "var_reference_kalpha2"):
            try:
                self.reference_kalpha2 = bool(self.var_reference_kalpha2.get())
            except Exception:
                pass
        if hasattr(self, "var_reference_panel_height"):
            try:
                self.reference_panel_height = max(0.05, min(3.0, float(self.var_reference_panel_height.get())))
            except Exception:
                pass
        if hasattr(self, "var_reference_label_size"):
            try:
                self.reference_label_size = max(5, min(30, int(float(self.var_reference_label_size.get()))))
            except Exception:
                pass
        if hasattr(self, "var_reference_stick_width"):
            try:
                self.reference_stick_width = max(0.1, min(6.0, float(self.var_reference_stick_width.get())))
            except Exception:
                pass
        if hasattr(self, "var_reference_label_position"):
            try:
                pos = str(self.var_reference_label_position.get()).lower().strip()
                self.reference_label_position = pos if pos in ("left", "right") else "left"
            except Exception:
                pass
        if hasattr(self, "var_reference_label_bold"):
            try:
                self.reference_label_bold = bool(self.var_reference_label_bold.get())
            except Exception:
                pass

    def _visible_reference_peak_count(self):
        return sum(
            1
            for ref in getattr(self, "reference_peaks", [])
            if ref.get("visible", True) and ref.get("peaks")
        )

    def _reference_panel_height_ratio(self):
        # Treat the UI value as a per-reference-row height, then scale by the
        # number of visible references so rows never collapse into each other.
        rows = max(1, self._visible_reference_peak_count())
        row_height = max(0.05, float(getattr(self, "reference_panel_height", 0.75)))
        return min(5.0, row_height * rows)

    def _reference_panel_requested(self):
        self._sync_reference_controls()
        if not bool(getattr(self, "reference_peaks_enabled", False)):
            return False
        return any(ref.get("visible", True) and ref.get("peaks") for ref in getattr(self, "reference_peaks", []))

    def _load_default_reference_cifs(self, refresh_ui=True, redraw=True, silent=False):
        folder = Path(getattr(self, "reference_cif_dir", Path(__file__).resolve().parent / "CIF file"))
        if not folder.exists():
            if not silent:
                messagebox.showinfo("Reference Peaks", f"CIF folder was not found:\n{folder}")
            return
        loaded = 0
        for path in sorted(folder.glob("*.cif")):
            if self._add_reference_cif(path, refresh_ui=False, redraw=False, silent=True):
                loaded += 1
        if refresh_ui:
            self._refresh_reference_peak_list()
        if redraw:
            self._request_draw_plot()
        if loaded == 0 and not silent:
            messagebox.showinfo("Reference Peaks", "No new CIF files were loaded.")

    def add_reference_cif_dialog(self):
        paths = filedialog.askopenfilenames(
            title="Add CIF Reference Peak File(s)",
            filetypes=[("CIF files", "*.cif"), ("All files", "*.*")],
            initialdir=str(getattr(self, "reference_cif_dir", Path.cwd())),
        )
        if not paths:
            return
        for path in paths:
            self._add_reference_cif(path, refresh_ui=False, redraw=False, silent=False)
        self._refresh_reference_peak_list()
        self._request_draw_plot()

    def load_reference_cif_folder_dialog(self):
        folder = filedialog.askdirectory(
            title="Load CIF Reference Folder",
            initialdir=str(getattr(self, "reference_cif_dir", Path.cwd())),
        )
        if not folder:
            return
        self.reference_cif_dir = Path(folder)
        self._load_default_reference_cifs(refresh_ui=True, redraw=True, silent=False)

    def _add_reference_cif(self, path, refresh_ui=True, redraw=True, silent=False):
        path = Path(path)
        if not path.exists():
            return False
        path_key = str(path.resolve()).lower()
        for ref in self.reference_peaks:
            if str(Path(ref.get("path", "")).resolve()).lower() == path_key:
                return False
        try:
            structure = self._parse_cif(path)
            peaks = self._calculate_reference_pattern(structure, wavelength=float(self.reference_wavelength))
        except Exception as exc:
            if not silent:
                messagebox.showerror("Reference CIF", f"Failed to read CIF:\n{path}\n\n{exc}")
            return False
        color = self._reference_palette[len(self.reference_peaks) % len(self._reference_palette)]
        self.reference_peaks.append({
            "path": str(path),
            "label": structure.get("formula") or path.stem.replace("-SYM", ""),
            "color": color,
            "visible": True,
            "height": 1.0,
            "structure": structure,
            "peaks": peaks,
            "wavelength": float(self.reference_wavelength),
            "kalpha2": bool(getattr(self, "reference_kalpha2", True)),
        })
        if refresh_ui:
            self._refresh_reference_peak_list()
        if redraw:
            self._request_draw_plot()
        return True

    def _selected_reference_peak_index(self):
        try:
            idx = int(getattr(self, "reference_peak_selected_index", -1))
            if 0 <= idx < len(self.reference_peaks):
                return idx
        except Exception:
            pass
        return None

    def _apply_reference_peak_selection_style(self):
        selected = self._selected_reference_peak_index()
        normal_bg = getattr(self, "ui_panel", "#ffffff")
        selected_bg = getattr(self, "ui_accent_soft", "#dbeafe")
        for idx, widgets in enumerate(getattr(self, "reference_peak_row_widgets", [])):
            row, checkbutton, label = widgets
            bg = selected_bg if idx == selected else normal_bg
            row.configure(bg=bg)
            checkbutton.configure(bg=bg, activebackground=bg, selectcolor=bg)
            label.configure(bg=bg)

    def _select_reference_peak_row(self, idx):
        try:
            idx = int(idx)
        except Exception:
            return
        if not 0 <= idx < len(self.reference_peaks):
            return
        self.reference_peak_selected_index = idx
        self._apply_reference_peak_selection_style()

    def _set_reference_peak_visible(self, idx, visible):
        try:
            idx = int(idx)
        except Exception:
            return
        if not 0 <= idx < len(self.reference_peaks):
            return
        self.reference_peak_selected_index = idx
        self.reference_peaks[idx]["visible"] = bool(visible)
        self._apply_reference_peak_selection_style()
        self._request_draw_plot()

    def _refresh_reference_peak_list(self):
        if not hasattr(self, "reference_list_rows"):
            return
        try:
            selected = self._selected_reference_peak_index()
            scroll_fraction = 0.0
            if hasattr(self, "reference_list_canvas"):
                view = self.reference_list_canvas.yview()
                if view:
                    scroll_fraction = float(view[0])
            for child in self.reference_list_rows.winfo_children():
                child.destroy()
            self.reference_peak_visibility_vars = []
            self.reference_peak_row_widgets = []
            for idx, ref in enumerate(self.reference_peaks):
                label = str(ref.get("label", Path(ref.get("path", "")).stem))
                row = tk.Frame(self.reference_list_rows, bg=self.ui_panel)
                row.pack(fill='x')
                row.columnconfigure(1, weight=1)
                visible_var = tk.BooleanVar(value=bool(ref.get("visible", True)))
                checkbutton = tk.Checkbutton(
                    row,
                    text="",
                    variable=visible_var,
                    command=lambda i=idx, var=visible_var: self._set_reference_peak_visible(i, var.get()),
                    bg=self.ui_panel,
                    activebackground=self.ui_panel,
                    highlightthickness=0,
                    bd=0,
                    padx=0,
                    pady=0,
                )
                checkbutton.grid(row=0, column=0, sticky='w', padx=(3, 1), pady=1)
                label_widget = tk.Label(
                    row,
                    text=f"{idx + 1}. {label}",
                    anchor='w',
                    bg=self.ui_panel,
                    fg=getattr(self, "ui_text", "#111111"),
                    font=getattr(self, "ui_font", None),
                )
                label_widget.grid(row=0, column=1, sticky='ew', padx=(1, 3), pady=1)
                row.bind('<Button-1>', lambda _event, i=idx: self._select_reference_peak_row(i))
                label_widget.bind('<Button-1>', lambda _event, i=idx: self._select_reference_peak_row(i))
                checkbutton.bind('<Button-1>', lambda _event, i=idx: self._select_reference_peak_row(i), add='+')
                self.reference_peak_visibility_vars.append(visible_var)
                self.reference_peak_row_widgets.append((row, checkbutton, label_widget))
            if selected is not None and selected < len(self.reference_peaks):
                self.reference_peak_selected_index = selected
            elif not self.reference_peaks:
                self.reference_peak_selected_index = None
            if hasattr(self, "_normalize_section_controls"):
                self._normalize_section_controls(self.reference_list_rows)
            self._apply_reference_peak_selection_style()
            if hasattr(self, "reference_list_canvas"):
                self.reference_list_rows.update_idletasks()
                self.reference_list_canvas.configure(scrollregion=self.reference_list_canvas.bbox('all'))
                self.reference_list_canvas.yview_moveto(scroll_fraction)
        except Exception:
            pass

    def toggle_selected_reference_peak(self):
        idx = self._selected_reference_peak_index()
        if idx is None:
            return
        self.reference_peaks[idx]["visible"] = not bool(self.reference_peaks[idx].get("visible", True))
        self._refresh_reference_peak_list()
        self._request_draw_plot()

    def remove_selected_reference_peak(self):
        idx = self._selected_reference_peak_index()
        if idx is None:
            return
        del self.reference_peaks[idx]
        self.reference_peak_selected_index = min(idx, len(self.reference_peaks) - 1) if self.reference_peaks else None
        self._refresh_reference_peak_list()
        self._request_draw_plot()

    def clear_reference_peaks(self):
        self.reference_peaks = []
        self.reference_peak_selected_index = None
        self._refresh_reference_peak_list()
        self._request_draw_plot()

    def rename_selected_reference_peak(self):
        idx = self._selected_reference_peak_index()
        if idx is None:
            return
        current = str(self.reference_peaks[idx].get("label", ""))
        value = simpledialog.askstring("Reference Label", "Reference peak label:", initialvalue=current, parent=self.root)
        if value is None:
            return
        self.reference_peaks[idx]["label"] = value.strip() or current
        self._refresh_reference_peak_list()
        self._request_draw_plot()

    def pick_selected_reference_peak_color(self):
        idx = self._selected_reference_peak_index()
        if idx is None:
            return
        current = str(self.reference_peaks[idx].get("color", "#555555"))
        color = choose_color(self.root, title="Reference Peak Color", initial_color=current)
        if not color:
            return
        self.reference_peaks[idx]["color"] = color
        self._request_draw_plot()

    def move_selected_reference_peak(self, delta):
        idx = self._selected_reference_peak_index()
        if idx is None:
            return
        new_idx = idx + int(delta)
        if new_idx < 0 or new_idx >= len(self.reference_peaks):
            return
        self.reference_peaks[idx], self.reference_peaks[new_idx] = self.reference_peaks[new_idx], self.reference_peaks[idx]
        self.reference_peak_selected_index = new_idx
        self._refresh_reference_peak_list()
        dialog = getattr(self, "_color_settings_dialog", None)
        try:
            if dialog is not None and dialog.winfo_exists():
                dialog.sync_source_order("Reference Peaks")
        except Exception:
            pass
        self._request_draw_plot()

    def _recalculate_reference_patterns_if_needed(self):
        self._sync_reference_controls()
        wl = float(getattr(self, "reference_wavelength", 1.5406))
        use_kalpha2 = bool(getattr(self, "reference_kalpha2", True))
        for ref in getattr(self, "reference_peaks", []):
            if (
                abs(float(ref.get("wavelength", 0.0)) - wl) < 1e-8
                and bool(ref.get("kalpha2", False)) == use_kalpha2
                and ref.get("peaks")
            ):
                continue
            try:
                ref["peaks"] = self._calculate_reference_pattern(ref.get("structure", {}), wavelength=wl)
                ref["wavelength"] = wl
                ref["kalpha2"] = use_kalpha2
            except Exception:
                ref["peaks"] = []

    def _reference_label_font_prop(self):
        size = self._scale_font_size(self.reference_label_size, min_size=5, max_size=30)
        bold = bool(getattr(self, "reference_label_bold", True))
        return self._font_prop(size=size, bold=bold)

    def _draw_reference_peak_panel(self, ax, x_min, x_max, draw_labels=True):
        self._recalculate_reference_patterns_if_needed()
        refs = [ref for ref in self.reference_peaks if ref.get("visible", True) and ref.get("peaks")]
        n = len(refs)
        if n <= 0:
            return
        x_span = max(float(x_max) - float(x_min), 1e-6)
        label_position = str(getattr(self, "reference_label_position", "left")).lower()
        if label_position == "right":
            label_x = float(x_max) - x_span * 0.015
            label_ha = "right"
        else:
            label_x = float(x_min) + x_span * 0.015
            label_ha = "left"
        ax._xrd_color_role = "reference"
        ax.set_facecolor("white")
        for side in ("left", "right", "top", "bottom"):
            try:
                ax.spines[side].set_visible(True)
                ax.spines[side].set_linewidth(self._scaled_line_width(getattr(self, "plot_box_linewidth", 1.0)))
                ax.spines[side].set_color("black")
            except Exception:
                pass
        for sep in range(1, n):
            ax.axhline(sep, color=self._element_color("reference_separator", "#5f5f5f"), linewidth=self._scaled_line_width(0.6), zorder=3)
        for idx, ref in enumerate(refs):
            # The first manager row is the top graph row, so Move Up/Down and
            # the displayed row numbers match the visual order exactly.
            graph_row = n - idx - 1
            y0, y1 = float(graph_row), graph_row + 0.86
            peaks = [(tt, inten) for tt, inten, _hkl in ref.get("peaks", []) if x_min <= tt <= x_max]
            if peaks:
                max_i = max(max(float(i), 0.0) for _tt, i in peaks) or 1.0
                xs = [float(tt) for tt, _i in peaks]
                bottoms = [y0] * len(xs)
                tops = [y0 + (y1 - y0) * max(0.04, min(1.0, float(i) / max_i)) for _tt, i in peaks]
                color = str(ref.get("color", "#4a4a4a"))
                ax.vlines(xs, bottoms, tops, colors=color, linewidth=self._scaled_line_width(self.reference_stick_width))
            if draw_labels:
                label = format_chemical_formula_mathtext(
                    str(ref.get("label", "Reference"))
                )
                label = self._format_tex(label)
                txt = ax.text(
                    label_x,
                    graph_row + 0.74,
                    label,
                    ha=label_ha,
                    va="center",
                    color=self._element_color("reference_label", str(ref.get("color", "#4a4a4a"))),
                    fontproperties=self._reference_label_font_prop(),
                    clip_on=False,
                )
                try:
                    self.art_engine.apply_text_art(txt)
                except Exception:
                    pass
        ax.set_ylim(0, n)
        ax.set_yticks([])
        ax.set_ylabel("")
        ax.set_xlim(x_min, x_max)
        ax.grid(False, which="both", axis="both")

    def _parse_cif(self, path):
        text = Path(path).read_text(encoding="utf-8", errors="ignore")
        lines = [line.strip() for line in text.splitlines() if line.strip() and not line.strip().startswith("#")]
        fields = {}
        loops = []
        i = 0
        while i < len(lines):
            line = lines[i]
            if line.lower() == "loop_":
                i += 1
                headers = []
                while i < len(lines) and lines[i].startswith("_"):
                    headers.append(lines[i].split()[0])
                    i += 1
                rows = []
                while i < len(lines) and not lines[i].lower() == "loop_" and not lines[i].startswith("_"):
                    try:
                        rows.append(shlex.split(lines[i], posix=True))
                    except Exception:
                        rows.append(lines[i].split())
                    i += 1
                loops.append((headers, rows))
                continue
            if line.startswith("_"):
                parts = line.split(None, 1)
                fields[parts[0]] = self._cif_clean_token(parts[1]) if len(parts) > 1 else ""
            i += 1

        cell = {
            "a": self._cif_float(fields.get("_cell_length_a", 1.0)),
            "b": self._cif_float(fields.get("_cell_length_b", 1.0)),
            "c": self._cif_float(fields.get("_cell_length_c", 1.0)),
            "alpha": self._cif_float(fields.get("_cell_angle_alpha", 90.0)),
            "beta": self._cif_float(fields.get("_cell_angle_beta", 90.0)),
            "gamma": self._cif_float(fields.get("_cell_angle_gamma", 90.0)),
        }
        formula = fields.get("_chemical_formula_structural", "") or fields.get("_chemical_formula_sum", "")
        formula = str(formula).replace("'", "").replace('"', "").strip()

        sym_ops = []
        atoms = []
        for headers, rows in loops:
            lower = [h.lower() for h in headers]
            if "_symmetry_equiv_pos_as_xyz" in lower or "_space_group_symop_operation_xyz" in lower:
                op_idx = lower.index("_symmetry_equiv_pos_as_xyz") if "_symmetry_equiv_pos_as_xyz" in lower else lower.index("_space_group_symop_operation_xyz")
                for row in rows:
                    if len(row) > op_idx:
                        sym_ops.append(str(row[op_idx]).strip().strip("'\""))
            if "_atom_site_fract_x" in lower and "_atom_site_fract_y" in lower and "_atom_site_fract_z" in lower:
                type_idx = lower.index("_atom_site_type_symbol") if "_atom_site_type_symbol" in lower else None
                label_idx = lower.index("_atom_site_label") if "_atom_site_label" in lower else None
                x_idx = lower.index("_atom_site_fract_x")
                y_idx = lower.index("_atom_site_fract_y")
                z_idx = lower.index("_atom_site_fract_z")
                occ_idx = lower.index("_atom_site_occupancy") if "_atom_site_occupancy" in lower else None
                b_idx = lower.index("_atom_site_b_iso_or_equiv") if "_atom_site_b_iso_or_equiv" in lower else None
                u_idx = lower.index("_atom_site_u_iso_or_equiv") if "_atom_site_u_iso_or_equiv" in lower else None
                for row in rows:
                    try:
                        raw_symbol = row[type_idx] if type_idx is not None and len(row) > type_idx else row[label_idx]
                        b_iso = 0.0
                        if b_idx is not None and len(row) > b_idx:
                            b_iso = max(0.0, self._cif_float(row[b_idx]))
                        elif u_idx is not None and len(row) > u_idx:
                            b_iso = max(0.0, 8.0 * math.pi * math.pi * self._cif_float(row[u_idx]))
                        atoms.append({
                            "element": self._element_from_symbol(raw_symbol),
                            "species": self._species_from_symbol(raw_symbol),
                            "x": self._cif_float(row[x_idx]),
                            "y": self._cif_float(row[y_idx]),
                            "z": self._cif_float(row[z_idx]),
                            "occ": self._cif_float(row[occ_idx]) if occ_idx is not None and len(row) > occ_idx else 1.0,
                            "b_iso": b_iso,
                        })
                    except Exception:
                        pass
        if not sym_ops:
            sym_ops = ["x,y,z"]
        return {"cell": cell, "atoms": self._expand_cif_atoms(atoms, sym_ops), "formula": formula, "path": str(path)}

    def _cif_clean_token(self, value):
        return str(value).strip().strip("'\"")

    def _cif_float(self, value):
        value = re.sub(r"\([^)]*\)", "", self._cif_clean_token(value))
        return float(value)

    def _element_from_symbol(self, symbol):
        match = re.match(r"([A-Z][a-z]?)", str(symbol).strip().strip("'\""))
        return match.group(1) if match else str(symbol)[:1].upper()

    def _species_from_symbol(self, symbol):
        raw = str(symbol).strip().strip("'\"")
        element = self._element_from_symbol(raw)
        match = re.match(r"^[A-Z][a-z]?(\d*)([+-])$", raw)
        if match:
            magnitude = match.group(1)
            return f"{element}{magnitude}{match.group(2)}" if magnitude else f"{element}{match.group(2)}"
        match = re.match(r"^[A-Z][a-z]?([+-])(\d+)$", raw)
        if match:
            magnitude = "" if match.group(2) == "1" else match.group(2)
            return f"{element}{magnitude}{match.group(1)}"
        return element

    def _expand_cif_atoms(self, atoms, sym_ops):
        expanded = []
        seen = set()
        for atom in atoms:
            x, y, z = atom["x"], atom["y"], atom["z"]
            for op in sym_ops:
                parts = [p.strip() for p in str(op).split(",")]
                if len(parts) != 3:
                    continue
                try:
                    nx = self._eval_sym_expr(parts[0], x, y, z) % 1.0
                    ny = self._eval_sym_expr(parts[1], x, y, z) % 1.0
                    nz = self._eval_sym_expr(parts[2], x, y, z) % 1.0
                except Exception:
                    continue
                key = (atom.get("species", atom["element"]), round(nx, 6), round(ny, 6), round(nz, 6))
                if key in seen:
                    continue
                seen.add(key)
                expanded.append({
                    "element": atom["element"],
                    "species": atom.get("species", atom["element"]),
                    "x": nx,
                    "y": ny,
                    "z": nz,
                    "occ": atom.get("occ", 1.0),
                    "b_iso": atom.get("b_iso", 0.0),
                })
        return expanded

    def _eval_sym_expr(self, expr, x, y, z):
        return float(eval(str(expr).lower().replace(" ", ""), {"__builtins__": {}}, {"x": x, "y": y, "z": z}))

    def _xray_form_factor(self, atom, s_sq):
        table = _rietan_form_factor_table()
        species = str(atom.get("species", atom.get("element", "")))
        element = str(atom.get("element", ""))
        params = table.get(species) or table.get(element)
        if not params:
            return float(ATOMIC_Z.get(element, 10))
        return float(params["c"]) + sum(
            float(a) * math.exp(-float(b) * s_sq)
            for a, b in zip(params["a"], params["b"])
        )

    def _calculate_reference_pattern(self, structure, wavelength=1.5406):
        cell = structure.get("cell", {})
        atoms = structure.get("atoms", [])
        if not atoms:
            return []
        native_pattern = try_calculate_reference_pattern(
            structure,
            _rietan_form_factor_table(),
            ATOMIC_Z,
            wavelength=float(wavelength),
            include_kalpha2=bool(getattr(self, "reference_kalpha2", True)),
        )
        if native_pattern is not None:
            return native_pattern
        a, b, c = float(cell["a"]), float(cell["b"]), float(cell["c"])
        alpha = math.radians(float(cell.get("alpha", 90.0)))
        beta = math.radians(float(cell.get("beta", 90.0)))
        gamma = math.radians(float(cell.get("gamma", 90.0)))
        avec = np.array([a, 0.0, 0.0], dtype=float)
        bvec = np.array([b * math.cos(gamma), b * math.sin(gamma), 0.0], dtype=float)
        cx = c * math.cos(beta)
        cy = c * (math.cos(alpha) - math.cos(beta) * math.cos(gamma)) / max(math.sin(gamma), 1e-12)
        cz = math.sqrt(max(c * c - cx * cx - cy * cy, 1e-12))
        cvec = np.array([cx, cy, cz], dtype=float)
        volume = float(np.dot(avec, np.cross(bvec, cvec)))
        astar = np.cross(bvec, cvec) / volume
        bstar = np.cross(cvec, avec) / volume
        cstar = np.cross(avec, bvec) / volume

        # Conventional Cu K-alpha doublet and graphite-monochromator polarization.
        wavelength = float(wavelength)
        radiation = [(wavelength, 1.0)]
        if bool(getattr(self, "reference_kalpha2", True)):
            radiation.append((wavelength * (1.54439 / 1.54056), 0.5))

        max_two_theta = 120.0
        shortest_wavelength = min(line[0] for line in radiation)
        q_max = 2.0 * math.sin(math.radians(max_two_theta / 2.0)) / shortest_wavelength
        reciprocal = np.column_stack((astar, bstar, cstar))
        reciprocal_inverse = np.linalg.inv(reciprocal)
        bounds = [
            int(max(3, math.ceil(q_max * float(np.linalg.norm(reciprocal_inverse[row, :]))) + 1))
            for row in range(3)
        ]
        hmax, kmax, lmax = bounds
        grouped = {}
        tol = 1e-5
        cthm1 = 0.7998
        for h in range(-hmax, hmax + 1):
            for k in range(-kmax, kmax + 1):
                for l in range(-lmax, lmax + 1):
                    if h == 0 and k == 0 and l == 0:
                        continue
                    q = h * astar + k * bstar + l * cstar
                    qn = float(np.linalg.norm(q))
                    if qn <= 1e-12:
                        continue
                    d = 1.0 / qn
                    for line_wavelength, line_weight in radiation:
                        arg = line_wavelength / (2.0 * d)
                        if arg <= 0 or arg >= 1:
                            continue
                        theta = math.asin(arg)
                        two_theta = math.degrees(2.0 * theta)
                        if two_theta <= 0 or two_theta > max_two_theta:
                            continue
                        s_sq = (math.sin(theta) / line_wavelength) ** 2
                        f = 0j
                        for atom in atoms:
                            atomic_f = self._xray_form_factor(atom, s_sq)
                            b_iso = max(0.0, float(atom.get("b_iso", 0.0)))
                            thermal = math.exp(-b_iso * s_sq)
                            phase = 2.0 * math.pi * (h * atom["x"] + k * atom["y"] + l * atom["z"])
                            f += atom.get("occ", 1.0) * atomic_f * thermal * cmath.exp(1j * phase)
                        structure_intensity = f.real * f.real + f.imag * f.imag
                        if structure_intensity <= 1e-10:
                            continue
                        sin_theta = max(math.sin(theta), 1e-12)
                        cos_theta = max(math.cos(theta), 1e-12)
                        polarization = 1.0 + cthm1 * math.cos(2.0 * theta) ** 2
                        lorentz_polarization = (
                            polarization
                            / ((1.0 + cthm1) * sin_theta * sin_theta * cos_theta)
                        )
                        intensity = float(line_weight) * structure_intensity * lorentz_polarization
                        key = int(round(two_theta / tol))
                        if key in grouped:
                            grouped[key][1] += intensity
                        else:
                            grouped[key] = [two_theta, intensity, (h, k, l)]
        peaks = list(grouped.values())
        if not peaks:
            return []
        max_i = max(p[1] for p in peaks) or 1.0
        normalized = [
            (float(tt), float(i) / max_i * 100.0, hkl)
            for tt, i, hkl in peaks
            if i / max_i >= 1e-5
        ]
        normalized.sort(key=lambda item: item[0])
        return normalized
