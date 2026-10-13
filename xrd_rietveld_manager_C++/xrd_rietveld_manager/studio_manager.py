# SPDX-License-Identifier: GPL-2.0-or-later
from xrd_rietveld_manager.common import *
from xrd_rietveld_manager.ui_schema import CONTROL_LOCATIONS, EXTENDED_FONT_SIZE_MAX, FONT_SIZE_MAX, UI_GROUPS


class StudioManagerMixin:
    def open_art_director(self):
        win = tk.Toplevel(self.root)
        win.withdraw()
        win.title("Art Director")
        win.after_idle(lambda: place_window_on_parent_monitor(win, self.root, 620, 520))
        win.configure(bg=self.ui_panel)

        header = tk.Frame(win, bg=self.ui_text)
        header.pack(fill="x", padx=10, pady=(10, 6))
        tk.Label(
            header,
            text="Figure Art Director",
            bg=self.ui_text,
            fg="white",
            font=getattr(self, "ui_font_title", self.ui_font_bold),
            anchor="w",
        ).pack(fill="x", padx=12, pady=(10, 0))
        tk.Label(
            header,
            text="One-click visual directions. These only change style controls, not loaded data.",
            bg=self.ui_text,
            fg="#D5DEE7",
            font=self.ui_font,
            anchor="w",
            justify="left",
            wraplength=560,
        ).pack(fill="x", padx=12, pady=(2, 10))

        body = tk.Frame(win, bg=self.ui_panel)
        body.pack(fill="both", expand=True, padx=10, pady=4)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)

        presets = [
            (
                "Journal Minimal",
                "Clean white page, no effects, high readability.",
                {
                    "palette": "Editorial Ink",
                    "art": False,
                    "line": "none",
                    "halo": True,
                    "bg": False,
                    "bg_mode": "solid",
                    "bg_color": "#FFFFFF",
                    "grad_start": "#FFFFFF",
                    "grad_end": "#FFFFFF",
                },
            ),
            (
                "Soft Gallery",
                "Subtle shadow, soft phase colors, publication-friendly warmth.",
                {
                    "palette": "Ceramic Pastel",
                    "art": True,
                    "line": "soft shadow",
                    "halo": True,
                    "bg": True,
                    "bg_mode": "gradient",
                    "bg_color": "#FFFFFF",
                    "grad_start": "#FFFFFF",
                    "grad_end": "#EEF5F3",
                },
            ),
            (
                "High Contrast",
                "Sharper contrast for dense multi-phase plots.",
                {
                    "palette": "Clean Contrast",
                    "art": True,
                    "line": "soft shadow",
                    "halo": True,
                    "bg": False,
                    "bg_mode": "solid",
                    "bg_color": "#FFFFFF",
                    "grad_start": "#FFFFFF",
                    "grad_end": "#FFFFFF",
                },
            ),
            (
                "Gradient Poster",
                "More artistic background, glow-capable, designed for presentation figures.",
                {
                    "palette": "Anodized Spectrum",
                    "art": True,
                    "line": "glow",
                    "halo": True,
                    "bg": True,
                    "bg_mode": "gradient",
                    "bg_color": "#FFFFFF",
                    "grad_start": "#F9FBFD",
                    "grad_end": "#E5F1F0",
                },
            ),
        ]

        for idx, (name, desc, settings) in enumerate(presets):
            card = tk.Frame(body, bg=self.ui_surface, highlightbackground=self.ui_border, highlightthickness=1)
            card.grid(row=idx // 2, column=idx % 2, sticky="nsew", padx=5, pady=5)
            tk.Label(card, text=name, bg=self.ui_surface, fg=self.ui_text, font=self.ui_font_bold, anchor="w").pack(fill="x", padx=10, pady=(9, 2))
            tk.Label(card, text=desc, bg=self.ui_surface, fg=self.ui_muted, font=self.ui_font, wraplength=250, justify="left", anchor="w").pack(fill="x", padx=10, pady=(0, 8))
            tk.Button(
                card,
                text="Apply Direction",
                command=lambda s=settings: self._apply_art_director_preset(s),
                bg=self.ui_accent,
                fg="white",
                relief=tk.FLAT,
                bd=0,
                font=self.ui_font_bold,
                cursor="hand2",
            ).pack(fill="x", padx=10, pady=(0, 10))

        footer = tk.Frame(win, bg=self.ui_panel)
        footer.pack(fill="x", padx=10, pady=(2, 10))
        tk.Button(footer, text="Close", command=win.destroy, bg=self.ui_button_light, font=self.ui_font).pack(side="right")

    def _apply_art_director_preset(self, settings):
        self.art_palette_name = settings.get("palette", self.art_palette_name)
        self.art_effects_enabled = bool(settings.get("art", self.art_effects_enabled))
        self.art_line_effect = settings.get("line", self.art_line_effect)
        self.art_text_halo = bool(settings.get("halo", self.art_text_halo))
        self.plot_bg_enabled = bool(settings.get("bg", self.plot_bg_enabled))
        self.plot_bg_mode = settings.get("bg_mode", self.plot_bg_mode)
        self.plot_bg_color = settings.get("bg_color", self.plot_bg_color)
        self.plot_bg_grad_start = settings.get("grad_start", self.plot_bg_grad_start)
        self.plot_bg_grad_end = settings.get("grad_end", self.plot_bg_grad_end)

        var_updates = {
            "var_art_palette": self.art_palette_name,
            "var_art_effects_enabled": self.art_effects_enabled,
            "var_art_line_effect": self.art_line_effect,
            "var_art_text_halo": self.art_text_halo,
            "var_plot_bg_enabled": self.plot_bg_enabled,
            "var_plot_bg_mode": self.plot_bg_mode,
        }
        for attr, value in var_updates.items():
            obj = getattr(self, attr, None)
            if obj is not None and hasattr(obj, "set"):
                obj.set(value)

        has_phases = any(getattr(loader, "phase_names", None) for loader in self.loaded_files.values())
        if has_phases:
            self.apply_art_palette_to_phases()
        else:
            self._request_draw_plot()

    def open_ui_inventory(self):
        win = tk.Toplevel(self.root)
        win.withdraw()
        win.title("UI Inventory")
        win.after_idle(lambda: place_window_on_parent_monitor(win, self.root, 760, 560))
        win.configure(bg=self.ui_panel)

        nb = ttk.Notebook(win)
        nb.pack(fill="both", expand=True, padx=8, pady=8)

        overview = tk.Frame(nb, bg=self.ui_surface)
        nb.add(overview, text="Target Groups")
        for idx, group in enumerate(UI_GROUPS):
            frame = tk.LabelFrame(overview, text=f"{idx + 1}. {group['label']}", bg=self.ui_surface, font=self.ui_font_bold)
            frame.pack(fill="x", padx=8, pady=5)
            tk.Label(frame, text=group["purpose"], bg=self.ui_surface, anchor="w", justify="left", wraplength=700).pack(fill="x", padx=6, pady=(4, 2))
            tk.Label(frame, text=", ".join(group["controls"]), bg=self.ui_surface, fg=self.ui_muted, anchor="w", justify="left", wraplength=700).pack(fill="x", padx=6, pady=(0, 5))

        controls = tk.Frame(nb, bg=self.ui_surface)
        nb.add(controls, text="Control Map")
        tree = ttk.Treeview(controls, columns=("target",), show="headings", height=18)
        tree.heading("target", text="Target Location")
        tree.column("target", width=420, anchor="w")
        tree.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)
        scroll = ttk.Scrollbar(controls, orient="vertical", command=tree.yview)
        scroll.pack(side="right", fill="y", pady=8, padx=(0, 8))
        tree.configure(yscrollcommand=scroll.set)
        tree["columns"] = ("control", "target")
        tree.heading("control", text="Control")
        tree.heading("target", text="Should Live In")
        tree.column("control", width=220, anchor="w")
        tree.column("target", width=420, anchor="w")
        for control, target in sorted(CONTROL_LOCATIONS.items()):
            tree.insert("", "end", values=(control, target))

    def open_style_studio(self):
        win = tk.Toplevel(self.root)
        win.withdraw()
        win.title("Style Studio")
        win.after_idle(lambda: place_window_on_parent_monitor(win, self.root, 720, 640))
        win.configure(bg=self.ui_panel)

        nb = ttk.Notebook(win)
        nb.pack(fill="both", expand=True, padx=8, pady=8)

        font_tab = tk.Frame(nb, bg=self.ui_surface)
        nb.add(font_tab, text="Typography")
        self._studio_size_control(font_tab, "Plot Title", "var_title_size", 8, EXTENDED_FONT_SIZE_MAX)
        self._studio_size_control(font_tab, "Axis Label", "var_axis_size", 6, EXTENDED_FONT_SIZE_MAX)
        self._studio_size_control(font_tab, "Tick Label", "var_tick_label_size", 6, FONT_SIZE_MAX)
        self._studio_size_control(font_tab, "Legend", "var_legend_font_size", 6, 30)
        self._studio_size_control(font_tab, "Residual Label", "var_resid_size", 6, 30)
        self._studio_checkbox(font_tab, "Plot Title Bold", "var_plot_title_bold")
        self._studio_checkbox(font_tab, "Axis Label Bold", "var_axis_label_bold")
        self._studio_checkbox(font_tab, "Tick Label Bold", "var_tick_label_bold")

        legend_tab = tk.Frame(nb, bg=self.ui_surface)
        nb.add(legend_tab, text="Legend")
        self._studio_checkbox(legend_tab, "Show Legend", "var_show_legend")
        self._studio_checkbox(legend_tab, "Transparent Legend", "var_legend_transparent")
        self._studio_combo(legend_tab, "Orientation", "var_legend_orientation", ["vertical", "horizontal"])
        self._studio_combo(legend_tab, "Location", "var_legend_location", ["auto", "upper right", "upper left", "lower right", "lower left", "center right", "center left", "upper center", "lower center"])
        self._studio_size_control(legend_tab, "Legend Columns", "var_legend_ncol", 1, 12)
        self._studio_size_control(legend_tab, "Max Width %", "var_legend_max_width", 40, 100)

        tick_tab = tk.Frame(nb, bg=self.ui_surface)
        nb.add(tick_tab, text="Ticks & Box")
        self._studio_combo(tick_tab, "2D Tick Direction", "cmb_tick_dir_2d", ["in", "out", "inout", "none"])
        self._studio_size_control(tick_tab, "Tick Length", "var_tick_length_2d", 0.0, 20.0, resolution=0.5)
        self._studio_size_control(tick_tab, "Tick Width", "var_tick_width_2d", 0.1, 6.0, resolution=0.1)
        self._studio_checkbox(tick_tab, "Show X Ticks", "var_tick_x_2d")
        self._studio_checkbox(tick_tab, "Show Y Ticks", "var_tick_y_2d")
        self._studio_checkbox(tick_tab, "Show X Tick Labels", "var_tick_label_x_2d")
        self._studio_checkbox(tick_tab, "Show Y Tick Labels", "var_tick_label_y_2d")
        self._studio_size_control(tick_tab, "Plot Box Width", "var_plot_box_linewidth", 0.1, 8.0, resolution=0.1)

        bg_tab = tk.Frame(nb, bg=self.ui_surface)
        nb.add(bg_tab, text="Background & Art")
        self._studio_checkbox(bg_tab, "Enable Background", "var_plot_bg_enabled")
        self._studio_combo(bg_tab, "Background Mode", "var_plot_bg_mode", ["solid", "gradient"])
        self._studio_checkbox(bg_tab, "Enable Art Effects", "var_art_effects_enabled")
        self._studio_combo(bg_tab, "Line Effect", "var_art_line_effect", ["none", "soft shadow", "glow", "cyberpunk"])
        self._studio_checkbox(bg_tab, "Text Halo", "var_art_text_halo")
        self._studio_checkbox(bg_tab, "3D Marker Feel", "var_art_marker_depth")
        self._studio_checkbox(bg_tab, "Auto Label Adjust", "var_art_label_adjust")

        btns = tk.Frame(win, bg=self.ui_panel)
        btns.pack(fill="x", padx=8, pady=(0, 8))
        tk.Button(btns, text="Apply", command=self._request_draw_plot, bg=self.ui_accent, fg="white", font=self.ui_font_bold).pack(side="right", padx=4)
        tk.Button(btns, text="Close", command=win.destroy, bg=self.ui_button_light, font=self.ui_font).pack(side="right", padx=4)

    def _studio_get_var(self, attr):
        return getattr(self, attr, None)

    def _studio_size_control(self, parent, label, attr, vmin, vmax, resolution=1):
        var = self._studio_get_var(attr)
        if var is None:
            return
        row = tk.Frame(parent, bg=self.ui_surface)
        row.pack(fill="x", padx=10, pady=5)
        row.columnconfigure(1, weight=1)
        tk.Label(row, text=label, bg=self.ui_surface, width=18, anchor="w").grid(row=0, column=0, sticky="w")
        tk.Scale(row, from_=vmin, to=vmax, resolution=resolution, orient="horizontal", variable=var, command=lambda _v: self._request_draw_plot(), showvalue=False, bg=self.ui_surface, highlightthickness=0).grid(row=0, column=1, sticky="ew", padx=6)
        entry = tk.Entry(row, textvariable=var, width=7)
        entry.grid(row=0, column=2, sticky="e")
        entry.bind("<Return>", lambda _e: self._request_draw_plot())
        entry.bind("<FocusOut>", lambda _e: self._request_draw_plot())

    def _studio_checkbox(self, parent, label, attr):
        var = self._studio_get_var(attr)
        if var is None:
            return
        tk.Checkbutton(parent, text=label, variable=var, command=self._request_draw_plot, bg=self.ui_surface).pack(anchor="w", padx=10, pady=4)

    def _studio_combo(self, parent, label, attr, values):
        obj = self._studio_get_var(attr)
        if obj is None:
            return
        row = tk.Frame(parent, bg=self.ui_surface)
        row.pack(fill="x", padx=10, pady=5)
        tk.Label(row, text=label, bg=self.ui_surface, width=18, anchor="w").pack(side="left")

        if isinstance(obj, ttk.Combobox):
            var = tk.StringVar(value=obj.get())

            def sync():
                obj.set(var.get())
                self._request_draw_plot()
        else:
            var = obj

            def sync():
                self._request_draw_plot()

        cmb = ttk.Combobox(row, textvariable=var, values=values, state="readonly", width=18)
        cmb.pack(side="left", fill="x", expand=True)
        cmb.bind("<<ComboboxSelected>>", lambda _e: sync())

