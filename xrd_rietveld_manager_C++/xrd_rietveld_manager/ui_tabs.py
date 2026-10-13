# SPDX-License-Identifier: GPL-2.0-or-later
from xrd_rietveld_manager.common import *
from xrd_rietveld_manager.ui2_widgets import ModernScale, build_ui2_indicator_images


class UiTabsMixin:
    def _tab_banner(self, parent, title, subtitle, accent=None):
        accent = accent or self.ui_accent
        outer = tk.Frame(parent, bg=self.ui_surface, highlightbackground=self.ui_border, highlightthickness=1, bd=0)
        outer.pack(fill=tk.X, pady=(0, 8))
        body = tk.Frame(outer, bg=self.ui_surface)
        body.pack(fill="both", expand=True, padx=11, pady=9)
        tk.Label(
            body,
            text=title,
            bg=self.ui_surface,
            fg=accent,
            font=getattr(self, "ui_font_title", self.ui_font_bold),
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            body,
            text=subtitle,
            bg=self.ui_surface,
            fg=self.ui_muted,
            font=self.ui_font,
            anchor="w",
            justify="left",
            wraplength=max(280, self.left_panel_width - 80),
        ).pack(fill="x", pady=(2, 0))
        return outer

    def _accent_button(self, parent, text, command, color=None, **kwargs):
        cfg = dict(
            text=text,
            command=command,
            bg=color or self.ui_accent,
            fg="white",
            activebackground=self.ui_accent_deep,
            activeforeground="white",
            relief=tk.FLAT,
            bd=0,
            cursor="hand2",
            font=self.ui_font_bold,
        )
        cfg.update(kwargs)
        return tk.Button(parent, **cfg)

    def _themed_radio_button(self, parent, text, variable, value, command=None, background=None):
        if not hasattr(self, "_ui2_indicator_images"):
            self._ui2_indicator_images = build_ui2_indicator_images(
                self.root,
                accent=self.ui_accent,
                border="#9AA0A6",
            )
        indicators = self._ui2_indicator_images
        background = background or self.ui_surface
        return tk.Radiobutton(
            parent,
            text=f" {text}",
            variable=variable,
            value=value,
            command=command,
            bg=background,
            fg=self.ui_text,
            activebackground=background,
            activeforeground=self.ui_text,
            selectcolor=background,
            font=self.ui_font,
            anchor="w",
            padx=0,
            pady=3,
            cursor="hand2",
            bd=0,
            highlightthickness=0,
            indicatoron=False,
            image=indicators["radio_off"],
            selectimage=indicators["radio_on"],
            compound=tk.LEFT,
            relief=tk.FLAT,
            offrelief=tk.FLAT,
            overrelief=tk.FLAT,
        )

    def _style_settings_card(self, frame):
        frame.configure(
            bg=self.ui_surface,
            fg=self.ui_text,
            font=self.ui_font_bold,
            padx=8,
            pady=8,
            highlightbackground=self.ui_border,
            highlightthickness=1,
            bd=0,
        )

    def _make_plot_card_collapsible(self, frame, title, expanded=False):
        """Give Plot cards one consistent open/closed interaction."""
        state = {"expanded": bool(expanded)}
        child_layouts = []
        for child in frame.winfo_children():
            manager = child.winfo_manager()
            if manager == "pack":
                pack_info = {
                    key: value
                    for key, value in child.pack_info().items()
                    if key != "in" and value != ""
                }
                child_layouts.append((child, manager, pack_info))
            elif manager == "grid":
                child_layouts.append((child, manager, None))

        def refresh():
            is_open = state["expanded"]
            display_title = ("\u25be   " if is_open else "\u25b8   ") + title
            frame.configure(text=display_title)
            title_button.configure(text=display_title)
            frame.pack_propagate(is_open)
            frame.grid_propagate(is_open)
            if is_open:
                for child, manager, layout_info in child_layouts:
                    if manager == "pack" and not child.winfo_manager():
                        child.pack(**layout_info)
                    elif manager == "grid" and not child.winfo_manager():
                        child.grid()
            else:
                for child, manager, _layout_info in child_layouts:
                    if manager == "pack":
                        child.pack_forget()
                    elif manager == "grid":
                        child.grid_remove()
                frame.configure(height=28)

        def toggle(_event=None):
            state["expanded"] = not state["expanded"]
            refresh()

        title_button = tk.Button(
            frame,
            command=toggle,
            bg=self.ui_surface,
            fg=self.ui_text,
            activebackground=self.ui_surface,
            activeforeground=self.ui_text,
            font=self.ui_font_bold,
            anchor="w",
            width=44,
            relief=tk.FLAT,
            overrelief=tk.FLAT,
            bd=0,
            highlightthickness=0,
            padx=5,
            pady=3,
            takefocus=False,
            cursor="hand2",
        )
        title_button._ui2_card_header = True
        frame.configure(labelwidget=title_button)

        frame._plot_card_state = state
        frame._plot_card_title_button = title_button
        frame.unbind("<Button-1>")
        frame.unbind("<Motion>")
        frame.unbind("<Leave>")
        frame.unbind("<Configure>")
        frame.configure(cursor="arrow")
        refresh()

    def _normalize_section_controls(self, parent):
        """Apply one control rhythm without touching DATA, LAYERS, or Figure Set."""
        surface_colors = {str(self.ui_panel), str(self.ui_surface)}
        if not hasattr(self, "_ui2_indicator_images"):
            self._ui2_indicator_images = build_ui2_indicator_images(
                self.root,
                accent=self.ui_accent,
                border="#9AA0A6",
            )
        indicators = self._ui2_indicator_images

        def visit(widget):
            try:
                if isinstance(widget, tk.LabelFrame):
                    self._style_settings_card(widget)
                elif isinstance(widget, tk.Button):
                    if getattr(widget, "_ui2_card_header", False):
                        widget.configure(
                            bg=self.ui_surface,
                            fg=self.ui_text,
                            activebackground=self.ui_surface,
                            activeforeground=self.ui_text,
                            relief=tk.FLAT,
                            overrelief=tk.FLAT,
                            bd=0,
                            highlightthickness=0,
                            font=self.ui_font_bold,
                            padx=5,
                            pady=3,
                            takefocus=False,
                            cursor="hand2",
                        )
                    else:
                        widget.configure(
                            relief=tk.FLAT,
                            bd=0,
                            highlightthickness=0,
                            font=(
                                widget.cget("font")
                                if getattr(widget, "_ui2_preserve_font", False)
                                else self.ui_font_bold
                            ),
                            pady=6,
                            cursor="hand2",
                        )
                elif isinstance(widget, tk.Checkbutton):
                    label = str(widget.cget("text") or "")
                    widget.configure(
                        text=(f" {label.lstrip()}" if label else ""),
                        bg=self.ui_surface,
                        activebackground=self.ui_surface,
                        font=self.ui_font,
                        anchor="w",
                        pady=2,
                        padx=0,
                        highlightthickness=0,
                        indicatoron=False,
                        image=indicators["check_off"],
                        selectimage=indicators["check_on"],
                        compound=tk.LEFT,
                        relief=tk.FLAT,
                        offrelief=tk.FLAT,
                        overrelief=tk.FLAT,
                        bd=0,
                    )
                elif isinstance(widget, tk.Radiobutton):
                    widget.configure(
                        bg=self.ui_surface,
                        activebackground=self.ui_surface,
                        font=self.ui_font,
                        anchor="w",
                        pady=2,
                        padx=0,
                        highlightthickness=0,
                        indicatoron=False,
                        image=indicators["radio_off"],
                        selectimage=indicators["radio_on"],
                        compound=tk.LEFT,
                        relief=tk.FLAT,
                        offrelief=tk.FLAT,
                        overrelief=tk.FLAT,
                        bd=0,
                    )
                elif isinstance(widget, tk.Scale):
                    widget.configure(
                        bg=self.ui_surface,
                        activebackground=self.ui_accent,
                        troughcolor=self.ui_border,
                        sliderrelief=tk.FLAT,
                        sliderlength=16,
                        width=10,
                        bd=0,
                        highlightthickness=0,
                        showvalue=False,
                    )
                elif isinstance(widget, tk.Entry):
                    siblings = widget.master.winfo_children()
                    is_slider_value = any(
                        isinstance(sibling, (ModernScale, tk.Scale))
                        for sibling in siblings
                    )
                    if is_slider_value:
                        widget.configure(
                            width=5,
                            justify=tk.CENTER,
                            font=self.ui_font,
                            bg="#FFFFFF",
                            fg=self.ui_text,
                            insertbackground=self.ui_text,
                            selectbackground=self.ui_accent_soft,
                            selectforeground=self.ui_text,
                            disabledbackground="#F1F3F4",
                            disabledforeground="#9AA0A6",
                            relief=tk.FLAT,
                            bd=0,
                            highlightthickness=1,
                            highlightbackground="#C9CFD6",
                            highlightcolor=self.ui_accent,
                        )
                        manager = widget.winfo_manager()
                        if manager == "grid":
                            widget.grid_configure(
                                sticky="w",
                                ipadx=0,
                                ipady=1,
                            )
                        elif manager == "pack":
                            widget.pack_configure(
                                fill=tk.NONE,
                                expand=False,
                                ipadx=0,
                                ipady=1,
                            )
                    else:
                        widget.configure(font=self.ui_font, relief=tk.SOLID, bd=1)
                elif isinstance(widget, tk.Frame):
                    if str(widget.cget("bg")) in surface_colors:
                        widget.configure(bg=self.ui_surface)
                elif isinstance(widget, tk.Label):
                    if str(widget.cget("bg")) in surface_colors:
                        widget.configure(bg=self.ui_surface)
            except Exception:
                pass
            for child in widget.winfo_children():
                visit(child)

        for child in parent.winfo_children():
            visit(child)
            if isinstance(child, tk.LabelFrame) and child.winfo_manager() == "pack":
                try:
                    child.pack_configure(fill=tk.X, padx=10, pady=(0, 8))
                except Exception:
                    pass

    def _show_plot_section(self, section_key):
        pages = getattr(self, "plot_section_pages", {})
        page = pages.get(section_key)
        if page is None:
            return
        page.tkraise()
        self.active_plot_section = section_key
        for key, button in getattr(self, "plot_section_buttons", {}).items():
            active = key == section_key
            button.configure(
                bg=self.ui_accent if active else self.ui_button_light,
                fg="#FFFFFF" if active else self.ui_muted,
                activebackground=self.ui_accent_deep if active else "#E3E6EA",
                activeforeground="#FFFFFF" if active else self.ui_text,
            )

    def _create_plot_section_shell(self):
        parent = self.tab_plot
        header = tk.Frame(parent, bg=self.ui_bg)
        header.pack(fill=tk.X, padx=10, pady=(12, 7))
        tk.Label(
            header,
            text="PLOT",
            bg=self.ui_bg,
            fg=self.ui_text,
            font=("Calibri", 14, "bold"),
            anchor="w",
        ).pack(anchor="w")

        section_bar = tk.Frame(parent, bg=self.ui_bg)
        section_bar.pack(fill=tk.X, padx=10, pady=(0, 8))
        self.plot_section_buttons = {}
        section_specs = (
            ("quick", "QUICK"),
            ("axes", "AXES"),
            ("style", "STYLE"),
            ("3d", "3D"),
            ("advanced", "ADVANCED"),
        )
        for column, (key, label) in enumerate(section_specs):
            section_bar.grid_columnconfigure(column, weight=1, uniform="plot_sections")
            button = tk.Button(
                section_bar,
                text=label,
                command=lambda section=key: self._show_plot_section(section),
                relief=tk.FLAT,
                bd=0,
                highlightthickness=0,
                font=("Calibri", 8, "bold"),
                pady=7,
                cursor="hand2",
            )
            button.grid(
                row=0,
                column=column,
                sticky="ew",
                padx=(0 if column == 0 else 2, 0 if column == len(section_specs) - 1 else 2),
            )
            self.plot_section_buttons[key] = button

        host = tk.Frame(parent, bg=self.ui_bg)
        host.pack(fill=tk.BOTH, expand=True)
        host.grid_rowconfigure(0, weight=1)
        host.grid_columnconfigure(0, weight=1)
        self.plot_section_pages = {}
        self.plot_section_bodies = {}
        self.plot_section_scrolls = {}
        for key, _label in section_specs:
            page = tk.Frame(host, bg=self.ui_bg)
            page.grid(row=0, column=0, sticky="nsew")
            scroll = ScrollableFrame(page, bg=self.ui_bg)
            scroll.pack(fill=tk.BOTH, expand=True)
            self.plot_section_pages[key] = page
            self.plot_section_scrolls[key] = scroll
            self.plot_section_bodies[key] = scroll.scrollable_frame

        # Compatibility aliases keep the existing feature builders and any
        # external navigation hooks working after COLORS/AXES/3D are embedded.
        self.tab_colors = self.plot_section_bodies["style"]
        self.tab_color_body = self.plot_section_bodies["style"]
        self.color_scroll = self.plot_section_scrolls["style"]
        self.tab_axes = self.plot_section_bodies["axes"]
        self.tab_axes_body = self.plot_section_bodies["axes"]
        self.axes_scroll = self.plot_section_scrolls["axes"]
        self.tab_3d = self.plot_section_bodies["3d"]
        self.tab_3d_body = self.plot_section_bodies["3d"]
        self.d3_scroll = self.plot_section_scrolls["3d"]
        self._plot_sections_embedded = True
        self._show_plot_section("quick")

    def _ensure_plot_font_var(self):
        if not hasattr(self, "var_plot_font_display"):
            self.var_plot_font_display = tk.StringVar(value=self.plot_font_display)
        return self.var_plot_font_display

    def _build_plot_font_selector(self, parent, compact=False):
        font_var = self._ensure_plot_font_var()
        row = tk.Frame(parent, bg=self.ui_panel)
        row.pack(fill=tk.X, padx=5, pady=(3, 1))
        row.columnconfigure(1, weight=1)
        tk.Label(row, text="Plot Font:", bg=self.ui_panel, font=self.ui_font).grid(row=0, column=0, sticky="w")
        cmb_plot_font = ttk.Combobox(
            row,
            textvariable=font_var,
            values=available_plot_fonts(),
            state="readonly",
            width=18 if compact else 24,
        )
        cmb_plot_font.grid(row=0, column=1, sticky="ew", padx=(5, 0))
        cmb_plot_font.bind("<<ComboboxSelected>>", lambda e: self.set_plot_font(font_var.get()))

        self.lbl_active_font = tk.Label(
            parent,
            text=f"Active: {self.plot_font_display}",
            bg=self.ui_panel,
            fg=self.ui_text,
            justify="left",
            anchor="w",
            font=self.ui_font,
        )
        self.lbl_active_font.pack(fill=tk.X, padx=5, pady=(1, 0))
        self.lbl_plot_font_path = tk.Label(
            parent,
            text=f"Font file: {self.plot_font_path if self.plot_font_path else 'Matplotlib fallback'}",
            bg=self.ui_panel,
            fg=self.ui_muted,
            justify="left",
            anchor="w",
            wraplength=max(250, self.left_panel_width - 70),
            font=self.ui_font,
        )
        self.lbl_plot_font_path.pack(fill=tk.X, padx=5, pady=(0, 3))
        if not hasattr(self, "plot_font_status_labels"):
            self.plot_font_status_labels = []
        self.plot_font_status_labels.append((self.lbl_active_font, self.lbl_plot_font_path))
        return cmb_plot_font

    def _refresh_legend_layout_controls(self, redraw=True):
        """Enable horizontal-only legend layout options and keep their styling in sync."""
        if not hasattr(self, "var_legend_orientation"):
            return
        horizontal = self.var_legend_orientation.get() == "horizontal"
        combo = getattr(self, "cmb_legend_column_mode", None)
        if combo is not None:
            combo.configure(state="readonly" if horizontal else "disabled")
        for entry_name in ("ent_legend_ncol", "ent_legend_max_width"):
            entry = getattr(self, entry_name, None)
            if entry is not None:
                entry.configure(state="normal" if horizontal else "disabled")
        scale = getattr(self, "scale_legend_max_width", None)
        if scale is not None:
            if hasattr(scale, "set_enabled"):
                scale.set_enabled(horizontal)
            else:
                scale.configure(state="normal" if horizontal else "disabled")
        for label in getattr(self, "legend_horizontal_only_labels", ()):
            label.configure(fg=self.ui_text if horizontal else self.ui_muted)
        if redraw:
            self._request_draw_plot()

    def _setup_main_tab(self):
        parent = getattr(self, "tab_main_body", self.tab_main)
        header = tk.Frame(parent, bg=self.ui_bg)
        header.pack(fill=tk.X, padx=10, pady=(12, 7))
        tk.Label(
            header, text="DATA", bg=self.ui_bg, fg=self.ui_text,
            font=("Calibri", 14, "bold"), anchor="w",
        ).pack(anchor="w")

        file_card = tk.LabelFrame(
            parent, text="Project Files", bg=self.ui_surface, fg=self.ui_text,
            font=self.ui_font_bold, padx=8, pady=8,
            highlightbackground=self.ui_border, highlightthickness=1, bd=0,
        )
        file_card.pack(fill=tk.X, padx=10, pady=(0, 8))

        primary_row = tk.Frame(file_card, bg=self.ui_surface)
        primary_row.pack(fill=tk.X, pady=(0, 5))
        primary_row.grid_columnconfigure(0, weight=1, uniform="data_primary")
        primary_row.grid_columnconfigure(1, weight=1, uniform="data_primary")
        tk.Button(
            primary_row, text="Load Data", command=self.load_new_file,
            bg=self.ui_accent, fg="#FFFFFF", activebackground=self.ui_accent_deep,
            activeforeground="#FFFFFF", relief=tk.FLAT, bd=0,
            font=self.ui_font_bold, pady=6, cursor="hand2",
        ).grid(row=0, column=0, sticky="ew", padx=(0, 3))
        tk.Button(
            primary_row, text="Remove Selected", command=self.remove_selected_file,
            bg=self.ui_button_light, fg=self.ui_danger, activebackground="#FCE8E6",
            activeforeground="#A50E0E", relief=tk.FLAT, bd=0,
            font=self.ui_font_bold, pady=6, cursor="hand2",
        ).grid(row=0, column=1, sticky="ew", padx=(3, 0))

        secondary_row = tk.Frame(file_card, bg=self.ui_surface)
        secondary_row.pack(fill=tk.X, pady=(0, 5))
        secondary_specs = [
            ("Check All", lambda: self.set_all_visibility(True)),
            ("Uncheck All", lambda: self.set_all_visibility(False)),
            ("Move Up", self.move_file_up),
            ("Move Down", self.move_file_down),
        ]
        for column, (text, command) in enumerate(secondary_specs):
            secondary_row.grid_columnconfigure(column, weight=1, uniform="data_secondary")
            tk.Button(
                secondary_row, text=text, command=command,
                bg=self.ui_bg, fg=self.ui_muted,
                activebackground=self.ui_accent_soft, activeforeground=self.ui_accent_deep,
                relief=tk.FLAT, bd=0, highlightthickness=1,
                highlightbackground="#D7DCE3", highlightcolor="#A8C7FA",
                takefocus=False, font=("Calibri", 8), pady=4, cursor="hand2",
            ).grid(row=0, column=column, sticky="ew", padx=(0 if column == 0 else 2, 0 if column == 3 else 2))

        self._initialize_file_visibility_icons()
        # Root project rows do not need the standard 17 px expand-indicator
        # gutter.  A small transparent spacer keeps the eye comfortably inset
        # without shifting the row's selection background.
        project_tree_style = "ProjectFiles.Treeview"
        self.project_file_tree_spacer = tk.PhotoImage(master=self.root, width=8, height=1)
        project_tree_spacer_element = "ProjectFiles.Treeitem.spacer"
        if project_tree_spacer_element not in self.style.element_names():
            self.style.element_create(
                project_tree_spacer_element,
                "image",
                self.project_file_tree_spacer,
            )
        self.style.layout(
            f"{project_tree_style}.Item",
            [
                (
                    "Treeitem.padding",
                    {
                        "sticky": "nswe",
                        "children": [
                            (project_tree_spacer_element, {"side": "left", "sticky": ""}),
                            ("Treeitem.image", {"side": "left", "sticky": ""}),
                            ("Treeitem.text", {"sticky": "nswe"}),
                        ],
                    },
                )
            ],
        )
        # Keep row/selection backgrounds flush with the tree edges; only the
        # transparent spacer above offsets the eye icon.
        self.style.configure(
            project_tree_style,
            padding=(0, 0, 0, 0),
            bordercolor=self.ui_border,
            lightcolor=self.ui_border,
            darkcolor=self.ui_border,
        )
        self.style.map(
            project_tree_style,
            bordercolor=[("focus", self.ui_border), ("!focus", self.ui_border)],
        )
        self.file_tree = ttk.Treeview(
            file_card,
            selectmode="browse",
            show="tree headings",
            height=13,
            style=project_tree_style,
        )
        self.file_tree.heading("#0", text="Project Files")
        self.file_tree.pack(fill=tk.BOTH, expand=True, pady=(2, 0))
        self.file_tree.bind("<Button-1>", self.on_file_click)
        self.file_tree.bind("<Button-3>", self.on_file_right_click)
        self.file_tree.bind("<<TreeviewSelect>>", self._update_selected_file_summary)

        selected_card = tk.LabelFrame(
            parent, text="Selected File", bg=self.ui_surface, fg=self.ui_text,
            font=self.ui_font_bold, padx=8, pady=8,
            highlightbackground=self.ui_border, highlightthickness=1, bd=0,
        )
        selected_card.pack(fill=tk.X, padx=10, pady=(0, 8))
        self.lbl_selected_file = tk.Label(
            selected_card, text="No file selected", bg=self.ui_surface,
            fg=self.ui_muted, font=self.ui_font, anchor="w", justify="left",
        )
        self.lbl_selected_file.pack(fill=tk.X, pady=(0, 6))
        tk.Button(
            selected_card, text="Export Selected XY", command=self.export_xy_data,
            bg=self.ui_button_light, fg=self.ui_button_dark,
            activebackground="#E8EAED", activeforeground=self.ui_text,
            relief=tk.FLAT, bd=0, font=self.ui_font_bold, pady=6, cursor="hand2",
        ).pack(fill=tk.X)

        output_card = tk.LabelFrame(
            parent, text="Plot Output", bg=self.ui_surface, fg=self.ui_text,
            font=self.ui_font_bold, padx=8, pady=8,
            highlightbackground=self.ui_border, highlightthickness=1, bd=0,
        )
        output_card.pack(fill=tk.X, padx=10, pady=(0, 12))
        output_card.grid_columnconfigure(0, weight=1, uniform="data_output")
        output_card.grid_columnconfigure(1, weight=1, uniform="data_output")
        tk.Button(
            output_card, text="Save Image", command=self.save_image,
            bg=self.ui_accent, fg="#FFFFFF", activebackground=self.ui_accent_deep,
            activeforeground="#FFFFFF", relief=tk.FLAT, bd=0,
            font=self.ui_font_bold, pady=6, cursor="hand2",
        ).grid(row=0, column=0, sticky="ew", padx=(0, 3))
        tk.Button(
            output_card, text="Copy Plot", command=self.copy_plot_to_clipboard,
            bg=self.ui_button_light, fg=self.ui_button_dark,
            activebackground="#E8EAED", activeforeground=self.ui_text,
            relief=tk.FLAT, bd=0, font=self.ui_font_bold, pady=6, cursor="hand2",
        ).grid(row=0, column=1, sticky="ew", padx=(3, 0))

        canvas_card = tk.Frame(
            output_card,
            bg=self.ui_bg,
            highlightbackground=self.ui_border,
            highlightthickness=1,
            bd=0,
            padx=9,
            pady=8,
        )
        canvas_card.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        canvas_card.columnconfigure(0, weight=1, uniform="canvas_sizing")
        canvas_card.columnconfigure(1, weight=1, uniform="canvas_sizing")
        tk.Label(
            canvas_card, text="CANVAS SIZING", bg=self.ui_bg, fg=self.ui_muted,
            font=(self.ui_font_family, 8, "bold"), anchor="w",
        ).grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 4))
        self.var_panel_canvas_mode = tk.StringVar(value=self.panel_canvas_mode)
        self.radio_panel_canvas_fit = self._themed_radio_button(
            canvas_card, "Fit to Window", self.var_panel_canvas_mode,
            "fit", self.on_panel_canvas_mode_change, self.ui_bg,
        )
        self.radio_panel_canvas_fit.grid(row=1, column=0, sticky="w", padx=(0, 8))
        self.radio_panel_canvas_preserve = self._themed_radio_button(
            canvas_card, "Preserve Plot Ratio", self.var_panel_canvas_mode,
            "preserve", self.on_panel_canvas_mode_change, self.ui_bg,
        )
        self.radio_panel_canvas_preserve.grid(row=1, column=1, sticky="w", padx=(8, 0))
        tk.Label(
            canvas_card,
            text="Preserve mode expands the canvas when panels are added.",
            bg=self.ui_bg, fg=self.ui_muted, font=(self.ui_font_family, 9),
            anchor="w", justify=tk.LEFT, wraplength=310,
        ).grid(row=2, column=0, columnspan=2, sticky="ew", pady=(4, 0))

    def _update_selected_file_summary(self, _event=None):
        if not hasattr(self, "lbl_selected_file"):
            return
        selection = self.file_tree.selection()
        loader = self.loaded_files.get(selection[0]) if selection else None
        if loader is None:
            self.lbl_selected_file.configure(text="No file selected")
            return
        self.lbl_selected_file.configure(
            text=(f"{loader.filename}\n{getattr(loader, 'source_format', 'Profex / BGMN DIA')}\n"
                  f"{len(loader.x):,} data points · {len(loader.phase_names)} phase curve(s)"
                  + ("\nBackground not provided" if not loader.back else ""))
        )

    def _setup_layers_tab(self):
        header = tk.Frame(self.tab_layers, bg=self.ui_bg)
        header.pack(fill=tk.X, padx=10, pady=(12, 7))
        tk.Label(
            header,
            text="LAYERS",
            bg=self.ui_bg,
            fg=self.ui_text,
            anchor="w",
            font=("Calibri", 14, "bold"),
        ).pack(anchor="w")

        ctrl_frame = tk.LabelFrame(
            self.tab_layers,
            text="Offset Tools",
            bg=self.ui_surface,
            fg=self.ui_text,
            font=self.ui_font_bold,
            padx=8,
            pady=8,
            highlightbackground=self.ui_border,
            highlightthickness=1,
            bd=0,
        )
        ctrl_frame.pack(fill=tk.X, padx=10, pady=(0, 8))

        step_row = tk.Frame(ctrl_frame, bg=self.ui_surface)
        step_row.pack(fill=tk.X, pady=(0, 5))
        tk.Label(
            step_row,
            text="Offset step",
            bg=self.ui_surface,
            fg=self.ui_muted,
            anchor="w",
            font=self.ui_font,
        ).pack(side=tk.LEFT, padx=(2, 24))
        self.var_offset_step = tk.StringVar(value="0.05")
        ttk.Combobox(
            step_row,
            textvariable=self.var_offset_step,
            values=["0.01", "0.02", "0.05", "0.1", "0.2"],
            state="readonly",
            width=10,
        ).pack(side=tk.LEFT)

        btn_row = tk.Frame(ctrl_frame, bg=self.ui_surface)
        btn_row.pack(fill=tk.X)
        btn_row.columnconfigure(0, weight=1)
        btn_row.columnconfigure(1, weight=1)
        blue_button = dict(
            bg=self.ui_accent,
            fg="#FFFFFF",
            activebackground=self.ui_accent_deep,
            activeforeground="#FFFFFF",
            relief=tk.FLAT,
            bd=0,
            font=self.ui_font_bold,
            cursor="hand2",
            pady=6,
        )
        tk.Button(
            btn_row,
            text="Stack Files",
            command=self.auto_plot_stack_deferred,
            **blue_button,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 3), pady=(0, 4))
        tk.Button(
            btn_row,
            text="Stack Phases",
            command=self.distribute_offsets_evenly_deferred,
            **blue_button,
        ).grid(row=0, column=1, sticky="ew", padx=(3, 0), pady=(0, 4))
        tk.Button(
            btn_row,
            text="Reset Offsets",
            command=self.reset_offsets_deferred,
            bg=self.ui_button_light,
            fg=self.ui_muted,
            activebackground="#E3E6EA",
            activeforeground=self.ui_text,
            relief=tk.FLAT,
            bd=0,
            font=self.ui_font,
            cursor="hand2",
            pady=6,
        ).grid(row=1, column=0, columnspan=2, sticky="ew")

        plot_layout_frame = tk.LabelFrame(
            self.tab_layers,
            text="Plot Layout",
            bg=self.ui_surface,
            fg=self.ui_text,
            font=self.ui_font_bold,
        )
        plot_layout_frame.grid_columnconfigure(0, weight=1, uniform="layer_plot_layout")
        plot_layout_frame.grid_columnconfigure(1, weight=1, uniform="layer_plot_layout")

        self.var_plot_layout = tk.StringVar(value=self.plot_layout_mode)
        tk.Radiobutton(
            plot_layout_frame,
            text="Combined",
            variable=self.var_plot_layout,
            value="combined",
            command=self._request_draw_plot,
            bg=self.ui_surface,
            activebackground=self.ui_surface,
            anchor="w",
            highlightthickness=0,
            bd=0,
        ).grid(row=0, column=0, sticky="w", padx=(2, 8), pady=2)
        tk.Radiobutton(
            plot_layout_frame,
            text="Split by File",
            variable=self.var_plot_layout,
            value="split",
            command=self._request_draw_plot,
            bg=self.ui_surface,
            activebackground=self.ui_surface,
            anchor="w",
            highlightthickness=0,
            bd=0,
        ).grid(row=0, column=1, sticky="w", padx=(8, 2), pady=2)

        quick_tools_frame = tk.LabelFrame(
            self.tab_layers,
            text="Quick Tools",
            bg=self.ui_surface,
            fg=self.ui_text,
            font=self.ui_font_bold,
        )
        for column in range(3):
            quick_tools_frame.grid_columnconfigure(column, weight=1, uniform="quick_tools")
        quick_tools_font = self.ui_font
        self.btn_cross = tk.Button(
            quick_tools_frame,
            text="Crosshair",
            command=self.toggle_crosshair_state,
            bg=self.ui_button_light,
            font=quick_tools_font,
        )
        self.btn_cross.grid(row=0, column=0, sticky="ew", padx=3, pady=3)
        self.btn_bg = tk.Button(
            quick_tools_frame,
            text="Subtract BG",
            command=self.toggle_bg_sub_state,
            bg=self.ui_button_light,
            font=quick_tools_font,
        )
        self.btn_bg.grid(row=0, column=1, sticky="ew", padx=3, pady=3)
        set_x_range_button = tk.Button(
            quick_tools_frame,
            text="Set X Range",
            command=self.open_xscale_dialog,
            bg=self.ui_button_light,
            font=quick_tools_font,
        )
        set_x_range_button.grid(row=0, column=2, sticky="ew", padx=3, pady=3)
        for button in (self.btn_cross, self.btn_bg, set_x_range_button):
            button._ui2_preserve_font = True

        for frame, title in (
            (plot_layout_frame, "Plot Layout"),
            (quick_tools_frame, "Quick Tools"),
        ):
            self._style_settings_card(frame)
            self._normalize_section_controls(frame)
            frame.pack(fill=tk.X, padx=10, pady=(0, 8))
            self._make_plot_card_collapsible(frame, title, expanded=True)

        # Same-name phase colors are synchronized automatically.  Keep the
        # variable only for template/backward compatibility; no manual toggle
        # or "Sync Now" action is needed in the Layers UI.
        self.var_link_phase_colors = tk.BooleanVar(value=True)

        order_card = tk.LabelFrame(
            self.tab_layers,
            text="Layer Order & Style",
            bg=self.ui_surface,
            fg=self.ui_text,
            font=self.ui_font_bold,
            padx=8,
            pady=8,
            highlightbackground=self.ui_border,
            highlightthickness=1,
            bd=0,
        )
        order_card.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 12))
        self.layer_scroll = ScrollableFrame(order_card, bg=self.ui_surface)
        self.layer_scroll.pack(fill=tk.BOTH, expand=True)
        self.layer_frame = self.layer_scroll.scrollable_frame

    def _setup_export_tab(self):
        parent = getattr(self, "tab_export_body", self.tab_export)
        header = tk.Frame(parent, bg=self.ui_bg)
        header.pack(fill=tk.X, padx=10, pady=(12, 7))
        tk.Label(
            header,
            text="OUTPUT",
            bg=self.ui_bg,
            fg=self.ui_text,
            font=("Calibri", 14, "bold"),
            anchor="w",
        ).pack(anchor="w")

        def card(title):
            frame = tk.LabelFrame(
                parent,
                text=title,
                bg=self.ui_surface,
                fg=self.ui_text,
                font=self.ui_font_bold,
                padx=8,
                pady=8,
                highlightbackground=self.ui_border,
                highlightthickness=1,
                bd=0,
            )
            frame.pack(fill=tk.X, padx=10, pady=(0, 8))
            return frame

        def output_button(frame, text, command, primary=False):
            return tk.Button(
                frame,
                text=text,
                command=command,
                bg=self.ui_accent if primary else self.ui_button_light,
                fg="#FFFFFF" if primary else self.ui_button_dark,
                activebackground=self.ui_accent_deep if primary else "#E3E6EA",
                activeforeground="#FFFFFF" if primary else self.ui_text,
                relief=tk.FLAT,
                bd=0,
                font=self.ui_font_bold,
                pady=6,
                cursor="hand2",
            )

        exp_frame = card("Export")
        for column in range(2):
            exp_frame.columnconfigure(column, weight=1, uniform="output_export")
        output_button(exp_frame, "Save Image", self.save_image, primary=True).grid(
            row=0, column=0, sticky="ew", padx=(0, 3), pady=(0, 5)
        )
        output_button(exp_frame, "Copy Plot", self.copy_plot_to_clipboard).grid(
            row=0, column=1, sticky="ew", padx=(3, 0), pady=(0, 5)
        )
        output_button(exp_frame, "SVG / PDF Artwork", self.export_vector_artwork).grid(
            row=1, column=0, sticky="ew", padx=(0, 3)
        )
        output_button(exp_frame, "Selected XY", self.export_xy_data).grid(
            row=1, column=1, sticky="ew", padx=(3, 0)
        )

        tpl_frame = card("Template")
        for column in range(2):
            tpl_frame.columnconfigure(column, weight=1, uniform="output_template")
        output_button(tpl_frame, "Save Template", self.save_template, primary=True).grid(
            row=0, column=0, sticky="ew", padx=(0, 3)
        )
        output_button(tpl_frame, "Load Template", self.load_template).grid(
            row=0, column=1, sticky="ew", padx=(3, 0)
        )

        tools_frame = card("Design Tools")
        for column in range(2):
            tools_frame.columnconfigure(column, weight=1, uniform="output_tools")
        output_button(tools_frame, "Open Art Director", self.open_art_director, primary=True).grid(
            row=0, column=0, columnspan=2, sticky="ew", pady=(0, 5)
        )
        output_button(tools_frame, "Style Studio", self.open_style_studio).grid(
            row=1, column=0, sticky="ew", padx=(0, 3)
        )
        output_button(tools_frame, "UI Map", self.open_ui_inventory).grid(
            row=1, column=1, sticky="ew", padx=(3, 0)
        )
        tk.Label(
            tools_frame,
            text="Design tools change visual settings only; loaded files and numeric data remain unchanged.",
            bg=self.ui_surface,
            fg=self.ui_muted,
            justify="left",
            wraplength=300,
            font=self.ui_font,
        ).grid(row=2, column=0, columnspan=2, sticky="ew", pady=(7, 0))
        self._normalize_section_controls(parent)

    def _apply_3d_font_settings(self):
        """Commit the selected view mode and redraw with all 3D/font values."""
        self.is_3d_mode = bool(self.var_3d.get())
        self._draw_plot_now()

    def _setup_3d_tab(self):
        parent = getattr(self, "tab_3d_body", self.tab_3d)
        if not getattr(self, "_plot_sections_embedded", False):
            self._tab_banner(parent, "Art & 3D", "Depth controls, typography, and dimensional figure effects live here.", self.ui_accent_deep)

        mode_frame = tk.LabelFrame(parent, text="View Mode", bg=self.ui_panel, font=self.ui_font_bold)
        mode_frame.pack(fill=tk.X, pady=5)
        mode_frame.columnconfigure(0, weight=1)
        mode_frame.columnconfigure(1, weight=1)
        tk.Radiobutton(
            mode_frame,
            text="2D Plot",
            variable=self.var_3d,
            value=False,
            bg=self.ui_panel,
        ).grid(row=0, column=0, sticky="w", padx=5, pady=3)
        tk.Radiobutton(
            mode_frame,
            text="3D Waterfall",
            variable=self.var_3d,
            value=True,
            bg=self.ui_panel,
        ).grid(row=0, column=1, sticky="w", padx=5, pady=3)

        btn_apply = self._accent_button(
            mode_frame,
            "Apply 3D/Font Settings",
            self._apply_3d_font_settings,
            self.ui_accent,
        )
        btn_apply.grid(
            row=1,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=5,
            pady=(3, 1),
        )

        # 3D Settings
        d3_frame = tk.LabelFrame(parent, text="3D View Settings", bg=self.ui_panel, font=self.ui_font_bold)
        d3_frame.pack(fill=tk.X, pady=5)
        
        def add_slider(parent, label, vmin, vmax, vinit, attr):
            f = tk.Frame(parent, bg=self.ui_panel); f.pack(fill=tk.X, padx=5, pady=2)
            tk.Label(f, text=label, width=10, bg=self.ui_panel, anchor='w').pack(side='left')
            var = tk.DoubleVar(value=vinit)
            setattr(self, attr, var)
            # Removed command=self.draw_plot
            ModernScale(f, from_=vmin, to=vmax, orient='horizontal', variable=var, showvalue=False, bg=self.ui_panel).pack(side='left', fill='x', expand=True)
            tk.Entry(f, textvariable=var, width=5).pack(side='left')
        
        add_slider(d3_frame, "Elevation", -90, 90, 30, "var_elev")
        add_slider(d3_frame, "Azimuth", -180, 180, -45, "var_azim")
        add_slider(d3_frame, "Distance", 1, 50, 10, "var_dist")
        
        # Axis & Ticks
        ax_frame = tk.LabelFrame(parent, text="Axis & Ticks", bg=self.ui_panel, font=self.ui_font_bold)
        ax_frame.pack(fill=tk.X, pady=5)
        
        # Y Label
        yl_frame = tk.Frame(ax_frame, bg=self.ui_panel); yl_frame.pack(fill='x', padx=5, pady=2)
        tk.Label(yl_frame, text="Y Label:", bg=self.ui_panel).pack(side='left')
        self.var_ylabel = tk.StringVar(value="Scan / Depth")
        tk.Entry(yl_frame, textvariable=self.var_ylabel).pack(side='left', fill='x', expand=True)
        # Removed immediate set button, use Apply

        # Tick Dir
        td_frame = tk.Frame(ax_frame, bg=self.ui_panel); td_frame.pack(fill='x', padx=5, pady=2)
        tk.Label(td_frame, text="Tick Dir:", bg=self.ui_panel).pack(side='left')
        self.cmb_tick_dir = ttk.Combobox(td_frame, values=["in", "out", "inout", "none"], state="readonly", width=8)
        self.cmb_tick_dir.set("in")
        self.cmb_tick_dir.pack(side='left', padx=5)
        # Removed bind

        # Tick Vis
        vis_frame = tk.Frame(ax_frame, bg=self.ui_panel); vis_frame.pack(fill='x', padx=5, pady=2)
        self.var_tick_x = tk.BooleanVar(value=True)
        self.var_tick_y = tk.BooleanVar(value=False)
        self.var_tick_z = tk.BooleanVar(value=False)
        # Removed commands
        tk.Checkbutton(vis_frame, text="X Label", variable=self.var_tick_x, bg=self.ui_panel).pack(side='left')
        tk.Checkbutton(vis_frame, text="Y Label", variable=self.var_tick_y, bg=self.ui_panel).pack(side='left')
        tk.Checkbutton(vis_frame, text="Z Label", variable=self.var_tick_z, bg=self.ui_panel).pack(side='left')

        # Global Scaling
        sc_frame = tk.LabelFrame(parent, text="Global Scaling Factors", bg=self.ui_panel, font=self.ui_font_bold)
        sc_frame.pack(fill=tk.X, pady=5)
        
        add_slider(sc_frame, "Int Scale", 0.1, 5.0, 1.0, "var_int_scale")
        add_slider(sc_frame, "Depth Scale", 0.1, 5.0, 1.0, "var_depth_scale")
        
        # Font Settings
        font_frame = tk.LabelFrame(parent, text="Font Settings", bg=self.ui_panel, font=self.ui_font_bold)
        font_frame.pack(fill=tk.X, pady=5)

        self._build_plot_font_selector(font_frame)
        
        f1 = tk.Frame(font_frame, bg=self.ui_panel); f1.pack(fill=tk.X, padx=5)
        tk.Label(f1, text="Title Size:", bg=self.ui_panel).pack(side='left')
        ModernScale(f1, from_=8, to=72, orient='horizontal', variable=self.var_title_size, bg=self.ui_panel).pack(side='left', fill='x', expand=True)
        
        f2 = tk.Frame(font_frame, bg=self.ui_panel); f2.pack(fill=tk.X, padx=5)
        tk.Label(f2, text="Axis Size:", bg=self.ui_panel).pack(side='left')
        ModernScale(f2, from_=6, to=72, orient='horizontal', variable=self.var_axis_size, bg=self.ui_panel).pack(side='left', fill='x', expand=True)

        # Apply button handles this
        self._normalize_section_controls(parent)

    def _toggle_quick_phase_peaks(self):
        """Redraw the 2D layout immediately after changing the peak panel."""
        self.show_phase_peaks_top = bool(self.var_show_phase_peaks_top.get())
        self._draw_plot_now()
        if hasattr(self, "_sync_plot_canvas_viewport"):
            self.root.after_idle(self._sync_plot_canvas_viewport)

    def _setup_plot_tab(self):
        self._create_plot_section_shell()
        quick_parent = self.plot_section_bodies["quick"]
        style_parent = self.plot_section_bodies["style"]
        advanced_parent = self.plot_section_bodies["advanced"]

        vis_frame = tk.LabelFrame(quick_parent, text="Legend", bg=self.ui_panel, font=self.ui_font_bold)
        vis_frame.pack(fill=tk.X, pady=5)

        plot_show_legend_control = tk.Checkbutton(
            vis_frame, text="Show Legend", variable=self.var_show_legend,
            command=self._request_draw_plot, bg=self.ui_panel
        )
        plot_show_legend_control.pack(anchor='w', padx=5)
        self.var_show_phase_peaks_top = tk.BooleanVar(value=self.show_phase_peaks_top)
        plot_show_phase_peaks_control = tk.Checkbutton(
            vis_frame, text="Show Top Phase Peaks", variable=self.var_show_phase_peaks_top,
            command=self._request_draw_plot, bg=self.ui_panel
        )
        plot_show_phase_peaks_control.pack(anchor='w', padx=5)
        plot_show_residual_control = tk.Checkbutton(
            vis_frame, text="Show Residual", variable=self.var_show_residual,
            command=self._request_draw_plot, bg=self.ui_panel
        )
        plot_show_residual_control.pack(anchor='w', padx=5)

        self.var_legend_transparent = tk.BooleanVar(value=self.legend_transparent)
        tk.Checkbutton(
            vis_frame,
            text="Legend Transparent",
            variable=self.var_legend_transparent,
            command=self._request_draw_plot,
            bg=self.ui_panel,
        ).pack(anchor='w', padx=5, pady=2)

        legend_size_row = tk.Frame(vis_frame, bg=self.ui_panel)
        legend_size_row.pack(fill='x', padx=5, pady=(4, 2))
        legend_size_row.columnconfigure(1, weight=1)
        tk.Label(
            legend_size_row,
            text="Legend Size:",
            anchor='w',
            bg=self.ui_panel,
        ).grid(row=0, column=0, columnspan=4, sticky='w', pady=(2, 0))
        self.var_legend_font_size = tk.IntVar(value=self.legend_font_size)
        self.scale_legend_font_size = ModernScale(
            legend_size_row,
            from_=6,
            to=30,
            orient='horizontal',
            variable=self.var_legend_font_size,
            command=lambda v: self._request_draw_plot(),
            showvalue=False,
            length=170,
            bg=self.ui_panel
        )
        self.scale_legend_font_size.grid(
            row=1, column=0, columnspan=2, sticky='ew', padx=(6, 5), pady=(0, 3)
        )
        self.ent_legend_size = tk.Entry(legend_size_row, textvariable=self.var_legend_font_size, width=4)
        self.ent_legend_size.grid(row=1, column=2, sticky='w', padx=(0, 8), pady=(0, 3))
        self.ent_legend_size.bind("<Return>", lambda e: self._request_draw_plot())
        self.ent_legend_size.bind("<FocusOut>", lambda e: self._request_draw_plot())
        self.var_legend_bold = tk.BooleanVar(value=getattr(self, "legend_bold", False))
        self.chk_legend_bold = tk.Checkbutton(
            legend_size_row,
            text="Bold",
            variable=self.var_legend_bold,
            command=self._request_draw_plot,
            bg=self.ui_panel,
        )
        self.chk_legend_bold.grid(row=1, column=3, sticky='e', pady=(0, 3))

        max_width_label = tk.Label(legend_size_row, text="Max Width %:", bg=self.ui_panel)
        max_width_label.grid(row=2, column=0, columnspan=4, sticky='w', pady=(4, 0))
        self.var_legend_max_width = tk.IntVar(value=int(self.legend_max_width_ratio * 100))
        self.scale_legend_max_width = ModernScale(
            legend_size_row,
            from_=40,
            to=100,
            orient='horizontal',
            variable=self.var_legend_max_width,
            command=lambda v: self._request_draw_plot(),
            showvalue=False,
            length=170,
            bg=self.ui_panel
        )
        self.scale_legend_max_width.grid(
            row=3, column=0, columnspan=2, sticky='ew', padx=(6, 5), pady=(0, 3)
        )
        self.ent_legend_max_width = tk.Entry(legend_size_row, textvariable=self.var_legend_max_width, width=4)
        self.ent_legend_max_width.grid(row=3, column=2, sticky='w', padx=(0, 8), pady=(0, 3))
        self.ent_legend_max_width.bind("<Return>", lambda e: self._request_draw_plot())
        self.ent_legend_max_width.bind("<FocusOut>", lambda e: self._request_draw_plot())

        legend_opt_frame = tk.Frame(vis_frame, bg=self.ui_panel)
        legend_opt_frame.pack(fill='x', padx=5, pady=2)
        legend_opt_frame.columnconfigure(1, weight=1, uniform="legend_combo")
        legend_opt_frame.columnconfigure(3, weight=1, uniform="legend_combo")

        tk.Label(legend_opt_frame, text="Orientation:", bg=self.ui_panel).grid(row=0, column=0, sticky='w', pady=2)
        self.var_legend_orientation = tk.StringVar(value=self.legend_orientation)
        self.cmb_legend_orientation = ttk.Combobox(
            legend_opt_frame,
            textvariable=self.var_legend_orientation,
            values=["vertical", "horizontal"],
            state="readonly",
            width=11
        )
        self.cmb_legend_orientation.grid(row=0, column=1, sticky='ew', padx=(4, 8), pady=2)
        self.cmb_legend_orientation.bind(
            "<<ComboboxSelected>>",
            lambda _event: self._refresh_legend_layout_controls(),
        )

        tk.Label(legend_opt_frame, text="Location:", bg=self.ui_panel).grid(row=0, column=2, sticky='e', pady=2)
        self.var_legend_location = tk.StringVar(value=self.legend_location)
        self.cmb_legend_location = ttk.Combobox(
            legend_opt_frame,
            textvariable=self.var_legend_location,
            values=["auto", "upper right", "upper left", "upper center", "lower right", "lower left", "lower center", "center right", "center left", "center"],
            state="readonly",
            width=11
        )
        self.cmb_legend_location.grid(row=0, column=3, sticky='ew', padx=(4, 0), pady=2)
        self.cmb_legend_location.bind("<<ComboboxSelected>>", lambda e: self._request_draw_plot())

        legend_wrap_row = legend_opt_frame
        wrap_label = tk.Label(legend_wrap_row, text="Wrap:", bg=self.ui_panel)
        wrap_label.grid(row=1, column=0, sticky='w', pady=2)
        legend_column_mode = "custom" if self.legend_column_mode == "manual" else self.legend_column_mode
        self.var_legend_column_mode = tk.StringVar(value=legend_column_mode)
        self.cmb_legend_column_mode = ttk.Combobox(
            legend_wrap_row,
            textvariable=self.var_legend_column_mode,
            values=["auto", "custom"],
            state="readonly",
            width=11
        )
        self.cmb_legend_column_mode.grid(row=1, column=1, sticky='ew', padx=(4, 8), pady=2)
        self.cmb_legend_column_mode.bind("<<ComboboxSelected>>", lambda e: self._request_draw_plot())

        column_label = tk.Label(legend_wrap_row, text="Column:", bg=self.ui_panel)
        column_label.grid(row=1, column=2, sticky='e', pady=2)
        self.var_legend_ncol = tk.IntVar(value=self.legend_ncol)
        self.ent_legend_ncol = tk.Entry(legend_wrap_row, textvariable=self.var_legend_ncol, width=4)
        self.ent_legend_ncol.grid(row=1, column=3, sticky='w', padx=(4, 0), pady=2)
        self.ent_legend_ncol.bind("<Return>", lambda e: self._request_draw_plot())
        self.ent_legend_ncol.bind("<FocusOut>", lambda e: self._request_draw_plot())

        self.legend_horizontal_only_labels = (wrap_label, column_label, max_width_label)
        self._refresh_legend_layout_controls(redraw=False)

        phase_label_frame = tk.LabelFrame(quick_parent, text="Phase Peaks", bg=self.ui_panel, font=self.ui_font_bold)
        phase_label_frame.pack(fill=tk.X, pady=5)
        tk.Label(phase_label_frame, text="Phase Labels", bg=self.ui_panel, fg=self.ui_text, font=self.ui_font_bold).pack(anchor='w', padx=5, pady=(3, 0))
        self.var_show_phase_display_labels = tk.BooleanVar(value=self.show_phase_display_labels)
        tk.Checkbutton(
            phase_label_frame,
            text="Show Phase Labels",
            variable=self.var_show_phase_display_labels,
            command=self._request_draw_plot,
            bg=self.ui_panel
        ).pack(anchor='w', padx=5, pady=(2, 1))

        phase_label_size_row = tk.Frame(phase_label_frame, bg=self.ui_panel)
        phase_label_size_row.pack(fill='x', padx=5, pady=2)
        phase_label_size_row.columnconfigure(1, weight=1)
        tk.Label(
            phase_label_size_row,
            text="Phase Label Size:",
            anchor='w',
            bg=self.ui_panel,
        ).grid(row=0, column=0, columnspan=4, sticky='w', pady=(2, 0))
        self.var_phase_display_label_size = tk.IntVar(value=self.phase_display_label_size)
        self.scale_phase_display_label_size = ModernScale(
            phase_label_size_row,
            from_=6,
            to=30,
            orient='horizontal',
            variable=self.var_phase_display_label_size,
            command=lambda v: self._request_draw_plot(),
            showvalue=False,
            length=170,
            bg=self.ui_panel
        )
        self.scale_phase_display_label_size.grid(
            row=1, column=0, columnspan=2, sticky='ew', padx=(6, 5), pady=(0, 3)
        )
        self.ent_phase_display_label_size = tk.Entry(
            phase_label_size_row,
            textvariable=self.var_phase_display_label_size,
            width=4,
        )
        self.ent_phase_display_label_size.grid(row=1, column=2, sticky='w', padx=(0, 8), pady=(0, 3))
        self.ent_phase_display_label_size.bind("<Return>", lambda e: self._request_draw_plot())
        self.ent_phase_display_label_size.bind("<FocusOut>", lambda e: self._request_draw_plot())
        self.var_phase_display_label_bold = tk.BooleanVar(value=self.phase_display_label_bold)
        self.chk_phase_display_label_bold = tk.Checkbutton(
            phase_label_size_row,
            text="Bold",
            variable=self.var_phase_display_label_bold,
            command=self._request_draw_plot,
            bg=self.ui_panel
        )
        self.chk_phase_display_label_bold.grid(row=1, column=3, sticky='e', pady=(0, 3))

        phase_label_position_row = tk.Frame(phase_label_frame, bg=self.ui_panel)
        phase_label_position_row.pack(fill='x', padx=5, pady=2)
        tk.Label(
            phase_label_position_row,
            text="Position:",
            width=12,
            anchor='w',
            bg=self.ui_panel,
        ).grid(row=0, column=0, sticky='w')
        self.var_phase_display_label_position = tk.StringVar(value=self.phase_display_label_position)
        self.cmb_phase_label_position = ttk.Combobox(
            phase_label_position_row,
            textvariable=self.var_phase_display_label_position,
            values=["right", "left", "below", "above"],
            state="readonly",
            width=12,
        )
        self.cmb_phase_label_position.grid(row=0, column=1, sticky='w', padx=(6, 0))
        self.cmb_phase_label_position.bind(
            "<<ComboboxSelected>>", lambda e: self._request_draw_plot()
        )

        phase_label_offset_row = tk.Frame(phase_label_frame, bg=self.ui_panel)
        phase_label_offset_row.pack(fill='x', padx=5, pady=2)
        phase_label_offset_row.columnconfigure(1, weight=1)
        tk.Label(phase_label_offset_row, text="Vertical Shift:", bg=self.ui_panel).grid(
            row=0, column=0, columnspan=3, sticky='w', pady=(2, 0)
        )
        self.var_phase_label_vertical_shift = tk.DoubleVar(value=self.phase_label_vertical_shift)
        self.scale_phase_label_vertical_shift = ModernScale(
            phase_label_offset_row,
            from_=-0.5,
            to=0.5,
            resolution=0.01,
            orient='horizontal',
            variable=self.var_phase_label_vertical_shift,
            command=lambda v: self._request_draw_plot(),
            showvalue=False,
            length=170,
            bg=self.ui_panel
        )
        self.scale_phase_label_vertical_shift.grid(
            row=1, column=0, columnspan=2, sticky='ew', padx=(6, 5), pady=(0, 3)
        )
        self.ent_phase_label_vertical_shift = tk.Entry(
            phase_label_offset_row, textvariable=self.var_phase_label_vertical_shift, width=5
        )
        self.ent_phase_label_vertical_shift.grid(row=1, column=2, sticky='w', pady=(0, 3))
        self.ent_phase_label_vertical_shift.bind("<Return>", lambda e: self._request_draw_plot())
        self.ent_phase_label_vertical_shift.bind("<FocusOut>", lambda e: self._request_draw_plot())

        tk.Frame(phase_label_frame, height=1, bg=self.ui_border).pack(fill='x', padx=5, pady=(6, 4))
        tk.Label(phase_label_frame, text="Sample Labels", bg=self.ui_panel, fg=self.ui_text, font=self.ui_font_bold).pack(anchor='w', padx=5)
        self.var_show_sample_labels = tk.BooleanVar(value=self.show_sample_labels)
        tk.Checkbutton(
            phase_label_frame,
            text="Show Sample Labels",
            variable=self.var_show_sample_labels,
            command=self._request_draw_plot,
            bg=self.ui_panel
        ).pack(anchor='w', padx=5, pady=(2, 1))

        sample_size_row = tk.Frame(phase_label_frame, bg=self.ui_panel)
        sample_size_row.pack(fill='x', padx=5, pady=2)
        sample_size_row.columnconfigure(1, weight=1)
        tk.Label(
            sample_size_row,
            text="Sample Label Size:",
            anchor='w',
            bg=self.ui_panel,
        ).grid(row=0, column=0, columnspan=4, sticky='w', pady=(2, 0))
        self.var_sample_label_size = tk.IntVar(value=self.sample_label_size)
        self.scale_sample_label_size = ModernScale(
            sample_size_row,
            from_=6,
            to=30,
            orient='horizontal',
            variable=self.var_sample_label_size,
            command=lambda v: self._request_draw_plot(),
            showvalue=False,
            length=170,
            bg=self.ui_panel
        )
        self.scale_sample_label_size.grid(
            row=1, column=0, columnspan=2, sticky='ew', padx=(6, 5), pady=(0, 3)
        )
        self.ent_sample_label_size = tk.Entry(
            sample_size_row,
            textvariable=self.var_sample_label_size,
            width=4,
        )
        self.ent_sample_label_size.grid(row=1, column=2, sticky='w', padx=(0, 8), pady=(0, 3))
        self.ent_sample_label_size.bind("<Return>", lambda e: self._request_draw_plot())
        self.ent_sample_label_size.bind("<FocusOut>", lambda e: self._request_draw_plot())
        self.var_sample_label_bold = tk.BooleanVar(value=self.sample_label_bold)
        self.chk_sample_label_bold = tk.Checkbutton(
            sample_size_row,
            text="Bold",
            variable=self.var_sample_label_bold,
            command=self._request_draw_plot,
            bg=self.ui_panel
        )
        self.chk_sample_label_bold.grid(row=1, column=3, sticky='e', pady=(0, 3))

        sample_label_position_row = tk.Frame(phase_label_frame, bg=self.ui_panel)
        sample_label_position_row.pack(fill='x', padx=5, pady=2)
        tk.Label(
            sample_label_position_row,
            text="Position:",
            width=12,
            anchor='w',
            bg=self.ui_panel,
        ).grid(row=0, column=0, sticky='w')
        self.var_sample_label_position = tk.StringVar(value=self.sample_label_position)
        self.cmb_sample_label_position = ttk.Combobox(
            sample_label_position_row,
            textvariable=self.var_sample_label_position,
            values=["right", "left", "below", "above"],
            state="readonly",
            width=12,
        )
        self.cmb_sample_label_position.grid(row=0, column=1, sticky='w', padx=(6, 0))
        self.cmb_sample_label_position.bind(
            "<<ComboboxSelected>>", lambda e: self._request_draw_plot()
        )

        sample_label_offset_row = tk.Frame(phase_label_frame, bg=self.ui_panel)
        sample_label_offset_row.pack(fill='x', padx=5, pady=(2, 5))
        sample_label_offset_row.columnconfigure(1, weight=1)
        tk.Label(sample_label_offset_row, text="Vertical Shift:", bg=self.ui_panel).grid(
            row=0, column=0, columnspan=3, sticky='w', pady=(2, 0)
        )
        self.var_sample_label_vertical_shift = tk.DoubleVar(value=self.sample_label_vertical_shift)
        self.scale_sample_label_vertical_shift = ModernScale(
            sample_label_offset_row,
            from_=-0.5,
            to=0.5,
            resolution=0.01,
            orient='horizontal',
            variable=self.var_sample_label_vertical_shift,
            command=lambda v: self._request_draw_plot(),
            showvalue=False,
            length=170,
            bg=self.ui_panel
        )
        self.scale_sample_label_vertical_shift.grid(
            row=1, column=0, columnspan=2, sticky='ew', padx=(6, 5), pady=(0, 3)
        )
        self.ent_sample_label_vertical_shift = tk.Entry(
            sample_label_offset_row, textvariable=self.var_sample_label_vertical_shift, width=5
        )
        self.ent_sample_label_vertical_shift.grid(row=1, column=2, sticky='w', pady=(0, 3))
        self.ent_sample_label_vertical_shift.bind("<Return>", lambda e: self._request_draw_plot())
        self.ent_sample_label_vertical_shift.bind("<FocusOut>", lambda e: self._request_draw_plot())

        ref_frame = tk.LabelFrame(quick_parent, text="Reference Peaks", bg=self.ui_panel, font=self.ui_font_bold)
        ref_frame.pack(fill=tk.X, pady=5)
        self.var_reference_peaks_enabled = tk.BooleanVar(value=self.reference_peaks_enabled)
        plot_show_reference_control = tk.Checkbutton(
            ref_frame,
            text="Show reference stick patterns",
            variable=self.var_reference_peaks_enabled,
            command=self._request_draw_plot,
            bg=self.ui_panel,
        )
        plot_show_reference_control.pack(anchor='w', padx=5, pady=(3, 1))

        ref_btn_row = tk.Frame(ref_frame, bg=self.ui_panel)
        ref_btn_row.pack(fill='x', padx=5, pady=2)
        ref_btn_row.columnconfigure(0, weight=1)
        ref_btn_row.columnconfigure(1, weight=1)
        tk.Button(ref_btn_row, text="Add CIF", command=self.add_reference_cif_dialog, bg=self.ui_button_light, font=self.ui_font).grid(row=0, column=0, sticky='ew', padx=2, pady=1)
        tk.Button(ref_btn_row, text="Load Folder", command=self.load_reference_cif_folder_dialog, bg=self.ui_button_light, font=self.ui_font).grid(row=0, column=1, sticky='ew', padx=2, pady=1)
        tk.Button(ref_btn_row, text="Color", command=self.pick_selected_reference_peak_color, bg=self.ui_button_light, font=self.ui_font).grid(row=1, column=0, sticky='ew', padx=2, pady=1)
        tk.Button(ref_btn_row, text="Rename", command=self.rename_selected_reference_peak, bg=self.ui_button_light, font=self.ui_font).grid(row=1, column=1, sticky='ew', padx=2, pady=1)
        tk.Button(ref_btn_row, text="Remove", command=self.remove_selected_reference_peak, bg=self.ui_button_light, font=self.ui_font).grid(row=2, column=0, columnspan=2, sticky='ew', padx=2, pady=1)
        tk.Button(ref_btn_row, text="Move Up", command=lambda: self.move_selected_reference_peak(-1), bg=self.ui_button_light, font=self.ui_font).grid(row=3, column=0, sticky='ew', padx=2, pady=1)
        tk.Button(ref_btn_row, text="Move Down", command=lambda: self.move_selected_reference_peak(1), bg=self.ui_button_light, font=self.ui_font).grid(row=3, column=1, sticky='ew', padx=2, pady=1)

        self.reference_list_container = tk.Frame(
            ref_frame,
            bg=self.ui_panel,
            bd=0,
            highlightthickness=1,
            highlightbackground=self.ui_border,
        )
        self.reference_list_container.pack(fill='x', padx=5, pady=3)
        self.reference_list_canvas = tk.Canvas(
            self.reference_list_container,
            width=1,
            height=112,
            bg=self.ui_panel,
            bd=0,
            highlightthickness=0,
        )
        self.reference_list_scrollbar = tk.Scrollbar(
            self.reference_list_container,
            orient='vertical',
            command=self.reference_list_canvas.yview,
        )
        self.reference_list_canvas.configure(yscrollcommand=self.reference_list_scrollbar.set)
        self.reference_list_canvas.pack(side='left', fill='x', expand=True)
        self.reference_list_scrollbar.pack(side='right', fill='y')
        self.reference_list_rows = tk.Frame(self.reference_list_canvas, bg=self.ui_panel)
        self.reference_list_window = self.reference_list_canvas.create_window(
            (0, 0), window=self.reference_list_rows, anchor='nw'
        )

        def sync_reference_list_scrollregion(_event=None):
            self.reference_list_canvas.configure(
                scrollregion=self.reference_list_canvas.bbox('all')
            )

        def sync_reference_list_width(event):
            self.reference_list_canvas.itemconfigure(
                self.reference_list_window, width=max(1, event.width)
            )

        self.reference_list_rows.bind('<Configure>', sync_reference_list_scrollregion)
        self.reference_list_canvas.bind('<Configure>', sync_reference_list_width)

        ref_param_grid = tk.Frame(ref_frame, bg=self.ui_panel)
        ref_param_grid.pack(fill='x', padx=5, pady=2)
        ref_param_grid.columnconfigure(1, weight=1)
        self.reference_param_grid = ref_param_grid
        self.var_reference_wavelength = tk.DoubleVar(value=self.reference_wavelength)
        self.var_reference_kalpha2 = tk.BooleanVar(value=self.reference_kalpha2)
        self.var_reference_panel_height = tk.DoubleVar(value=self.reference_panel_height)
        self.var_reference_label_size = tk.IntVar(value=self.reference_label_size)
        self.var_reference_label_bold = tk.BooleanVar(value=self.reference_label_bold)
        self.var_reference_label_position = tk.StringVar(value=self.reference_label_position)
        self.var_reference_stick_width = tk.DoubleVar(value=self.reference_stick_width)

        def add_ref_param(row, label, variable, from_, to_, resolution, width=5):
            tk.Label(ref_param_grid, text=label, bg=self.ui_panel).grid(
                row=row, column=0, columnspan=4, sticky='w', padx=(0, 3), pady=(4, 0)
            )
            scale = ModernScale(
                ref_param_grid,
                from_=from_,
                to=to_,
                resolution=resolution,
                orient='horizontal',
                variable=variable,
                command=lambda v: self._request_draw_plot(),
                showvalue=False,
                length=170,
                bg=self.ui_panel,
            )
            scale.grid(
                row=row + 1,
                column=0,
                columnspan=2,
                sticky='ew',
                padx=(6, 5),
                pady=(0, 3),
            )
            ent = tk.Entry(ref_param_grid, textvariable=variable, width=width)
            ent.grid(row=row + 1, column=2, sticky='w', padx=(0, 5), pady=(0, 3))
            ent.bind("<Return>", lambda e: self._request_draw_plot())
            ent.bind("<FocusOut>", lambda e: self._request_draw_plot())
            return scale, ent

        self.chk_reference_kalpha2 = tk.Checkbutton(
            ref_param_grid,
            text="K-alpha 2 (intensity ratio 1:0.5)",
            variable=self.var_reference_kalpha2,
            command=self._request_draw_plot,
            bg=self.ui_panel,
        )
        self.chk_reference_kalpha2.grid(
            row=0, column=0, columnspan=4, sticky="w", padx=2, pady=(1, 3)
        )

        tk.Label(ref_param_grid, text="Cu K-alpha:", bg=self.ui_panel).grid(
            row=1, column=0, sticky="w", padx=(0, 3), pady=2
        )
        self.ent_reference_wavelength = tk.Entry(
            ref_param_grid, textvariable=self.var_reference_wavelength, width=9
        )
        self.ent_reference_wavelength.grid(
            row=1, column=1, sticky="w", padx=(6, 0), pady=2
        )
        self.ent_reference_wavelength.bind("<Return>", lambda e: self._request_draw_plot())
        self.ent_reference_wavelength.bind("<FocusOut>", lambda e: self._request_draw_plot())

        tk.Label(ref_param_grid, text="Label Position:", bg=self.ui_panel).grid(
            row=2, column=0, sticky="w", padx=(0, 3), pady=2
        )
        self.cmb_reference_label_position = ttk.Combobox(
            ref_param_grid,
            textvariable=self.var_reference_label_position,
            values=["left", "right"],
            state="readonly",
            width=10,
        )
        self.cmb_reference_label_position.grid(
            row=2, column=1, sticky="w", padx=(6, 0), pady=2
        )
        self.cmb_reference_label_position.bind(
            "<<ComboboxSelected>>", lambda e: self._request_draw_plot()
        )

        self.scale_reference_label_size, self.ent_reference_label_size = add_ref_param(
            3, "Reference Label Size:", self.var_reference_label_size, 5, 30, 1, width=4
        )
        self.chk_reference_label_bold = tk.Checkbutton(
            ref_param_grid,
            text="Bold",
            variable=self.var_reference_label_bold,
            command=self._request_draw_plot,
            bg=self.ui_panel,
        )
        self.chk_reference_label_bold.grid(row=4, column=3, sticky="w", pady=(0, 3))

        self.scale_reference_panel_height, self.ent_reference_panel_height = add_ref_param(
            5, "Reference Panel Height:", self.var_reference_panel_height, 0.05, 2.5, 0.01
        )
        self.scale_reference_stick_width, self.ent_reference_stick_width = add_ref_param(
            7, "Reference Stick Width:", self.var_reference_stick_width, 0.2, 4.0, 0.1
        )
        tk.Button(ref_frame, text="Clear References", command=self.clear_reference_peaks, bg=self.ui_button_light, font=self.ui_font).pack(fill='x', padx=5, pady=(2, 4))
        tk.Label(ref_frame, text="Default folder: xrd_rietveld_manager/CIF file. Reference Panel Height is per row; panel background stays white.", bg=self.ui_panel, fg=self.ui_muted, wraplength=300, justify='left').pack(anchor='w', padx=5, pady=(0, 4))
        self._refresh_reference_peak_list()

        layout_frame = tk.LabelFrame(quick_parent, text="Layout & Panels", bg=self.ui_panel, font=self.ui_font_bold)
        layout_frame.pack(fill=tk.X, pady=5)
        layout_frame.columnconfigure(0, weight=1)
        layout_frame.columnconfigure(1, weight=1)
        layout_frame.columnconfigure(2, weight=1)
        if not hasattr(self, "var_plot_layout"):
            self.var_plot_layout = tk.StringVar(value=self.plot_layout_mode)
        self.var_show_split_panel_titles = tk.BooleanVar(value=self.show_split_panel_titles)
        tk.Checkbutton(layout_frame, text="Panel Titles", variable=self.var_show_split_panel_titles, command=self._request_draw_plot, bg=self.ui_panel).grid(row=0, column=0, sticky='w', padx=5, pady=3)
        self.var_split_panel_title_source = tk.StringVar(value=self.split_panel_title_source)
        cmb_split_title_source = ttk.Combobox(
            layout_frame,
            textvariable=self.var_split_panel_title_source,
            values=["observed", "filename"],
            state="readonly",
            width=10
        )
        cmb_split_title_source.grid(row=0, column=1, sticky='w', padx=5, pady=3)
        cmb_split_title_source.bind("<<ComboboxSelected>>", lambda e: self._request_draw_plot())
        tk.Button(layout_frame, text="Edit Split Titles", command=self.open_split_title_editor, bg=self.ui_button_light, font=self.ui_font).grid(row=0, column=2, sticky='ew', padx=5, pady=3)

        panel_size_row = tk.Frame(layout_frame, bg=self.ui_panel)
        panel_size_row.grid(row=1, column=0, columnspan=3, sticky='ew', padx=5, pady=2)
        panel_size_row.columnconfigure(1, weight=1)
        tk.Label(panel_size_row, text="Panel Title Size:", bg=self.ui_panel).grid(
            row=0, column=0, columnspan=3, sticky='w', pady=(2, 0)
        )
        self.var_split_panel_title_size = tk.IntVar(value=self.split_panel_title_size)
        self.scale_split_panel_title_size = ModernScale(
            panel_size_row,
            from_=6,
            to=72,
            orient='horizontal',
            variable=self.var_split_panel_title_size,
            command=lambda v: self._request_draw_plot(),
            showvalue=False,
            length=170,
            bg=self.ui_panel
        )
        self.scale_split_panel_title_size.grid(
            row=1, column=0, columnspan=2, sticky='ew', padx=(6, 5), pady=(0, 3)
        )
        self.ent_split_panel_title_size = tk.Entry(
            panel_size_row, textvariable=self.var_split_panel_title_size, width=4
        )
        self.ent_split_panel_title_size.grid(row=1, column=2, sticky='w', pady=(0, 3))
        self.ent_split_panel_title_size.bind("<Return>", lambda e: self._request_draw_plot())
        self.ent_split_panel_title_size.bind("<FocusOut>", lambda e: self._request_draw_plot())

        split_arr_row = tk.Frame(layout_frame, bg=self.ui_panel)
        split_arr_row.grid(row=2, column=0, columnspan=3, sticky='ew', padx=5, pady=2)
        tk.Label(split_arr_row, text="Split Arrangement:", bg=self.ui_panel).pack(side='left')
        self.var_split_arrangement = tk.StringVar(value=self.split_arrangement)
        cmb_split_arr = ttk.Combobox(
            split_arr_row,
            textvariable=self.var_split_arrangement,
            values=["vertical", "horizontal"],
            state="readonly",
            width=10
        )
        cmb_split_arr.pack(side='left', padx=4)
        cmb_split_arr.bind("<<ComboboxSelected>>", lambda e: self._request_draw_plot())

        ratio_frame = tk.Frame(layout_frame, bg=self.ui_panel)
        ratio_frame.grid(row=3, column=0, columnspan=3, sticky='ew', padx=5, pady=3)
        tk.Label(ratio_frame, text="Plot Ratio:", bg=self.ui_panel).pack(side='left')
        self.var_plot_aspect_ratio = tk.StringVar(value=self.plot_aspect_ratio)
        cmb_ratio = ttk.Combobox(
            ratio_frame,
            textvariable=self.var_plot_aspect_ratio,
            values=["Auto", "1:1", "4:3", "16:9", "Custom"],
            state="readonly",
            width=8
        )
        cmb_ratio.pack(side='left', padx=4)
        cmb_ratio.bind("<<ComboboxSelected>>", lambda e: self.on_plot_ratio_change())
        tk.Label(ratio_frame, text="Custom W:H:", bg=self.ui_panel).pack(side='left', padx=(8, 2))
        self.var_custom_plot_aspect_ratio = tk.StringVar(value=getattr(self, "custom_plot_aspect_ratio", "1:2"))
        ent_custom_ratio = tk.Entry(ratio_frame, textvariable=self.var_custom_plot_aspect_ratio, width=7)
        ent_custom_ratio.pack(side='left', padx=(0, 4))
        ent_custom_ratio.bind("<Return>", lambda e: self.on_plot_ratio_change())
        ent_custom_ratio.bind("<FocusOut>", lambda e: self.on_plot_ratio_change())
        tk.Label(
            layout_frame,
            text="Custom accepts W:H, e.g. 1:3 for tall/narrow zoom panels.",
            bg=self.ui_panel,
            fg=self.ui_muted
        ).grid(row=4, column=0, columnspan=3, sticky='w', padx=5, pady=(2, 0))

        plot_font_frame = tk.LabelFrame(style_parent, text="Plot Font", bg=self.ui_panel, font=self.ui_font_bold)
        plot_font_frame.pack(fill=tk.X, pady=5)
        self._build_plot_font_selector(plot_font_frame)

        color_frame = tk.LabelFrame(style_parent, text="Color", bg=self.ui_panel, font=self.ui_font_bold)
        color_frame.pack(fill=tk.X, pady=5)
        tk.Button(
            color_frame,
            text="Color Setting",
            command=self.open_color_settings,
            bg=self.ui_button_light,
            font=self.ui_font,
        ).pack(fill=tk.X, padx=5, pady=5)

        title_frame = tk.LabelFrame(style_parent, text="Plot Title", bg=self.ui_panel, font=self.ui_font_bold)
        title_frame.pack(fill=tk.X, pady=5)
        self.var_plot_title = tk.StringVar(value=self.plot_title_text)
        self.var_plot_title_bold = tk.BooleanVar(value=self.plot_title_bold)
        self.var_plot_title_drag = tk.BooleanVar(value=self.plot_title_drag_enabled)

        ent_title = tk.Entry(title_frame, textvariable=self.var_plot_title)
        ent_title.pack(fill='x', padx=5, pady=3)
        ent_title.bind("<Return>", lambda e: self._request_draw_plot())
        ent_title.bind("<FocusOut>", lambda e: self._request_draw_plot())

        title_size_row = tk.Frame(title_frame, bg=self.ui_panel)
        title_size_row.pack(fill='x', padx=5, pady=2)
        tk.Label(title_size_row, text="Title Size:", bg=self.ui_panel).pack(side='left')
        ModernScale(
            title_size_row,
            from_=8,
            to=72,
            orient='horizontal',
            variable=self.var_title_size,
            command=lambda v: self._request_draw_plot(),
            showvalue=False,
            length=120,
            bg=self.ui_panel
        ).pack(side='left', padx=4)
        ent_title_size = tk.Entry(title_size_row, textvariable=self.var_title_size, width=4)
        ent_title_size.pack(side='left')
        ent_title_size.bind("<Return>", lambda e: self._request_draw_plot())
        ent_title_size.bind("<FocusOut>", lambda e: self._request_draw_plot())

        tk.Checkbutton(title_frame, text="Bold", variable=self.var_plot_title_bold, command=self._request_draw_plot, bg=self.ui_panel).pack(anchor='w', padx=5)
        tk.Checkbutton(title_frame, text="Enable Drag", variable=self.var_plot_title_drag, command=self._request_draw_plot, bg=self.ui_panel).pack(anchor='w', padx=5)
        tk.Button(title_frame, text="Reset Position", command=self.reset_plot_title_position, bg=self.ui_button_light, font=self.ui_font).pack(anchor='w', padx=5, pady=2)
        tk.Label(title_frame, text="Default: top-left inside axis. Drag title directly on plot.", bg=self.ui_panel, fg=self.ui_muted).pack(anchor='w', padx=5, pady=(0, 3))

        zoom_frame = tk.LabelFrame(advanced_parent, text="XRD Zoom Panels", bg=self.ui_panel, font=self.ui_font_bold)
        zoom_frame.pack(fill=tk.X, pady=5)
        self.var_zoom_panels_enabled = tk.BooleanVar(value=self.zoom_panels_enabled)
        self.var_zoom_panel_ranges = tk.StringVar(value=self.zoom_panel_ranges)
        self.var_zoom_panel_width = tk.DoubleVar(value=self.zoom_panel_width)
        self.var_zoom_panel_gap = tk.DoubleVar(value=self.zoom_panel_gap)
        self.var_zoom_highlight_ranges = tk.BooleanVar(value=self.zoom_highlight_ranges)

        tk.Checkbutton(
            zoom_frame,
            text="Show zoom panels beside plot",
            variable=self.var_zoom_panels_enabled,
            command=self._request_draw_plot,
            bg=self.ui_panel,
        ).pack(anchor='w', padx=5, pady=(2, 1))

        range_row = tk.Frame(zoom_frame, bg=self.ui_panel)
        range_row.pack(fill='x', padx=5, pady=2)
        tk.Label(range_row, text="X Ranges:", bg=self.ui_panel).pack(side='left')
        ent_zoom_ranges = tk.Entry(range_row, textvariable=self.var_zoom_panel_ranges)
        ent_zoom_ranges.pack(side='left', fill='x', expand=True, padx=(5, 0))
        ent_zoom_ranges.bind("<Return>", lambda e: self._request_draw_plot())
        ent_zoom_ranges.bind("<FocusOut>", lambda e: self._request_draw_plot())

        zoom_size_grid = tk.Frame(zoom_frame, bg=self.ui_panel)
        zoom_size_grid.pack(fill='x', padx=5, pady=2)
        zoom_size_grid.columnconfigure(1, weight=1)
        zoom_size_grid.columnconfigure(4, weight=1)
        tk.Label(zoom_size_grid, text="Width:", bg=self.ui_panel).grid(row=0, column=0, sticky='w')
        ModernScale(
            zoom_size_grid,
            from_=0.4,
            to=2.0,
            resolution=0.05,
            orient='horizontal',
            variable=self.var_zoom_panel_width,
            command=lambda v: self._request_draw_plot(),
            showvalue=False,
            length=80,
            bg=self.ui_panel,
        ).grid(row=0, column=1, sticky='ew', padx=3)
        ent_zoom_width = tk.Entry(zoom_size_grid, textvariable=self.var_zoom_panel_width, width=5)
        ent_zoom_width.grid(row=0, column=2, sticky='w', padx=(0, 8))
        ent_zoom_width.bind("<Return>", lambda e: self._request_draw_plot())
        ent_zoom_width.bind("<FocusOut>", lambda e: self._request_draw_plot())

        tk.Label(zoom_size_grid, text="Gap:", bg=self.ui_panel).grid(row=0, column=3, sticky='w')
        ModernScale(
            zoom_size_grid,
            from_=0.02,
            to=0.50,
            resolution=0.01,
            orient='horizontal',
            variable=self.var_zoom_panel_gap,
            command=lambda v: self._request_draw_plot(),
            showvalue=False,
            length=70,
            bg=self.ui_panel,
        ).grid(row=0, column=4, sticky='ew', padx=3)
        ent_zoom_gap = tk.Entry(zoom_size_grid, textvariable=self.var_zoom_panel_gap, width=5)
        ent_zoom_gap.grid(row=0, column=5, sticky='w')
        ent_zoom_gap.bind("<Return>", lambda e: self._request_draw_plot())
        ent_zoom_gap.bind("<FocusOut>", lambda e: self._request_draw_plot())

        tk.Checkbutton(
            zoom_frame,
            text="Highlight zoom ranges on main plot",
            variable=self.var_zoom_highlight_ranges,
            command=self._request_draw_plot,
            bg=self.ui_panel,
        ).pack(anchor='w', padx=5, pady=(2, 1))
        tk.Label(
            zoom_frame,
            text="Enter up to 4 ranges as start,end; start,end. Available in Combined 2D layout.",
            bg=self.ui_panel,
            fg=self.ui_muted,
            justify='left',
            wraplength=300,
        ).pack(anchor='w', padx=5, pady=(0, 3))

        memo_frame = tk.LabelFrame(advanced_parent, text="Plot Memos", bg=self.ui_panel, font=self.ui_font_bold)
        memo_frame.pack(fill=tk.X, pady=5)
        self.var_plot_memos_enabled = tk.BooleanVar(value=self.plot_memos_enabled)
        self.var_plot_top_space = tk.DoubleVar(value=self.plot_top_space)
        self.var_plot_memo_font = tk.StringVar(value=self.plot_memo_default_font)
        self.var_plot_memo_size = tk.IntVar(value=self.plot_memo_default_size)
        self.var_plot_memo_bold = tk.BooleanVar(value=self.plot_memo_default_bold)

        tk.Checkbutton(
            memo_frame,
            text="Show Plot Memos",
            variable=self.var_plot_memos_enabled,
            command=self._request_draw_plot,
            bg=self.ui_panel,
        ).pack(anchor='w', padx=5, pady=(2, 0))

        top_space_row = tk.Frame(memo_frame, bg=self.ui_panel)
        top_space_row.pack(fill='x', padx=5, pady=2)
        tk.Label(top_space_row, text="Top Space:", bg=self.ui_panel).pack(side='left')
        ModernScale(
            top_space_row,
            from_=0.0,
            to=0.35,
            resolution=0.01,
            orient='horizontal',
            variable=self.var_plot_top_space,
            command=lambda v: self._request_draw_plot(),
            showvalue=False,
            length=120,
            bg=self.ui_panel,
        ).pack(side='left', padx=4)
        ent_top_space = tk.Entry(top_space_row, textvariable=self.var_plot_top_space, width=5)
        ent_top_space.pack(side='left')
        ent_top_space.bind("<Return>", lambda e: self._request_draw_plot())
        ent_top_space.bind("<FocusOut>", lambda e: self._request_draw_plot())

        self.txt_plot_memo = tk.Text(memo_frame, height=3, wrap='word', font=self.ui_font)
        self.txt_plot_memo.pack(fill='x', padx=5, pady=(4, 2))

        memo_font_row = tk.Frame(memo_frame, bg=self.ui_panel)
        memo_font_row.pack(fill='x', padx=5, pady=2)
        memo_font_row.columnconfigure(1, weight=1)
        tk.Label(memo_font_row, text="Font:", bg=self.ui_panel).grid(row=0, column=0, sticky='w')
        memo_font_values = ["Use Plot Font"] + [f for f in available_plot_fonts() if f != "Use Plot Font"]
        cmb_memo_font = ttk.Combobox(
            memo_font_row,
            textvariable=self.var_plot_memo_font,
            values=memo_font_values,
            state="readonly",
            width=18,
        )
        cmb_memo_font.grid(row=0, column=1, sticky='ew', padx=4)
        cmb_memo_font.bind("<<ComboboxSelected>>", lambda e: self._request_draw_plot())
        tk.Label(memo_font_row, text="Size:", bg=self.ui_panel).grid(row=0, column=2, sticky='e')
        sp_memo_size = tk.Spinbox(
            memo_font_row,
            from_=6,
            to=96,
            textvariable=self.var_plot_memo_size,
            width=4,
            command=self._request_draw_plot,
        )
        sp_memo_size.grid(row=0, column=3, sticky='w', padx=4)
        sp_memo_size.bind("<Return>", lambda e: self._request_draw_plot())
        sp_memo_size.bind("<FocusOut>", lambda e: self._request_draw_plot())

        memo_style_row = tk.Frame(memo_frame, bg=self.ui_panel)
        memo_style_row.pack(fill='x', padx=5, pady=2)
        tk.Checkbutton(
            memo_style_row,
            text="Bold",
            variable=self.var_plot_memo_bold,
            command=self._request_draw_plot,
            bg=self.ui_panel,
        ).pack(side='left')
        tk.Button(
            memo_style_row,
            text="Color",
            command=self._choose_plot_memo_color,
            bg=self.ui_button_light,
            font=self.ui_font,
        ).pack(side='left', padx=(8, 4))
        self.lbl_plot_memo_color = tk.Label(
            memo_style_row,
            text=self.plot_memo_default_color,
            bg=self.plot_memo_default_color,
            fg="white",
            width=9,
        )
        self.lbl_plot_memo_color.pack(side='left')

        memo_btn_row = tk.Frame(memo_frame, bg=self.ui_panel)
        memo_btn_row.pack(fill='x', padx=5, pady=3)
        for text, command in (
            ("Add", self._add_plot_memo_from_editor),
            ("Update", self._update_selected_plot_memo),
            ("Delete", self._delete_selected_plot_memo),
            ("Clear", self._clear_plot_memos),
        ):
            tk.Button(memo_btn_row, text=text, command=command, bg=self.ui_button_light, font=self.ui_font).pack(side='left', padx=(0, 4))

        self.lb_plot_memos = tk.Listbox(memo_frame, height=4, exportselection=False, font=self.ui_font)
        self.lb_plot_memos.pack(fill='x', padx=5, pady=(0, 3))
        self.lb_plot_memos.bind("<<ListboxSelect>>", self._on_plot_memo_select)
        tk.Label(
            memo_frame,
            text="Each memo is draggable on the plot. Top Space reserves room above data.",
            bg=self.ui_panel,
            fg=self.ui_muted,
        ).pack(anchor='w', padx=5, pady=(0, 3))
        self._refresh_plot_memo_list()

        bg_frame = tk.LabelFrame(style_parent, text="Background", bg=self.ui_panel, font=self.ui_font_bold)
        bg_frame.pack(fill=tk.X, pady=5)
        self.var_plot_bg_enabled = tk.BooleanVar(value=self.plot_bg_enabled)
        tk.Checkbutton(bg_frame, text="Enable Background", variable=self.var_plot_bg_enabled, command=self._request_draw_plot, bg=self.ui_panel).pack(anchor='w', padx=5)

        bg_mode_row = tk.Frame(bg_frame, bg=self.ui_panel)
        bg_mode_row.pack(fill='x', padx=5, pady=2)
        bg_mode_row.columnconfigure(1, weight=1)
        tk.Label(bg_mode_row, text="Mode:", bg=self.ui_panel).grid(row=0, column=0, sticky='w')
        self.var_plot_bg_mode = tk.StringVar(value=self.plot_bg_mode)
        cmb_bg_mode = ttk.Combobox(bg_mode_row, textvariable=self.var_plot_bg_mode, values=["solid", "gradient"], state="readonly", width=10)
        cmb_bg_mode.grid(row=0, column=1, sticky='w', padx=4)
        cmb_bg_mode.bind("<<ComboboxSelected>>", lambda e: self._request_draw_plot())

        bg_btn_row = tk.Frame(bg_frame, bg=self.ui_panel)
        bg_btn_row.pack(fill='x', padx=5, pady=2)
        bg_btn_row.columnconfigure(0, weight=1)
        bg_btn_row.columnconfigure(1, weight=1)
        tk.Button(bg_btn_row, text="Solid Color", command=self.pick_plot_bg_color, bg=self.ui_button_light, font=self.ui_font).grid(row=0, column=0, sticky='ew', padx=2, pady=1)
        tk.Button(bg_btn_row, text="Gradient Start", command=self.pick_plot_bg_grad_start, bg=self.ui_button_light, font=self.ui_font).grid(row=0, column=1, sticky='ew', padx=2, pady=1)
        tk.Button(bg_btn_row, text="Gradient End", command=self.pick_plot_bg_grad_end, bg=self.ui_button_light, font=self.ui_font).grid(row=1, column=0, columnspan=2, sticky='ew', padx=2, pady=1)

        bg_grad_row = tk.Frame(bg_frame, bg=self.ui_panel)
        bg_grad_row.pack(fill='x', padx=5, pady=2)
        bg_grad_row.columnconfigure(1, weight=1)
        tk.Label(bg_grad_row, text="Direction:", bg=self.ui_panel).grid(row=0, column=0, sticky='w')
        self.var_plot_bg_direction = tk.StringVar(value=self.plot_bg_direction)
        cmb_bg_dir = ttk.Combobox(bg_grad_row, textvariable=self.var_plot_bg_direction, values=["vertical", "horizontal"], state="readonly", width=10)
        cmb_bg_dir.grid(row=0, column=1, sticky='w', padx=4)
        cmb_bg_dir.bind("<<ComboboxSelected>>", lambda e: self._request_draw_plot())

        tk.Label(bg_grad_row, text="Alpha:", bg=self.ui_panel).grid(row=1, column=0, sticky='w', padx=(0, 0), pady=(4, 0))
        self.var_plot_bg_alpha = tk.DoubleVar(value=self.plot_bg_alpha)
        ModernScale(bg_grad_row, from_=0.1, to=1.0, resolution=0.05, orient='horizontal', variable=self.var_plot_bg_alpha, command=lambda v: self._request_draw_plot(), showvalue=False, length=120, bg=self.ui_panel).grid(row=1, column=1, sticky='ew', padx=4, pady=(4, 0))
        ent_bg_alpha = tk.Entry(bg_grad_row, textvariable=self.var_plot_bg_alpha, width=4)
        ent_bg_alpha.grid(row=1, column=2, sticky='w', pady=(4, 0))
        ent_bg_alpha.bind("<Return>", lambda e: self._request_draw_plot())
        ent_bg_alpha.bind("<FocusOut>", lambda e: self._request_draw_plot())

        art_frame = tk.LabelFrame(style_parent, text="Art Effects", bg=self.ui_panel, font=self.ui_font_bold)
        art_frame.pack(fill=tk.X, pady=5)
        art_frame.columnconfigure(1, weight=1)
        self.var_art_effects_enabled = tk.BooleanVar(value=self.art_effects_enabled)
        self.var_art_line_effect = tk.StringVar(value=self.art_line_effect)
        # Art enable/line-effect controls live in Color Setting above Color List.

        self.var_art_text_halo = tk.BooleanVar(value=self.art_text_halo)
        self.var_art_marker_depth = tk.BooleanVar(value=self.art_marker_depth)
        self.var_art_label_adjust = tk.BooleanVar(value=self.art_label_adjust)
        tk.Checkbutton(art_frame, text="Text Halo", variable=self.var_art_text_halo, command=self._request_draw_plot, bg=self.ui_panel).grid(row=2, column=0, sticky='w', padx=5, pady=2)
        tk.Checkbutton(art_frame, text="3D Marker Feel", variable=self.var_art_marker_depth, command=self._request_draw_plot, bg=self.ui_panel).grid(row=2, column=1, sticky='w', padx=5, pady=2)
        tk.Checkbutton(art_frame, text="Auto Label Adjust", variable=self.var_art_label_adjust, command=self._request_draw_plot, bg=self.ui_panel).grid(row=3, column=0, columnspan=2, sticky='w', padx=5, pady=2)

        tk.Label(art_frame, text="Palette:", bg=self.ui_panel).grid(row=4, column=0, sticky='w', padx=5, pady=2)
        self.var_art_palette = tk.StringVar(value=self.art_palette_name)
        cmb_art_palette = ttk.Combobox(
            art_frame,
            textvariable=self.var_art_palette,
            values=available_palette_names(),
            state="readonly",
            width=18
        )
        cmb_art_palette.grid(row=4, column=1, sticky='ew', padx=5, pady=2)
        tk.Button(
            art_frame,
            text="Apply Palette to Phases",
            command=self.apply_art_palette_to_phases,
            bg=self.ui_button_light,
            font=self.ui_font
        ).grid(row=5, column=0, columnspan=2, sticky='ew', padx=5, pady=(2, 5))

        # The most frequently used display switches stay together at the top.
        quick_frame = tk.LabelFrame(
            quick_parent,
            text="Display",
            bg=self.ui_surface,
            fg=self.ui_text,
            font=self.ui_font_bold,
        )
        quick_frame.grid_columnconfigure(0, weight=1, uniform="quick_display")
        quick_frame.grid_columnconfigure(1, weight=1, uniform="quick_display")
        for index, (label, variable, command) in enumerate((
            ("Show Legend", self.var_show_legend, self._request_draw_plot),
            ("Show Residual", self.var_show_residual, self._request_draw_plot),
            ("Show Phase Peaks", self.var_show_phase_peaks_top, self._toggle_quick_phase_peaks),
            ("Show Reference", self.var_reference_peaks_enabled, self._request_draw_plot),
        )):
            row, column = divmod(index, 2)
            tk.Checkbutton(
                quick_frame,
                text=label,
                variable=variable,
                command=command,
                bg=self.ui_surface,
                activebackground=self.ui_surface,
                anchor="w",
                highlightthickness=0,
                bd=0,
            ).grid(row=row, column=column, sticky="w", padx=(0, 10), pady=2)

        # Remove controls duplicated by Display from their detailed cards.
        for duplicate in (
            plot_show_legend_control,
            plot_show_phase_peaks_control,
            plot_show_residual_control,
            plot_show_reference_control,
        ):
            duplicate.pack_forget()

        plot_cards = (
            (vis_frame, "Legend", False),
            (phase_label_frame, "Phase Peaks", False),
            (ref_frame, "Reference Peaks", False),
            (layout_frame, "Layout & Panels", True),
            (title_frame, "Plot Title", False),
            (zoom_frame, "XRD Zoom Panels", False),
            (memo_frame, "Plot Memos", False),
            (bg_frame, "Background", False),
            (art_frame, "Art Effects", False),
        )

        def make_collapsible(frame, title, expanded=False):
            state = {"expanded": bool(expanded)}
            child_layouts = []
            for child in frame.winfo_children():
                manager = child.winfo_manager()
                if manager == "pack":
                    pack_info = {
                        key: value
                        for key, value in child.pack_info().items()
                        if key != "in" and value != ""
                    }
                    child_layouts.append((child, manager, pack_info))
                elif manager == "grid":
                    child_layouts.append((child, manager, None))

            def refresh():
                is_open = state["expanded"]
                frame.configure(text=("▼ " if is_open else "▶ ") + title)
                frame.pack_propagate(is_open)
                frame.grid_propagate(is_open)
                if is_open:
                    for child, manager, layout_info in child_layouts:
                        if manager == "pack" and not child.winfo_manager():
                            child.pack(**layout_info)
                        elif manager == "grid" and not child.winfo_manager():
                            child.grid()
                else:
                    for child, manager, _layout_info in child_layouts:
                        if manager == "pack":
                            child.pack_forget()
                        elif manager == "grid":
                            child.grid_remove()
                    frame.configure(height=28)

            def toggle(_event=None):
                state["expanded"] = not state["expanded"]
                refresh()

            frame.bind("<Button-1>", toggle, add="+")
            frame.configure(cursor="hand2")
            refresh()

        # Repack in task order, using the same gray card language as DATA/LAYERS.
        for frame, _title, _expanded in plot_cards:
            frame.pack_forget()
            self._style_settings_card(frame)
        self._style_settings_card(quick_frame)

        quick_frame.pack(fill=tk.X, padx=10, pady=(0, 8))
        self._make_plot_card_collapsible(quick_frame, "Display", expanded=True)
        for frame, title, expanded in plot_cards:
            frame.pack(fill=tk.X, padx=10, pady=(0, 8))
            self._make_plot_card_collapsible(frame, title, expanded=expanded)
        self.quick_phase_frame = phase_label_frame
        self.quick_reference_frame = ref_frame
        for section_parent in (quick_parent, style_parent, advanced_parent):
            self._normalize_section_controls(section_parent)

    def _setup_axes_tab(self):
        parent = getattr(self, "tab_axes_body", self.tab_axes)
        if not getattr(self, "_plot_sections_embedded", False):
            self._tab_banner(parent, "Publication Style", "Grid, ticks, axis labels, box width, and residual-panel geometry.", self.ui_accent_alt)
            tk.Label(
                parent,
                text="Live Update: enabled",
                bg=self.ui_panel,
                fg="#2e7d32",
                font=self.ui_font_bold
            ).pack(anchor='w', pady=(2, 5))

        # Shared variables let these compact controls and the existing detailed
        # cards stay synchronized without duplicating plotting state.
        self.var_tick_x_2d = tk.BooleanVar(value=self.show_tick_x_2d)
        self.var_tick_y_2d = tk.BooleanVar(value=self.show_tick_y_2d)
        self.var_minor_tick_x_2d = tk.BooleanVar(value=getattr(self, "show_minor_tick_x_2d", True))
        self.var_minor_tick_y_2d = tk.BooleanVar(value=getattr(self, "show_minor_tick_y_2d", True))
        self.var_tick_label_x_2d = tk.BooleanVar(value=self.show_tick_label_x_2d)
        self.var_tick_label_y_2d = tk.BooleanVar(value=self.show_tick_label_y_2d)
        self.var_axis_title_x_2d = tk.BooleanVar(value=getattr(self, "show_axis_title_x_2d", True))
        self.var_axis_title_y_2d = tk.BooleanVar(value=getattr(self, "show_axis_title_y_2d", True))
        self.var_tick_label_size = tk.IntVar(value=self.tick_label_size)
        self.var_tick_label_bold = tk.BooleanVar(value=self.tick_label_bold)
        self.var_axis_label_bold = tk.BooleanVar(value=self.axis_label_bold)
        self.var_tick_length_2d = tk.DoubleVar(value=getattr(self, "tick_length_2d", 10.0))
        self.var_minor_tick_length_2d = tk.DoubleVar(value=getattr(self, "minor_tick_length_2d", 5.0))
        self.var_tick_width_2d = tk.DoubleVar(value=getattr(self, "tick_width_2d", 1.0))

        tick_visibility_frame = tk.LabelFrame(
            parent,
            text="Tick Visibility",
            bg=self.ui_panel,
            font=self.ui_font_bold,
        )
        tick_visibility_frame.pack(fill=tk.X, pady=5)
        tick_visibility_frame.columnconfigure(0, weight=1)
        for column in range(1, 5):
            tick_visibility_frame.columnconfigure(column, weight=1, uniform="tick_visibility_option")

        visibility_columns = (
            ("Major", self.var_tick_x_2d, self.var_tick_y_2d),
            ("Minor", self.var_minor_tick_x_2d, self.var_minor_tick_y_2d),
            ("Numbers", self.var_tick_label_x_2d, self.var_tick_label_y_2d),
            ("Label", self.var_axis_title_x_2d, self.var_axis_title_y_2d),
        )
        for column, (heading, _x_variable, _y_variable) in enumerate(visibility_columns, start=1):
            tk.Label(
                tick_visibility_frame,
                text=heading,
                bg=self.ui_panel,
                fg=self.ui_muted,
                font=self.ui_font_bold,
                anchor="center",
            ).grid(row=0, column=column, sticky="ew", padx=2, pady=(4, 3))

        for row, (axis_name, variable_index) in enumerate((("X Axis", 1), ("Y Axis", 2)), start=1):
            tk.Label(
                tick_visibility_frame,
                text=axis_name,
                bg=self.ui_panel,
                fg=self.ui_text,
                font=self.ui_font_bold,
                anchor="w",
            ).grid(row=row, column=0, sticky="w", padx=(5, 3), pady=2)
            for column, column_spec in enumerate(visibility_columns, start=1):
                tk.Checkbutton(
                    tick_visibility_frame,
                    text="",
                    variable=column_spec[variable_index],
                    command=self._request_draw_plot,
                    bg=self.ui_panel,
                    anchor="center",
                ).grid(row=row, column=column, padx=2, pady=2)

        tick_direction_row = tk.Frame(tick_visibility_frame, bg=self.ui_panel)
        tick_direction_row.grid(
            row=3,
            column=0,
            columnspan=5,
            sticky="ew",
            padx=5,
            pady=(5, 4),
        )
        tk.Label(
            tick_direction_row,
            text="2D Tick Direction:",
            bg=self.ui_panel,
        ).pack(side="left")
        self.cmb_tick_dir_2d = ttk.Combobox(
            tick_direction_row,
            values=["in", "out", "inout", "none"],
            state="readonly",
            width=8,
        )
        self.cmb_tick_dir_2d.set(self.tick_direction_2d)
        self.cmb_tick_dir_2d.pack(side="left", padx=(6, 0))
        self.cmb_tick_dir_2d.bind(
            "<<ComboboxSelected>>", lambda _event: self._request_draw_plot()
        )

        axes_size_frame = tk.LabelFrame(
            parent,
            text="Axes Size",
            bg=self.ui_panel,
            font=self.ui_font_bold,
        )
        axes_size_frame.pack(fill=tk.X, pady=5)
        axes_size_frame.columnconfigure(1, weight=1)

        def add_axes_size_control(row, label, variable, from_, to_, resolution=1, bold_var=None):
            label_row = row * 2
            control_row = label_row + 1
            tk.Label(axes_size_frame, text=label, bg=self.ui_panel).grid(
                row=label_row,
                column=0,
                columnspan=4,
                sticky="w",
                padx=(5, 3),
                pady=(4 if row else 3, 0),
            )
            scale = ModernScale(
                axes_size_frame,
                from_=from_,
                to=to_,
                resolution=resolution,
                orient="horizontal",
                variable=variable,
                command=lambda _value: self._request_draw_plot(),
                showvalue=False,
                length=170,
                bg=self.ui_panel,
            )
            scale.grid(
                row=control_row,
                column=0,
                columnspan=2,
                sticky="ew",
                padx=(11, 5),
                pady=(0, 3),
            )
            entry = tk.Entry(axes_size_frame, textvariable=variable, width=5)
            entry.grid(row=control_row, column=2, sticky="w", padx=(0, 6), pady=(0, 3))
            entry.bind("<Return>", lambda _event: self._request_draw_plot())
            entry.bind("<FocusOut>", lambda _event: self._request_draw_plot())
            if bold_var is not None:
                bold_check = tk.Checkbutton(
                    axes_size_frame,
                    text="Bold",
                    variable=bold_var,
                    command=self._request_draw_plot,
                    bg=self.ui_panel,
                )
                bold_check.grid(
                    row=control_row, column=3, sticky="w", padx=(0, 5), pady=(0, 3)
                )
            return scale, entry

        self.scale_axis_number_size, self.ent_axis_number_size = add_axes_size_control(
            0, "Axis Number Size:", self.var_tick_label_size, 6, 96, bold_var=self.var_tick_label_bold
        )
        self.scale_tick_label_size_axes, self.ent_tick_label_size_axes = add_axes_size_control(
            1, "Tick Label Size:", self.var_axis_size, 6, 96, bold_var=self.var_axis_label_bold
        )
        self.scale_major_length_size, self.ent_major_length_size = add_axes_size_control(
            2, "Major Length Size:", self.var_tick_length_2d, 0.0, 20.0, resolution=0.5
        )
        self.scale_minor_length_size, self.ent_minor_length_size = add_axes_size_control(
            3, "Minor Length Size:", self.var_minor_tick_length_2d, 0.0, 20.0, resolution=0.5
        )
        self.scale_tick_width, self.ent_tick_width = add_axes_size_control(
            4, "Tick Width:", self.var_tick_width_2d, 0.1, 6.0, resolution=0.1
        )

        tools_frame = tk.LabelFrame(parent, text="Tools", bg=self.ui_panel, font=self.ui_font_bold)
        tools_frame.pack(fill=tk.X, pady=5)
        tools_frame.columnconfigure(0, weight=1)
        tools_frame.columnconfigure(1, weight=1)
        self.var_y_autoscale_to_x_range = tk.BooleanVar(value=self.y_autoscale_to_x_range)
        tk.Checkbutton(
            tools_frame,
            text="Auto Y to X Range",
            variable=self.var_y_autoscale_to_x_range,
            command=self._request_draw_plot,
            bg=self.ui_panel
        ).grid(row=0, column=0, columnspan=2, sticky='w', padx=5, pady=(3, 1))
        self.var_normalize_y_in_x_range = tk.BooleanVar(value=self.normalize_y_in_x_range)
        tk.Checkbutton(
            tools_frame,
            text="Normalize in X Range",
            variable=self.var_normalize_y_in_x_range,
            command=self._request_draw_plot,
            bg=self.ui_panel
        ).grid(row=1, column=0, columnspan=2, sticky='w', padx=5, pady=(0, 1))
        ypad_row = tk.Frame(tools_frame, bg=self.ui_panel)
        ypad_row.grid(row=2, column=0, columnspan=2, sticky='ew', padx=5, pady=(0, 4))
        ypad_row.columnconfigure(1, weight=1)
        tk.Label(ypad_row, text="Y Padding %:", bg=self.ui_panel).grid(
            row=0, column=0, columnspan=3, sticky='w', pady=(2, 0)
        )
        self.var_y_autoscale_padding = tk.DoubleVar(value=self.y_autoscale_padding_percent)
        self.scale_y_autoscale_padding = ModernScale(
            ypad_row,
            from_=0,
            to=40,
            resolution=1,
            orient='horizontal',
            variable=self.var_y_autoscale_padding,
            command=lambda v: self._request_draw_plot(),
            showvalue=False,
            length=170,
            bg=self.ui_panel
        )
        self.scale_y_autoscale_padding.grid(
            row=1, column=0, columnspan=2, sticky='ew', padx=(6, 5), pady=(0, 3)
        )
        self.ent_y_autoscale_padding = tk.Entry(
            ypad_row, textvariable=self.var_y_autoscale_padding, width=5
        )
        self.ent_y_autoscale_padding.grid(row=1, column=2, sticky='w', pady=(0, 3))
        self.ent_y_autoscale_padding.bind("<Return>", lambda e: self._request_draw_plot())
        self.ent_y_autoscale_padding.bind("<FocusOut>", lambda e: self._request_draw_plot())

        grid_frame = tk.LabelFrame(parent, text="Grid", bg=self.ui_panel, font=self.ui_font_bold)
        grid_frame.pack(fill=tk.X, pady=5)
        self.var_grid_x = tk.BooleanVar(value=self.show_grid_x)
        self.var_grid_y = tk.BooleanVar(value=self.show_grid_y)
        tk.Checkbutton(grid_frame, text="Vertical Grid (X)", variable=self.var_grid_x, command=self._request_draw_plot, bg=self.ui_panel).pack(anchor='w', padx=5)
        tk.Checkbutton(grid_frame, text="Horizontal Grid (Y)", variable=self.var_grid_y, command=self._request_draw_plot, bg=self.ui_panel).pack(anchor='w', padx=5)

        tick_label_frame = tk.LabelFrame(parent, text="Axis Number Rotation", bg=self.ui_panel, font=self.ui_font_bold)
        tick_label_frame.pack(fill=tk.X, pady=5)
        self.var_tick_label_font = tk.StringVar(value=getattr(self, "tick_label_font", "Use Plot Font"))
        self.var_tick_label_color = tk.StringVar(value=getattr(self, "tick_label_color", "#000000"))
        self.var_tick_label_x_rotation = tk.DoubleVar(value=getattr(self, "tick_label_x_rotation", 0.0))
        self.var_tick_label_y_rotation = tk.DoubleVar(value=getattr(self, "tick_label_y_rotation", 0.0))
        self.var_max_x_tick_labels = tk.IntVar(value=getattr(self, "max_x_tick_labels", 6))
        self.var_max_y_tick_labels = tk.IntVar(value=getattr(self, "max_y_tick_labels", 6))

        tick_density_row = tk.Frame(tick_label_frame, bg=self.ui_panel)
        tick_density_row.pack(fill='x', padx=5, pady=(3, 5))
        tick_density_row.columnconfigure(1, weight=1)

        def add_tick_label_metric(row, label, variable, from_, to_, resolution):
            label_row = row * 2
            control_row = label_row + 1
            tk.Label(tick_density_row, text=label, bg=self.ui_panel).grid(
                row=label_row,
                column=0,
                columnspan=3,
                sticky='w',
                padx=(0, 3),
                pady=(4 if row else 2, 0),
            )
            scale = ModernScale(
                tick_density_row,
                from_=from_,
                to=to_,
                resolution=resolution,
                orient='horizontal',
                variable=variable,
                command=lambda v: self._request_draw_plot(),
                showvalue=False,
                length=170,
                bg=self.ui_panel
            )
            scale.grid(
                row=control_row,
                column=0,
                columnspan=2,
                sticky='ew',
                padx=(6, 5),
                pady=(0, 3),
            )
            ent = tk.Entry(tick_density_row, textvariable=variable, width=5)
            ent.grid(row=control_row, column=2, sticky='w', padx=(0, 4), pady=(0, 3))
            ent.bind("<Return>", lambda e: self._request_draw_plot())
            ent.bind("<FocusOut>", lambda e: self._request_draw_plot())
            return scale, ent

        self.scale_tick_x_rotation, self.ent_tick_x_rotation = add_tick_label_metric(
            0, "X Rotation:", self.var_tick_label_x_rotation, -90, 90, 5
        )
        self.scale_tick_y_rotation, self.ent_tick_y_rotation = add_tick_label_metric(
            1, "Y Rotation:", self.var_tick_label_y_rotation, -90, 90, 5
        )


        box_frame = tk.LabelFrame(parent, text="Plot Box", bg=self.ui_panel, font=self.ui_font_bold)
        box_frame.pack(fill=tk.X, pady=5)
        box_row = tk.Frame(box_frame, bg=self.ui_panel)
        box_row.pack(fill='x', padx=5, pady=2)
        box_row.columnconfigure(1, weight=1)
        tk.Label(box_row, text="Box Line Width:", bg=self.ui_panel).grid(
            row=0, column=0, columnspan=3, sticky='w', pady=(2, 0)
        )
        self.var_plot_box_linewidth = tk.DoubleVar(value=self.plot_box_linewidth)
        self.scale_plot_box_linewidth = ModernScale(
            box_row,
            from_=0.2,
            to=5.0,
            resolution=0.1,
            orient='horizontal',
            variable=self.var_plot_box_linewidth,
            command=lambda v: self._request_draw_plot(),
            showvalue=False,
            length=170,
            bg=self.ui_panel
        )
        self.scale_plot_box_linewidth.grid(
            row=1, column=0, columnspan=2, sticky='ew', padx=(6, 5), pady=(0, 3)
        )
        self.ent_plot_box_linewidth = tk.Entry(
            box_row, textvariable=self.var_plot_box_linewidth, width=5
        )
        self.ent_plot_box_linewidth.grid(row=1, column=2, sticky='w', pady=(0, 3))
        self.ent_plot_box_linewidth.bind("<Return>", lambda e: self._request_draw_plot())
        self.ent_plot_box_linewidth.bind("<FocusOut>", lambda e: self._request_draw_plot())

        fixed_box_row = tk.Frame(box_frame, bg=self.ui_panel)
        fixed_box_row.pack(fill='x', padx=5, pady=(4, 2))
        self.var_fixed_plot_box_enabled = tk.BooleanVar(value=getattr(self, "fixed_plot_box_enabled", False))
        tk.Checkbutton(
            fixed_box_row,
            text="Fixed Box (cm)",
            variable=self.var_fixed_plot_box_enabled,
            command=self._request_draw_plot,
            bg=self.ui_panel
        ).pack(side='left')

        box_size_row = tk.Frame(box_frame, bg=self.ui_panel)
        box_size_row.pack(fill='x', padx=5, pady=(0, 4))
        self.var_plot_box_width_cm = tk.DoubleVar(value=getattr(self, "plot_box_width_cm", 12.0))
        self.var_plot_box_height_cm = tk.DoubleVar(value=getattr(self, "plot_box_height_cm", 8.0))
        tk.Label(box_size_row, text="W:", bg=self.ui_panel).pack(side='left')
        ent_box_w = tk.Entry(box_size_row, textvariable=self.var_plot_box_width_cm, width=6)
        ent_box_w.pack(side='left', padx=(2, 6))
        tk.Label(box_size_row, text="cm  H:", bg=self.ui_panel).pack(side='left')
        ent_box_h = tk.Entry(box_size_row, textvariable=self.var_plot_box_height_cm, width=6)
        ent_box_h.pack(side='left', padx=(2, 2))
        tk.Label(box_size_row, text="cm", bg=self.ui_panel).pack(side='left')
        ent_box_w.bind("<Return>", lambda e: self._request_draw_plot())
        ent_box_w.bind("<FocusOut>", lambda e: self._request_draw_plot())
        ent_box_h.bind("<Return>", lambda e: self._request_draw_plot())
        ent_box_h.bind("<FocusOut>", lambda e: self._request_draw_plot())

        axis_label_frame = tk.LabelFrame(parent, text="Axis Titles (2theta / Intensity)", bg=self.ui_panel, font=self.ui_font_bold)
        axis_label_frame.pack(fill=tk.X, pady=5)
        self.var_axis_label_font = tk.StringVar(value=getattr(self, "axis_label_font", "Use Plot Font"))
        self.var_axis_label_color = tk.StringVar(value=getattr(self, "axis_label_color", "#000000"))
        self.var_axis_label_x_pad = tk.DoubleVar(value=getattr(self, "axis_label_x_pad", 6.0))
        self.var_axis_label_y_pad = tk.DoubleVar(value=getattr(self, "axis_label_y_pad", 10.0))
        self.var_axis_label_y_coord = tk.DoubleVar(value=getattr(self, "axis_label_y_coord", -0.075))

        axis_vis_grid = tk.Frame(axis_label_frame, bg=self.ui_panel)
        axis_vis_grid.pack(fill='x', padx=5, pady=(3, 1))
        tk.Checkbutton(axis_vis_grid, text="X Title", variable=self.var_axis_title_x_2d, command=self._request_draw_plot, bg=self.ui_panel).grid(row=0, column=0, sticky='w', padx=(0, 8))
        tk.Checkbutton(axis_vis_grid, text="Y Title", variable=self.var_axis_title_y_2d, command=self._request_draw_plot, bg=self.ui_panel).grid(row=0, column=1, sticky='w', padx=(0, 8))

        axis_font_row = tk.Frame(axis_label_frame, bg=self.ui_panel)
        axis_font_row.pack(fill='x', padx=5, pady=2)
        axis_font_row.columnconfigure(1, weight=1)
        tk.Label(axis_font_row, text="Font:", bg=self.ui_panel).grid(row=0, column=0, sticky='w')
        axis_font_values = ["Use Plot Font"] + [f for f in available_plot_fonts() if f != "Use Plot Font"]
        cmb_axis_font = ttk.Combobox(
            axis_font_row,
            textvariable=self.var_axis_label_font,
            values=axis_font_values,
            state="readonly",
            width=16,
        )
        cmb_axis_font.grid(row=0, column=1, columnspan=2, sticky='ew', padx=4, pady=2)
        cmb_axis_font.bind("<<ComboboxSelected>>", lambda e: self._request_draw_plot())

        axis_size_row = tk.Frame(axis_label_frame, bg=self.ui_panel)
        axis_size_row.pack(fill='x', padx=5, pady=2)
        axis_size_row.columnconfigure(1, weight=1)
        tk.Label(axis_size_row, text="Size:", bg=self.ui_panel).grid(
            row=0, column=0, columnspan=4, sticky='w', pady=(2, 0)
        )
        self.scale_axis_title_size = ModernScale(
            axis_size_row,
            from_=6,
            to=96,
            orient='horizontal',
            variable=self.var_axis_size,
            command=lambda v: self._request_draw_plot(),
            showvalue=False,
            length=170,
            bg=self.ui_panel
        )
        self.scale_axis_title_size.grid(
            row=1, column=0, columnspan=2, sticky='ew', padx=(6, 5), pady=(0, 3)
        )
        self.ent_axis_title_size = tk.Entry(
            axis_size_row, textvariable=self.var_axis_size, width=4
        )
        self.ent_axis_title_size.grid(row=1, column=2, sticky='w', pady=(0, 3))
        self.ent_axis_title_size.bind("<Return>", lambda e: self._request_draw_plot())
        self.ent_axis_title_size.bind("<FocusOut>", lambda e: self._request_draw_plot())
        self.chk_axis_title_bold = tk.Checkbutton(
            axis_size_row,
            text="Bold",
            variable=self.var_axis_label_bold,
            command=self._request_draw_plot,
            bg=self.ui_panel,
        )
        self.chk_axis_title_bold.grid(row=1, column=3, sticky='w', pady=(0, 3))
        axis_color_row = tk.Frame(axis_label_frame, bg=self.ui_panel)
        axis_color_row.pack(fill='x', padx=5, pady=2)
        axis_color_row.columnconfigure(1, weight=1)
        tk.Label(axis_color_row, text="Color:", bg=self.ui_panel).grid(row=0, column=0, sticky='w')
        ent_axis_color = tk.Entry(axis_color_row, textvariable=self.var_axis_label_color, width=10)
        ent_axis_color.grid(row=0, column=1, sticky='ew', padx=4)
        ent_axis_color.bind("<Return>", lambda e: self._request_draw_plot())
        ent_axis_color.bind("<FocusOut>", lambda e: self._request_draw_plot())
        tk.Button(axis_color_row, text="Pick", command=self.pick_axis_label_color, bg=self.ui_button_light, font=self.ui_font).grid(row=0, column=2, sticky='w')
        axis_pad_row = tk.Frame(axis_label_frame, bg=self.ui_panel)
        axis_pad_row.pack(fill='x', padx=5, pady=2)
        axis_pad_row.columnconfigure(1, weight=1)

        def add_axis_title_metric(row, label, variable, from_, to_, resolution):
            label_row = row * 2
            control_row = label_row + 1
            tk.Label(axis_pad_row, text=label, bg=self.ui_panel).grid(
                row=label_row,
                column=0,
                columnspan=3,
                sticky='w',
                padx=(0, 3),
                pady=(4 if row else 2, 0),
            )
            scale = ModernScale(
                axis_pad_row,
                from_=from_,
                to=to_,
                resolution=resolution,
                orient='horizontal',
                variable=variable,
                command=lambda v: self._request_draw_plot(),
                showvalue=False,
                length=170,
                bg=self.ui_panel
            )
            scale.grid(
                row=control_row,
                column=0,
                columnspan=2,
                sticky='ew',
                padx=(6, 5),
                pady=(0, 3),
            )
            ent = tk.Entry(axis_pad_row, textvariable=variable, width=5)
            ent.grid(row=control_row, column=2, sticky='w', padx=(0, 4), pady=(0, 3))
            ent.bind("<Return>", lambda e: self._request_draw_plot())
            ent.bind("<FocusOut>", lambda e: self._request_draw_plot())
            return scale, ent

        self.scale_axis_x_padding, self.ent_axis_x_padding = add_axis_title_metric(
            0, "X Padding:", self.var_axis_label_x_pad, 0, 40, 0.5
        )
        self.scale_axis_y_padding, self.ent_axis_y_padding = add_axis_title_metric(
            1, "Y Padding:", self.var_axis_label_y_pad, 0, 50, 0.5
        )
        self.scale_axis_y_position, self.ent_axis_y_position = add_axis_title_metric(
            2, "Y Position:", self.var_axis_label_y_coord, -0.30, 0.05, 0.005
        )
        tk.Label(axis_label_frame, text="Y Pos default (-0.075) uses automatic spacing; changing it fixes the vertical title at that axes coordinate.", bg=self.ui_panel, fg=self.ui_muted, wraplength=300, justify='left').pack(anchor='w', padx=5, pady=(0, 4))

        quick_parent = self.plot_section_bodies["quick"]
        res_frame = tk.LabelFrame(quick_parent, text="Residual", bg=self.ui_panel, font=self.ui_font_bold)
        pack_options = {"fill": tk.X, "padx": 10, "pady": (0, 8)}
        if hasattr(self, "quick_phase_frame"):
            pack_options["before"] = self.quick_phase_frame
        elif hasattr(self, "quick_reference_frame"):
            pack_options["before"] = self.quick_reference_frame
        res_frame.pack(**pack_options)

        residual_metrics = tk.Frame(res_frame, bg=self.ui_panel)
        residual_metrics.pack(fill='x', padx=5, pady=(2, 4))
        residual_metrics.columnconfigure(1, weight=1)
        self.var_resid_ratio = tk.DoubleVar(value=self.residual_ratio)
        self.var_resid_scale = tk.DoubleVar(value=self.residual_scale)
        self.residual_metric_scales = {}
        self.residual_metric_entries = {}

        def add_residual_metric(row, key, label, variable, from_, to_, resolution=1):
            label_row = row * 2
            control_row = label_row + 1
            tk.Label(residual_metrics, text=label, bg=self.ui_panel).grid(
                row=label_row,
                column=0,
                columnspan=3,
                sticky='w',
                pady=(4 if row else 2, 0),
            )
            scale = ModernScale(
                residual_metrics,
                from_=from_,
                to=to_,
                resolution=resolution,
                orient='horizontal',
                variable=variable,
                command=lambda _value: self._request_draw_plot(),
                showvalue=False,
                length=170,
                bg=self.ui_panel,
            )
            scale.grid(
                row=control_row,
                column=0,
                columnspan=2,
                sticky='ew',
                padx=(6, 5),
                pady=(0, 3),
            )
            entry = tk.Entry(residual_metrics, textvariable=variable, width=5)
            entry.grid(row=control_row, column=2, sticky='w', pady=(0, 3))
            entry.bind("<Return>", lambda _event: self._request_draw_plot())
            entry.bind("<FocusOut>", lambda _event: self._request_draw_plot())
            self.residual_metric_scales[key] = scale
            self.residual_metric_entries[key] = entry

        add_residual_metric(0, "title", "Residual Title Size:", self.var_resid_size, 6, 30)
        add_residual_metric(1, "height", "Residual Panel Height:", self.var_resid_ratio, 0.5, 3.0, 0.1)
        add_residual_metric(2, "scale", "Residual Intensity Scale:", self.var_resid_scale, 0.2, 5.0, 0.1)
        self._style_settings_card(res_frame)
        self._make_plot_card_collapsible(res_frame, "Residual", expanded=False)
        self._normalize_section_controls(parent)
        self._normalize_section_controls(quick_parent)

    # ========================================================
    # Logic: File Management
    # ========================================================



