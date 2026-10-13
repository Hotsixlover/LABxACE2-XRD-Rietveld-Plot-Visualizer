# SPDX-License-Identifier: GPL-2.0-or-later
from xrd_rietveld_manager.common import *
from xrd_rietveld_manager.branding import APP_NAME
from xrd_rietveld_manager.ui2_widgets import RoundedScrollbar


class UiRuntimeMixin:
    def _create_ui(self):
        # Main workspace: UI2 workflow rail + one control page + canvas.
        self.status_bar = tk.Frame(self.root, bg=self.ui_surface, height=30)
        # `place` with relative dimensions follows the native toplevel client
        # area directly.  This avoids a Windows/Tk geometry edge case where a
        # maximized PanedWindow retained the initial 1400 px requested width.
        self.status_bar.place(x=0, rely=1.0, y=-30, relwidth=1.0, height=30)
        self.status_bar.pack_propagate(False)
        self.lbl_coords = tk.Label(
            self.status_bar,
            text="X: --   Y: --",
            bg=self.ui_surface,
            fg=self.ui_muted,
            font=("Consolas", 9),
            anchor="w",
        )
        self.lbl_coords.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=12)

        self.paned = tk.PanedWindow(
            self.root,
            orient=tk.HORIZONTAL,
            sashwidth=4,
            opaqueresize=False,
            bg=self.ui_surface,
            bd=0,
            sashrelief=tk.FLAT,
        )
        self.paned.place(x=0, y=0, relwidth=1.0, relheight=1.0, height=-30)
        self.paned.bind("<ButtonRelease-1>", self.on_canvas_resize)

        self.workflow_width = 112
        self.control_page_width = 350
        self.left_panel_width = self.workflow_width + self.control_page_width
        self.control_shell = tk.Frame(self.paned, bg=self.ui_bg, width=self.left_panel_width)
        self.paned.add(self.control_shell, minsize=410, stretch="never")

        self.nav_frame = tk.Frame(self.control_shell, bg=self.ui_accent_alt, width=self.workflow_width, bd=0)
        self.nav_frame.pack(side=tk.LEFT, fill=tk.Y)
        self.nav_frame.pack_propagate(False)
        tk.Label(
            self.nav_frame,
            text="WORKFLOW",
            bg=self.ui_accent_alt,
            fg="#DCE8FF",
            font=("Calibri", 8, "bold"),
            anchor="w",
        ).pack(fill=tk.X, padx=14, pady=(16, 10))

        self.page_host = tk.Frame(self.control_shell, bg=self.ui_bg, width=self.control_page_width)
        self.page_host.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.page_host.grid_rowconfigure(0, weight=1)
        self.page_host.grid_columnconfigure(0, weight=1)
        self.control_pages = {}
        self.nav_buttons = {}
        self.page_scrolls = {}
        self.page_bodies = {}

        page_specs = [
            ("data", "DATA", "tab_main", "main_scroll", "tab_main_body", True),
            ("layers", "LAYERS", "tab_layers", None, None, False),
            ("plot", "PLOT", "tab_plot", None, None, False),
            ("output", "OUTPUT", "tab_export", "export_scroll", "tab_export_body", True),
        ]
        for key, label, tab_attr, scroll_attr, body_attr, use_scroll in page_specs:
            button = tk.Button(
                self.nav_frame,
                text=label,
                command=lambda page_key=key: self._show_control_page(page_key),
                anchor="w",
                justify="left",
                relief=tk.FLAT,
                bd=0,
                bg=self.ui_accent_alt,
                fg="#F5F8FF",
                activebackground="#5A8BE3",
                activeforeground="#FFFFFF",
                font=("Calibri", 9, "bold"),
                padx=12,
                pady=11,
                cursor="hand2",
            )
            button.pack(fill=tk.X, padx=8, pady=3)
            self.nav_buttons[key] = button

            page = tk.Frame(self.page_host, bg=self.ui_bg, padx=6, pady=6)
            page.grid(row=0, column=0, sticky="nsew")
            self.control_pages[key] = page
            setattr(self, tab_attr, page)
            if use_scroll:
                scroll = ScrollableFrame(page, bg=self.ui_bg)
                scroll.pack(fill=tk.BOTH, expand=True)
                body = scroll.scrollable_frame
                self.page_scrolls[key] = scroll
                self.page_bodies[key] = body
                setattr(self, scroll_attr, scroll)
                setattr(self, body_attr, body)

        figure_button = tk.Button(
            self.nav_frame,
            text="FIGURE SET",
            command=lambda: self._show_center_page("figure_set"),
            anchor="w",
            justify="left",
            relief=tk.FLAT,
            bd=0,
            bg=self.ui_accent_alt,
            fg="#F5F8FF",
            activebackground="#5A8BE3",
            activeforeground="#FFFFFF",
            font=("Calibri", 9, "bold"),
            padx=12,
            pady=11,
            cursor="hand2",
        )
        figure_button.pack(fill=tk.X, padx=8, pady=3)
        self.nav_buttons["figure_set"] = figure_button

        # Compatibility aliases used by sizing and legacy UI helpers.
        self.left_shell = self.control_shell
        self.left_notebook = self.control_shell

        # Center Plot/Figure Set workspace. There is intentionally no right inspector.
        self.right_frame = tk.Frame(self.paned, bg=self.ui_canvas_bg)
        self.paned.add(self.right_frame, stretch="always")

        # Stack workspaces directly. A ttk.Notebook would expose duplicate
        # Plot Page/Figure Set tabs on some themes even with a custom layout.
        self.center_host = tk.Frame(self.right_frame, bg=self.ui_canvas_bg)
        self.center_host.pack(fill=tk.BOTH, expand=True)
        self.center_host.grid_rowconfigure(0, weight=1)
        self.center_host.grid_columnconfigure(0, weight=1)
        self.plot_page_frame = tk.Frame(self.center_host, bg=self.ui_canvas_bg)
        self.figure_set_frame = tk.Frame(self.center_host, bg=self.ui_bg)
        self.plot_page_frame.grid(row=0, column=0, sticky="nsew")
        self.figure_set_frame.grid(row=0, column=0, sticky="nsew")
        self.plot_page_frame.tkraise()

        self.fig = None
        self.canvas = None
        self._canvas_ready = False
        self._pending_canvas_draw = False
        self.canvas_placeholder = tk.Frame(self.plot_page_frame, bg=self.ui_canvas_bg)
        self.canvas_placeholder.pack(fill=tk.BOTH, expand=True)
        tk.Label(
            self.canvas_placeholder,
            text=APP_NAME,
            bg=self.ui_canvas_bg,
            fg=self.ui_text,
            font=getattr(self, "ui_font_title", self.ui_font_bold),
        ).pack(expand=True)
        
        # Setup Tabs
        self._setup_main_tab()
        self._setup_layers_tab()
        self._setup_plot_tab()
        self._setup_color_tab()
        self._setup_axes_tab()
        self._setup_3d_tab()
        self._setup_export_tab()
        self._setup_figure_set_page()
        self._show_control_page("data")
        self.paned.bind("<Configure>", self._schedule_left_panel_enforce, add="+")
        self.root.after_idle(self._enforce_left_panel_width)
        self.root.after_idle(self._init_plot_canvas)

    def _show_control_page(self, page_key):
        legacy_plot_sections = {
            "colors": "style",
            "axes": "axes",
            "3d": "3d",
        }
        requested_section = legacy_plot_sections.get(page_key)
        if requested_section:
            page_key = "plot"
        page = getattr(self, "control_pages", {}).get(page_key)
        if page is None:
            return
        self._set_figure_set_workspace_mode(False)
        page.tkraise()
        self.active_control_page = page_key
        if hasattr(self, "plot_page_frame"):
            self.plot_page_frame.tkraise()
        for key, button in self.nav_buttons.items():
            active = key == page_key
            button.configure(
                bg=self.ui_surface if active else self.ui_accent_alt,
                fg=self.ui_accent_deep if active else "#F5F8FF",
                activebackground=self.ui_surface if active else "#5A8BE3",
                activeforeground=self.ui_accent_deep if active else "#FFFFFF",
            )
        if requested_section and hasattr(self, "_show_plot_section"):
            self._show_plot_section(requested_section)

    def _set_figure_set_workspace_mode(self, enabled):
        """Hide ordinary controls while Figure Set owns the workspace."""
        enabled = bool(enabled)
        self._figure_set_workspace_active = enabled
        if enabled:
            if self.page_host.winfo_manager():
                self.page_host.pack_forget()
        elif not self.page_host.winfo_manager():
            self.page_host.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._enforce_left_panel_width()
        # Repacking page_host changes its requested width on the next idle
        # layout pass. Enforce once more so the PanedWindow cannot retain the
        # 112 px Figure Set rail width for ordinary control pages.
        if hasattr(self, "root"):
            self.root.after_idle(self._enforce_left_panel_width)


    def _show_center_page(self, page_name):
        if not hasattr(self, "center_host"):
            return
        target = self.figure_set_frame if page_name == "figure_set" else self.plot_page_frame
        try:
            figure_mode = page_name == "figure_set"
            self._set_figure_set_workspace_mode(figure_mode)
            target.tkraise()
            active_key = "figure_set" if page_name == "figure_set" else getattr(self, "active_control_page", "data")
            for key, button in self.nav_buttons.items():
                active = key == active_key
                button.configure(
                    bg=self.ui_surface if active else self.ui_accent_alt,
                    fg=self.ui_accent_deep if active else "#F5F8FF",
                    activebackground=self.ui_surface if active else "#5A8BE3",
                    activeforeground=self.ui_accent_deep if active else "#FFFFFF",
                )
        except Exception:
            pass

    def _init_plot_canvas(self):
        if self._canvas_ready:
            return
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        from matplotlib.figure import Figure

        try:
            self.canvas_placeholder.destroy()
        except Exception:
            pass
        self.fig = Figure(figsize=(8, 8), dpi=100, facecolor='white')
        self._plot_canvas_base_dpi = float(self.fig.get_dpi())
        self.plot_page_frame.rowconfigure(0, weight=1)
        self.plot_page_frame.columnconfigure(0, weight=1)
        self.plot_canvas_view = tk.Canvas(
            self.plot_page_frame,
            bg=self.ui_canvas_bg,
            highlightthickness=0,
            bd=0,
        )
        self.plot_canvas_vscroll = RoundedScrollbar(
            self.plot_page_frame,
            orient=tk.VERTICAL,
            command=self.plot_canvas_view.yview,
            bg=self.ui_canvas_bg,
        )
        self.plot_canvas_hscroll = RoundedScrollbar(
            self.plot_page_frame,
            orient=tk.HORIZONTAL,
            command=self.plot_canvas_view.xview,
            bg=self.ui_canvas_bg,
        )
        self.plot_canvas_view.configure(
            xscrollcommand=self.plot_canvas_hscroll.set,
            yscrollcommand=self.plot_canvas_vscroll.set,
        )
        self.plot_canvas_view.grid(row=0, column=0, sticky="nsew")
        # Scrollbars are added only when the rendered figure is larger than
        # the available viewport. Keeping them ungridded here also lets the
        # initial white canvas use the entire Plot Page.
        self._plot_vscroll_visible = False
        self._plot_hscroll_visible = False

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.plot_canvas_view)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.plot_canvas_window = self.plot_canvas_view.create_window(
            0,
            0,
            window=self.canvas_widget,
            anchor="nw",
        )
        self.plot_canvas_view.bind("<Configure>", self.on_canvas_resize)
        self.plot_canvas_view.bind("<Button-3>", self._on_plot_canvas_reset_click, add="+")
        self.plot_page_frame.bind("<Configure>", self.on_canvas_resize)
        self.right_frame.bind("<Configure>", self.on_canvas_resize)
        self._bind_plot_canvas_pan()
        self._bind_plot_canvas_wheel()

        self.canvas.mpl_connect('motion_notify_event', self.on_mouse_move)
        self.canvas.mpl_connect('axes_leave_event', self.on_leave_axes)
        self.canvas.mpl_connect('button_press_event', self.on_mpl_click)
        self.canvas.mpl_connect('button_release_event', self.on_mpl_release)
        self._canvas_ready = True
        self.root.after_idle(self._fit_initial_plot_canvas)
        if self._pending_canvas_draw:
            self._pending_canvas_draw = False
            self._request_draw_plot(delay_ms=1)

    def _plot_canvas_pan_enabled(self):
        """Return whether Ctrl-drag should pan the preserved plot canvas."""
        try:
            return bool(self._panel_canvas_ratio_is_preserved())
        except Exception:
            return False

    def _bind_plot_canvas_pan(self):
        """Bind hand-style viewport panning to the canvas and plotted figure."""
        self._plot_canvas_pan_active = False
        widgets = (
            getattr(self, "plot_canvas_view", None),
            getattr(self, "canvas_widget", None),
        )
        for widget in widgets:
            if widget is None:
                continue
            widget.bind("<Control-ButtonPress-1>", self._on_plot_canvas_pan_start, add="+")
            widget.bind("<Control-B1-Motion>", self._on_plot_canvas_pan_drag, add="+")
            widget.bind("<ButtonRelease-1>", self._on_plot_canvas_pan_end, add="+")

    def _plot_canvas_pointer(self):
        view = getattr(self, "plot_canvas_view", None)
        if view is None:
            return 0, 0
        return (
            int(view.winfo_pointerx() - view.winfo_rootx()),
            int(view.winfo_pointery() - view.winfo_rooty()),
        )

    def _set_plot_canvas_pan_cursor(self, active):
        cursor = "fleur" if active else ""
        for widget in (
            getattr(self, "plot_canvas_view", None),
            getattr(self, "canvas_widget", None),
        ):
            if widget is not None:
                try:
                    widget.configure(cursor=cursor)
                except Exception:
                    pass

    def _on_plot_canvas_pan_start(self, _event=None):
        if not self._plot_canvas_pan_enabled():
            return None
        view = getattr(self, "plot_canvas_view", None)
        if view is None:
            return None
        x, y = self._plot_canvas_pointer()
        view.scan_mark(x, y)
        self._plot_canvas_pan_active = True
        self._set_plot_canvas_pan_cursor(True)
        return "break"

    def _on_plot_canvas_pan_drag(self, _event=None):
        if not getattr(self, "_plot_canvas_pan_active", False):
            return None
        if not self._plot_canvas_pan_enabled():
            self._on_plot_canvas_pan_end()
            return None
        view = getattr(self, "plot_canvas_view", None)
        if view is None:
            return None
        x, y = self._plot_canvas_pointer()
        # gain=1 keeps the plot attached to the pointer like a sheet of paper.
        view.scan_dragto(x, y, gain=1)
        return "break"

    def _on_plot_canvas_pan_end(self, _event=None):
        if not getattr(self, "_plot_canvas_pan_active", False):
            return None
        self._plot_canvas_pan_active = False
        self._set_plot_canvas_pan_cursor(False)
        return "break"

    def _bind_plot_canvas_wheel(self):
        """Use the wheel for scrolling and Ctrl+wheel for canvas zoom."""
        if not hasattr(self, "_plot_canvas_zoom"):
            self._plot_canvas_zoom = 1.0
        widgets = (
            getattr(self, "plot_canvas_view", None),
            getattr(self, "canvas_widget", None),
        )
        for widget in widgets:
            if widget is None:
                continue
            widget.bind("<MouseWheel>", self._on_plot_canvas_mousewheel, add="+")
            widget.bind("<Control-MouseWheel>", self._on_plot_canvas_zoom_wheel, add="+")
            # Linux/X11 reports wheel input as mouse buttons instead of MouseWheel.
            widget.bind("<Button-4>", self._on_plot_canvas_mousewheel, add="+")
            widget.bind("<Button-5>", self._on_plot_canvas_mousewheel, add="+")
            widget.bind("<Control-Button-4>", self._on_plot_canvas_zoom_wheel, add="+")
            widget.bind("<Control-Button-5>", self._on_plot_canvas_zoom_wheel, add="+")

    @staticmethod
    def _plot_canvas_wheel_steps(event):
        button = getattr(event, "num", None)
        if button == 4:
            return 1
        if button == 5:
            return -1
        try:
            delta = int(getattr(event, "delta", 0))
        except Exception:
            delta = 0
        if delta == 0:
            return 0
        magnitude = max(1, min(3, int(round(abs(delta) / 120.0))))
        return magnitude if delta > 0 else -magnitude

    def _on_plot_canvas_mousewheel(self, event):
        # Some Tk builds dispatch the generic binding for modified wheel events.
        if int(getattr(event, "state", 0) or 0) & 0x0004:
            return self._on_plot_canvas_zoom_wheel(event)
        view = getattr(self, "plot_canvas_view", None)
        if view is None:
            return None
        steps = self._plot_canvas_wheel_steps(event)
        if steps:
            view.yview_scroll(-steps * 3, "units")
        return "break"

    def _on_plot_canvas_zoom_wheel(self, event):
        if not getattr(self, "_canvas_ready", False) or self.canvas is None:
            return "break"
        steps = self._plot_canvas_wheel_steps(event)
        if not steps:
            return "break"

        view = getattr(self, "plot_canvas_view", None)
        window = getattr(self, "plot_canvas_window", None)
        self._plot_canvas_zoom_anchor = None
        if view is not None and window is not None:
            try:
                pointer_x, pointer_y = self._plot_canvas_pointer()
                origin_x, origin_y = view.coords(window)
                fig_w, fig_h = self.canvas.get_width_height(physical=True)
                content_x = view.canvasx(pointer_x) - origin_x
                content_y = view.canvasy(pointer_y) - origin_y
                self._plot_canvas_zoom_anchor = (
                    pointer_x,
                    pointer_y,
                    max(0.0, min(1.0, content_x / max(1.0, float(fig_w)))),
                    max(0.0, min(1.0, content_y / max(1.0, float(fig_h)))),
                )
            except Exception:
                self._plot_canvas_zoom_anchor = None

        current = max(0.25, min(4.0, float(getattr(self, "_plot_canvas_zoom", 1.0))))
        updated = max(0.25, min(4.0, current * (1.12 ** steps)))
        if abs(updated - current) < 1e-6:
            self._plot_canvas_zoom_anchor = None
            return "break"
        self._plot_canvas_zoom = updated
        self._apply_plot_canvas_view_zoom()
        return "break"

    def _apply_plot_canvas_view_zoom(self):
        """Resize from the fixed 100% canvas size without rebuilding the plot."""
        base_size = getattr(self, "_plot_canvas_unzoomed_pixels", None)
        if not base_size:
            viewport = getattr(self, "plot_page_frame", None) or getattr(self, "plot_canvas_view", None)
            if viewport is None:
                return
            base_size = (max(2, int(viewport.winfo_width())), max(2, int(viewport.winfo_height())))
        self._apply_plot_aspect_ratio(width=base_size[0], height=base_size[1])
        self.canvas.draw_idle()
        self._sync_plot_canvas_viewport()

    def _reset_plot_canvas_zoom(self, immediate=False):
        try:
            current = float(getattr(self, "_plot_canvas_zoom", 1.0))
        except Exception:
            current = 1.0
        changed = abs(current - 1.0) >= 1e-6
        if not changed and not immediate:
            return False
        self._plot_canvas_zoom = 1.0
        self._plot_canvas_zoom_anchor = None
        if immediate:
            if hasattr(self, "_draw_plot_now"):
                self._draw_plot_now()
            else:
                self.draw_plot()
            return changed
        self._apply_plot_canvas_view_zoom()
        return changed

    def _on_plot_canvas_reset_click(self, event):
        if int(getattr(event, "state", 0) or 0) & 0x0004:
            return None
        return "break" if self._reset_plot_canvas_zoom() else None

    def _fit_initial_plot_canvas(self):
        """Expand the default figure to the complete visible Plot viewport."""
        if not getattr(self, "_canvas_ready", False):
            return
        view = getattr(self, "plot_canvas_view", None)
        if view is None:
            return
        frame = getattr(self, "plot_page_frame", view)
        width = int(frame.winfo_width())
        height = int(frame.winfo_height())
        if width <= 1 or height <= 1:
            self.root.after(60, self._fit_initial_plot_canvas)
            return
        if hasattr(self, "_fixed_plot_box_is_enabled") and self._fixed_plot_box_is_enabled():
            self._sync_plot_canvas_viewport()
            return
        self._apply_plot_aspect_ratio(width=width, height=height)
        self.canvas.draw_idle()
        self._sync_plot_canvas_viewport()

    def _set_plot_scrollbar_visibility(self, horizontal, vertical):
        horizontal = bool(horizontal)
        vertical = bool(vertical)
        if vertical != getattr(self, "_plot_vscroll_visible", False):
            if vertical:
                self.plot_canvas_vscroll.grid(row=0, column=1, sticky="ns")
            else:
                self.plot_canvas_vscroll.grid_remove()
            self._plot_vscroll_visible = vertical
        if horizontal != getattr(self, "_plot_hscroll_visible", False):
            if horizontal:
                self.plot_canvas_hscroll.grid(row=1, column=0, sticky="ew")
            else:
                self.plot_canvas_hscroll.grid_remove()
            self._plot_hscroll_visible = horizontal

    def _sync_plot_canvas_viewport(self):
        if not getattr(self, "_canvas_ready", False) or self.canvas is None:
            return
        view = getattr(self, "plot_canvas_view", None)
        window = getattr(self, "plot_canvas_window", None)
        widget = self.canvas.get_tk_widget()
        if view is None or window is None:
            return
        try:
            # Tk geometry and PhotoImage dimensions are physical pixels,
            # including on monitors using 125%, 150%, or 200% scaling.
            fig_w, fig_h = self.canvas.get_width_height(physical=True)
            fig_w = max(1, int(fig_w))
            fig_h = max(1, int(fig_h))
            widget.configure(width=fig_w, height=fig_h)
            frame = getattr(self, "plot_page_frame", view)
            frame_w = max(1, int(frame.winfo_width()))
            frame_h = max(1, int(frame.winfo_height()))
            if frame_w <= 1 or frame_h <= 1:
                return
            scrollbar_w = max(1, int(self.plot_canvas_vscroll.winfo_reqwidth()))
            scrollbar_h = max(1, int(self.plot_canvas_hscroll.winfo_reqheight()))

            # Resolve the horizontal/vertical dependency: one scrollbar can
            # reduce the other axis enough to make the second one necessary.
            need_h = fig_w > frame_w + 1
            need_v = fig_h > frame_h + 1
            for _ in range(2):
                avail_w = max(1, frame_w - (scrollbar_w if need_v else 0))
                avail_h = max(1, frame_h - (scrollbar_h if need_h else 0))
                need_h = fig_w > avail_w + 1
                need_v = fig_h > avail_h + 1
            self._set_plot_scrollbar_visibility(need_h, need_v)

            view_w = max(1, frame_w - (scrollbar_w if need_v else 0))
            view_h = max(1, frame_h - (scrollbar_h if need_h else 0))
            x = max(0, (view_w - fig_w) // 2)
            y = max(0, (view_h - fig_h) // 2)
            view.itemconfigure(window, width=fig_w, height=fig_h)
            view.coords(window, x, y)
            view.configure(scrollregion=(0, 0, max(view_w, x + fig_w), max(view_h, y + fig_h)))
            if not need_h:
                view.xview_moveto(0.0)
            if not need_v:
                view.yview_moveto(0.0)
            anchor = getattr(self, "_plot_canvas_zoom_anchor", None)
            self._plot_canvas_zoom_anchor = None
            if anchor:
                pointer_x, pointer_y, fraction_x, fraction_y = anchor
                if need_h:
                    region_w = max(1.0, float(max(view_w, x + fig_w)))
                    target_x = max(0.0, x + fraction_x * fig_w - pointer_x)
                    view.xview_moveto(min(1.0, target_x / region_w))
                if need_v:
                    region_h = max(1.0, float(max(view_h, y + fig_h)))
                    target_y = max(0.0, y + fraction_y * fig_h - pointer_y)
                    view.yview_moveto(min(1.0, target_y / region_h))
        except Exception:
            pass

    def _schedule_left_panel_enforce(self, event=None):
        if not hasattr(self, "root") or self._left_panel_after_id is not None:
            return
        self._left_panel_after_id = self.root.after(120, self._enforce_left_panel_width)

    def _enforce_left_panel_width(self):
        self._left_panel_after_id = None
        try:
            compact = bool(getattr(self, "_figure_set_workspace_active", False))
            desired_width = self.workflow_width if compact else self.left_panel_width
            self.control_shell.configure(width=desired_width)
            self.nav_frame.configure(width=self.workflow_width)
            if not compact:
                self.page_host.configure(width=self.control_page_width)
            self.paned.paneconfigure(
                self.control_shell,
                minsize=desired_width,
                width=desired_width,
                stretch="never",
            )
            sash_x = self.paned.sash_coord(0)[0]
            if abs(sash_x - desired_width) > 2:
                self.paned.sash_place(0, desired_width, 1)
        except Exception:
            pass

    def _request_draw_plot(self, delay_ms=140):
        if not getattr(self, "_canvas_ready", False):
            self._pending_canvas_draw = True
            return
        if self._draw_after_id is not None:
            try:
                self.root.after_cancel(self._draw_after_id)
            except Exception:
                pass
        self._draw_after_id = self.root.after(delay_ms, self._flush_draw_plot_request)

    def _flush_draw_plot_request(self):
        self._draw_after_id = None
        self.draw_plot()

    def _draw_plot_now(self):
        if not getattr(self, "_canvas_ready", False):
            self._pending_canvas_draw = True
            self.root.after_idle(self._init_plot_canvas)
            return
        if self._draw_after_id is not None:
            try:
                self.root.after_cancel(self._draw_after_id)
            except Exception:
                pass
            self._draw_after_id = None
        self.draw_plot()

