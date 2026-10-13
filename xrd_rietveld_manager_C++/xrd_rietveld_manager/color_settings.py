# SPDX-License-Identifier: GPL-2.0-or-later
"""Central color settings, with staged edits and explicit renderer hooks."""
import tkinter as tk
from tkinter import ttk, messagebox
from matplotlib.colors import to_hex, is_color_like

from xrd_rietveld_manager.color_picker import choose_color
from xrd_rietveld_manager.palettes import available_palette_names, get_palette_colors
from xrd_rietveld_manager.popup_utils import place_window_on_parent_monitor
from xrd_rietveld_manager.ui2_widgets import RoundedScrollbar, build_ui2_indicator_images


# None means that the renderer keeps its existing color/inheritance behavior.
PLOT_COLORS = {
    "canvas": "Canvas background", "title": "Plot title",
    "panel_title": "Panel titles", "sample_label": "Sample labels",
    "phase_label": "Phase labels", "reference_label": "Reference labels",
    "spine": "Axis borders", "tick": "Tick marks", "grid": "Grid lines",
    "zero": "Residual zero line", "crosshair": "Mouse crosshair",
    "reference_separator": "Reference separators",
    "reference_background": "Reference panel background",
    "residual_background": "Residual panel background",
    "legend_text": "Legend text", "legend_background": "Legend background",
    "legend_border": "Legend border", "pane_3d": "3D axis panes",
}
LEGACY_COLORS = {
    "axis_label_color": ("Axis titles", "#000000"),
    "tick_label_color": ("Tick labels", "#000000"),
    "residual_label_color": ("Residual labels", "#1f77b4"),
    "plot_bg_color": ("Plot background / solid", "#ffffff"),
    "plot_bg_grad_start": ("Plot gradient / start", "#ffffff"),
    "plot_bg_grad_end": ("Plot gradient / end", "#eeeeee"),
    "plot_memo_default_color": ("New memo default", "#111827"),
}


def normalize(value, allow_auto=False):
    value = str(value).strip()
    if allow_auto and value.lower() in ("", "auto"):
        return "auto"
    if len(value) == 6 and all(c in "0123456789abcdefABCDEF" for c in value):
        value = "#" + value
    if not is_color_like(value) or value.lower() == "none":
        raise ValueError("Enter a color name or a six-digit HEX color (for example #4285F4).")
    return to_hex(value)


class ColorSettingsMixin:
    def _element_color(self, key, fallback):
        return getattr(self, "element_colors", {}).get(key) or fallback

    def _color_setting_rows(self):
        rows = []
        def add(tab, label, kind, target, key, value, auto=False, group=None, default=None):
            rows.append(dict(tab=tab, label=label, kind=kind, target=target,
                             key=key, value=value, auto=auto, group=group,
                             default=("auto" if auto else value) if default is None else default))
        for key, label in PLOT_COLORS.items():
            add("Plot", label, "element", None, key,
                getattr(self, "element_colors", {}).get(key, "auto"), True, default="auto")
        for key, (label, fallback) in LEGACY_COLORS.items():
            var = getattr(self, "var_" + key, None)
            value = var.get() if var is not None else getattr(self, key, fallback)
            add("Plot", label, "attribute", None, key, value, default=fallback)
        seen = set()
        try:
            loader_items = list(self._ordered_loaders(visible_only=True))
        except (AttributeError, TypeError):
            loader_items = [
                (path, loader) for path, loader in self.loaded_files.items()
                if bool(getattr(loader, "global_visible", True))
            ]
        visible_loaders = [loader for _path, loader in loader_items]
        for path, loader in loader_items:
            # Color Setting follows the same visibility state as Project Files
            # and Layer Order & Style. Hidden files and hidden layers should
            # not occupy editor rows until they are shown again.
            if not bool(getattr(loader, "global_visible", True)):
                continue
            name = getattr(loader, "filename", str(path))
            add("Data", name + " / File & 3D", "file", loader, "project_color",
                getattr(loader, "project_color", "#000000"), group="project_color",
                default=getattr(loader, "default_project_color", getattr(loader, "project_color", "#000000")))
            for role in loader.styles:
                if not bool(getattr(loader, "visibility", {}).get(role, True)):
                    continue
                phase = role in loader.phase_names
                group = self._phase_color_group_key(loader, role) if phase else None
                if phase and group in seen:
                    continue
                if phase: seen.add(group)
                tab = "Phases" if phase else "Data"
                label = loader.display_names.get(role, role) if phase else name + " / " + role
                fields = [("color", "Line")]
                # Marker fill/edge are controlled by the phase line color in
                # this app, so only expose the independent area-fill option.
                if phase:
                    fields += [
                        ("fill_color", "Area fill"),
                    ]
                saved_defaults = getattr(loader, "default_styles", {})
                default_style = saved_defaults.get(role) if isinstance(saved_defaults, dict) else None
                if not isinstance(default_style, dict):
                    if phase:
                        # Compatibility for loaders created before reset
                        # snapshots existed: retain the phase's assigned color
                        # instead of falling back to generic black.
                        default_style = dict(loader.styles.get(role, {}))
                    else:
                        try:
                            default_style = loader._get_default_style(role)
                        except Exception:
                            default_style = {}
                for field, caption in fields:
                    default = default_style.get(field, "auto" if field != "color" else "#000000")
                    add(tab, label + " / " + caption, "phase" if phase else "style",
                        (loader, role, group), field,
                        loader.styles[role].get(field, "auto" if field != "color" else "#000000"),
                        field != "color", (role, field) if not phase else None, default=default)

        # Phase rows and Color List assignment follow the exact phase order in
        # Layer Order & Style.  The first visible file remains the tie-breaker
        # when the same linked phase is present in more than one file.
        phase_group_rank = {}
        for loader in visible_loaders:
            try:
                ordered_phases = self._get_loader_phase_order(loader, visible_only=True)
            except (AttributeError, TypeError):
                phase_names = list(getattr(loader, "phase_names", []))
                layer_order = list(getattr(loader, "layer_order", []) or [])
                ordered_phases = [role for role in layer_order if role in phase_names]
                ordered_phases.extend(role for role in phase_names if role not in ordered_phases)
                ordered_phases = [
                    role for role in ordered_phases
                    if bool(getattr(loader, "visibility", {}).get(role, True))
                ]
            for role in ordered_phases:
                group = self._phase_color_group_key(loader, role)
                if group not in phase_group_rank:
                    phase_group_rank[group] = len(phase_group_rank)

        phase_rows = [row for row in rows if row["tab"] == "Phases"]
        phase_rows.sort(
            key=lambda row: phase_group_rank.get(
                row["target"][2], len(phase_group_rank)
            )
        )
        rows = [row for row in rows if row["tab"] != "Phases"] + phase_rows

        for ref in getattr(self, "reference_peaks", []):
            add("References", str(ref.get("label", "Reference")), "mapping", ref,
                "color", ref.get("color", "#4a4a4a"), default="#4a4a4a")
        for index, memo in enumerate(getattr(self, "plot_memos", [])):
            add("Notes", f"{index + 1}. {str(memo.get('text', 'Memo'))[:60]}",
                "mapping", memo, "color", memo.get("color", "#111827"), default="#111827")
        return rows

    def _commit_color_settings(self, changes, background_mode=None):
        # Validate the whole transaction before touching the project.
        validated = [(row, normalize(value, row["auto"])) for row, value in changes]
        if background_mode not in (None, "Off", "Solid", "Gradient"):
            raise ValueError("Invalid background mode")
        for row, color in validated:
            kind, key, target = row["kind"], row["key"], row["target"]
            if kind == "element":
                self.element_colors = dict(getattr(self, "element_colors", {}))
                if color == "auto": self.element_colors.pop(key, None)
                else: self.element_colors[key] = color
            elif kind == "attribute":
                setattr(self, key, color)
                var = getattr(self, "var_" + key, None)
                if var is not None: var.set(color)
            elif kind == "file":
                setattr(target, key, color)
            elif kind == "mapping":
                target[key] = color
            else:
                loader, role, group = target
                targets = [(loader, role)]
                if kind == "phase":
                    targets = [(other, phase) for other in self.loaded_files.values()
                               for phase in other.phase_names
                               if self._phase_color_group_key(other, phase) == group]
                    if key == "color": self._apply_phase_group_color(group, color)
                for other, role_name in targets:
                    style = other.styles.setdefault(role_name, {})
                    if color == "auto": style.pop(key, None)
                    else: style[key] = color
                    if role_name == "Observed" and key == "color":
                        style["observed_custom_color"] = True
        if background_mode is not None:
            self.plot_bg_enabled = background_mode != "Off"
            self.plot_bg_mode = "gradient" if background_mode == "Gradient" else "solid"
            for key in ("plot_bg_enabled", "plot_bg_mode"):
                var = getattr(self, "var_" + key, None)
                if var is not None: var.set(getattr(self, key))

    def _apply_element_colors(self):
        colors = getattr(self, "element_colors", {})
        self.fig.patch.set_facecolor(self._element_color("canvas", "white"))
        for ax in self.fig.axes:
            if "panel_title" in colors:
                ax.title.set_color(colors["panel_title"])
            if "spine" in colors:
                for spine in ax.spines.values(): spine.set_edgecolor(colors["spine"])
            role = getattr(ax, "_xrd_color_role", "")
            if role + "_background" in colors:
                # A solid panel override supersedes its gradient background.
                for artist in ax.images:
                    if artist.get_zorder() == -100: artist.set_visible(False)
                ax.set_facecolor(colors[role + "_background"])
            for axis in [ax.xaxis, ax.yaxis] + ([ax.zaxis] if hasattr(ax, "zaxis") else []):
                if "tick" in colors: axis.set_tick_params(which="both", color=colors["tick"])
                if "grid" in colors:
                    axis.set_tick_params(which="both", grid_color=colors["grid"])
                    if hasattr(axis, "_axinfo"): axis._axinfo["grid"]["color"] = colors["grid"]
                if "pane_3d" in colors and hasattr(axis, "pane"):
                    axis.pane.fill = True
                    axis.set_pane_color(colors["pane_3d"])
            legend = ax.get_legend()
            if legend is not None:
                for text in legend.get_texts():
                    if "legend_text" in colors: text.set_color(colors["legend_text"])
                frame = legend.get_frame()
                if "legend_background" in colors:
                    frame.set_facecolor(colors["legend_background"])
                if "legend_border" in colors: frame.set_edgecolor(colors["legend_border"])
        title = getattr(self, "title_artist", None)
        if title is not None and "title" in colors: title.set_color(colors["title"])

    def open_color_settings(self):
        existing = getattr(self, "_color_settings_dialog", None)
        if existing is not None and existing.winfo_exists():
            existing.lift(); existing.focus_force(); return
        try:
            self._color_settings_dialog = ColorSettingsDialog(self)
        except Exception as exc:
            self._color_settings_dialog = None
            messagebox.showerror(
                "Color Setting",
                f"The Color Setting window could not be opened.\n{exc}",
                parent=self.root,
            )


class _LegacyColorSettingsDialog(tk.Toplevel):
    r'''
    def __init__(self, app):
        super().__init__(app.root)
        self.withdraw()
        self.app = app
        self.title("Color Setting")
        self.transient(app.root)
        self.theme_bg = getattr(app, "ui_bg", app.ui_surface)
        self.configure(bg=self.theme_bg)
        self.rows = app._color_setting_rows()
        self.values = {str(i): str(row["value"]) for i, row in enumerate(self.rows)}
        self.original = dict(self.values)
        self.selected = None
        self.trees = {}
        tk.Label(self, text="Color Setting", font=("Calibri", 16, "bold"),
                 bg=app.ui_surface, fg=app.ui_text).pack(anchor="w", padx=18, pady=(14, 4))
        tk.Label(self, text="Select an element, then set its color. Auto follows the existing style.\n"
                 "Changes are saved only with Apply or OK. Same-name phases stay linked.",
                 justify="left", bg=app.ui_surface, fg=app.ui_muted).pack(anchor="w", padx=18)
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=18, pady=12)
        for tab in ("Plot", "Data", "Phases", "References", "Notes"):
            page = ttk.Frame(notebook)
            notebook.add(page, text=tab)
            tree = ttk.Treeview(page, columns=("color",), show="tree headings", selectmode="browse")
            tree.heading("#0", text="Element")
            tree.heading("color", text="Color")
            tree.column("#0", width=390, minwidth=150)
            tree.column("color", width=105, minwidth=85, stretch=False)
            scroll = ttk.Scrollbar(page, orient="vertical", command=tree.yview)
            tree.configure(yscrollcommand=scroll.set)
            scroll.pack(side="right", fill="y")
            tree.pack(fill="both", expand=True)
            self.trees[tab] = tree
            for i, row in enumerate(self.rows):
                if row["tab"] == tab:
                    tree.insert("", "end", iid=str(i), text=row["label"], values=(row["value"],))
            if not tree.get_children():
                tree.insert("", "end", iid="empty", text="No items loaded in this category.")
            tree.bind("<<TreeviewSelect>>", lambda e, t=tree: self.select(t))
            tree.bind("<Double-1>", lambda e: self.pick())
        editor = ttk.Frame(self)
        editor.pack(fill="x", padx=18)
        self.caption = tk.StringVar(value="Select an element above")
        ttk.Label(editor, textvariable=self.caption, wraplength=540).pack(anchor="w")
        controls = ttk.Frame(editor)
        controls.pack(fill="x", pady=8)
        self.hex = tk.StringVar()
        self.swatch = tk.Label(controls, width=3, bg="#ffffff", relief="solid", bd=1)
        self.swatch.pack(side="left", padx=(0, 8))
        self.entry = ttk.Entry(controls, textvariable=self.hex, width=14)
        self.entry.pack(side="left")
        self.entry.bind("<Return>", lambda e: self.store())
        ttk.Button(controls, text="Choose…", command=self.pick).pack(side="left", padx=5)
        ttk.Button(controls, text="Set", command=self.store).pack(side="left")
        self.auto_button = ttk.Button(controls, text="Auto", command=self.auto)
        self.auto_button.pack(side="left", padx=5)
        self.match_button = ttk.Button(editor, text="Use for this element in all loaded files", command=self.match)
        self.match_button.pack(anchor="w", pady=(0, 8))
        options = ttk.Frame(self)
        options.pack(fill="x", padx=18, pady=4)
        ttk.Label(options, text="Plot background:").pack(side="left")
        enabled = getattr(app, "var_plot_bg_enabled", None)
        enabled = enabled.get() if enabled is not None else getattr(app, "plot_bg_enabled", False)
        mode = getattr(app, "var_plot_bg_mode", None)
        mode = mode.get() if mode is not None else getattr(app, "plot_bg_mode", "solid")
        self.background = tk.StringVar(value=("Gradient" if mode == "gradient" else "Solid") if enabled else "Off")
        self.original_background = self.background.get()
        ttk.Combobox(options, textvariable=self.background, values=("Off", "Solid", "Gradient"),
                     state="readonly", width=10).pack(side="left", padx=8)
        self.status = tk.StringVar(value="")
        ttk.Label(self, textvariable=self.status).pack(anchor="w", padx=18, pady=4)
        footer = ttk.Frame(self)
        footer.pack(fill="x", padx=18, pady=(4, 14))
        ttk.Button(footer, text="Cancel", command=self.destroy).pack(side="right")
        ttk.Button(footer, text="OK", command=lambda: self.apply(True)).pack(side="right", padx=6)
        ttk.Button(footer, text="Apply", command=self.apply).pack(side="right")
        self.bind("<Escape>", lambda e: self.destroy())
        place_window_on_parent_monitor(self, app.root, 680, 680)
        self.deiconify()
        self.grab_set()

    def _theme_button(self, parent, text, command, width=None, primary=False):
        background = self.app.ui_accent if primary else self.app.ui_button_light
        foreground = "#FFFFFF" if primary else self.app.ui_text
        button = tk.Button(
            parent, text=text, command=command, width=width,
            bg=background, fg=foreground, relief=tk.FLAT, bd=0,
            highlightthickness=0, cursor="hand2", font=self.app.ui_font,
            activebackground=self.app.ui_accent_deep if primary else "#E3E6EA",
            activeforeground="#FFFFFF" if primary else self.app.ui_text,
            padx=7, pady=4,
        )
        return button

    def select(self, tree):
        selection = tree.selection()
        if not selection or selection[0] == "empty": return
        if not self.store(): return
        self.selected = selection[0]
        row = self.rows[int(self.selected)]
        self.caption.set(row["label"])
        self.hex.set(self.values[self.selected])
        self.auto_button.configure(state="normal" if row["auto"] else "disabled")
        self.match_button.configure(state="normal" if row["group"] is not None else "disabled")
        self.preview()

    def preview(self):
        value = self.hex.get()
        self.swatch.configure(bg=value if is_color_like(value) else "#ffffff")

    def store(self):
        if self.selected is None: return True
        row = self.rows[int(self.selected)]
        try: value = normalize(self.hex.get(), row["auto"])
        except ValueError as exc:
            self.status.set(str(exc)); return False
        self.values[self.selected] = value
        self.trees[row["tab"]].set(self.selected, "color", value)
        self.hex.set(value)
        self.preview()
        self.status.set("Ready to apply")
        return True

    def pick(self):
        if self.selected is None: return
        value = self.hex.get()
        color = choose_color(self, title=self.caption.get(), initial_color=value if is_color_like(value) else "#4285f4")
        self.grab_set()
        if color: self.hex.set(color); self.store()

    def auto(self):
        if self.selected is not None and self.rows[int(self.selected)]["auto"]:
            self.hex.set("auto"); self.store()

    def match(self):
        if self.selected is None or not self.store(): return
        group = self.rows[int(self.selected)]["group"]
        if group is None: return
        for i, row in enumerate(self.rows):
            if row["group"] == group:
                self.values[str(i)] = self.hex.get()
                self.trees[row["tab"]].set(str(i), "color", self.hex.get())

    def apply(self, close=False):
        if not self.store(): return
        changes = [(self.rows[int(i)], v) for i, v in self.values.items() if v != self.original[i]]
        mode = self.background.get()
        try:
            self.app._commit_color_settings(changes, mode if mode != self.original_background else None)
        except ValueError as exc:
            messagebox.showerror("Color Setting", str(exc), parent=self); return
        self.original = dict(self.values)
        self.original_background = mode
        self.app._set_residual_label_color_preview()
        self.app._set_plot_memo_color_label()
        self.app.rebuild_layer_controls()
        self.app._request_draw_plot()
        self.status.set("Colors applied")
        if close: self.destroy()
    '''


class ColorSettingsDialog(tk.Toplevel):
    """Role-grouped color editor with row controls and live plot preview."""

    GROUPS = (
        "Data Curves", "Phases", "Reference Peaks",
        "Labels & Guides", "3D Curves", "Notes",
    )
    LABEL_GROUPS = (
        "Titles & Text", "Phase Labels", "Reference Panel",
        "Axes & Guides", "Residual Panel", "Legend",
        "Plot Background & 3D",
    )
    COLOR_LIST = tuple(available_palette_names())
    ROW_COLUMN_MINSIZES = (54, 0, 126, 58, 48, 68)

    def __init__(self, app):
        super().__init__(app.root)
        self.withdraw()
        self.app = app
        self.title("Color Setting")
        self.transient(app.root)
        self.theme_bg = getattr(app, "ui_bg", app.ui_surface)
        self.configure(bg=self.theme_bg)
        self.rows = app._color_setting_rows()
        self.values = {str(i): str(row["value"]) for i, row in enumerate(self.rows)}
        self.committed_values = dict(self.values)
        self.applied_values = dict(self.values)
        self.committed_observed_flags = self._observed_flag_snapshot()
        self.variables = {}
        self.swatches = {}
        self.row_widgets = {}
        self.section_bodies = {}
        self.section_buttons = {}
        self.section_cards = {}
        self.active_section = None
        self._preview_after_id = None
        self._closing = False

        enabled_var = getattr(app, "var_plot_bg_enabled", None)
        enabled = enabled_var.get() if enabled_var is not None else getattr(app, "plot_bg_enabled", False)
        mode_var = getattr(app, "var_plot_bg_mode", None)
        mode = mode_var.get() if mode_var is not None else getattr(app, "plot_bg_mode", "solid")
        current_background = ("Gradient" if mode == "gradient" else "Solid") if enabled else "Off"
        self.background = tk.StringVar(value=current_background)
        self.committed_background = current_background
        self.applied_background = current_background
        initial_color_list = str(getattr(app, "phase_color_palette", "Journal Muted"))
        if initial_color_list not in self.COLOR_LIST:
            initial_color_list = "Journal Muted"
        self.color_list_name = tk.StringVar(value=initial_color_list)
        self.color_list_reverse = tk.BooleanVar(value=False)
        self.apply_scope = tk.StringVar(value="Current category")
        self._apply_scope_targets = {"Current category": ("category", None)}
        self.status = tk.StringVar(value="Changes preview on the plot immediately.")
        self.rule_lock_var = getattr(app, "var_lock_same_phase_colors", None)
        if self.rule_lock_var is None:
            self.rule_lock_var = tk.BooleanVar(master=app.root, value=getattr(app, "lock_same_phase_colors", True))
            app.var_lock_same_phase_colors = self.rule_lock_var
        self.rule_preserve_var = getattr(app, "var_preserve_manual_colors", None)
        if self.rule_preserve_var is None:
            self.rule_preserve_var = tk.BooleanVar(master=app.root, value=getattr(app, "preserve_manual_colors", False))
            app.var_preserve_manual_colors = self.rule_preserve_var
        self.line_effects_enabled_var = getattr(app, "var_art_effects_enabled", None)
        if self.line_effects_enabled_var is None:
            self.line_effects_enabled_var = tk.BooleanVar(master=app.root, value=getattr(app, "art_effects_enabled", False))
            app.var_art_effects_enabled = self.line_effects_enabled_var
        self.line_effect_var = getattr(app, "var_art_line_effect", None)
        if self.line_effect_var is None:
            self.line_effect_var = tk.StringVar(master=app.root, value=getattr(app, "art_line_effect", "none"))
            app.var_art_line_effect = self.line_effect_var

        self._build_header()
        self._build_scroller()
        self._build_sections()
        self._build_footer()
        self.protocol("WM_DELETE_WINDOW", self.cancel)
        self.bind("<Escape>", lambda _event: self.cancel())
        self.bind("<MouseWheel>", self._on_mousewheel, add="+")
        place_window_on_parent_monitor(self, app.root, 820, 760)
        self.deiconify()

    def _theme_button(self, parent, text, command, width=None, primary=False):
        background = self.app.ui_accent if primary else self.app.ui_button_light
        foreground = "#FFFFFF" if primary else self.app.ui_text
        return tk.Button(
            parent, text=text, command=command, width=width,
            bg=background, fg=foreground, relief=tk.FLAT, bd=0,
            highlightthickness=0, cursor="hand2", font=self.app.ui_font,
            activebackground=self.app.ui_accent_deep if primary else "#E3E6EA",
            activeforeground="#FFFFFF" if primary else self.app.ui_text,
            padx=7, pady=4,
        )

    def _theme_checkbutton(self, parent, text, variable, command=None, background=None):
        if not hasattr(self, "_checkbox_indicator_images"):
            self._checkbox_indicator_images = getattr(self.app, "_ui2_indicator_images", None)
            if self._checkbox_indicator_images is None:
                self._checkbox_indicator_images = build_ui2_indicator_images(
                    self, accent=self.app.ui_accent, border="#9AA0A6",
                )
        indicators = self._checkbox_indicator_images
        background = background or self.app.ui_panel
        return tk.Checkbutton(
            parent, text=f" {text}", variable=variable, command=command,
            bg=background, fg=self.app.ui_text,
            activebackground=background, activeforeground=self.app.ui_text,
            selectcolor=background, font=self.app.ui_font, anchor="w",
            padx=0, pady=2, cursor="hand2", bd=0, highlightthickness=0,
            indicatoron=False, image=indicators["check_off"],
            selectimage=indicators["check_on"], compound=tk.LEFT,
            relief=tk.FLAT, offrelief=tk.FLAT, overrelief=tk.FLAT,
        )

    def _build_header(self):
        header = tk.Frame(self, bg=self.theme_bg)
        header.pack(fill="x", padx=18, pady=(14, 8))
        tk.Label(header, text="Color Setting", font=("Calibri", 16, "bold"),
                 bg=self.theme_bg, fg=self.app.ui_text).pack(anchor="w")
        tk.Label(
            header,
            text="Colors are grouped by role. Click a swatch or enter a HEX value directly.",
            bg=self.theme_bg, fg=self.app.ui_muted, justify="left",
        ).pack(anchor="w", pady=(2, 9))
        self._build_category_bar(header)
        self._build_rules_and_effects(header)
        tools = tk.Frame(header, bg=self.app.ui_panel, highlightbackground=self.app.ui_border,
                         highlightthickness=1, padx=10, pady=9)
        tools.pack(fill="x", pady=(8, 0))
        palette_row = tk.Frame(tools, bg=self.app.ui_panel)
        palette_row.pack(fill="x")
        palette_row.columnconfigure(3, weight=1)
        tk.Label(palette_row, text="Color List", bg=self.app.ui_panel, fg=self.app.ui_text,
                 font=self.app.ui_font_bold).grid(row=0, column=0, sticky="w")
        self.color_list_box = ttk.Combobox(
            palette_row, textvariable=self.color_list_name, values=self.COLOR_LIST,
            state="readonly", width=24,
        )
        self.color_list_box.grid(row=0, column=1, sticky="w", padx=(8, 8))
        self.color_list_box.bind("<<ComboboxSelected>>", lambda _event: self._refresh_color_list_preview())
        self.color_list_reverse_button = self._theme_checkbutton(
            palette_row, "Reverse", self.color_list_reverse,
            command=self._refresh_color_list_preview,
        )
        self.color_list_reverse_button.grid(row=0, column=2, sticky="w")
        self.color_list_preview = tk.Canvas(
            palette_row, width=132, height=24, bg=self.app.ui_panel,
            highlightthickness=0, bd=0,
        )
        self.color_list_preview.grid(row=0, column=4, sticky="e", padx=(12, 0))

        scope_row = tk.Frame(tools, bg=self.app.ui_panel)
        scope_row.pack(fill="x", pady=(7, 0))
        scope_row.columnconfigure(4, weight=1)
        tk.Label(scope_row, text="Apply to", bg=self.app.ui_panel,
                 fg=self.app.ui_text).grid(row=0, column=0, sticky="w")
        self.apply_scope_box = ttk.Combobox(
            scope_row, textvariable=self.apply_scope,
            values=("Current category",), state="readonly", width=27,
        )
        self.apply_scope_box.grid(row=0, column=1, sticky="w", padx=(21, 5))
        self.apply_colors_button = self._theme_button(
            scope_row, "Apply Colors", self.apply_color_list, primary=True
        )
        self.apply_colors_button.grid(row=0, column=2, sticky="w")
        self._theme_button(scope_row, "Reset All", self.reset_all).grid(
            row=0, column=3, sticky="w", padx=(6, 18)
        )
        tk.Label(scope_row, text="Plot background", bg=self.app.ui_panel,
                 fg=self.app.ui_text).grid(row=0, column=5, sticky="e")
        background_box = ttk.Combobox(
            scope_row, textvariable=self.background, values=("Off", "Solid", "Gradient"),
            state="readonly", width=10,
        )
        background_box.grid(row=0, column=6, sticky="e", padx=(8, 0))
        background_box.bind("<<ComboboxSelected>>", lambda _event: self._schedule_live_preview())
        self._refresh_color_list_preview()

    def _build_rules_and_effects(self, parent):
        panel = tk.Frame(
            parent, bg=self.app.ui_panel,
            highlightbackground=self.app.ui_border, highlightthickness=1,
        )
        panel.pack(fill="x", pady=(8, 0))
        panel.columnconfigure(0, weight=1, uniform="color_options")
        panel.columnconfigure(1, weight=1, uniform="color_options")

        rules = tk.Frame(panel, bg=self.app.ui_panel)
        rules.grid(row=0, column=0, sticky="nsew", padx=(10, 8), pady=8)
        tk.Label(rules, text="RULES", bg=self.app.ui_panel, fg=self.app.ui_muted,
                 font=("Calibri", 8, "bold"), anchor="w").pack(fill="x", pady=(0, 3))
        self._theme_checkbutton(
            rules, "Lock same phase name to same color",
            self.rule_lock_var, self._apply_rule_effect_settings,
        ).pack(fill="x", anchor="w")
        self._theme_checkbutton(
            rules, "Keep custom Observed colors",
            self.rule_preserve_var, self._apply_rule_effect_settings,
        ).pack(fill="x", anchor="w")

        effects = tk.Frame(panel, bg=self.app.ui_panel)
        effects.grid(row=0, column=1, sticky="nsew", padx=(8, 10), pady=8)
        tk.Label(effects, text="LINE EFFECT", bg=self.app.ui_panel, fg=self.app.ui_muted,
                 font=("Calibri", 8, "bold"), anchor="w").pack(fill="x", pady=(0, 3))
        effect_row = tk.Frame(effects, bg=self.app.ui_panel)
        effect_row.pack(fill="x")
        effect_row.columnconfigure(1, weight=1)
        self._theme_checkbutton(
            effect_row, "Enable effects", self.line_effects_enabled_var,
            self._apply_rule_effect_settings,
        ).grid(row=0, column=0, sticky="w")
        effect_box = ttk.Combobox(
            effect_row, textvariable=self.line_effect_var,
            values=("none", "soft shadow", "glow", "cyberpunk"),
            state="readonly", width=13,
        )
        effect_box.grid(row=0, column=1, sticky="ew", padx=(10, 0))
        effect_box.bind("<<ComboboxSelected>>", lambda _event: self._apply_rule_effect_settings())

    def _apply_rule_effect_settings(self):
        self.app.lock_same_phase_colors = bool(self.rule_lock_var.get())
        self.app.preserve_manual_colors = bool(self.rule_preserve_var.get())
        self.app.art_effects_enabled = bool(self.line_effects_enabled_var.get())
        self.app.art_line_effect = str(self.line_effect_var.get())
        self.app._request_draw_plot()

    def _build_category_bar(self, parent):
        bar = tk.Frame(parent, bg=self.theme_bg)
        bar.pack(fill="x")
        labels = {
            "Data Curves": "CURVES",
            "Phases": "PHASES",
            "Reference Peaks": "REFERENCES",
            "Labels & Guides": "LABELS",
            "3D Curves": "3D CURVES",
            "Notes": "NOTES",
        }
        for column, title in enumerate(self.GROUPS):
            bar.grid_columnconfigure(column, weight=1, uniform="color_sections")
            button = tk.Button(
                bar, text=labels[title], command=lambda name=title: self._show_category(name),
                relief=tk.FLAT, bd=0, highlightthickness=0,
                font=("Calibri", 8, "bold"), pady=7, cursor="hand2",
            )
            button.grid(
                row=0, column=column, sticky="ew",
                padx=(0 if column == 0 else 2, 0 if column == len(self.GROUPS) - 1 else 2),
            )
            self.section_buttons[title] = button

    def _build_scroller(self):
        shell = tk.Frame(self, bg=self.theme_bg)
        shell.pack(fill="both", expand=True, padx=18, pady=(0, 8))
        self.canvas = tk.Canvas(shell, bg=self.theme_bg, highlightthickness=0, bd=0)
        scrollbar = RoundedScrollbar(shell, orient="vertical", command=self.canvas.yview, bg=self.theme_bg)
        self.canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scroll_body = tk.Frame(self.canvas, bg=self.theme_bg)
        self._body_window = self.canvas.create_window((0, 0), window=self.scroll_body, anchor="nw")
        self.scroll_body.bind("<Configure>", self._update_scroll_region)
        self.canvas.bind("<Configure>", self._resize_scroll_body)
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.scroll_body.bind("<MouseWheel>", self._on_mousewheel)

    def _build_sections(self):
        grouped = {name: [] for name in self.GROUPS}
        for index, row in enumerate(self.rows):
            grouped[self._group_for_row(row)].append(index)
        for title in self.GROUPS:
            self._build_section(title, grouped[title])
        initial = "Data Curves" if grouped["Data Curves"] else "Labels & Guides"
        self._show_category(initial)

    @staticmethod
    def _show_column_heading(title):
        return False

    def _build_section(self, title, indexes):
        card = tk.Frame(self.scroll_body, bg=self.app.ui_panel,
                        highlightbackground=self.app.ui_border, highlightthickness=1)
        self.section_cards[title] = card
        title_row = tk.Frame(card, bg=self.app.ui_panel)
        title_row.pack(fill="x", padx=10, pady=(9, 6))
        tk.Label(title_row, text=title, bg=self.app.ui_panel, fg=self.app.ui_text,
                 font=("Calibri", 11, "bold"), anchor="w").pack(side="left")
        tk.Label(title_row, text=f"{len(indexes)} elements", bg=self.app.ui_panel,
                 fg=self.app.ui_muted, font=self.app.ui_font).pack(side="right")
        body = tk.Frame(card, bg=self.app.ui_panel)
        self.section_bodies[title] = body
        body.pack(fill="x", padx=1, pady=(0, 8))
        if indexes:
            show_column_heading = self._show_column_heading(title)
            if show_column_heading:
                heading = tk.Frame(body, bg=self.app.ui_panel)
                heading.pack(fill="x", padx=9, pady=(0, 2))
                tk.Label(heading, text="Color", width=7, anchor="w", bg=self.app.ui_panel,
                         fg=self.app.ui_muted).grid(row=0, column=0, sticky="w")
                tk.Label(heading, text="Element", anchor="w", bg=self.app.ui_panel,
                         fg=self.app.ui_muted).grid(row=0, column=1, sticky="w")
                tk.Label(heading, text="HEX / name", width=14, anchor="w", bg=self.app.ui_panel,
                         fg=self.app.ui_muted).grid(row=0, column=2, sticky="w")
                for column, minsize in enumerate(self.ROW_COLUMN_MINSIZES):
                    heading.grid_columnconfigure(
                        column,
                        weight=1 if column == 1 else 0,
                        minsize=minsize,
                    )
            if title == "Labels & Guides":
                first_group = True
                for group_name in self.LABEL_GROUPS:
                    group_indexes = [
                        index for index in indexes
                        if self._label_group_for_row(self.rows[index]) == group_name
                    ]
                    if not group_indexes:
                        continue
                    self._build_label_group_header(body, group_name, first_group)
                    first_group = False
                    for index in group_indexes:
                        self._build_color_row(body, index)
            else:
                current_loader = None
                file_number = 0
                for index in indexes:
                    display_label = None
                    if title == "Data Curves":
                        loader, display_label = self._curve_row_context(self.rows[index])
                        if loader is not current_loader:
                            current_loader = loader
                            file_number += 1
                            self._build_curve_file_header(body, loader, file_number)
                    self._build_color_row(body, index, display_label=display_label)
        else:
            tk.Label(body, text="No items loaded in this category.", bg=self.app.ui_panel,
                     fg=self.app.ui_muted, anchor="w").pack(fill="x", padx=12, pady=(0, 9))

    @staticmethod
    def _curve_row_context(row):
        target = row.get("target")
        if row.get("kind") != "style" or not isinstance(target, tuple) or len(target) < 2:
            return None, row.get("label", "")
        loader, role = target[0], str(target[1])
        caption = str(row.get("label", "")).rsplit(" / ", 1)[-1]
        return loader, f"{role} / {caption}"

    def _build_curve_file_header(self, parent, loader, file_number):
        if file_number > 1:
            tk.Frame(parent, height=1, bg=self.app.ui_border).pack(fill="x", padx=9, pady=(8, 7))
        background = getattr(self.app, "ui_accent_soft", "#E8F0FE")
        foreground = self.app.ui_accent_deep
        header = tk.Frame(parent, bg=background)
        header.pack(fill="x", padx=9, pady=(2, 5))
        tk.Label(
            header, text=f"FILE {file_number}", bg=background, fg=foreground,
            font=("Calibri", 8, "bold"), padx=8, pady=5,
        ).pack(side="left")
        tk.Label(
            header, text=str(getattr(loader, "filename", "Untitled")),
            bg=background, fg=self.app.ui_text, font=self.app.ui_font_bold,
            anchor="w", padx=4, pady=5,
        ).pack(side="left", fill="x", expand=True)

    @staticmethod
    def _label_group_for_row(row):
        key = str(row.get("key", ""))
        if key in {"phase_label"}:
            return "Phase Labels"
        if key in {"reference_label", "reference_separator", "reference_background"}:
            return "Reference Panel"
        if key in {"spine", "tick", "grid", "crosshair", "axis_label_color", "tick_label_color"}:
            return "Axes & Guides"
        if key in {"zero", "residual_background", "residual_label_color"}:
            return "Residual Panel"
        if key in {"legend_text", "legend_background", "legend_border"}:
            return "Legend"
        if key in {"canvas", "plot_bg_color", "plot_bg_grad_start", "plot_bg_grad_end", "pane_3d"}:
            return "Plot Background & 3D"
        return "Titles & Text"

    def _build_label_group_header(self, parent, title, first_group=False):
        if not first_group:
            tk.Frame(parent, height=1, bg=self.app.ui_border).pack(fill="x", padx=9, pady=(8, 7))
        background = getattr(self.app, "ui_accent_soft", "#E8F0FE")
        header = tk.Frame(parent, bg=background)
        header.pack(fill="x", padx=9, pady=(2, 5))
        tk.Label(
            header, text=title, bg=background, fg=self.app.ui_accent_deep,
            font=self.app.ui_font_bold, anchor="w", padx=8, pady=5,
        ).pack(fill="x")

    def _build_color_row(self, parent, index, display_label=None):
        key = str(index)
        row = self.rows[index]
        line = tk.Frame(parent, bg=self.app.ui_panel)
        line.pack(fill="x", padx=9, pady=2)
        for column, minsize in enumerate(self.ROW_COLUMN_MINSIZES):
            line.grid_columnconfigure(
                column,
                weight=1 if column == 1 else 0,
                minsize=minsize,
            )
        swatch = tk.Button(line, width=4, relief="solid", bd=1, cursor="hand2",
                           command=lambda i=index: self.pick(i))
        swatch.grid(row=0, column=0, sticky="w", padx=(0, 8))
        tk.Label(line, text=display_label or row["label"], anchor="w", bg=self.app.ui_panel,
                 fg=self.app.ui_text, font=self.app.ui_font).grid(row=0, column=1, sticky="ew", padx=(0, 8))
        variable = tk.StringVar(value=self.values[key])
        entry = ttk.Entry(line, textvariable=variable, width=14)
        entry.grid(row=0, column=2, sticky="e")
        entry.bind("<Return>", lambda _event, i=index: self.store_row(i))
        entry.bind("<FocusOut>", lambda _event, i=index: self.store_row(i, quiet=True))
        if row["auto"]:
            self._theme_button(line, "Auto", lambda i=index: self.set_auto(i), width=5).grid(
                row=0, column=3, sticky="ew", padx=(5, 0)
            )
        else:
            tk.Frame(line, bg=self.app.ui_panel).grid(row=0, column=3, sticky="ew")
        if row["group"] is not None:
            self._theme_button(line, "All", lambda i=index: self.match_row(i), width=4).grid(
                row=0, column=4, sticky="ew", padx=(5, 0)
            )
        else:
            tk.Frame(line, bg=self.app.ui_panel).grid(row=0, column=4, sticky="ew")
        self._theme_button(line, "Reset", lambda i=index: self.reset_row(i), width=6).grid(
            row=0, column=5, sticky="ew", padx=(5, 0)
        )
        self.variables[key] = variable
        self.swatches[key] = swatch
        self.row_widgets[key] = line
        self._update_swatch(index)

    def _build_footer(self):
        status_bar = tk.Frame(self, bg=self.theme_bg)
        status_bar.pack(fill="x", padx=18)
        tk.Label(status_bar, textvariable=self.status, bg=self.theme_bg,
                 fg=self.app.ui_muted, anchor="w").pack(side="left", fill="x", expand=True)
        tk.Label(status_bar, text="Auto = inherit existing style", bg=self.theme_bg,
                 fg=self.app.ui_muted).pack(side="right")
        footer = tk.Frame(self, bg=self.theme_bg)
        footer.pack(fill="x", padx=18, pady=(8, 14))
        self._theme_button(footer, "Cancel", self.cancel).pack(side="right")
        self._theme_button(footer, "OK", lambda: self.apply(True), primary=True).pack(side="right", padx=6)
        self._theme_button(footer, "Apply", self.apply).pack(side="right")

    def _group_for_row(self, row):
        if row["tab"] == "Phases": return "Phases"
        if row["tab"] == "References": return "Reference Peaks"
        if row["tab"] == "Notes": return "Notes"
        if row["tab"] == "Plot": return "Labels & Guides"
        if row["kind"] == "file": return "3D Curves"
        return "Data Curves"

    def _show_category(self, title):
        card = self.section_cards.get(title)
        if card is None:
            return
        self.sync_source_order(title)
        for other in self.section_cards.values():
            other.pack_forget()
        card.pack(fill="x")
        self.active_section = title
        self._refresh_apply_scope()
        self._update_color_list_enabled()
        for name, button in self.section_buttons.items():
            active = name == title
            button.configure(
                bg=self.app.ui_accent if active else self.app.ui_button_light,
                fg="#FFFFFF" if active else self.app.ui_muted,
                activebackground=self.app.ui_accent_deep if active else "#E3E6EA",
                activeforeground="#FFFFFF" if active else self.app.ui_text,
            )
        self.canvas.yview_moveto(0.0)
        self.after_idle(self._update_scroll_region)

    def _update_scroll_region(self, _event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _resize_scroll_body(self, event):
        self.canvas.itemconfigure(self._body_window, width=max(1, event.width))

    def _on_mousewheel(self, event):
        delta = int(getattr(event, "delta", 0) or 0)
        if delta:
            self.canvas.yview_scroll(-1 if delta > 0 else 1, "units")
        return "break"

    def _update_swatch(self, index):
        key = str(index)
        value = self.variables[key].get() if key in self.variables else self.values[key]
        color = value if is_color_like(value) and str(value).lower() != "none" else "#ffffff"
        self.swatches[key].configure(bg=color, activebackground=color,
                                     text="A" if str(value).lower() == "auto" else "")

    def store_row(self, index, quiet=False, schedule=True):
        key = str(index)
        row = self.rows[index]
        try:
            value = normalize(self.variables[key].get(), row["auto"])
        except ValueError as exc:
            if not quiet:
                self.status.set(str(exc))
                self.variables[key].set(self.values[key])
                self._update_swatch(index)
            return False
        self.values[key] = value
        self.variables[key].set(value)
        self._update_swatch(index)
        self.status.set("Preview updated - use Apply or OK to keep the change.")
        if schedule:
            self._schedule_live_preview()
        return True

    def pick(self, index):
        key = str(index)
        value = self.variables[key].get()
        color = choose_color(self, title=self.rows[index]["label"],
                             initial_color=value if is_color_like(value) else "#4285f4")
        self.lift()
        if color:
            self.variables[key].set(color)
            self.store_row(index)

    def set_auto(self, index):
        if self.rows[index]["auto"]:
            self.variables[str(index)].set("auto")
            self.store_row(index)

    def match_row(self, index):
        if not self.store_row(index, schedule=False):
            return
        group = self.rows[index]["group"]
        value = self.values[str(index)]
        for other_index, row in enumerate(self.rows):
            if group is not None and row["group"] == group:
                key = str(other_index)
                self.values[key] = value
                self.variables[key].set(value)
                self._update_swatch(other_index)
        self._schedule_live_preview()

    def reset_row(self, index):
        self.variables[str(index)].set(str(self.rows[index]["default"]))
        self.store_row(index)

    def reset_all(self):
        for index, row in enumerate(self.rows):
            key = str(index)
            self.values[key] = str(row["default"])
            self.variables[key].set(self.values[key])
            self._update_swatch(index)
        self.background.set("Off")
        self.status.set("Default colors are shown in the live preview.")
        self._schedule_live_preview()

    def _refresh_color_list_preview(self):
        canvas = getattr(self, "color_list_preview", None)
        if canvas is None:
            return
        canvas.delete("all")
        colors = self._color_list_colors(
            self.color_list_name.get(), 8, self.color_list_reverse.get()
        )
        width, height = 132, 24
        gap = 2
        swatch_width = (width - gap * (len(colors) - 1)) / max(1, len(colors))
        for index, color in enumerate(colors):
            x0 = index * (swatch_width + gap)
            canvas.create_rectangle(
                x0, 3, x0 + swatch_width, height - 3,
                fill=color, outline=color,
            )

    @staticmethod
    def _color_list_colors(palette_name, count, reverse=False):
        colors = list(get_palette_colors(palette_name, count))
        return list(reversed(colors)) if reverse else colors

    def _refresh_apply_scope(self):
        box = getattr(self, "apply_scope_box", None)
        if box is None or self.active_section is None:
            return

        section = self.active_section
        targets = {}
        if section == "Data Curves":
            targets["All curves"] = ("category", None)
            for role in ("Observed", "Calculated", "Background", "Difference"):
                if any(
                    row["tab"] == "Data" and row["kind"] == "style"
                    and isinstance(row.get("target"), tuple) and row["target"][1] == role
                    for row in self.rows
                ):
                    targets[f"{role} only"] = ("role", role)

            loaders = []
            for row in self.rows:
                if row["tab"] != "Data" or row["kind"] != "style":
                    continue
                loader = row["target"][0]
                if not any(existing is loader for existing in loaders):
                    loaders.append(loader)
            for number, loader in enumerate(loaders, 1):
                filename = str(getattr(loader, "filename", "Untitled"))
                targets[f"File {number}: {filename}"] = ("file", loader)
        else:
            labels = {
                "3D Curves": "All visible files",
                "Phases": "All visible phases",
                "Reference Peaks": "All visible references",
                "Labels & Guides": "Not available for labels",
                "Notes": "All visible notes",
            }
            targets[labels.get(section, "Current category")] = ("category", None)

        self._apply_scope_targets = targets
        choices = tuple(targets)
        box.configure(values=choices)
        if self.apply_scope.get() not in targets:
            self.apply_scope.set(choices[0] if choices else "Current category")

    @staticmethod
    def _color_list_enabled_for_section(section):
        return section != "Labels & Guides"

    def _update_color_list_enabled(self):
        enabled = self._color_list_enabled_for_section(self.active_section)
        self.color_list_box.configure(state="readonly" if enabled else "disabled")
        self.color_list_reverse_button.configure(state=tk.NORMAL if enabled else tk.DISABLED)
        self.apply_scope_box.configure(state="readonly" if enabled else "disabled")
        self.apply_colors_button.configure(state=tk.NORMAL if enabled else tk.DISABLED)

    def _color_scope_indices(self, section=None, scope=None):
        section = section or self.active_section
        if scope is None:
            scope = self._apply_scope_targets.get(
                self.apply_scope.get(), ("category", None)
            )
        scope_kind, scope_value = scope
        indexes = [
            index for index, row in enumerate(self.rows)
            if self._group_for_row(row) == section
        ]
        if section != "Data Curves":
            return self._ordered_section_indices(section, indexes)
        if scope_kind == "role":
            return [
                index for index in indexes
                if isinstance(self.rows[index].get("target"), tuple)
                and self.rows[index]["target"][1] == scope_value
            ]
        if scope_kind == "file":
            return [
                index for index in indexes
                if isinstance(self.rows[index].get("target"), tuple)
                and self.rows[index]["target"][0] is scope_value
            ]
        return indexes

    def _ordered_section_indices(self, section, indexes):
        indexes = list(indexes)
        if section != "Reference Peaks":
            return indexes
        reference_rank = {
            id(reference): rank
            for rank, reference in enumerate(getattr(self.app, "reference_peaks", []))
        }
        fallback_rank = len(reference_rank)
        return sorted(
            indexes,
            key=lambda index: reference_rank.get(
                id(self.rows[index].get("target")), fallback_rank + index
            ),
        )

    def sync_source_order(self, section):
        """Keep nonmodal Color Setting rows aligned with their source manager."""
        if section != "Reference Peaks" or not hasattr(self, "row_widgets"):
            return
        indexes = self._ordered_section_indices(
            section,
            [
                index for index, row in enumerate(self.rows)
                if self._group_for_row(row) == section
            ],
        )
        widgets = [self.row_widgets.get(str(index)) for index in indexes]
        widgets = [widget for widget in widgets if widget is not None]
        for widget in widgets:
            widget.pack_forget()
        for widget in widgets:
            widget.pack(fill="x", padx=9, pady=2)
        if widgets:
            self._update_scroll_region()

    def _apply_color_list_to_indices(self, indexes, scope_label):
        palette_name = self.color_list_name.get()
        if palette_name not in self.COLOR_LIST:
            return
        indexes = list(indexes)
        if not indexes:
            self.status.set(f"No visible colors match {scope_label}.")
            return

        colors = self._color_list_colors(
            palette_name, max(10, len(indexes)), self.color_list_reverse.get()
        )
        phase_colors = {}
        color_index = 0
        changed = 0
        for index in indexes:
            row = self.rows[index]
            if row["tab"] == "Phases":
                _loader, _role, group = row["target"]
                if group not in phase_colors:
                    phase_colors[group] = colors[color_index % len(colors)]
                    color_index += 1
                value = phase_colors[group]
            else:
                value = colors[color_index % len(colors)]
                color_index += 1

            key = str(index)
            self.values[key] = str(value)
            self.variables[key].set(str(value))
            self._update_swatch(index)
            changed += 1

        self.status.set(
            f"{palette_name} applied to {scope_label} ({changed} colors)."
        )
        self._schedule_live_preview()

    def apply_color_list(self):
        if not self._color_list_enabled_for_section(self.active_section):
            self.status.set("Color List is not available for Labels & Guides.")
            return
        label = self.apply_scope.get()
        self._apply_color_list_to_indices(self._color_scope_indices(), label)

    def _schedule_live_preview(self):
        if self._preview_after_id is not None:
            try: self.after_cancel(self._preview_after_id)
            except Exception: pass
        self._preview_after_id = self.after(80, self._live_preview)

    def _observed_flag_snapshot(self):
        snapshot = []
        for loader in getattr(self.app, "loaded_files", {}).values():
            style = getattr(loader, "styles", {}).get("Observed")
            if isinstance(style, dict):
                snapshot.append((style, "observed_custom_color" in style,
                                 bool(style.get("observed_custom_color", False))))
        return snapshot

    @staticmethod
    def _restore_observed_flags(snapshot):
        for style, existed, value in snapshot:
            if existed:
                style["observed_custom_color"] = value
            else:
                style.pop("observed_custom_color", None)

    def _pending_changes(self, baseline):
        return [
            (self.rows[index], self.values[str(index)])
            for index in range(len(self.rows))
            if self.values[str(index)] != baseline[str(index)]
        ]

    def _commit_pending_preview(self):
        changes = self._pending_changes(self.applied_values)
        background = self.background.get()
        mode = background if background != self.applied_background else None
        if not changes and mode is None:
            return
        self.app._commit_color_settings(changes, mode)
        for index in range(len(self.rows)):
            key = str(index)
            self.applied_values[key] = self.values[key]
        self.applied_background = background

    def _live_preview(self):
        self._preview_after_id = None
        if self._closing:
            return
        try:
            self._commit_pending_preview()
            self._refresh_app_preview(final=False)
        except ValueError as exc:
            self.status.set(str(exc))

    def _refresh_app_preview(self, final=False):
        self.app._set_residual_label_color_preview()
        self.app._set_plot_memo_color_label()
        if final:
            self.app.rebuild_layer_controls()
        self.app._request_draw_plot()

    def apply(self, close=False):
        for index in range(len(self.rows)):
            if not self.store_row(index, schedule=False):
                return
        try:
            self._commit_pending_preview()
        except ValueError as exc:
            messagebox.showerror("Color Setting", str(exc), parent=self)
            return
        self.committed_values = dict(self.values)
        self.committed_background = self.background.get()
        self.committed_observed_flags = self._observed_flag_snapshot()
        self._refresh_app_preview(final=True)
        self.status.set("Colors applied.")
        if close:
            self._closing = True
            self.destroy()

    def cancel(self):
        if self._closing:
            return
        self._closing = True
        if self._preview_after_id is not None:
            try: self.after_cancel(self._preview_after_id)
            except Exception: pass
            self._preview_after_id = None
        try:
            changes = [
                (self.rows[index], self.committed_values[str(index)])
                for index in range(len(self.rows))
                if self.committed_values[str(index)] != self.applied_values[str(index)]
            ]
            mode = self.committed_background if self.committed_background != self.applied_background else None
            self.app._commit_color_settings(changes, mode)
            self._restore_observed_flags(self.committed_observed_flags)
            self._refresh_app_preview(final=True)
        except Exception:
            pass
        self.destroy()
