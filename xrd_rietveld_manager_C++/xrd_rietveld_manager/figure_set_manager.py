# SPDX-License-Identifier: GPL-2.0-or-later
import hashlib
import base64
import io
import math
import time
import uuid
from datetime import datetime

from xrd_rietveld_manager.common import *
from xrd_rietveld_manager.branding import APP_NAME
from xrd_rietveld_manager.profile_parsers import PROFILE_FILE_TYPES
from xrd_rietveld_manager.figure_set_model import FigureSetItem, FigureSetPage

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle
import matplotlib.image as mpimg

try:
    from PIL import Image, ImageOps, ImageTk
except Exception:
    Image = None
    ImageOps = None
    ImageTk = None


class FigureSetManagerMixin:
    def _init_figure_set_state(self):
        self.figure_set_page = FigureSetPage()
        self.figure_set_selected_id = None
        self.figure_set_selected_ids = set()
        self.figure_set_drag = None
        self.figure_set_canvas_items = {}
        self.figure_set_resize_handles = {}
        self.figure_set_subplot_label_hits = {}
        self.figure_set_photo_refs = {}
        self.figure_set_margin_px = 36
        self.figure_set_px_per_cm = 42.0
        self.figure_set_undo_stack = []
        self.figure_set_redo_stack = []
        self._figure_set_history_limit = 30
        self._figure_set_history_suspended = False
        self.figure_set_render_cache = {}
        self.figure_set_render_cache_order = []
        self.figure_set_render_cache_limit = 48
        self._figure_set_render_dpi_override = None
        self._figure_set_last_interactive_refresh = 0.0
        self._figure_set_drag_fast_preview = True
        self.figure_set_clipboard = []
        self.figure_set_export_sidecar_errors = []

    def _setup_figure_set_page(self):
        if not hasattr(self, "figure_set_frame"):
            return

        toolbar = tk.Frame(self.figure_set_frame, bg=self.ui_surface, highlightbackground=self.ui_border, highlightthickness=1)
        toolbar.pack(fill=tk.X, padx=8, pady=(8, 4))

        tk.Button(
            toolbar,
            text="Add Current Plot",
            command=self.add_current_plot_to_figure_set,
            bg=self.ui_accent,
            fg="white",
            font=self.ui_font_bold,
        ).pack(side=tk.LEFT, padx=(8, 4), pady=6)
        tk.Button(
            toolbar,
            text="Replace Selected",
            command=self.replace_selected_figure_set_item_with_current_plot,
            bg=self.ui_button_light,
            font=self.ui_font,
        ).pack(side=tk.LEFT, padx=(0, 4), pady=6)
        tk.Button(
            toolbar,
            text="Undo",
            command=self.undo_figure_set,
            bg=self.ui_button_light,
            font=self.ui_font,
        ).pack(side=tk.LEFT, padx=(4, 2), pady=6)
        tk.Button(
            toolbar,
            text="Redo",
            command=self.redo_figure_set,
            bg=self.ui_button_light,
            font=self.ui_font,
        ).pack(side=tk.LEFT, padx=(0, 4), pady=6)
        tk.Button(
            toolbar,
            text="Clear Set",
            command=self.clear_figure_set,
            bg=self.ui_button_mid,
            fg="white",
            font=self.ui_font,
        ).pack(side=tk.LEFT, padx=4, pady=6)
        tk.Button(
            toolbar,
            text="Save Set",
            command=self.save_figure_set,
            bg=self.ui_button_light,
            font=self.ui_font,
        ).pack(side=tk.LEFT, padx=(8, 2), pady=6)
        tk.Button(
            toolbar,
            text="Load Set",
            command=self.load_figure_set,
            bg=self.ui_button_light,
            font=self.ui_font,
        ).pack(side=tk.LEFT, padx=2, pady=6)
        tk.Button(
            toolbar,
            text="Export Figure",
            command=self.export_figure_set,
            bg=self.ui_accent_deep,
            fg="white",
            font=self.ui_font_bold,
        ).pack(side=tk.LEFT, padx=(8, 2), pady=6)

        tk.Label(toolbar, text="Page", bg=self.ui_surface, fg=self.ui_text, font=self.ui_font_bold).pack(side=tk.LEFT, padx=(14, 4))
        self.var_figset_page_w = tk.DoubleVar(value=self.figure_set_page.width_cm)
        self.var_figset_page_h = tk.DoubleVar(value=self.figure_set_page.height_cm)
        self.var_figset_unit = tk.StringVar(value=self.figure_set_page.unit)
        self.var_figset_preset = tk.StringVar(value=getattr(self.figure_set_page, "preset_name", "Custom"))
        self.var_figset_zoom = tk.IntVar(value=self.figure_set_page.zoom_percent)
        self.var_figset_export_dpi = tk.IntVar(value=self.figure_set_page.export_dpi)
        self.var_figset_transparent = tk.BooleanVar(value=self.figure_set_page.transparent_background)
        self.var_figset_borders = tk.BooleanVar(value=self.figure_set_page.show_item_borders)
        self.var_figset_panel_transparent = tk.BooleanVar(value=getattr(self.figure_set_page, "panel_transparent_background", True))
        self.var_figset_panel_scale = tk.StringVar(value=f"{float(getattr(self.figure_set_page, 'panel_render_scale', 1.0)):g}x")
        self.var_figset_tight_bbox = tk.BooleanVar(value=getattr(self.figure_set_page, "export_tight_bbox", False))
        self.var_figset_export_padding = tk.DoubleVar(value=getattr(self.figure_set_page, "export_padding_cm", 0.0))
        self.var_figset_metadata = tk.BooleanVar(value=getattr(self.figure_set_page, "export_metadata_enabled", True))
        self.var_figset_set_copy = tk.BooleanVar(value=getattr(self.figure_set_page, "export_set_copy_enabled", True))
        self.var_figset_grid = tk.BooleanVar(value=self.figure_set_page.show_grid)
        self.var_figset_grid_step = tk.DoubleVar(value=getattr(self.figure_set_page, "grid_step_cm", 0.5))
        self.var_figset_guides = tk.BooleanVar(value=self.figure_set_page.show_guides)
        self.var_figset_margin_guides = tk.BooleanVar(value=getattr(self.figure_set_page, "show_margin_guides", True))
        self.var_figset_margin_cm = tk.DoubleVar(value=getattr(self.figure_set_page, "margin_guide_cm", 0.5))
        self.var_figset_manual_guides_x = tk.StringVar(value="")
        self.var_figset_manual_guides_y = tk.StringVar(value="")
        self.var_figset_snap = tk.BooleanVar(value=self.figure_set_page.snap_enabled)
        self.var_figset_master_typography = tk.BooleanVar(value=getattr(self.figure_set_page, "master_typography_enabled", True))
        self.var_figset_master_font = tk.StringVar(value=getattr(self.figure_set_page, "master_font_display", "Current Plot Font"))
        self.var_figset_master_title_size = tk.IntVar(value=getattr(self.figure_set_page, "master_title_size", 12))
        self.var_figset_master_axis_size = tk.IntVar(value=getattr(self.figure_set_page, "master_axis_size", 10))
        self.var_figset_master_tick_size = tk.IntVar(value=getattr(self.figure_set_page, "master_tick_size", 10))
        self.var_figset_master_legend_size = tk.IntVar(value=getattr(self.figure_set_page, "master_legend_size", 10))
        self.var_figset_master_residual_size = tk.IntVar(value=getattr(self.figure_set_page, "master_residual_size", 10))
        self.var_figset_master_memo_size = tk.IntVar(value=getattr(self.figure_set_page, "master_memo_size", 10))
        self.var_figset_master_reference_size = tk.IntVar(value=getattr(self.figure_set_page, "master_reference_size", 8))
        self.var_figset_control_mode = tk.StringVar(value=getattr(self, "figure_set_control_mode", "Layout"))

        tk.Entry(toolbar, textvariable=self.var_figset_page_w, width=6).pack(side=tk.LEFT, padx=2)
        tk.Label(toolbar, text="x", bg=self.ui_surface, fg=self.ui_muted).pack(side=tk.LEFT)
        tk.Entry(toolbar, textvariable=self.var_figset_page_h, width=6).pack(side=tk.LEFT, padx=2)
        ttk.Combobox(toolbar, textvariable=self.var_figset_unit, values=["cm", "inch"], state="readonly", width=5).pack(side=tk.LEFT, padx=(4, 10))
        tk.Label(toolbar, text="Zoom", bg=self.ui_surface, fg=self.ui_text).pack(side=tk.LEFT)
        sp_zoom = tk.Spinbox(toolbar, from_=10, to=800, increment=10, textvariable=self.var_figset_zoom, width=5, command=self.refresh_figure_set_canvas)
        sp_zoom.pack(side=tk.LEFT, padx=(4, 3))
        tk.Button(toolbar, text="Fit", command=self.fit_figure_set_page_to_view, bg=self.ui_button_light, font=self.ui_font).pack(side=tk.LEFT, padx=(0, 2), pady=6)
        tk.Button(toolbar, text="100%", command=lambda: self.set_figure_set_zoom(100), bg=self.ui_button_light, font=self.ui_font).pack(side=tk.LEFT, padx=(0, 10), pady=6)

        tk.Checkbutton(toolbar, text="Grid", variable=self.var_figset_grid, command=self.refresh_figure_set_canvas, bg=self.ui_surface).pack(side=tk.LEFT)
        tk.Checkbutton(toolbar, text="Guides", variable=self.var_figset_guides, command=self.refresh_figure_set_canvas, bg=self.ui_surface).pack(side=tk.LEFT)
        tk.Checkbutton(toolbar, text="Snap", variable=self.var_figset_snap, command=self.refresh_figure_set_canvas, bg=self.ui_surface).pack(side=tk.LEFT)
        tk.Label(toolbar, text="Controls", bg=self.ui_surface, fg=self.ui_text, font=self.ui_font_bold).pack(side=tk.LEFT, padx=(14, 4))
        cmb_figset_mode = ttk.Combobox(
            toolbar,
            textvariable=self.var_figset_control_mode,
            values=["Layout", "Page", "Export", "Item", "Crop/Labels", "All"],
            state="readonly",
            width=10,
        )
        cmb_figset_mode.pack(side=tk.LEFT, padx=(0, 8))
        cmb_figset_mode.bind("<<ComboboxSelected>>", lambda _e: self.apply_figure_set_control_mode())

        for widget in toolbar.winfo_children():
            if isinstance(widget, tk.Entry):
                widget.bind("<Return>", lambda _e: self.refresh_figure_set_canvas())
                widget.bind("<FocusOut>", lambda _e: self.refresh_figure_set_canvas())
        for widget in toolbar.winfo_children():
            if isinstance(widget, ttk.Combobox):
                widget.bind("<<ComboboxSelected>>", lambda _e: self.refresh_figure_set_canvas(), add="+")

        page_tools = tk.Frame(self.figure_set_frame, bg=self.ui_surface, highlightbackground=self.ui_border, highlightthickness=1)
        page_tools.pack(fill=tk.X, padx=8, pady=(0, 4))
        tk.Label(page_tools, text="Page Preset", bg=self.ui_surface, fg=self.ui_text, font=self.ui_font_bold).pack(side=tk.LEFT, padx=(8, 6), pady=5)
        preset_box = ttk.Combobox(
            page_tools,
            textvariable=self.var_figset_preset,
            values=list(self._figure_set_page_presets().keys()),
            state="readonly",
            width=24,
        )
        preset_box.pack(side=tk.LEFT, padx=(0, 4), pady=5)
        preset_box.bind("<<ComboboxSelected>>", lambda _e: self.apply_figure_set_page_preset())
        tk.Button(page_tools, text="Apply", command=self.apply_figure_set_page_preset, bg=self.ui_button_light, font=self.ui_font).pack(side=tk.LEFT, padx=(0, 12), pady=5)
        tk.Button(page_tools, text="Save Page Tpl", command=self.save_figure_set_page_template, bg=self.ui_button_light, font=self.ui_font).pack(side=tk.LEFT, padx=(0, 2), pady=5)
        tk.Button(page_tools, text="Load Page Tpl", command=self.load_figure_set_page_template, bg=self.ui_button_light, font=self.ui_font).pack(side=tk.LEFT, padx=(0, 12), pady=5)
        tk.Label(page_tools, text="Grid Step cm", bg=self.ui_surface, fg=self.ui_muted).pack(side=tk.LEFT, padx=(2, 2), pady=5)
        sp_grid = tk.Spinbox(page_tools, from_=0.1, to=5.0, increment=0.1, textvariable=self.var_figset_grid_step, width=5, command=self.refresh_figure_set_canvas)
        sp_grid.pack(side=tk.LEFT, padx=(0, 8), pady=5)
        tk.Checkbutton(page_tools, text="Margin Guides", variable=self.var_figset_margin_guides, command=self.refresh_figure_set_canvas, bg=self.ui_surface).pack(side=tk.LEFT, padx=(0, 2), pady=5)
        tk.Label(page_tools, text="cm", bg=self.ui_surface, fg=self.ui_muted).pack(side=tk.LEFT, padx=(2, 2), pady=5)
        sp_margin = tk.Spinbox(page_tools, from_=0.0, to=5.0, increment=0.1, textvariable=self.var_figset_margin_cm, width=5, command=self.refresh_figure_set_canvas)
        sp_margin.pack(side=tk.LEFT, padx=(0, 4), pady=5)
        for widget in (sp_grid, sp_margin):
            widget.bind("<Return>", lambda _e: self.refresh_figure_set_canvas())
            widget.bind("<FocusOut>", lambda _e: self.refresh_figure_set_canvas())

        guide_tools = tk.Frame(self.figure_set_frame, bg=self.ui_surface, highlightbackground=self.ui_border, highlightthickness=1)
        guide_tools.pack(fill=tk.X, padx=8, pady=(0, 4))
        tk.Label(guide_tools, text="Manual Guides cm", bg=self.ui_surface, fg=self.ui_text, font=self.ui_font_bold).pack(side=tk.LEFT, padx=(8, 6), pady=5)
        tk.Label(guide_tools, text="X", bg=self.ui_surface, fg=self.ui_muted).pack(side=tk.LEFT, padx=(2, 2), pady=5)
        ent_guides_x = tk.Entry(guide_tools, textvariable=self.var_figset_manual_guides_x, width=20)
        ent_guides_x.pack(side=tk.LEFT, padx=(0, 6), pady=5)
        tk.Label(guide_tools, text="Y", bg=self.ui_surface, fg=self.ui_muted).pack(side=tk.LEFT, padx=(2, 2), pady=5)
        ent_guides_y = tk.Entry(guide_tools, textvariable=self.var_figset_manual_guides_y, width=20)
        ent_guides_y.pack(side=tk.LEFT, padx=(0, 6), pady=5)
        tk.Button(guide_tools, text="Apply Guides", command=self.apply_figure_set_manual_guides, bg=self.ui_button_light, font=self.ui_font).pack(side=tk.LEFT, padx=(4, 2), pady=5)
        tk.Button(guide_tools, text="Clear Guides", command=self.clear_figure_set_manual_guides, bg=self.ui_button_light, font=self.ui_font).pack(side=tk.LEFT, padx=2, pady=5)
        for ent in (ent_guides_x, ent_guides_y):
            ent.bind("<Return>", lambda _e: self.apply_figure_set_manual_guides())
            ent.bind("<FocusOut>", lambda _e: self.apply_figure_set_manual_guides())

        typography_tools = tk.Frame(self.figure_set_frame, bg=self.ui_surface, highlightbackground=self.ui_border, highlightthickness=1)
        typography_tools.pack(fill=tk.X, padx=8, pady=(0, 4))
        tk.Label(typography_tools, text="Absolute Font Lock", bg=self.ui_surface, fg=self.ui_text, font=self.ui_font_bold).pack(side=tk.LEFT, padx=(8, 6), pady=5)
        tk.Checkbutton(
            typography_tools,
            text="Use",
            variable=self.var_figset_master_typography,
            command=self.apply_figure_set_master_typography,
            bg=self.ui_surface,
        ).pack(side=tk.LEFT, padx=(0, 6), pady=5)
        font_values = ["Current Plot Font"] + [name for name in available_plot_fonts() if name != "Current Plot Font"]
        cmb_master_font = ttk.Combobox(
            typography_tools,
            textvariable=self.var_figset_master_font,
            values=font_values,
            state="readonly",
            width=18,
        )
        cmb_master_font.pack(side=tk.LEFT, padx=(0, 8), pady=5)
        cmb_master_font.bind("<<ComboboxSelected>>", lambda _e: self.apply_figure_set_master_typography())
        for text, var, min_size, max_size in [
            ("Title", self.var_figset_master_title_size, 4, 72),
            ("Axis", self.var_figset_master_axis_size, 4, 72),
            ("Tick", self.var_figset_master_tick_size, 4, 72),
            ("Legend", self.var_figset_master_legend_size, 6, 30),
            ("Residual", self.var_figset_master_residual_size, 6, 30),
            ("Memo", self.var_figset_master_memo_size, 4, 72),
            ("Ref", self.var_figset_master_reference_size, 4, 30),
        ]:
            tk.Label(typography_tools, text=text, bg=self.ui_surface, fg=self.ui_muted).pack(side=tk.LEFT, padx=(4, 2), pady=5)
            sp = tk.Spinbox(
                typography_tools,
                from_=min_size,
                to=max_size,
                increment=1,
                textvariable=var,
                width=4,
                command=self.apply_figure_set_master_typography,
            )
            sp.pack(side=tk.LEFT, padx=(0, 3), pady=5)
            sp.bind("<Return>", lambda _e: self.apply_figure_set_master_typography())
            sp.bind("<FocusOut>", lambda _e: self.apply_figure_set_master_typography())
        tk.Button(
            typography_tools,
            text="Use Current Sizes",
            command=self.use_current_plot_typography_for_figure_set,
            bg=self.ui_button_light,
            font=self.ui_font,
        ).pack(side=tk.LEFT, padx=(8, 2), pady=5)
        tk.Button(
            typography_tools,
            text="Apply to All Panels",
            command=self.lock_all_figure_set_panel_fonts,
            bg=self.ui_accent,
            fg="white",
            font=self.ui_font_bold,
        ).pack(side=tk.LEFT, padx=(4, 2), pady=5)

        tools = tk.Frame(self.figure_set_frame, bg=self.ui_surface, highlightbackground=self.ui_border, highlightthickness=1)
        tools.pack(fill=tk.X, padx=8, pady=(0, 4))
        tk.Label(tools, text="Arrange", bg=self.ui_surface, fg=self.ui_text, font=self.ui_font_bold).pack(side=tk.LEFT, padx=(8, 6), pady=5)
        for text, mode in [
            ("Left", "left"),
            ("H Center", "hcenter"),
            ("Right", "right"),
            ("Top", "top"),
            ("V Center", "vcenter"),
            ("Bottom", "bottom"),
        ]:
            tk.Button(tools, text=text, command=lambda m=mode: self.align_figure_set_selection(m), bg=self.ui_button_light, font=self.ui_font).pack(side=tk.LEFT, padx=2, pady=5)
        tk.Button(tools, text="Distribute H", command=lambda: self.distribute_figure_set_items("h"), bg=self.ui_button_light, font=self.ui_font).pack(side=tk.LEFT, padx=(8, 2), pady=5)
        tk.Button(tools, text="Distribute V", command=lambda: self.distribute_figure_set_items("v"), bg=self.ui_button_light, font=self.ui_font).pack(side=tk.LEFT, padx=2, pady=5)
        tk.Button(tools, text="Same W", command=lambda: self.match_figure_set_item_size("w"), bg=self.ui_button_light, font=self.ui_font).pack(side=tk.LEFT, padx=(8, 2), pady=5)
        tk.Button(tools, text="Same H", command=lambda: self.match_figure_set_item_size("h"), bg=self.ui_button_light, font=self.ui_font).pack(side=tk.LEFT, padx=2, pady=5)
        tk.Button(tools, text="Same Size", command=lambda: self.match_figure_set_item_size("both"), bg=self.ui_button_light, font=self.ui_font).pack(side=tk.LEFT, padx=2, pady=5)
        tk.Button(tools, text="Duplicate", command=self.duplicate_selected_figure_set_item, bg=self.ui_button_light, font=self.ui_font).pack(side=tk.LEFT, padx=(8, 2), pady=5)
        tk.Button(tools, text="Front", command=lambda: self.reorder_figure_set_item("front"), bg=self.ui_button_light, font=self.ui_font).pack(side=tk.LEFT, padx=2, pady=5)
        tk.Button(tools, text="Back", command=lambda: self.reorder_figure_set_item("back"), bg=self.ui_button_light, font=self.ui_font).pack(side=tk.LEFT, padx=2, pady=5)
        tk.Button(tools, text="Delete", command=self.delete_selected_figure_set_item, bg=self.ui_danger, fg="white", font=self.ui_font).pack(side=tk.LEFT, padx=(8, 2), pady=5)

        layout_tools = tk.Frame(self.figure_set_frame, bg=self.ui_surface, highlightbackground=self.ui_border, highlightthickness=1)
        layout_tools.pack(fill=tk.X, padx=8, pady=(0, 4))
        tk.Label(layout_tools, text="Auto Layout", bg=self.ui_surface, fg=self.ui_text, font=self.ui_font_bold).pack(side=tk.LEFT, padx=(8, 6), pady=5)
        self.var_figset_layout_rows = tk.IntVar(value=1)
        self.var_figset_layout_cols = tk.IntVar(value=2)
        self.var_figset_layout_gap = tk.DoubleVar(value=0.3)
        self.var_figset_layout_margin = tk.DoubleVar(value=0.5)
        for text, var, width in [
            ("Rows", self.var_figset_layout_rows, 4),
            ("Cols", self.var_figset_layout_cols, 4),
            ("Gap cm", self.var_figset_layout_gap, 5),
            ("Margin cm", self.var_figset_layout_margin, 5),
        ]:
            tk.Label(layout_tools, text=text, bg=self.ui_surface, fg=self.ui_muted).pack(side=tk.LEFT, padx=(4, 2), pady=5)
            sp = tk.Spinbox(layout_tools, from_=0 if "cm" in text else 1, to=20, increment=0.1 if "cm" in text else 1, textvariable=var, width=width)
            sp.pack(side=tk.LEFT, padx=(0, 4), pady=5)
        tk.Button(layout_tools, text="Apply to Selection", command=lambda: self.auto_layout_figure_set_items("selected"), bg=self.ui_button_light, font=self.ui_font).pack(side=tk.LEFT, padx=(8, 2), pady=5)
        tk.Button(layout_tools, text="Apply to All", command=lambda: self.auto_layout_figure_set_items("all"), bg=self.ui_button_light, font=self.ui_font).pack(side=tk.LEFT, padx=2, pady=5)

        export_tools = tk.Frame(self.figure_set_frame, bg=self.ui_surface, highlightbackground=self.ui_border, highlightthickness=1)
        export_tools.pack(fill=tk.X, padx=8, pady=(0, 4))
        tk.Label(export_tools, text="Export", bg=self.ui_surface, fg=self.ui_text, font=self.ui_font_bold).pack(side=tk.LEFT, padx=(8, 6), pady=5)
        tk.Label(export_tools, text="DPI", bg=self.ui_surface, fg=self.ui_muted).pack(side=tk.LEFT)
        sp_dpi = tk.Spinbox(
            export_tools,
            from_=150,
            to=1200,
            increment=50,
            textvariable=self.var_figset_export_dpi,
            width=6,
            command=self.refresh_figure_set_canvas,
        )
        sp_dpi.pack(side=tk.LEFT, padx=(3, 10), pady=5)
        sp_dpi.bind("<Return>", lambda _e: self.refresh_figure_set_canvas())
        sp_dpi.bind("<FocusOut>", lambda _e: self.refresh_figure_set_canvas())
        tk.Checkbutton(export_tools, text="Transparent BG", variable=self.var_figset_transparent, command=self.refresh_figure_set_canvas, bg=self.ui_surface).pack(side=tk.LEFT)
        tk.Checkbutton(export_tools, text="Show Panel Borders", variable=self.var_figset_borders, command=self.refresh_figure_set_canvas, bg=self.ui_surface).pack(side=tk.LEFT, padx=(8, 0))
        tk.Button(export_tools, text="Preflight", command=self.preflight_figure_set, bg=self.ui_button_light, font=self.ui_font).pack(side=tk.LEFT, padx=(12, 2), pady=5)
        tk.Button(export_tools, text="Render QA", command=self.deep_preflight_figure_set, bg=self.ui_button_light, font=self.ui_font).pack(side=tk.LEFT, padx=2, pady=5)
        tk.Button(export_tools, text="Relink Sources", command=self.relink_figure_set_sources, bg=self.ui_button_light, font=self.ui_font).pack(side=tk.LEFT, padx=(8, 2), pady=5)
        tk.Button(export_tools, text="Export Selected Panels", command=self.export_selected_figure_set_panels, bg=self.ui_button_light, font=self.ui_font).pack(side=tk.LEFT, padx=(12, 2), pady=5)
        tk.Button(export_tools, text="Export All Panels", command=self.export_all_figure_set_panels, bg=self.ui_button_light, font=self.ui_font).pack(side=tk.LEFT, padx=2, pady=5)
        tk.Button(export_tools, text="Clear Render Cache", command=self.clear_figure_set_render_cache, bg=self.ui_button_light, font=self.ui_font).pack(side=tk.LEFT, padx=(8, 2), pady=5)

        quality_tools = tk.Frame(self.figure_set_frame, bg=self.ui_surface, highlightbackground=self.ui_border, highlightthickness=1)
        quality_tools.pack(fill=tk.X, padx=8, pady=(0, 4))
        tk.Label(quality_tools, text="Export Quality", bg=self.ui_surface, fg=self.ui_text, font=self.ui_font_bold).pack(side=tk.LEFT, padx=(8, 6), pady=5)
        tk.Label(quality_tools, text="Panel DPI", bg=self.ui_surface, fg=self.ui_muted).pack(side=tk.LEFT, padx=(2, 2), pady=5)
        cmb_panel_scale = ttk.Combobox(
            quality_tools,
            textvariable=self.var_figset_panel_scale,
            values=["1x", "1.5x", "2x", "3x"],
            state="readonly",
            width=5,
        )
        cmb_panel_scale.pack(side=tk.LEFT, padx=(0, 8), pady=5)
        cmb_panel_scale.bind("<<ComboboxSelected>>", lambda _e: self.apply_figure_set_export_quality())
        tk.Checkbutton(quality_tools, text="No Panel BG", variable=self.var_figset_panel_transparent, command=self.apply_figure_set_export_quality, bg=self.ui_surface).pack(side=tk.LEFT, padx=(0, 8), pady=5)
        tk.Checkbutton(quality_tools, text="Tight BBox", variable=self.var_figset_tight_bbox, command=self.apply_figure_set_export_quality, bg=self.ui_surface).pack(side=tk.LEFT, padx=(0, 2), pady=5)
        tk.Label(quality_tools, text="Pad cm", bg=self.ui_surface, fg=self.ui_muted).pack(side=tk.LEFT, padx=(6, 2), pady=5)
        sp_pad = tk.Spinbox(
            quality_tools,
            from_=0.0,
            to=2.0,
            increment=0.05,
            textvariable=self.var_figset_export_padding,
            width=5,
            command=self.apply_figure_set_export_quality,
        )
        sp_pad.pack(side=tk.LEFT, padx=(0, 8), pady=5)
        sp_pad.bind("<Return>", lambda _e: self.apply_figure_set_export_quality())
        sp_pad.bind("<FocusOut>", lambda _e: self.apply_figure_set_export_quality())
        tk.Checkbutton(quality_tools, text="Metadata", variable=self.var_figset_metadata, command=self.apply_figure_set_export_quality, bg=self.ui_surface).pack(side=tk.LEFT, padx=(0, 8), pady=5)
        tk.Checkbutton(quality_tools, text="Save Set Copy", variable=self.var_figset_set_copy, command=self.apply_figure_set_export_quality, bg=self.ui_surface).pack(side=tk.LEFT, padx=(0, 8), pady=5)

        canvas_shell = tk.Frame(self.figure_set_frame, bg=self.ui_canvas_bg)
        canvas_shell.pack(fill=tk.BOTH, expand=True, padx=8, pady=(4, 8))
        self.figure_set_canvas_shell = canvas_shell
        self.figure_set_canvas = tk.Canvas(canvas_shell, bg="#e5e7eb", highlightthickness=0)
        xscroll = ttk.Scrollbar(canvas_shell, orient=tk.HORIZONTAL, command=self.figure_set_canvas.xview)
        yscroll = ttk.Scrollbar(canvas_shell, orient=tk.VERTICAL, command=self.figure_set_canvas.yview)
        self.figure_set_canvas.configure(xscrollcommand=xscroll.set, yscrollcommand=yscroll.set)
        self.figure_set_canvas.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        canvas_shell.grid_columnconfigure(0, weight=1)
        canvas_shell.grid_rowconfigure(0, weight=1)

        self.figure_set_canvas.bind("<ButtonPress-1>", self._on_figure_set_press)
        self.figure_set_canvas.bind("<B1-Motion>", self._on_figure_set_drag)
        self.figure_set_canvas.bind("<ButtonRelease-1>", self._on_figure_set_release)
        self.figure_set_canvas.bind("<Configure>", lambda _e: self.refresh_figure_set_canvas())
        self.figure_set_canvas.bind("<KeyPress>", self._on_figure_set_keypress)
        self.figure_set_canvas.bind("<Control-z>", lambda _e: (self.undo_figure_set(), "break")[-1])
        self.figure_set_canvas.bind("<Control-y>", lambda _e: (self.redo_figure_set(), "break")[-1])
        self.figure_set_canvas.bind("<Control-Z>", lambda _e: (self.undo_figure_set(), "break")[-1])
        self.figure_set_canvas.bind("<Control-Y>", lambda _e: (self.redo_figure_set(), "break")[-1])
        self.figure_set_canvas.bind("<Control-c>", lambda _e: (self.copy_selected_figure_set_items(), "break")[-1])
        self.figure_set_canvas.bind("<Control-v>", lambda _e: (self.paste_figure_set_items(), "break")[-1])
        self.figure_set_canvas.bind("<Control-C>", lambda _e: (self.copy_selected_figure_set_items(), "break")[-1])
        self.figure_set_canvas.bind("<Control-V>", lambda _e: (self.paste_figure_set_items(), "break")[-1])
        self.figure_set_canvas.bind("<MouseWheel>", self._on_figure_set_mousewheel)
        self.figure_set_canvas.bind("<Button-4>", self._on_figure_set_mousewheel)
        self.figure_set_canvas.bind("<Button-5>", self._on_figure_set_mousewheel)

        hint_bar = tk.Frame(self.figure_set_frame, bg=self.ui_surface, highlightbackground=self.ui_border, highlightthickness=1)
        hint_bar.pack(fill=tk.X, padx=8, pady=(0, 4))
        tk.Label(
            hint_bar,
            text="Canvas shortcuts: Ctrl+Wheel = zoom, Wheel = vertical scroll, Shift+Wheel = horizontal scroll, Ctrl+C/V = copy/paste, Arrow = nudge, Alt+Arrow = resize.",
            bg=self.ui_surface,
            fg=self.ui_muted,
            font=self.ui_font,
            anchor="w",
        ).pack(fill=tk.X, padx=8, pady=5)
        self.var_figset_status = tk.StringVar(value="Figure Set status: ready")
        self.figure_set_status_label = tk.Label(
            hint_bar,
            textvariable=self.var_figset_status,
            bg=self.ui_surface,
            fg=self.ui_muted,
            font=self.ui_font,
            anchor="w",
        )
        self.figure_set_status_label.pack(fill=tk.X, padx=8, pady=(0, 5))

        panel_list_bar = tk.Frame(self.figure_set_frame, bg=self.ui_surface, highlightbackground=self.ui_border, highlightthickness=1)
        panel_list_bar.pack(fill=tk.X, padx=8, pady=(0, 8))
        tk.Label(panel_list_bar, text="Panels", bg=self.ui_surface, fg=self.ui_text, font=self.ui_font_bold).pack(side=tk.LEFT, padx=(8, 8), pady=6)
        self.figure_set_panel_listbox = tk.Listbox(
            panel_list_bar,
            height=4,
            selectmode=tk.EXTENDED,
            exportselection=False,
            font=self.ui_font,
            bg="white",
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=self.ui_border,
        )
        self.figure_set_panel_listbox.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8), pady=6)
        self.figure_set_panel_listbox.bind("<<ListboxSelect>>", self._on_figure_set_panel_list_select)
        tk.Button(panel_list_bar, text="Select All", command=self.select_all_figure_set_items, bg=self.ui_button_light, font=self.ui_font).pack(side=tk.LEFT, padx=2, pady=6)
        tk.Button(panel_list_bar, text="Copy", command=self.copy_selected_figure_set_items, bg=self.ui_button_light, font=self.ui_font).pack(side=tk.LEFT, padx=2, pady=6)
        tk.Button(panel_list_bar, text="Paste", command=self.paste_figure_set_items, bg=self.ui_button_light, font=self.ui_font).pack(side=tk.LEFT, padx=2, pady=6)
        tk.Button(panel_list_bar, text="Duplicate", command=self.duplicate_selected_figure_set_item, bg=self.ui_button_light, font=self.ui_font).pack(side=tk.LEFT, padx=2, pady=6)
        tk.Button(panel_list_bar, text="Delete", command=self.delete_selected_figure_set_item, bg=self.ui_danger, fg="white", font=self.ui_font).pack(side=tk.LEFT, padx=(2, 8), pady=6)

        item_bar = tk.Frame(self.figure_set_frame, bg=self.ui_surface, highlightbackground=self.ui_border, highlightthickness=1)
        item_bar.pack(fill=tk.X, padx=8, pady=(0, 8))
        tk.Label(item_bar, text="Selected Item", bg=self.ui_surface, fg=self.ui_text, font=self.ui_font_bold).pack(side=tk.LEFT, padx=(8, 8), pady=6)
        self.var_figset_item_label = tk.StringVar(value="")
        self.var_figset_item_x = tk.DoubleVar(value=0.0)
        self.var_figset_item_y = tk.DoubleVar(value=0.0)
        self.var_figset_item_w = tk.DoubleVar(value=0.0)
        self.var_figset_item_h = tk.DoubleVar(value=0.0)
        self.var_figset_item_keep_font = tk.BooleanVar(value=True)
        self.var_figset_item_fit = tk.StringVar(value="contain")
        self.var_figset_item_size_preset = tk.StringVar(value="Custom")
        for label, var in [("Label", self.var_figset_item_label), ("X", self.var_figset_item_x), ("Y", self.var_figset_item_y), ("W", self.var_figset_item_w), ("H", self.var_figset_item_h)]:
            tk.Label(item_bar, text=label, bg=self.ui_surface, fg=self.ui_muted).pack(side=tk.LEFT, padx=(4, 2))
            width = 16 if label == "Label" else 6
            ent = tk.Entry(item_bar, textvariable=var, width=width)
            ent.pack(side=tk.LEFT, padx=(0, 4), pady=6)
            ent.bind("<Return>", lambda _e: self.apply_figure_set_item_properties())
            ent.bind("<FocusOut>", lambda _e: self.apply_figure_set_item_properties())
        tk.Label(item_bar, text="Fit", bg=self.ui_surface, fg=self.ui_muted).pack(side=tk.LEFT, padx=(4, 2))
        fit_box = ttk.Combobox(
            item_bar,
            textvariable=self.var_figset_item_fit,
            values=["contain", "fill", "stretch"],
            state="readonly",
            width=8,
        )
        fit_box.pack(side=tk.LEFT, padx=(0, 4), pady=6)
        fit_box.bind("<<ComboboxSelected>>", lambda _e: self.apply_figure_set_item_properties())
        tk.Checkbutton(
            item_bar,
            text="Fixed Font",
            variable=self.var_figset_item_keep_font,
            command=self.apply_figure_set_item_properties,
            bg=self.ui_surface,
        ).pack(side=tk.LEFT, padx=(8, 4))
        tk.Button(item_bar, text="Apply", command=self.apply_figure_set_item_properties, bg=self.ui_button_light, font=self.ui_font).pack(side=tk.LEFT, padx=4)
        tk.Label(item_bar, text="Preset", bg=self.ui_surface, fg=self.ui_muted).pack(side=tk.LEFT, padx=(8, 2))
        cmb_item_size = ttk.Combobox(
            item_bar,
            textvariable=self.var_figset_item_size_preset,
            values=list(self._figure_set_item_size_presets().keys()),
            state="readonly",
            width=12,
        )
        cmb_item_size.pack(side=tk.LEFT, padx=(0, 3), pady=6)
        cmb_item_size.bind("<<ComboboxSelected>>", lambda _e: self.apply_figure_set_item_size_preset())
        tk.Button(item_bar, text="Set Size", command=self.apply_figure_set_item_size_preset, bg=self.ui_button_light, font=self.ui_font).pack(side=tk.LEFT, padx=2)
        tk.Button(item_bar, text="Swap W/H", command=self.swap_figure_set_item_size, bg=self.ui_button_light, font=self.ui_font).pack(side=tk.LEFT, padx=(2, 4))

        crop_bar = tk.Frame(self.figure_set_frame, bg=self.ui_surface, highlightbackground=self.ui_border, highlightthickness=1)
        crop_bar.pack(fill=tk.X, padx=8, pady=(0, 8))
        tk.Label(crop_bar, text="Panel Crop", bg=self.ui_surface, fg=self.ui_text, font=self.ui_font_bold).pack(side=tk.LEFT, padx=(8, 8), pady=6)
        tk.Label(crop_bar, text="Trim rendered panel image before fitting. Unit: % per side.", bg=self.ui_surface, fg=self.ui_muted, font=self.ui_font).pack(side=tk.LEFT, padx=(0, 10), pady=6)
        self.var_figset_crop_left = tk.DoubleVar(value=0.0)
        self.var_figset_crop_right = tk.DoubleVar(value=0.0)
        self.var_figset_crop_top = tk.DoubleVar(value=0.0)
        self.var_figset_crop_bottom = tk.DoubleVar(value=0.0)
        for text, var in [
            ("L", self.var_figset_crop_left),
            ("R", self.var_figset_crop_right),
            ("T", self.var_figset_crop_top),
            ("B", self.var_figset_crop_bottom),
        ]:
            tk.Label(crop_bar, text=text, bg=self.ui_surface, fg=self.ui_muted).pack(side=tk.LEFT, padx=(4, 2), pady=6)
            sp = tk.Spinbox(
                crop_bar,
                from_=0,
                to=90,
                increment=0.5,
                textvariable=var,
                width=5,
                command=self.apply_figure_set_crop_properties,
            )
            sp.pack(side=tk.LEFT, padx=(0, 4), pady=6)
            sp.bind("<Return>", lambda _e: self.apply_figure_set_crop_properties())
            sp.bind("<FocusOut>", lambda _e: self.apply_figure_set_crop_properties())
        tk.Button(crop_bar, text="Apply Crop", command=self.apply_figure_set_crop_properties, bg=self.ui_button_light, font=self.ui_font).pack(side=tk.LEFT, padx=(8, 2), pady=6)
        tk.Button(crop_bar, text="Reset Crop", command=self.reset_figure_set_crop_properties, bg=self.ui_button_light, font=self.ui_font).pack(side=tk.LEFT, padx=2, pady=6)
        tk.Button(crop_bar, text="Crop Editor", command=self.open_figure_set_crop_editor, bg=self.ui_button_light, font=self.ui_font).pack(side=tk.LEFT, padx=(8, 2), pady=6)

        label_bar = tk.Frame(self.figure_set_frame, bg=self.ui_surface, highlightbackground=self.ui_border, highlightthickness=1)
        label_bar.pack(fill=tk.X, padx=8, pady=(0, 8))
        tk.Label(label_bar, text="Subplot Label", bg=self.ui_surface, fg=self.ui_text, font=self.ui_font_bold).pack(side=tk.LEFT, padx=(8, 8), pady=6)
        self.var_figset_subplot_visible = tk.BooleanVar(value=True)
        self.var_figset_subplot_label = tk.StringVar(value="")
        self.var_figset_subplot_size = tk.IntVar(value=10)
        self.var_figset_subplot_bold = tk.BooleanVar(value=True)
        self.var_figset_subplot_x = tk.DoubleVar(value=0.10)
        self.var_figset_subplot_y = tk.DoubleVar(value=0.10)
        self.var_figset_subplot_color = tk.StringVar(value="#111827")
        tk.Checkbutton(label_bar, text="Show", variable=self.var_figset_subplot_visible, command=self.apply_figure_set_subplot_properties, bg=self.ui_surface).pack(side=tk.LEFT)
        tk.Label(label_bar, text="Text", bg=self.ui_surface, fg=self.ui_muted).pack(side=tk.LEFT, padx=(6, 2))
        ent_sub = tk.Entry(label_bar, textvariable=self.var_figset_subplot_label, width=8)
        ent_sub.pack(side=tk.LEFT, padx=(0, 4), pady=6)
        tk.Label(label_bar, text="Size", bg=self.ui_surface, fg=self.ui_muted).pack(side=tk.LEFT, padx=(6, 2))
        sp_sub_size = tk.Spinbox(label_bar, from_=5, to=48, increment=1, textvariable=self.var_figset_subplot_size, width=4, command=self.apply_figure_set_subplot_properties)
        sp_sub_size.pack(side=tk.LEFT, padx=(0, 4), pady=6)
        tk.Checkbutton(label_bar, text="Bold", variable=self.var_figset_subplot_bold, command=self.apply_figure_set_subplot_properties, bg=self.ui_surface).pack(side=tk.LEFT)
        tk.Button(label_bar, text="Color", command=self.choose_figure_set_subplot_color, bg=self.ui_button_light, font=self.ui_font).pack(side=tk.LEFT, padx=(6, 2))
        tk.Label(label_bar, text="X/Y cm", bg=self.ui_surface, fg=self.ui_muted).pack(side=tk.LEFT, padx=(8, 2))
        ent_sub_x = tk.Entry(label_bar, textvariable=self.var_figset_subplot_x, width=5)
        ent_sub_x.pack(side=tk.LEFT, padx=(0, 2), pady=6)
        ent_sub_y = tk.Entry(label_bar, textvariable=self.var_figset_subplot_y, width=5)
        ent_sub_y.pack(side=tk.LEFT, padx=(0, 4), pady=6)
        for ent in (ent_sub, ent_sub_x, ent_sub_y, sp_sub_size):
            ent.bind("<Return>", lambda _e: self.apply_figure_set_subplot_properties())
            ent.bind("<FocusOut>", lambda _e: self.apply_figure_set_subplot_properties())
        tk.Button(label_bar, text="Auto a,b,c", command=self.auto_label_figure_set_items, bg=self.ui_button_light, font=self.ui_font).pack(side=tk.LEFT, padx=(8, 2))
        tk.Button(label_bar, text="Clear", command=self.clear_figure_set_subplot_labels, bg=self.ui_button_light, font=self.ui_font).pack(side=tk.LEFT, padx=2)
        self.figure_set_top_control_sections = [
            ("page", page_tools),
            ("guides", guide_tools),
            ("typography", typography_tools),
            ("arrange", tools),
            ("layout", layout_tools),
            ("export", export_tools),
            ("quality", quality_tools),
        ]
        self.figure_set_bottom_control_sections = [
            ("hint", hint_bar),
            ("panels", panel_list_bar),
            ("item", item_bar),
            ("crop", crop_bar),
            ("label", label_bar),
        ]
        self._figure_set_section_pack_options = {
            "page": {"fill": tk.X, "padx": 8, "pady": (0, 4)},
            "guides": {"fill": tk.X, "padx": 8, "pady": (0, 4)},
            "typography": {"fill": tk.X, "padx": 8, "pady": (0, 4)},
            "arrange": {"fill": tk.X, "padx": 8, "pady": (0, 4)},
            "layout": {"fill": tk.X, "padx": 8, "pady": (0, 4)},
            "export": {"fill": tk.X, "padx": 8, "pady": (0, 4)},
            "quality": {"fill": tk.X, "padx": 8, "pady": (0, 4)},
            "hint": {"fill": tk.X, "padx": 8, "pady": (0, 4)},
            "panels": {"fill": tk.X, "padx": 8, "pady": (0, 8)},
            "item": {"fill": tk.X, "padx": 8, "pady": (0, 8)},
            "crop": {"fill": tk.X, "padx": 8, "pady": (0, 8)},
            "label": {"fill": tk.X, "padx": 8, "pady": (0, 8)},
        }
        self.apply_figure_set_control_mode()
        self.refresh_figure_set_canvas()

    def apply_figure_set_control_mode(self):
        if not hasattr(self, "figure_set_canvas_shell"):
            return
        mode = str(self.var_figset_control_mode.get() if hasattr(self, "var_figset_control_mode") else "Layout")
        self.figure_set_control_mode = mode
        visible = {
            "All": {
                "page", "guides", "typography", "arrange", "layout", "export", "quality",
                "hint", "panels", "item", "crop", "label",
            },
            "Layout": {"page", "guides", "typography", "arrange", "layout", "hint", "panels", "item"},
            "Page": {"page", "guides", "typography", "hint"},
            "Export": {"export", "quality", "typography", "hint", "panels"},
            "Item": {"arrange", "hint", "panels", "item"},
            "Crop/Labels": {"hint", "panels", "item", "crop", "label"},
        }.get(mode, {"page", "guides", "typography", "arrange", "layout", "hint", "panels", "item"})

        sections = list(getattr(self, "figure_set_top_control_sections", [])) + list(getattr(self, "figure_set_bottom_control_sections", []))
        for _name, frame in sections:
            try:
                frame.pack_forget()
            except Exception:
                pass

        for name, frame in getattr(self, "figure_set_top_control_sections", []):
            if name not in visible:
                continue
            options = dict(self._figure_set_section_pack_options.get(name, {"fill": tk.X, "padx": 8, "pady": (0, 4)}))
            options["before"] = self.figure_set_canvas_shell
            frame.pack(**options)

        anchor = self.figure_set_canvas_shell
        for name, frame in getattr(self, "figure_set_bottom_control_sections", []):
            if name not in visible:
                continue
            options = dict(self._figure_set_section_pack_options.get(name, {"fill": tk.X, "padx": 8, "pady": (0, 8)}))
            options["after"] = anchor
            frame.pack(**options)
            anchor = frame

    def _cm_to_inches(self, value_cm):
        return float(value_cm) / 2.54

    def _figure_set_page_presets(self):
        return {
            "Custom": None,
            "Single column 8.9 x 6.5 cm": (8.9, 6.5),
            "Single column tall 8.9 x 12.0 cm": (8.9, 12.0),
            "Double column 17.8 x 12.0 cm": (17.8, 12.0),
            "Double column compact 17.8 x 8.9 cm": (17.8, 8.9),
            "Square panel 8.9 x 8.9 cm": (8.9, 8.9),
            "Graphical abstract 8.25 x 4.45 cm": (8.25, 4.45),
            "A4 portrait 21.0 x 29.7 cm": (21.0, 29.7),
            "A4 landscape 29.7 x 21.0 cm": (29.7, 21.0),
        }

    def apply_figure_set_page_preset(self):
        if not hasattr(self, "var_figset_preset"):
            return
        name = str(self.var_figset_preset.get() or "Custom")
        preset = self._figure_set_page_presets().get(name)
        self._push_figure_set_undo_state()
        self.figure_set_page.preset_name = name
        if preset is not None:
            width_cm, height_cm = preset
            self.figure_set_page.width_cm = float(width_cm)
            self.figure_set_page.height_cm = float(height_cm)
            if hasattr(self, "var_figset_unit") and str(self.var_figset_unit.get()).lower() == "inch":
                self.var_figset_page_w.set(round(width_cm / 2.54, 4))
                self.var_figset_page_h.set(round(height_cm / 2.54, 4))
            else:
                self.var_figset_page_w.set(round(width_cm, 4))
                self.var_figset_page_h.set(round(height_cm, 4))
        self.refresh_figure_set_canvas()

    def _sync_figure_set_page_from_ui(self):
        if not hasattr(self, "var_figset_page_w"):
            return
        try:
            w = float(self.var_figset_page_w.get())
            h = float(self.var_figset_page_h.get())
            if str(self.var_figset_unit.get()).lower() == "inch":
                w *= 2.54
                h *= 2.54
            self.figure_set_page.width_cm = max(1.0, w)
            self.figure_set_page.height_cm = max(1.0, h)
        except Exception:
            pass
        try:
            self.figure_set_page.zoom_percent = max(10, min(800, int(float(self.var_figset_zoom.get()))))
        except Exception:
            self.figure_set_page.zoom_percent = 100
        try:
            self.figure_set_page.export_dpi = max(150, min(1200, int(float(self.var_figset_export_dpi.get()))))
        except Exception:
            self.figure_set_page.export_dpi = 600
        self.figure_set_page.preset_name = str(self.var_figset_preset.get() or "Custom") if hasattr(self, "var_figset_preset") else "Custom"
        self.figure_set_page.unit = self.var_figset_unit.get()
        self.figure_set_page.transparent_background = bool(self.var_figset_transparent.get())
        if hasattr(self, "var_figset_panel_transparent"):
            self.figure_set_page.panel_transparent_background = bool(self.var_figset_panel_transparent.get())
        if hasattr(self, "var_figset_panel_scale"):
            scale_text = str(self.var_figset_panel_scale.get() or "1x").lower().replace("x", "").strip()
            try:
                self.figure_set_page.panel_render_scale = max(1.0, min(3.0, float(scale_text)))
            except Exception:
                self.figure_set_page.panel_render_scale = 1.0
        if hasattr(self, "var_figset_tight_bbox"):
            self.figure_set_page.export_tight_bbox = bool(self.var_figset_tight_bbox.get())
        if hasattr(self, "var_figset_export_padding"):
            try:
                self.figure_set_page.export_padding_cm = max(0.0, min(2.0, float(self.var_figset_export_padding.get())))
            except Exception:
                self.figure_set_page.export_padding_cm = 0.0
        if hasattr(self, "var_figset_metadata"):
            self.figure_set_page.export_metadata_enabled = bool(self.var_figset_metadata.get())
        if hasattr(self, "var_figset_set_copy"):
            self.figure_set_page.export_set_copy_enabled = bool(self.var_figset_set_copy.get())
        self.figure_set_page.show_item_borders = bool(self.var_figset_borders.get())
        self.figure_set_page.show_grid = bool(self.var_figset_grid.get())
        try:
            self.figure_set_page.grid_step_cm = max(0.1, min(5.0, float(self.var_figset_grid_step.get())))
        except Exception:
            self.figure_set_page.grid_step_cm = 0.5
        self.figure_set_page.show_guides = bool(self.var_figset_guides.get())
        self.figure_set_page.show_margin_guides = bool(self.var_figset_margin_guides.get())
        try:
            self.figure_set_page.margin_guide_cm = max(0.0, min(10.0, float(self.var_figset_margin_cm.get())))
        except Exception:
            self.figure_set_page.margin_guide_cm = 0.5
        self.figure_set_page.manual_guides_x_cm = self._parse_figure_set_guides(
            self.var_figset_manual_guides_x.get() if hasattr(self, "var_figset_manual_guides_x") else "",
            self.figure_set_page.width_cm,
        )
        self.figure_set_page.manual_guides_y_cm = self._parse_figure_set_guides(
            self.var_figset_manual_guides_y.get() if hasattr(self, "var_figset_manual_guides_y") else "",
            self.figure_set_page.height_cm,
        )
        self.figure_set_page.snap_enabled = bool(self.var_figset_snap.get())
        if hasattr(self, "var_figset_master_typography"):
            self.figure_set_page.master_typography_enabled = bool(self.var_figset_master_typography.get())
        if hasattr(self, "var_figset_master_font"):
            self.figure_set_page.master_font_display = str(self.var_figset_master_font.get() or "Current Plot Font")
        for attr, var_name, fallback, lo, hi in [
            ("master_title_size", "var_figset_master_title_size", 12, 4, 72),
            ("master_axis_size", "var_figset_master_axis_size", 10, 4, 72),
            ("master_tick_size", "var_figset_master_tick_size", 10, 4, 72),
            ("master_legend_size", "var_figset_master_legend_size", 10, 6, 30),
            ("master_residual_size", "var_figset_master_residual_size", 10, 6, 30),
            ("master_memo_size", "var_figset_master_memo_size", 10, 4, 72),
            ("master_reference_size", "var_figset_master_reference_size", 8, 4, 30),
        ]:
            if not hasattr(self, var_name):
                continue
            try:
                value = int(float(getattr(self, var_name).get()))
                setattr(self.figure_set_page, attr, max(lo, min(hi, value)))
            except Exception:
                setattr(self.figure_set_page, attr, fallback)

    def _parse_figure_set_guides(self, text, upper_bound):
        values = []
        for part in re.split(r"[,;\s]+", str(text or "").strip()):
            if not part:
                continue
            try:
                value = float(part)
            except Exception:
                continue
            if 0.0 <= value <= float(upper_bound):
                values.append(round(value, 4))
        return sorted(set(values))

    def _format_figure_set_guides(self, values):
        return ", ".join(f"{float(value):g}" for value in values or [])

    def _coerce_figure_set_guide_list(self, values, upper_bound):
        result = []
        for value in values or []:
            try:
                number = float(value)
            except Exception:
                continue
            if 0.0 <= number <= float(upper_bound):
                result.append(round(number, 4))
        return sorted(set(result))

    def apply_figure_set_manual_guides(self):
        self._push_figure_set_undo_state()
        self.refresh_figure_set_canvas()

    def clear_figure_set_manual_guides(self):
        self._push_figure_set_undo_state()
        self.figure_set_page.manual_guides_x_cm = []
        self.figure_set_page.manual_guides_y_cm = []
        if hasattr(self, "var_figset_manual_guides_x"):
            self.var_figset_manual_guides_x.set("")
        if hasattr(self, "var_figset_manual_guides_y"):
            self.var_figset_manual_guides_y.set("")
        self.refresh_figure_set_canvas()

    def apply_figure_set_master_typography(self):
        self._sync_figure_set_page_from_ui()
        self.clear_figure_set_render_cache(show_message=False)
        self.refresh_figure_set_canvas()

    def lock_all_figure_set_panel_fonts(self):
        """Force every Figure Set panel to render with common absolute pt sizes."""
        self._push_figure_set_undo_state()
        if hasattr(self, "var_figset_master_typography"):
            self.var_figset_master_typography.set(True)
        self._sync_figure_set_page_from_ui()
        self.figure_set_page.master_typography_enabled = True
        for item in getattr(self.figure_set_page, "items", []):
            item.keep_font_fixed = True
        self.clear_figure_set_render_cache(show_message=False)
        self.refresh_figure_set_canvas()
        self._update_figure_set_item_bar()

    def use_current_plot_typography_for_figure_set(self):
        self._push_figure_set_undo_state()
        if hasattr(self, "var_figset_master_font"):
            self.var_figset_master_font.set(getattr(self, "plot_font_display", "Current Plot Font"))
        if hasattr(self, "var_figset_master_title_size"):
            self.var_figset_master_title_size.set(int(self._get_ui_value("var_title_size", getattr(self, "title_size", 12))))
        if hasattr(self, "var_figset_master_axis_size"):
            self.var_figset_master_axis_size.set(int(self._get_ui_value("var_axis_size", getattr(self, "axis_label_size", 10))))
        if hasattr(self, "var_figset_master_tick_size"):
            self.var_figset_master_tick_size.set(int(self._get_ui_value("var_tick_label_size", getattr(self, "tick_label_size", 10))))
        if hasattr(self, "var_figset_master_legend_size"):
            self.var_figset_master_legend_size.set(int(self._get_ui_value("var_legend_font_size", getattr(self, "legend_font_size", 10))))
        if hasattr(self, "var_figset_master_residual_size"):
            self.var_figset_master_residual_size.set(int(self._get_ui_value("var_resid_size", getattr(self, "residual_label_size", 10))))
        if hasattr(self, "var_figset_master_memo_size"):
            self.var_figset_master_memo_size.set(int(getattr(self, "plot_memo_default_size", 10)))
        if hasattr(self, "var_figset_master_reference_size"):
            self.var_figset_master_reference_size.set(int(getattr(self, "reference_label_size", 8)))
        self.apply_figure_set_master_typography()

    def apply_figure_set_export_quality(self):
        self._sync_figure_set_page_from_ui()
        self.clear_figure_set_render_cache(show_message=False)
        self.refresh_figure_set_canvas()

    def _figset_scale(self):
        return self.figure_set_px_per_cm * (self.figure_set_page.zoom_percent / 100.0)

    def set_figure_set_zoom(self, zoom_percent):
        try:
            zoom = int(round(float(zoom_percent)))
        except Exception:
            zoom = 100
        zoom = max(10, min(800, zoom))
        self.figure_set_page.zoom_percent = zoom
        if hasattr(self, "var_figset_zoom"):
            self.var_figset_zoom.set(zoom)
        self.refresh_figure_set_canvas()

    def fit_figure_set_page_to_view(self):
        if not hasattr(self, "figure_set_canvas"):
            return
        self._sync_figure_set_page_from_ui()
        try:
            self.figure_set_canvas.update_idletasks()
        except Exception:
            pass
        page_w = max(0.1, float(getattr(self.figure_set_page, "width_cm", 0.1) or 0.1))
        page_h = max(0.1, float(getattr(self.figure_set_page, "height_cm", 0.1) or 0.1))
        canvas_w = max(1, int(self.figure_set_canvas.winfo_width() or 1))
        canvas_h = max(1, int(self.figure_set_canvas.winfo_height() or 1))
        available_w = max(80, canvas_w - self.figure_set_margin_px * 2 - 28)
        available_h = max(80, canvas_h - self.figure_set_margin_px * 2 - 28)
        scale = min(available_w / page_w, available_h / page_h)
        zoom = int(round((scale / max(1.0, float(self.figure_set_px_per_cm))) * 100.0))
        self.set_figure_set_zoom(zoom)

    def _cm_to_canvas(self, x_cm, y_cm):
        scale = self._figset_scale()
        return self.figure_set_margin_px + x_cm * scale, self.figure_set_margin_px + y_cm * scale

    def _canvas_to_cm(self, x_px, y_px):
        scale = self._figset_scale()
        return (x_px - self.figure_set_margin_px) / scale, (y_px - self.figure_set_margin_px) / scale

    def refresh_figure_set_canvas(self):
        if not hasattr(self, "figure_set_canvas"):
            return
        self._sync_figure_set_page_from_ui()
        c = self.figure_set_canvas
        c.delete("all")
        self.figure_set_canvas_items = {}
        self.figure_set_resize_handles = {}
        self.figure_set_subplot_label_hits = {}
        self.figure_set_photo_refs = {}
        scale = self._figset_scale()
        page_w = self.figure_set_page.width_cm * scale
        page_h = self.figure_set_page.height_cm * scale
        x0 = self.figure_set_margin_px
        y0 = self.figure_set_margin_px
        x1 = x0 + page_w
        y1 = y0 + page_h
        c.configure(scrollregion=(0, 0, x1 + self.figure_set_margin_px, y1 + self.figure_set_margin_px))
        c.create_rectangle(x0, y0, x1, y1, fill="white", outline="#111827", width=1.4, tags=("page",))
        page_label = f"{self.figure_set_page.width_cm:.2g} x {self.figure_set_page.height_cm:.2g} cm"
        preset_name = str(getattr(self.figure_set_page, "preset_name", "Custom"))
        if preset_name and preset_name != "Custom":
            page_label = f"{page_label} | {preset_name}"
        c.create_text(x0, y0 - 12, anchor="sw", text=page_label, fill="#64748b", font=(self.plot_font_family, 8), tags=("page_label",))

        if self.figure_set_page.show_grid:
            self._draw_figure_set_grid(x0, y0, x1, y1, scale)
        if self.figure_set_page.show_guides:
            self._draw_figure_set_fixed_guides(x0, y0, x1, y1)

        for item in self.figure_set_page.items:
            self._draw_figure_set_item(item)
        self._draw_figure_set_selection_bounds()
        self._refresh_figure_set_panel_list()
        self._update_figure_set_item_bar()
        self._update_figure_set_status()

    def _update_figure_set_status(self):
        if not hasattr(self, "var_figset_status"):
            return
        try:
            result = self._collect_figure_set_preflight()
            errors = len(result.get("errors", []))
            warnings = len(result.get("warnings", []))
            panels = len(getattr(self.figure_set_page, "items", []) or [])
            selected = len(self._selected_figure_set_items())
            page_w = float(getattr(self.figure_set_page, "width_cm", 0.0) or 0.0)
            page_h = float(getattr(self.figure_set_page, "height_cm", 0.0) or 0.0)
            if errors:
                status = "FAILED"
                color = "#dc2626"
            elif warnings:
                status = "CHECK"
                color = "#d97706"
            else:
                status = "PASS"
                color = "#15803d"
            self.var_figset_status.set(
                f"Figure Set status: {status} | panels {panels} | selected {selected} | warnings {warnings} | errors {errors} | page {page_w:g} x {page_h:g} cm"
            )
            if hasattr(self, "figure_set_status_label"):
                self.figure_set_status_label.configure(fg=color)
        except Exception as exc:
            self.var_figset_status.set(f"Figure Set status: unable to validate ({exc})")
            if hasattr(self, "figure_set_status_label"):
                self.figure_set_status_label.configure(fg="#dc2626")

    def _refresh_figure_set_panel_list(self):
        if not hasattr(self, "figure_set_panel_listbox"):
            return
        lb = self.figure_set_panel_listbox
        self._syncing_figure_set_panel_list = True
        try:
            lb.delete(0, tk.END)
            selected_ids = set(getattr(self, "figure_set_selected_ids", set()))
            for idx, item in enumerate(self.figure_set_page.items):
                label = str(getattr(item, "label", "") or f"Panel {idx + 1}")
                size = f"{float(item.width_cm):.2g} x {float(item.height_cm):.2g} cm"
                fit = str(getattr(item, "fit_mode", "contain"))
                subplot = str(getattr(item, "subplot_label", "") or "").strip()
                prefix = f"{subplot} " if subplot else ""
                lb.insert(tk.END, f"{idx + 1}. {prefix}{label}   [{size}, {fit}]")
                if item.item_id in selected_ids:
                    lb.selection_set(idx)
            if selected_ids:
                first_idx = next((idx for idx, item in enumerate(self.figure_set_page.items) if item.item_id in selected_ids), None)
                if first_idx is not None:
                    lb.see(first_idx)
        finally:
            self._syncing_figure_set_panel_list = False

    def _on_figure_set_panel_list_select(self, _event=None):
        if getattr(self, "_syncing_figure_set_panel_list", False):
            return
        if not hasattr(self, "figure_set_panel_listbox"):
            return
        indices = list(self.figure_set_panel_listbox.curselection())
        ids = [
            self.figure_set_page.items[idx].item_id
            for idx in indices
            if 0 <= idx < len(self.figure_set_page.items)
        ]
        self._set_figure_set_selection(ids)
        self.refresh_figure_set_canvas()

    def select_all_figure_set_items(self):
        self._set_figure_set_selection([item.item_id for item in self.figure_set_page.items])
        self.refresh_figure_set_canvas()

    def _draw_figure_set_grid(self, x0, y0, x1, y1, scale):
        c = self.figure_set_canvas
        step = max(0.1, float(getattr(self.figure_set_page, "grid_step_cm", 0.5))) * scale
        x = x0 + step
        while x < x1 - 1:
            c.create_line(x, y0, x, y1, fill="#edf2f7", width=1, tags=("grid",))
            x += step
        y = y0 + step
        while y < y1 - 1:
            c.create_line(x0, y, x1, y, fill="#edf2f7", width=1, tags=("grid",))
            y += step

    def _draw_figure_set_fixed_guides(self, x0, y0, x1, y1):
        c = self.figure_set_canvas
        cx = (x0 + x1) * 0.5
        cy = (y0 + y1) * 0.5
        c.create_line(cx, y0, cx, y1, fill="#93c5fd", dash=(5, 5), tags=("guide",))
        c.create_line(x0, cy, x1, cy, fill="#93c5fd", dash=(5, 5), tags=("guide",))
        if getattr(self.figure_set_page, "show_margin_guides", True):
            scale = self._figset_scale()
            margin = max(0.0, float(getattr(self.figure_set_page, "margin_guide_cm", 0.5))) * scale
            if margin > 0 and x0 + margin < x1 - margin and y0 + margin < y1 - margin:
                guide_color = "#bfdbfe"
                c.create_rectangle(
                    x0 + margin,
                    y0 + margin,
                    x1 - margin,
                    y1 - margin,
                    outline=guide_color,
                    dash=(4, 4),
                    width=1,
                    tags=("guide",),
                )
        for x_cm in getattr(self.figure_set_page, "manual_guides_x_cm", []) or []:
            gx = x0 + float(x_cm) * self._figset_scale()
            if x0 <= gx <= x1:
                c.create_line(gx, y0, gx, y1, fill="#f97316", dash=(3, 3), width=1.2, tags=("guide", "manual_guide"))
                c.create_text(gx + 3, y0 + 3, anchor="nw", text=f"X {float(x_cm):g}", fill="#ea580c", font=(self.plot_font_family, 7), tags=("guide", "manual_guide"))
        for y_cm in getattr(self.figure_set_page, "manual_guides_y_cm", []) or []:
            gy = y0 + float(y_cm) * self._figset_scale()
            if y0 <= gy <= y1:
                c.create_line(x0, gy, x1, gy, fill="#f97316", dash=(3, 3), width=1.2, tags=("guide", "manual_guide"))
                c.create_text(x0 + 3, gy + 3, anchor="nw", text=f"Y {float(y_cm):g}", fill="#ea580c", font=(self.plot_font_family, 7), tags=("guide", "manual_guide"))

    def _draw_figure_set_item(self, item):
        c = self.figure_set_canvas
        x0, y0 = self._cm_to_canvas(item.x_cm, item.y_cm)
        scale = self._figset_scale()
        x1 = x0 + item.width_cm * scale
        y1 = y0 + item.height_cm * scale
        tag = f"figitem:{item.item_id}"
        selected = self._is_figure_set_item_selected(item.item_id)
        fill = "#f8fafc"
        outline = self.ui_accent if selected else "#334155"
        width = 2.0 if selected else 1.1
        c.create_rectangle(x0, y0, x1, y1, fill=fill, outline=outline, width=width, tags=("figitem", tag))

        photo = self._figure_set_photo_for_item(item, max(1, int(x1 - x0 - 8)), max(1, int(y1 - y0 - 28)))
        if photo is not None:
            self.figure_set_photo_refs[item.item_id] = photo
            c.create_image(x0 + 4, y0 + 22, anchor="nw", image=photo, tags=("figitem", tag))
        else:
            c.create_line(x0, y0, x1, y1, fill="#cbd5e1", tags=("figitem", tag))
            c.create_line(x0, y1, x1, y0, fill="#cbd5e1", tags=("figitem", tag))
        c.create_text(
            x0 + 8,
            y0 + 8,
            anchor="nw",
            text=item.label,
            fill="#111827",
            font=(self.plot_font_family, 10, "bold"),
            tags=("figitem", tag),
        )
        self._draw_figure_set_subplot_label_on_canvas(item, x0, y0, tag)
        size_text = f"{item.width_cm:.2g} x {item.height_cm:.2g} cm"
        c.create_text(
            x0 + 8,
            y1 - 8,
            anchor="sw",
            text=size_text,
            fill="#64748b",
            font=(self.plot_font_family, 8),
            tags=("figitem", tag),
        )
        handle = 8
        handle_id = c.create_rectangle(
            x1 - handle,
            y1 - handle,
            x1 + handle * 0.5,
            y1 + handle * 0.5,
            fill=self.ui_accent if selected else "#94a3b8",
            outline="white",
            width=1,
            tags=("figitem", "resize_handle", tag),
        )
        self.figure_set_resize_handles[handle_id] = item.item_id
        self.figure_set_canvas_items[item.item_id] = (x0, y0, x1, y1)

    def _move_figure_set_canvas_item_directly(self, item_id, dx_px, dy_px):
        """Move an already-drawn panel without rebuilding the whole canvas."""
        if not hasattr(self, "figure_set_canvas"):
            return False
        tag = f"figitem:{item_id}"
        try:
            if not self.figure_set_canvas.find_withtag(tag):
                return False
            self.figure_set_canvas.move(tag, dx_px, dy_px)
            box = self.figure_set_canvas_items.get(item_id)
            if box:
                x0, y0, x1, y1 = box
                self.figure_set_canvas_items[item_id] = (x0 + dx_px, y0 + dy_px, x1 + dx_px, y1 + dy_px)
            return True
        except Exception:
            return False

    def _draw_figure_set_selection_bounds(self):
        selected = self._selected_figure_set_items()
        if len(selected) < 2 or not hasattr(self, "figure_set_canvas"):
            return
        boxes = [self.figure_set_canvas_items.get(item.item_id) for item in selected]
        boxes = [box for box in boxes if box]
        if len(boxes) < 2:
            return
        x0 = min(box[0] for box in boxes)
        y0 = min(box[1] for box in boxes)
        x1 = max(box[2] for box in boxes)
        y1 = max(box[3] for box in boxes)
        self.figure_set_canvas.create_rectangle(
            x0,
            y0,
            x1,
            y1,
            outline="#ef4444",
            dash=(5, 4),
            width=1.4,
            tags=("selection_bounds",),
        )
        self.figure_set_canvas.create_text(
            x0 + 4,
            y0 - 4,
            anchor="sw",
            text=f"{len(selected)} selected",
            fill="#ef4444",
            font=(self.plot_font_family, 8, "bold"),
            tags=("selection_bounds",),
        )

    def _draw_figure_set_subplot_label_on_canvas(self, item, x0, y0, tag):
        if not getattr(item, "subplot_label_visible", True):
            return
        label = str(getattr(item, "subplot_label", "")).strip()
        if not label:
            return
        scale = self._figset_scale()
        x = x0 + max(0.0, float(getattr(item, "subplot_label_x_cm", 0.10))) * scale
        y = y0 + max(0.0, float(getattr(item, "subplot_label_y_cm", 0.10))) * scale
        size = max(5, min(48, int(getattr(item, "subplot_label_size_pt", 10))))
        weight = "bold" if getattr(item, "subplot_label_bold", True) else "normal"
        label_id = self.figure_set_canvas.create_text(
            x,
            y,
            anchor="nw",
            text=label,
            fill=str(getattr(item, "subplot_label_color", "#111827")),
            font=(self.plot_font_family, size, weight),
            tags=("figitem", "subplot_label", tag),
        )
        self.figure_set_subplot_label_hits[label_id] = item.item_id

    def _is_figure_set_item_selected(self, item_id):
        selected = getattr(self, "figure_set_selected_ids", set())
        if selected:
            return item_id in selected
        return item_id == getattr(self, "figure_set_selected_id", None)

    def _set_figure_set_selection(self, item_ids):
        ids = {str(item_id) for item_id in item_ids if item_id}
        self.figure_set_selected_ids = ids
        self.figure_set_selected_id = next(iter(ids), None) if ids else None

    def _selected_figure_set_items(self):
        ids = getattr(self, "figure_set_selected_ids", set())
        if not ids and getattr(self, "figure_set_selected_id", None):
            ids = {self.figure_set_selected_id}
        return [item for item in self.figure_set_page.items if item.item_id in ids]

    def _is_multi_select_event(self, event):
        state = int(getattr(event, "state", 0) or 0)
        return bool(state & 0x0001) or bool(state & 0x0004)

    def _snapshot_figure_set_state(self):
        try:
            return json.loads(json.dumps(self._figure_set_to_dict()))
        except Exception:
            return None

    def _push_figure_set_undo_state(self):
        if getattr(self, "_figure_set_history_suspended", False):
            return
        snapshot = self._snapshot_figure_set_state()
        if snapshot is None:
            return
        self.figure_set_undo_stack.append(snapshot)
        if len(self.figure_set_undo_stack) > self._figure_set_history_limit:
            self.figure_set_undo_stack = self.figure_set_undo_stack[-self._figure_set_history_limit:]
        self.figure_set_redo_stack.clear()

    def _restore_figure_set_state(self, snapshot):
        if not snapshot:
            return
        self._figure_set_history_suspended = True
        try:
            self._load_figure_set_data(snapshot)
        finally:
            self._figure_set_history_suspended = False

    def undo_figure_set(self):
        if not getattr(self, "figure_set_undo_stack", None):
            return
        current = self._snapshot_figure_set_state()
        snapshot = self.figure_set_undo_stack.pop()
        if current is not None:
            self.figure_set_redo_stack.append(current)
        self._restore_figure_set_state(snapshot)

    def redo_figure_set(self):
        if not getattr(self, "figure_set_redo_stack", None):
            return
        current = self._snapshot_figure_set_state()
        snapshot = self.figure_set_redo_stack.pop()
        if current is not None:
            self.figure_set_undo_stack.append(current)
        self._restore_figure_set_state(snapshot)

    def _figure_set_photo_for_item(self, item, width_px, height_px):
        # Normal preview uses a low-DPI re-render so absolute font sizes remain
        # stable without paying the full export-DPI cost on every refresh.
        # During drag/resize, use the stored thumbnail for responsiveness and
        # re-render once on mouse release.
        img_array = None
        fast_drag = bool(getattr(self, "figure_set_drag", None)) and bool(getattr(self, "_figure_set_drag_fast_preview", True))
        has_recipe = isinstance(getattr(item, "recipe", None), dict) and item.recipe
        if has_recipe and not (fast_drag and item.thumbnail_data):
            img_array = self._render_figure_set_item_preview_image(
                item,
                width_px=width_px,
                height_px=height_px,
            )
        if img_array is None and item.thumbnail_data:
            try:
                raw = base64.b64decode(item.thumbnail_data)
                img_array = mpimg.imread(io.BytesIO(raw), format="png")
            except Exception:
                img_array = None
        if img_array is None:
            return None
        try:
            if Image is not None and ImageTk is not None:
                arr = np.asarray(img_array)
                if arr.dtype != np.uint8:
                    arr = (np.clip(arr, 0.0, 1.0) * 255).astype(np.uint8)
                if arr.ndim == 2:
                    img = Image.fromarray(arr, mode="L").convert("RGBA")
                else:
                    img = Image.fromarray(arr).convert("RGBA")
                img = self._crop_figure_set_pil_image(img, item)
                fit_mode = str(getattr(item, "fit_mode", "contain") or "contain").lower()
                target = (max(1, width_px), max(1, height_px))
                if fit_mode == "stretch":
                    img = img.resize(target, Image.LANCZOS)
                elif fit_mode == "fill" and ImageOps is not None:
                    img = ImageOps.fit(img, target, method=Image.LANCZOS, centering=(0.5, 0.5))
                else:
                    img.thumbnail(target, Image.LANCZOS)
                return ImageTk.PhotoImage(img)
            if item.thumbnail_data:
                return tk.PhotoImage(data=item.thumbnail_data)
            return None
        except Exception:
            return None

    def _crop_figure_set_pil_image(self, pil, item):
        if pil is None:
            return pil
        left, right, top, bottom = self._normalized_figure_set_crop_pct(item)
        if max(left, right, top, bottom) <= 0:
            return pil
        try:
            w, h = pil.size
            x0 = int(round(w * left / 100.0))
            x1 = int(round(w * (1.0 - right / 100.0)))
            y0 = int(round(h * top / 100.0))
            y1 = int(round(h * (1.0 - bottom / 100.0)))
            if x1 <= x0 + 1 or y1 <= y0 + 1:
                return pil
            return pil.crop((x0, y0, x1, y1))
        except Exception:
            return pil

    def add_current_plot_to_figure_set(self):
        if not getattr(self, "_canvas_ready", False) or self.fig is None:
            messagebox.showwarning("Figure Set", "Create a plot first.")
            return
        self._push_figure_set_undo_state()
        label = self._make_figure_set_item_label()
        thumbnail = self._capture_current_plot_thumbnail()
        panel_width_cm, panel_height_cm = self._current_plot_figure_set_dimensions()
        item = FigureSetItem(
            item_id=str(uuid.uuid4()),
            label=label,
            x_cm=1.0 + len(self.figure_set_page.items) * 0.5,
            y_cm=1.0 + len(self.figure_set_page.items) * 0.5,
            width_cm=panel_width_cm,
            height_cm=panel_height_cm,
            recipe=self._capture_plot_recipe(),
            thumbnail_data=thumbnail,
        )
        self.figure_set_page.items.append(item)
        self._set_figure_set_selection([item.item_id])
        self.refresh_figure_set_canvas()
        if hasattr(self, "_show_center_page"):
            self._show_center_page("figure_set")

    def replace_selected_figure_set_item_with_current_plot(self):
        if not getattr(self, "_canvas_ready", False) or self.fig is None:
            messagebox.showwarning("Figure Set", "Create a plot first.")
            return
        selected = self._selected_figure_set_items()
        if len(selected) != 1:
            messagebox.showwarning("Figure Set", "Select exactly one Figure Set item to replace.")
            return
        self._push_figure_set_undo_state()
        item = selected[0]
        item.recipe = self._capture_plot_recipe()
        item.thumbnail_data = self._capture_current_plot_thumbnail()
        if not str(item.label).strip():
            item.label = self._make_figure_set_item_label()
        self.clear_figure_set_render_cache(show_message=False)
        self.refresh_figure_set_canvas()

    def _make_figure_set_item_label(self):
        if getattr(self, "plot_title_text", ""):
            return self.plot_title_text.strip()
        selected = [os.path.basename(p) for p in getattr(self, "loaded_files", {})]
        if len(selected) == 1:
            return os.path.splitext(selected[0])[0]
        if selected:
            return f"Plot {len(self.figure_set_page.items) + 1}"
        return f"Plot {len(self.figure_set_page.items) + 1}"

    def _current_plot_figure_set_dimensions(self, preferred_width_cm=6.0):
        """Choose a compact panel size without changing the source aspect ratio."""
        width_cm = max(0.5, float(preferred_width_cm))
        try:
            width_in, height_in = self.fig.get_size_inches()
            aspect = float(width_in) / max(float(height_in), 1e-9)
            if not np.isfinite(aspect) or aspect <= 0:
                raise ValueError("invalid figure aspect ratio")
            height_cm = width_cm / aspect
        except Exception:
            height_cm = 4.0

        # Keep unusually tall plots inside the initial page while preserving
        # their aspect ratio. Users can still resize the panel afterwards.
        page_height = float(getattr(self.figure_set_page, "height_cm", 12.0) or 12.0)
        max_height_cm = max(2.0, page_height - 2.0)
        if height_cm > max_height_cm:
            factor = max_height_cm / height_cm
            width_cm *= factor
            height_cm = max_height_cm
        return max(0.5, width_cm), max(0.5, height_cm)

    def _capture_current_plot_thumbnail(self):
        try:
            buf = io.BytesIO()
            # This is a lossless fallback for missing/relinked source files.
            # Preserve the exact canvas bounds/aspect instead of tight-cropping
            # and keep enough pixels for high-DPI Figure Set previews.
            dpi = max(240, min(360, int(round(self._figure_set_export_dpi() * 0.5))))
            self.fig.savefig(
                buf,
                format="png",
                dpi=dpi,
                bbox_inches=None,
                pad_inches=0,
                facecolor=self.fig.get_facecolor(),
                edgecolor="none",
                transparent=False,
            )
            return base64.b64encode(buf.getvalue()).decode("ascii")
        except Exception:
            return None

    def _capture_plot_recipe(self):
        try:
            recipe = self._collect_template_data()
        except Exception:
            recipe = {}
        settings = recipe.setdefault("settings", {})
        if isinstance(settings, dict):
            # Keep a full panel-local snapshot even if an older template manager
            # does not yet serialize every runtime option.
            settings["plot_font_display"] = str(getattr(self, "plot_font_display", ACTIVE_PLOT_FONT_DISPLAY))
            settings["plot_layout"] = str(self._get_ui_value("var_plot_layout", getattr(self, "plot_layout_mode", "combined")))
            settings["plot_aspect_ratio"] = str(self._get_ui_value("var_plot_aspect_ratio", getattr(self, "plot_aspect_ratio", "Auto")))
            settings["custom_plot_aspect_ratio"] = str(self._get_ui_value("var_custom_plot_aspect_ratio", getattr(self, "custom_plot_aspect_ratio", "1:1")))
            settings["scale_text_with_ratio"] = bool(self._get_ui_value("var_scale_text_with_ratio", getattr(self, "scale_text_with_ratio", False)))
            settings["plot_size_mode"] = str(self._get_ui_value("var_plot_size_mode", getattr(self, "plot_size_mode", "Auto")))
            settings["plot_size_unit"] = str(self._get_ui_value("var_plot_size_unit", getattr(self, "plot_size_unit", "cm")))
            settings["plot_width_value"] = float(self._get_ui_value("var_plot_width_value", getattr(self, "plot_width_value", 14.0)))
            settings["plot_height_value"] = float(self._get_ui_value("var_plot_height_value", getattr(self, "plot_height_value", 8.0)))
            settings["plot_view_zoom"] = int(self._get_ui_value("var_plot_view_zoom", getattr(self, "plot_view_zoom", 100)))
        loaded_files = getattr(self, "loaded_files", {})
        file_visibility = {
            str(path): bool(getattr(loader, "global_visible", True))
            for path, loader in loaded_files.items()
        }
        # A Figure Set panel is a snapshot of the plot as it looks now.  Keep
        # visibility separate from the general template payload so later
        # project changes (or newly loaded files) cannot leak into the panel.
        recipe["figure_set_recipe_version"] = 2
        recipe["source_label"] = self._make_figure_set_item_label()
        recipe["figure_set_file_visibility"] = file_visibility
        recipe["source_files"] = [path for path, visible in file_visibility.items() if visible]
        recipe["source_file_info"] = self._figure_set_source_file_info(recipe["source_files"])
        recipe["font_policy"] = "fixed-point-size"
        recipe = self._json_safe(recipe) if hasattr(self, "_json_safe") else recipe
        try:
            return json.loads(json.dumps(recipe, ensure_ascii=False, default=str))
        except Exception:
            return recipe

    def _figure_set_source_file_info(self, source_files):
        info = []
        for path in source_files or []:
            entry = {
                "path": str(path),
                "basename": os.path.basename(str(path)),
                "exists": bool(os.path.exists(str(path))),
                "size": None,
                "mtime": None,
            }
            try:
                stat = os.stat(str(path))
                entry["size"] = int(stat.st_size)
                entry["mtime"] = round(float(stat.st_mtime), 3)
            except Exception:
                pass
            info.append(entry)
        return info

    def clear_figure_set(self):
        if not self.figure_set_page.items:
            return
        if messagebox.askyesno("Figure Set", "Clear all items from the Figure Set page?"):
            self._push_figure_set_undo_state()
            self.figure_set_page.items.clear()
            self._set_figure_set_selection([])
            self.clear_figure_set_render_cache(show_message=False)
            self.refresh_figure_set_canvas()

    def _update_figure_set_item_bar(self):
        selected_items = self._selected_figure_set_items()
        item = selected_items[0] if len(selected_items) == 1 else None
        if not hasattr(self, "var_figset_item_label"):
            return
        if len(selected_items) > 1:
            self.var_figset_item_label.set(f"{len(selected_items)} items selected")
            self.var_figset_item_x.set(0.0)
            self.var_figset_item_y.set(0.0)
            self.var_figset_item_w.set(0.0)
            self.var_figset_item_h.set(0.0)
            self.var_figset_item_keep_font.set(all(bool(it.keep_font_fixed) for it in selected_items))
            self.var_figset_item_fit.set(str(getattr(selected_items[0], "fit_mode", "contain")))
            if hasattr(self, "var_figset_crop_left"):
                self.var_figset_crop_left.set(round(float(getattr(selected_items[0], "crop_left_pct", 0.0)), 2))
                self.var_figset_crop_right.set(round(float(getattr(selected_items[0], "crop_right_pct", 0.0)), 2))
                self.var_figset_crop_top.set(round(float(getattr(selected_items[0], "crop_top_pct", 0.0)), 2))
                self.var_figset_crop_bottom.set(round(float(getattr(selected_items[0], "crop_bottom_pct", 0.0)), 2))
            self.var_figset_subplot_visible.set(all(bool(getattr(it, "subplot_label_visible", True)) for it in selected_items))
            self.var_figset_subplot_label.set("multi")
            self.var_figset_subplot_size.set(int(getattr(selected_items[0], "subplot_label_size_pt", 10)))
            self.var_figset_subplot_bold.set(all(bool(getattr(it, "subplot_label_bold", True)) for it in selected_items))
            self.var_figset_subplot_color.set(str(getattr(selected_items[0], "subplot_label_color", "#111827")))
            self.var_figset_subplot_x.set(round(float(getattr(selected_items[0], "subplot_label_x_cm", 0.10)), 3))
            self.var_figset_subplot_y.set(round(float(getattr(selected_items[0], "subplot_label_y_cm", 0.10)), 3))
            return
        if not item:
            self.var_figset_item_label.set("")
            self.var_figset_item_x.set(0.0)
            self.var_figset_item_y.set(0.0)
            self.var_figset_item_w.set(0.0)
            self.var_figset_item_h.set(0.0)
            self.var_figset_item_keep_font.set(True)
            self.var_figset_item_fit.set("contain")
            if hasattr(self, "var_figset_crop_left"):
                self.var_figset_crop_left.set(0.0)
                self.var_figset_crop_right.set(0.0)
                self.var_figset_crop_top.set(0.0)
                self.var_figset_crop_bottom.set(0.0)
            self.var_figset_subplot_visible.set(True)
            self.var_figset_subplot_label.set("")
            self.var_figset_subplot_size.set(10)
            self.var_figset_subplot_bold.set(True)
            self.var_figset_subplot_color.set("#111827")
            self.var_figset_subplot_x.set(0.10)
            self.var_figset_subplot_y.set(0.10)
            return
        self.var_figset_item_label.set(item.label)
        self.var_figset_item_x.set(round(item.x_cm, 3))
        self.var_figset_item_y.set(round(item.y_cm, 3))
        self.var_figset_item_w.set(round(item.width_cm, 3))
        self.var_figset_item_h.set(round(item.height_cm, 3))
        self.var_figset_item_keep_font.set(bool(item.keep_font_fixed))
        self.var_figset_item_fit.set(str(getattr(item, "fit_mode", "contain") or "contain"))
        if hasattr(self, "var_figset_crop_left"):
            self.var_figset_crop_left.set(round(float(getattr(item, "crop_left_pct", 0.0)), 2))
            self.var_figset_crop_right.set(round(float(getattr(item, "crop_right_pct", 0.0)), 2))
            self.var_figset_crop_top.set(round(float(getattr(item, "crop_top_pct", 0.0)), 2))
            self.var_figset_crop_bottom.set(round(float(getattr(item, "crop_bottom_pct", 0.0)), 2))
        self.var_figset_subplot_visible.set(bool(getattr(item, "subplot_label_visible", True)))
        self.var_figset_subplot_label.set(str(getattr(item, "subplot_label", "")))
        self.var_figset_subplot_size.set(int(getattr(item, "subplot_label_size_pt", 10)))
        self.var_figset_subplot_bold.set(bool(getattr(item, "subplot_label_bold", True)))
        self.var_figset_subplot_color.set(str(getattr(item, "subplot_label_color", "#111827")))
        self.var_figset_subplot_x.set(round(float(getattr(item, "subplot_label_x_cm", 0.10)), 3))
        self.var_figset_subplot_y.set(round(float(getattr(item, "subplot_label_y_cm", 0.10)), 3))

    def apply_figure_set_item_properties(self):
        selected_items = self._selected_figure_set_items()
        if len(selected_items) != 1:
            return
        item = selected_items[0]
        if not item:
            return
        try:
            self._push_figure_set_undo_state()
            item.label = str(self.var_figset_item_label.get()).strip() or item.label
            item.x_cm = max(0.0, float(self.var_figset_item_x.get()))
            item.y_cm = max(0.0, float(self.var_figset_item_y.get()))
            item.width_cm = max(0.2, float(self.var_figset_item_w.get()))
            item.height_cm = max(0.2, float(self.var_figset_item_h.get()))
            item.keep_font_fixed = bool(self.var_figset_item_keep_font.get())
            fit_mode = str(self.var_figset_item_fit.get() or "contain").lower()
            item.fit_mode = fit_mode if fit_mode in {"contain", "fill", "stretch"} else "contain"
            item.x_cm = min(item.x_cm, max(0.0, self.figure_set_page.width_cm - item.width_cm))
            item.y_cm = min(item.y_cm, max(0.0, self.figure_set_page.height_cm - item.height_cm))
        except Exception:
            pass
        self.refresh_figure_set_canvas()

    def _figure_set_item_size_presets(self):
        return {
            "Custom": None,
            "Square 4 cm": (4.0, 4.0),
            "Square 5 cm": (5.0, 5.0),
            "Single 8.5 cm": (8.5, 6.0),
            "Double 17 cm": (17.0, 9.5),
            "Tall Zoom 5x14": (5.0, 14.0),
            "Wide Strip 14x5": (14.0, 5.0),
            "3 Panel 5.5x5": (5.5, 5.0),
            "Inset 3x3": (3.0, 3.0),
        }

    def apply_figure_set_item_size_preset(self):
        selected = self._selected_figure_set_items()
        if not selected:
            return
        preset_name = str(self.var_figset_item_size_preset.get() if hasattr(self, "var_figset_item_size_preset") else "Custom")
        size = self._figure_set_item_size_presets().get(preset_name)
        if not size:
            return
        self._push_figure_set_undo_state()
        width_cm, height_cm = size
        for item in selected:
            item.width_cm = max(0.2, min(float(width_cm), self.figure_set_page.width_cm - item.x_cm))
            item.height_cm = max(0.2, min(float(height_cm), self.figure_set_page.height_cm - item.y_cm))
        self.refresh_figure_set_canvas()
        self._update_figure_set_item_bar()

    def swap_figure_set_item_size(self):
        selected = self._selected_figure_set_items()
        if not selected:
            return
        self._push_figure_set_undo_state()
        for item in selected:
            new_w = max(0.2, min(float(item.height_cm), self.figure_set_page.width_cm - item.x_cm))
            new_h = max(0.2, min(float(item.width_cm), self.figure_set_page.height_cm - item.y_cm))
            item.width_cm, item.height_cm = new_w, new_h
        if hasattr(self, "var_figset_item_size_preset"):
            self.var_figset_item_size_preset.set("Custom")
        self.refresh_figure_set_canvas()
        self._update_figure_set_item_bar()

    def _clamp_figure_set_crop_pct(self, value):
        try:
            return max(0.0, min(90.0, float(value)))
        except Exception:
            return 0.0

    def _normalized_figure_set_crop_pct(self, item):
        left = self._clamp_figure_set_crop_pct(getattr(item, "crop_left_pct", 0.0))
        right = self._clamp_figure_set_crop_pct(getattr(item, "crop_right_pct", 0.0))
        top = self._clamp_figure_set_crop_pct(getattr(item, "crop_top_pct", 0.0))
        bottom = self._clamp_figure_set_crop_pct(getattr(item, "crop_bottom_pct", 0.0))
        if left + right >= 95.0:
            scale = 94.0 / max(1e-9, left + right)
            left *= scale
            right *= scale
        if top + bottom >= 95.0:
            scale = 94.0 / max(1e-9, top + bottom)
            top *= scale
            bottom *= scale
        return left, right, top, bottom

    def apply_figure_set_crop_properties(self):
        selected_items = self._selected_figure_set_items()
        if not selected_items or not hasattr(self, "var_figset_crop_left"):
            return
        self._push_figure_set_undo_state()
        left = self._clamp_figure_set_crop_pct(self.var_figset_crop_left.get())
        right = self._clamp_figure_set_crop_pct(self.var_figset_crop_right.get())
        top = self._clamp_figure_set_crop_pct(self.var_figset_crop_top.get())
        bottom = self._clamp_figure_set_crop_pct(self.var_figset_crop_bottom.get())
        for item in selected_items:
            item.crop_left_pct = left
            item.crop_right_pct = right
            item.crop_top_pct = top
            item.crop_bottom_pct = bottom
        self.refresh_figure_set_canvas()

    def reset_figure_set_crop_properties(self):
        selected_items = self._selected_figure_set_items()
        if not selected_items:
            return
        self._push_figure_set_undo_state()
        for item in selected_items:
            item.crop_left_pct = 0.0
            item.crop_right_pct = 0.0
            item.crop_top_pct = 0.0
            item.crop_bottom_pct = 0.0
        if hasattr(self, "var_figset_crop_left"):
            self.var_figset_crop_left.set(0.0)
            self.var_figset_crop_right.set(0.0)
            self.var_figset_crop_top.set(0.0)
            self.var_figset_crop_bottom.set(0.0)
        self.refresh_figure_set_canvas()

    def _figure_set_image_array_to_pil(self, img):
        if Image is None or img is None:
            return None
        try:
            arr = np.asarray(img)
            if arr.dtype != np.uint8:
                arr = (np.clip(arr, 0.0, 1.0) * 255).astype(np.uint8)
            if arr.ndim == 2:
                return Image.fromarray(arr, mode="L").convert("RGBA")
            return Image.fromarray(arr).convert("RGBA")
        except Exception:
            return None

    def _figure_set_source_pil_for_item(self, item):
        img = self._render_figure_set_item_image(item)
        pil = self._figure_set_image_array_to_pil(img)
        if pil is not None:
            return pil
        if not getattr(item, "thumbnail_data", None) or Image is None:
            return None
        try:
            raw = base64.b64decode(item.thumbnail_data)
            return Image.open(io.BytesIO(raw)).convert("RGBA")
        except Exception:
            return None

    def open_figure_set_crop_editor(self):
        selected_items = self._selected_figure_set_items()
        if len(selected_items) != 1:
            messagebox.showwarning("Figure Set Crop", "Select exactly one panel to edit crop visually.")
            return
        if Image is None or ImageTk is None:
            messagebox.showerror("Figure Set Crop", "Pillow is required for the visual Crop Editor.")
            return
        item = selected_items[0]
        pil = self._figure_set_source_pil_for_item(item)
        if pil is None:
            messagebox.showerror("Figure Set Crop", "Could not render a preview image for this panel.")
            return

        top = tk.Toplevel(self.root)
        top.withdraw()
        top.title(f"Crop Editor - {item.label}")
        top.configure(bg=self.ui_bg)
        top.transient(self.root)

        max_w, max_h = 920, 640
        img_w, img_h = pil.size
        scale = min(max_w / max(1, img_w), max_h / max(1, img_h), 1.0)
        disp_w = max(1, int(round(img_w * scale)))
        disp_h = max(1, int(round(img_h * scale)))
        preview = pil.resize((disp_w, disp_h), Image.LANCZOS)
        photo = ImageTk.PhotoImage(preview)

        state = {
            "item": item,
            "img_w": img_w,
            "img_h": img_h,
            "scale": scale,
            "drag": None,
            "start": None,
            "rect": None,
            "photo": photo,
        }
        left, right, crop_top, bottom = self._normalized_figure_set_crop_pct(item)
        state["rect"] = [
            img_w * left / 100.0,
            img_h * crop_top / 100.0,
            img_w * (1.0 - right / 100.0),
            img_h * (1.0 - bottom / 100.0),
        ]

        header = tk.Frame(top, bg=self.ui_surface, highlightbackground=self.ui_border, highlightthickness=1)
        header.pack(fill=tk.X, padx=10, pady=(10, 6))
        tk.Label(
            header,
            text="Drag crop box edges/corners. Apply writes the crop to the selected Figure Set panel.",
            bg=self.ui_surface,
            fg=self.ui_text,
            font=self.ui_font,
        ).pack(side=tk.LEFT, padx=10, pady=7)

        body = tk.Frame(top, bg=self.ui_bg)
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)
        canvas = tk.Canvas(body, width=disp_w, height=disp_h, bg="#111827", highlightthickness=0)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=False)
        canvas.create_image(0, 0, anchor="nw", image=photo, tags=("image",))

        side = tk.Frame(body, bg=self.ui_surface, highlightbackground=self.ui_border, highlightthickness=1)
        side.pack(side=tk.LEFT, fill=tk.Y, padx=(10, 0))
        vars_local = {
            "L": tk.DoubleVar(value=left),
            "R": tk.DoubleVar(value=right),
            "T": tk.DoubleVar(value=crop_top),
            "B": tk.DoubleVar(value=bottom),
        }

        def rect_to_pct():
            x0, y0, x1, y1 = state["rect"]
            l = max(0.0, min(90.0, x0 / img_w * 100.0))
            r = max(0.0, min(90.0, (1.0 - x1 / img_w) * 100.0))
            t = max(0.0, min(90.0, y0 / img_h * 100.0))
            b = max(0.0, min(90.0, (1.0 - y1 / img_h) * 100.0))
            return l, r, t, b

        def pct_to_rect():
            l = self._clamp_figure_set_crop_pct(vars_local["L"].get())
            r = self._clamp_figure_set_crop_pct(vars_local["R"].get())
            t = self._clamp_figure_set_crop_pct(vars_local["T"].get())
            b = self._clamp_figure_set_crop_pct(vars_local["B"].get())
            if l + r >= 95.0:
                r = max(0.0, 94.0 - l)
            if t + b >= 95.0:
                b = max(0.0, 94.0 - t)
            state["rect"] = [
                img_w * l / 100.0,
                img_h * t / 100.0,
                img_w * (1.0 - r / 100.0),
                img_h * (1.0 - b / 100.0),
            ]
            draw_overlay(update_vars=True)

        for label in ["L", "R", "T", "B"]:
            row = tk.Frame(side, bg=self.ui_surface)
            row.pack(fill=tk.X, padx=10, pady=(8 if label == "L" else 3, 3))
            tk.Label(row, text=f"{label} %", bg=self.ui_surface, fg=self.ui_muted, width=4, anchor="w").pack(side=tk.LEFT)
            sp = tk.Spinbox(row, from_=0, to=90, increment=0.5, textvariable=vars_local[label], width=7, command=pct_to_rect)
            sp.pack(side=tk.LEFT)
            sp.bind("<Return>", lambda _e: pct_to_rect())
            sp.bind("<FocusOut>", lambda _e: pct_to_rect())

        info_label = tk.Label(side, text="", bg=self.ui_surface, fg=self.ui_text, font=self.ui_font)
        info_label.pack(fill=tk.X, padx=10, pady=(8, 4))

        def display_rect():
            x0, y0, x1, y1 = state["rect"]
            return [x0 * scale, y0 * scale, x1 * scale, y1 * scale]

        def draw_overlay(update_vars=False):
            canvas.delete("crop_overlay")
            x0, y0, x1, y1 = display_rect()
            canvas.create_rectangle(0, 0, disp_w, y0, fill="#000000", stipple="gray50", outline="", tags=("crop_overlay",))
            canvas.create_rectangle(0, y1, disp_w, disp_h, fill="#000000", stipple="gray50", outline="", tags=("crop_overlay",))
            canvas.create_rectangle(0, y0, x0, y1, fill="#000000", stipple="gray50", outline="", tags=("crop_overlay",))
            canvas.create_rectangle(x1, y0, disp_w, y1, fill="#000000", stipple="gray50", outline="", tags=("crop_overlay",))
            canvas.create_rectangle(x0, y0, x1, y1, outline="#f97316", width=2, tags=("crop_overlay", "crop_rect"))
            canvas.create_line((x0 + x1) / 2, y0, (x0 + x1) / 2, y1, fill="#fdba74", dash=(3, 3), tags=("crop_overlay",))
            canvas.create_line(x0, (y0 + y1) / 2, x1, (y0 + y1) / 2, fill="#fdba74", dash=(3, 3), tags=("crop_overlay",))
            handle_defs = {
                "nw": (x0, y0), "n": ((x0 + x1) / 2, y0), "ne": (x1, y0),
                "w": (x0, (y0 + y1) / 2), "e": (x1, (y0 + y1) / 2),
                "sw": (x0, y1), "s": ((x0 + x1) / 2, y1), "se": (x1, y1),
            }
            for name, (hx, hy) in handle_defs.items():
                canvas.create_rectangle(hx - 5, hy - 5, hx + 5, hy + 5, fill="#f97316", outline="white", tags=("crop_overlay", "crop_handle", f"handle:{name}"))
            l, r, t, b = rect_to_pct()
            if update_vars:
                for key, value in [("L", l), ("R", r), ("T", t), ("B", b)]:
                    vars_local[key].set(round(value, 2))
            info_label.config(text=f"Crop L/R/T/B: {l:.1f} / {r:.1f} / {t:.1f} / {b:.1f}%")

        def handle_at(event):
            current = canvas.find_withtag("current")
            if current:
                tags = canvas.gettags(current[0])
                for tag in tags:
                    if tag.startswith("handle:"):
                        return tag.split(":", 1)[1]
            x, y = event.x, event.y
            x0, y0, x1, y1 = display_rect()
            if x0 <= x <= x1 and y0 <= y <= y1:
                return "move"
            return None

        def on_press(event):
            handle = handle_at(event)
            if not handle:
                return
            state["drag"] = handle
            state["start"] = (event.x, event.y, list(state["rect"]))

        def on_drag(event):
            if not state.get("drag") or not state.get("start"):
                return
            start_x, start_y, start_rect = state["start"]
            dx = (event.x - start_x) / max(scale, 1e-9)
            dy = (event.y - start_y) / max(scale, 1e-9)
            x0, y0, x1, y1 = start_rect
            mode = state["drag"]
            min_w = max(10.0, img_w * 0.03)
            min_h = max(10.0, img_h * 0.03)
            if mode == "move":
                width = x1 - x0
                height = y1 - y0
                nx0 = max(0.0, min(img_w - width, x0 + dx))
                ny0 = max(0.0, min(img_h - height, y0 + dy))
                x0, y0, x1, y1 = nx0, ny0, nx0 + width, ny0 + height
            else:
                if "w" in mode:
                    x0 = max(0.0, min(x1 - min_w, x0 + dx))
                if "e" in mode:
                    x1 = min(float(img_w), max(x0 + min_w, x1 + dx))
                if "n" in mode:
                    y0 = max(0.0, min(y1 - min_h, y0 + dy))
                if "s" in mode:
                    y1 = min(float(img_h), max(y0 + min_h, y1 + dy))
            state["rect"] = [x0, y0, x1, y1]
            draw_overlay(update_vars=True)

        def on_release(_event):
            state["drag"] = None
            state["start"] = None

        canvas.bind("<ButtonPress-1>", on_press)
        canvas.bind("<B1-Motion>", on_drag)
        canvas.bind("<ButtonRelease-1>", on_release)

        def apply_crop():
            l, r, t, b = rect_to_pct()
            self._push_figure_set_undo_state()
            item.crop_left_pct = round(l, 4)
            item.crop_right_pct = round(r, 4)
            item.crop_top_pct = round(t, 4)
            item.crop_bottom_pct = round(b, 4)
            if hasattr(self, "var_figset_crop_left"):
                self.var_figset_crop_left.set(round(l, 2))
                self.var_figset_crop_right.set(round(r, 2))
                self.var_figset_crop_top.set(round(t, 2))
                self.var_figset_crop_bottom.set(round(b, 2))
            self.refresh_figure_set_canvas()

        def reset_crop():
            for key in vars_local:
                vars_local[key].set(0.0)
            pct_to_rect()

        buttons = tk.Frame(side, bg=self.ui_surface)
        buttons.pack(fill=tk.X, padx=10, pady=(12, 10))
        tk.Button(buttons, text="Apply", command=apply_crop, bg=self.ui_accent, fg="white", font=self.ui_font_bold).pack(fill=tk.X, pady=(0, 4))
        tk.Button(buttons, text="Reset", command=reset_crop, bg=self.ui_button_light, font=self.ui_font).pack(fill=tk.X, pady=2)
        tk.Button(buttons, text="Close", command=top.destroy, bg=self.ui_button_light, font=self.ui_font).pack(fill=tk.X, pady=2)

        draw_overlay(update_vars=True)
        top.after_idle(
            lambda: place_window_on_parent_monitor(
                top,
                self.root,
                min(1200, disp_w + 300),
                min(820, disp_h + 120),
            )
        )
        top.update_idletasks()
        try:
            top.geometry(f"+{self.root.winfo_rootx() + 80}+{self.root.winfo_rooty() + 80}")
        except Exception:
            pass

    def apply_figure_set_subplot_properties(self):
        selected_items = self._selected_figure_set_items()
        if not selected_items:
            return
        try:
            self._push_figure_set_undo_state()
            visible = bool(self.var_figset_subplot_visible.get())
            size = max(5, min(48, int(float(self.var_figset_subplot_size.get()))))
            bold = bool(self.var_figset_subplot_bold.get())
            color = str(self.var_figset_subplot_color.get() or "#111827")
            x_cm = max(0.0, float(self.var_figset_subplot_x.get()))
            y_cm = max(0.0, float(self.var_figset_subplot_y.get()))
            label_text = str(self.var_figset_subplot_label.get()).strip()
            for item in selected_items:
                item.subplot_label_visible = visible
                item.subplot_label_size_pt = size
                item.subplot_label_bold = bold
                item.subplot_label_color = color
                item.subplot_label_x_cm = min(max(0.0, item.width_cm), x_cm)
                item.subplot_label_y_cm = min(max(0.0, item.height_cm), y_cm)
                if len(selected_items) == 1:
                    item.subplot_label = label_text
        except Exception:
            pass
        self.refresh_figure_set_canvas()

    def choose_figure_set_subplot_color(self):
        selected_items = self._selected_figure_set_items()
        if not selected_items:
            return
        initial = str(getattr(selected_items[0], "subplot_label_color", "#111827"))
        color = choose_color(self.root, title="Figure Set Subplot Label Color", initial_color=initial, palette_name=getattr(self, "art_palette_name", "Journal Muted"))
        if not color:
            return
        self._push_figure_set_undo_state()
        self.var_figset_subplot_color.set(color)
        for item in selected_items:
            item.subplot_label_color = color
        self.refresh_figure_set_canvas()

    def delete_selected_figure_set_item(self):
        ids = {item.item_id for item in self._selected_figure_set_items()}
        if not ids:
            return
        self._push_figure_set_undo_state()
        self.figure_set_page.items = [item for item in self.figure_set_page.items if item.item_id not in ids]
        self._set_figure_set_selection([])
        self.clear_figure_set_render_cache(show_message=False)
        self.refresh_figure_set_canvas()

    def duplicate_selected_figure_set_item(self):
        selected_items = self._selected_figure_set_items()
        if not selected_items:
            return
        self._push_figure_set_undo_state()
        new_ids = []
        for item in selected_items:
            new_item = self._clone_figure_set_item(item, dx_cm=0.5, dy_cm=0.5, label_suffix=" copy")
            self.figure_set_page.items.append(new_item)
            new_ids.append(new_item.item_id)
        self._set_figure_set_selection(new_ids)
        self.refresh_figure_set_canvas()

    def copy_selected_figure_set_items(self):
        selected_items = self._selected_figure_set_items()
        if not selected_items:
            return
        self.figure_set_clipboard = [self._figure_set_item_to_dict(item) for item in selected_items]
        if hasattr(self, "var_figset_status"):
            self.var_figset_status.set(f"Figure Set clipboard: copied {len(self.figure_set_clipboard)} panel(s)")
            if hasattr(self, "figure_set_status_label"):
                self.figure_set_status_label.configure(fg="#2563eb")

    def paste_figure_set_items(self):
        clipboard = list(getattr(self, "figure_set_clipboard", []) or [])
        if not clipboard:
            return
        self._push_figure_set_undo_state()
        new_ids = []
        for entry in clipboard:
            item = self._figure_set_item_from_dict(entry, new_id=True)
            item.label = f"{item.label} copy"
            item.x_cm = min(max(0.0, item.x_cm + 0.5), max(0.0, self.figure_set_page.width_cm - item.width_cm))
            item.y_cm = min(max(0.0, item.y_cm + 0.5), max(0.0, self.figure_set_page.height_cm - item.height_cm))
            self.figure_set_page.items.append(item)
            new_ids.append(item.item_id)
        self._set_figure_set_selection(new_ids)
        self.refresh_figure_set_canvas()

    def _clone_figure_set_item(self, item, dx_cm=0.0, dy_cm=0.0, label_suffix=""):
        entry = self._figure_set_item_to_dict(item)
        new_item = self._figure_set_item_from_dict(entry, new_id=True)
        new_item.label = f"{new_item.label}{label_suffix}"
        new_item.x_cm = min(max(0.0, new_item.x_cm + float(dx_cm)), max(0.0, self.figure_set_page.width_cm - new_item.width_cm))
        new_item.y_cm = min(max(0.0, new_item.y_cm + float(dy_cm)), max(0.0, self.figure_set_page.height_cm - new_item.height_cm))
        return new_item

    def _figure_set_item_from_dict(self, entry, new_id=False):
        entry = entry or {}
        return FigureSetItem(
            item_id=str(uuid.uuid4() if new_id else (entry.get("item_id") or uuid.uuid4())),
            label=str(entry.get("label", "Plot")),
            x_cm=float(entry.get("x_cm", 1.0)),
            y_cm=float(entry.get("y_cm", 1.0)),
            width_cm=float(entry.get("width_cm", 6.0)),
            height_cm=float(entry.get("height_cm", 4.0)),
            keep_font_fixed=bool(entry.get("keep_font_fixed", True)),
            fit_mode=str(entry.get("fit_mode", "contain")),
            crop_left_pct=float(entry.get("crop_left_pct", 0.0)),
            crop_right_pct=float(entry.get("crop_right_pct", 0.0)),
            crop_top_pct=float(entry.get("crop_top_pct", 0.0)),
            crop_bottom_pct=float(entry.get("crop_bottom_pct", 0.0)),
            subplot_label=str(entry.get("subplot_label", "")),
            subplot_label_visible=bool(entry.get("subplot_label_visible", True)),
            subplot_label_size_pt=int(entry.get("subplot_label_size_pt", 10)),
            subplot_label_bold=bool(entry.get("subplot_label_bold", True)),
            subplot_label_x_cm=float(entry.get("subplot_label_x_cm", 0.10)),
            subplot_label_y_cm=float(entry.get("subplot_label_y_cm", 0.10)),
            subplot_label_color=str(entry.get("subplot_label_color", "#111827")),
            recipe=json.loads(json.dumps(entry.get("recipe", {}))) if isinstance(entry.get("recipe", {}), dict) else {},
            thumbnail_data=entry.get("thumbnail_data"),
        )

    def reorder_figure_set_item(self, mode):
        selected = self._selected_figure_set_items()
        if not selected:
            return
        self._push_figure_set_undo_state()
        items = self.figure_set_page.items
        selected_ids = {item.item_id for item in selected}
        selected_in_order = [item for item in items if item.item_id in selected_ids]
        remaining = [item for item in items if item.item_id not in selected_ids]
        if mode == "front":
            self.figure_set_page.items = remaining + selected_in_order
        elif mode == "back":
            self.figure_set_page.items = selected_in_order + remaining
        else:
            return
        self._set_figure_set_selection(selected_ids)
        self.refresh_figure_set_canvas()

    def match_figure_set_item_size(self, mode):
        selected = self._selected_figure_set_items()
        if len(selected) < 2:
            return
        self._push_figure_set_undo_state()
        ref = selected[0]
        for item in selected[1:]:
            if mode in {"w", "both"}:
                item.width_cm = min(ref.width_cm, max(0.2, self.figure_set_page.width_cm - item.x_cm))
            if mode in {"h", "both"}:
                item.height_cm = min(ref.height_cm, max(0.2, self.figure_set_page.height_cm - item.y_cm))
        self.refresh_figure_set_canvas()

    def auto_label_figure_set_items(self):
        items = self._selected_figure_set_items()
        if not items:
            items = list(self.figure_set_page.items)
        if not items:
            return
        self._push_figure_set_undo_state()
        for idx, item in enumerate(items):
            item.subplot_label = f"({self._figure_set_alpha_label(idx)})"
            item.subplot_label_visible = True
        self.refresh_figure_set_canvas()

    def _figure_set_alpha_label(self, idx):
        idx = int(idx)
        chars = []
        while True:
            chars.append(chr(ord("a") + (idx % 26)))
            idx = idx // 26 - 1
            if idx < 0:
                break
        return "".join(reversed(chars))

    def clear_figure_set_subplot_labels(self):
        items = self._selected_figure_set_items()
        if not items:
            items = list(self.figure_set_page.items)
        if not items:
            return
        self._push_figure_set_undo_state()
        for item in items:
            item.subplot_label = ""
        self.refresh_figure_set_canvas()

    def auto_layout_figure_set_items(self, scope="selected"):
        if scope == "selected":
            items = self._selected_figure_set_items()
            if not items:
                items = list(self.figure_set_page.items)
        else:
            items = list(self.figure_set_page.items)
        if not items:
            return
        self._push_figure_set_undo_state()
        try:
            rows = max(1, int(float(self.var_figset_layout_rows.get())))
            cols = max(1, int(float(self.var_figset_layout_cols.get())))
            gap = max(0.0, float(self.var_figset_layout_gap.get()))
            margin = max(0.0, float(self.var_figset_layout_margin.get()))
        except Exception:
            rows, cols, gap, margin = 1, max(1, len(items)), 0.3, 0.5

        needed_rows = int(math.ceil(len(items) / max(1, cols)))
        rows = max(rows, needed_rows)
        usable_w = max(0.2, self.figure_set_page.width_cm - 2 * margin - gap * max(0, cols - 1))
        usable_h = max(0.2, self.figure_set_page.height_cm - 2 * margin - gap * max(0, rows - 1))
        cell_w = usable_w / cols
        cell_h = usable_h / rows
        for idx, item in enumerate(items):
            row = idx // cols
            col = idx % cols
            item.x_cm = margin + col * (cell_w + gap)
            item.y_cm = margin + row * (cell_h + gap)
            item.width_cm = max(0.2, cell_w)
            item.height_cm = max(0.2, cell_h)
        self._set_figure_set_selection([item.item_id for item in items])
        self.refresh_figure_set_canvas()

    def _figure_set_page_to_dict(self):
        return {
            "preset_name": getattr(self.figure_set_page, "preset_name", "Custom"),
            "width_cm": self.figure_set_page.width_cm,
            "height_cm": self.figure_set_page.height_cm,
            "unit": self.figure_set_page.unit,
            "zoom_percent": self.figure_set_page.zoom_percent,
            "export_dpi": self.figure_set_page.export_dpi,
            "transparent_background": self.figure_set_page.transparent_background,
            "panel_transparent_background": bool(getattr(self.figure_set_page, "panel_transparent_background", False)),
            "panel_render_scale": float(getattr(self.figure_set_page, "panel_render_scale", 1.0)),
            "export_tight_bbox": bool(getattr(self.figure_set_page, "export_tight_bbox", False)),
            "export_padding_cm": float(getattr(self.figure_set_page, "export_padding_cm", 0.0)),
            "export_metadata_enabled": bool(getattr(self.figure_set_page, "export_metadata_enabled", True)),
            "export_set_copy_enabled": bool(getattr(self.figure_set_page, "export_set_copy_enabled", True)),
            "show_item_borders": self.figure_set_page.show_item_borders,
            "show_grid": self.figure_set_page.show_grid,
            "grid_step_cm": getattr(self.figure_set_page, "grid_step_cm", 0.5),
            "show_guides": self.figure_set_page.show_guides,
            "show_margin_guides": getattr(self.figure_set_page, "show_margin_guides", True),
            "margin_guide_cm": getattr(self.figure_set_page, "margin_guide_cm", 0.5),
            "manual_guides_x_cm": list(getattr(self.figure_set_page, "manual_guides_x_cm", []) or []),
            "manual_guides_y_cm": list(getattr(self.figure_set_page, "manual_guides_y_cm", []) or []),
            "snap_enabled": self.figure_set_page.snap_enabled,
            "master_typography_enabled": bool(getattr(self.figure_set_page, "master_typography_enabled", False)),
            "master_font_display": str(getattr(self.figure_set_page, "master_font_display", "Current Plot Font")),
            "master_title_size": int(getattr(self.figure_set_page, "master_title_size", 12)),
            "master_axis_size": int(getattr(self.figure_set_page, "master_axis_size", 10)),
            "master_tick_size": int(getattr(self.figure_set_page, "master_tick_size", 10)),
            "master_legend_size": int(getattr(self.figure_set_page, "master_legend_size", 10)),
            "master_residual_size": int(getattr(self.figure_set_page, "master_residual_size", 10)),
            "master_memo_size": int(getattr(self.figure_set_page, "master_memo_size", 10)),
            "master_reference_size": int(getattr(self.figure_set_page, "master_reference_size", 8)),
        }

    def _apply_figure_set_page_dict(self, page):
        page = page or {}
        self.figure_set_page.preset_name = str(page.get("preset_name", "Custom"))
        self.figure_set_page.width_cm = float(page.get("width_cm", 17.8))
        self.figure_set_page.height_cm = float(page.get("height_cm", 12.0))
        self.figure_set_page.unit = str(page.get("unit", "cm"))
        try:
            self.figure_set_page.zoom_percent = max(10, min(800, int(float(page.get("zoom_percent", 100)))))
        except Exception:
            self.figure_set_page.zoom_percent = 100
        self.figure_set_page.export_dpi = int(page.get("export_dpi", 600))
        self.figure_set_page.transparent_background = bool(page.get("transparent_background", False))
        self.figure_set_page.panel_transparent_background = bool(page.get("panel_transparent_background", True))
        try:
            self.figure_set_page.panel_render_scale = max(1.0, min(3.0, float(page.get("panel_render_scale", 1.0))))
        except Exception:
            self.figure_set_page.panel_render_scale = 1.0
        self.figure_set_page.export_tight_bbox = bool(page.get("export_tight_bbox", False))
        try:
            self.figure_set_page.export_padding_cm = max(0.0, min(2.0, float(page.get("export_padding_cm", 0.0))))
        except Exception:
            self.figure_set_page.export_padding_cm = 0.0
        self.figure_set_page.export_metadata_enabled = bool(page.get("export_metadata_enabled", True))
        self.figure_set_page.export_set_copy_enabled = bool(page.get("export_set_copy_enabled", True))
        self.figure_set_page.show_item_borders = bool(page.get("show_item_borders", False))
        self.figure_set_page.show_grid = bool(page.get("show_grid", True))
        self.figure_set_page.grid_step_cm = float(page.get("grid_step_cm", 0.5))
        self.figure_set_page.show_guides = bool(page.get("show_guides", True))
        self.figure_set_page.show_margin_guides = bool(page.get("show_margin_guides", True))
        self.figure_set_page.margin_guide_cm = float(page.get("margin_guide_cm", 0.5))
        self.figure_set_page.manual_guides_x_cm = self._coerce_figure_set_guide_list(page.get("manual_guides_x_cm", []), self.figure_set_page.width_cm)
        self.figure_set_page.manual_guides_y_cm = self._coerce_figure_set_guide_list(page.get("manual_guides_y_cm", []), self.figure_set_page.height_cm)
        self.figure_set_page.snap_enabled = bool(page.get("snap_enabled", True))
        self.figure_set_page.master_typography_enabled = bool(page.get("master_typography_enabled", False))
        self.figure_set_page.master_font_display = str(page.get("master_font_display", "Current Plot Font"))
        for attr, fallback, min_size, max_size in [
            ("master_title_size", 12, 4, 72),
            ("master_axis_size", 10, 4, 72),
            ("master_tick_size", 10, 4, 72),
            ("master_legend_size", 10, 6, 30),
            ("master_residual_size", 10, 6, 30),
            ("master_memo_size", 10, 4, 72),
            ("master_reference_size", 8, 4, 30),
        ]:
            try:
                value = int(float(page.get(attr, fallback)))
                setattr(self.figure_set_page, attr, max(min_size, min(max_size, value)))
            except Exception:
                setattr(self.figure_set_page, attr, fallback)
        self._clamp_figure_set_items_to_page()

    def _clamp_figure_set_items_to_page(self):
        for item in list(getattr(self.figure_set_page, "items", [])):
            item.width_cm = max(0.2, min(float(item.width_cm), max(0.2, self.figure_set_page.width_cm)))
            item.height_cm = max(0.2, min(float(item.height_cm), max(0.2, self.figure_set_page.height_cm)))
            item.x_cm = max(0.0, min(float(item.x_cm), max(0.0, self.figure_set_page.width_cm - item.width_cm)))
            item.y_cm = max(0.0, min(float(item.y_cm), max(0.0, self.figure_set_page.height_cm - item.height_cm)))

    def _figure_set_to_dict(self):
        return {
            "version": 1,
            "page": self._figure_set_page_to_dict(),
            "items": [self._figure_set_item_to_dict(item) for item in self.figure_set_page.items],
        }

    def _figure_set_item_to_dict(self, item):
        return {
            "item_id": item.item_id,
            "label": item.label,
            "x_cm": item.x_cm,
            "y_cm": item.y_cm,
            "width_cm": item.width_cm,
            "height_cm": item.height_cm,
            "keep_font_fixed": item.keep_font_fixed,
            "fit_mode": getattr(item, "fit_mode", "contain"),
            "crop_left_pct": getattr(item, "crop_left_pct", 0.0),
            "crop_right_pct": getattr(item, "crop_right_pct", 0.0),
            "crop_top_pct": getattr(item, "crop_top_pct", 0.0),
            "crop_bottom_pct": getattr(item, "crop_bottom_pct", 0.0),
            "subplot_label": item.subplot_label,
            "subplot_label_visible": item.subplot_label_visible,
            "subplot_label_size_pt": item.subplot_label_size_pt,
            "subplot_label_bold": item.subplot_label_bold,
            "subplot_label_x_cm": item.subplot_label_x_cm,
            "subplot_label_y_cm": item.subplot_label_y_cm,
            "subplot_label_color": item.subplot_label_color,
            "recipe": json.loads(json.dumps(item.recipe)) if isinstance(item.recipe, dict) else {},
            "thumbnail_data": item.thumbnail_data,
        }

    def preflight_figure_set(self):
        result = self._collect_figure_set_preflight()
        messagebox.showinfo("Figure Set Preflight", self._format_figure_set_preflight(result))

    def deep_preflight_figure_set(self):
        result = self._collect_figure_set_preflight(deep_render=True)
        messagebox.showinfo("Figure Set Render QA", self._format_figure_set_preflight(result))

    def _collect_figure_set_preflight(self, items=None, deep_render=False):
        self._sync_figure_set_page_from_ui()
        items = list(items) if items is not None else list(self.figure_set_page.items)
        errors = []
        warnings = []
        info = []
        render_info = []
        page_w = max(1.0, float(self.figure_set_page.width_cm))
        page_h = max(1.0, float(self.figure_set_page.height_cm))
        dpi = self._figure_set_render_dpi()
        export_dpi = self._figure_set_export_dpi()

        if not items:
            errors.append("No panels in Figure Set.")
        if export_dpi < 300:
            warnings.append(f"Export DPI is {export_dpi}; journal raster export usually needs 300 dpi or higher.")
        if page_w < 2.0 or page_h < 2.0:
            warnings.append(f"Page size is very small: {page_w:g} x {page_h:g} cm.")

        labels = {}
        panel_boxes = []
        loaded_files = set(getattr(self, "loaded_files", {}).keys())
        for idx, item in enumerate(items, 1):
            label = str(getattr(item, "label", "") or f"Panel {idx}").strip()
            labels[label] = labels.get(label, 0) + 1

            if item.width_cm <= 0 or item.height_cm <= 0:
                errors.append(f"Panel {idx} '{label}' has invalid size.")
            elif item.width_cm < 1.0 or item.height_cm < 1.0:
                warnings.append(f"Panel {idx} '{label}' is smaller than 1 cm in at least one direction.")

            if item.x_cm < -1e-9 or item.y_cm < -1e-9 or item.x_cm + item.width_cm > page_w + 1e-9 or item.y_cm + item.height_cm > page_h + 1e-9:
                errors.append(f"Panel {idx} '{label}' is outside the page bounds.")
            else:
                panel_boxes.append((idx, label, float(item.x_cm), float(item.y_cm), float(item.width_cm), float(item.height_cm)))

            crop_l = float(getattr(item, "crop_left_pct", 0.0) or 0.0)
            crop_r = float(getattr(item, "crop_right_pct", 0.0) or 0.0)
            crop_t = float(getattr(item, "crop_top_pct", 0.0) or 0.0)
            crop_b = float(getattr(item, "crop_bottom_pct", 0.0) or 0.0)
            crop_x = max(0.0, crop_l) + max(0.0, crop_r)
            crop_y = max(0.0, crop_t) + max(0.0, crop_b)
            if crop_x >= 95.0 or crop_y >= 95.0:
                errors.append(f"Panel {idx} '{label}' crop removes almost the entire panel.")
            elif crop_x >= 70.0 or crop_y >= 70.0:
                warnings.append(f"Panel {idx} '{label}' crop is aggressive: L/R {crop_x:g}% and T/B {crop_y:g}%.")

            recipe = item.recipe if isinstance(getattr(item, "recipe", None), dict) else {}
            thumbnail_ok = bool(getattr(item, "thumbnail_data", None))
            if not recipe and not thumbnail_ok:
                errors.append(f"Panel {idx} '{label}' has neither render recipe nor thumbnail.")
                continue
            if not recipe and thumbnail_ok:
                warnings.append(f"Panel {idx} '{label}' will export from thumbnail only.")
                continue

            source_files = recipe.get("source_files", []) or []
            missing = [path for path in source_files if path not in loaded_files]
            if missing:
                missing_names = [os.path.basename(str(path)) for path in missing[:3]]
                suffix = f" ({', '.join(missing_names)}" + ("..." if len(missing) > 3 else "") + ")"
                if thumbnail_ok:
                    warnings.append(f"Panel {idx} '{label}' is missing {len(missing)} source file(s){suffix}; thumbnail fallback will be used. Use Relink Sources for editable re-render.")
                else:
                    errors.append(f"Panel {idx} '{label}' is missing {len(missing)} source file(s){suffix} and has no thumbnail fallback.")

            if getattr(item, "keep_font_fixed", True) is False:
                warnings.append(f"Panel {idx} '{label}' has Fixed Font disabled.")

            px_w = int(round(self._cm_to_inches(max(0.2, item.width_cm)) * dpi))
            px_h = int(round(self._cm_to_inches(max(0.2, item.height_cm)) * dpi))
            if px_w < 600 or px_h < 400:
                warnings.append(f"Panel {idx} '{label}' raster size is modest: {px_w} x {px_h} px at {dpi} dpi.")
            if deep_render:
                render_result = self._preflight_render_figure_set_item(item, idx, label)
                if render_result.get("error"):
                    errors.append(render_result["error"])
                warnings.extend(render_result.get("warnings", []))
                if render_result.get("info"):
                    render_info.append(render_result["info"])

        duplicate_labels = [label for label, count in labels.items() if label and count > 1]
        if duplicate_labels:
            warnings.append("Duplicate panel labels: " + ", ".join(duplicate_labels[:6]))

        for a_pos, a in enumerate(panel_boxes):
            a_idx, a_label, ax, ay, aw, ah = a
            ax2, ay2 = ax + aw, ay + ah
            for b in panel_boxes[a_pos + 1:]:
                b_idx, b_label, bx, by, bw, bh = b
                bx2, by2 = bx + bw, by + bh
                overlap_w = min(ax2, bx2) - max(ax, bx)
                overlap_h = min(ay2, by2) - max(ay, by)
                if overlap_w > 0.01 and overlap_h > 0.01:
                    overlap_area = overlap_w * overlap_h
                    ref_area = max(0.01, min(aw * ah, bw * bh))
                    overlap_pct = 100.0 * overlap_area / ref_area
                    warnings.append(
                        f"Panels {a_idx} '{a_label}' and {b_idx} '{b_label}' overlap by {overlap_w:g} x {overlap_h:g} cm ({overlap_pct:.1f}% of the smaller panel)."
                    )

        info.append(f"Panels: {len(items)}")
        info.append(f"Page: {page_w:g} x {page_h:g} cm")
        info.append(f"Export DPI: {export_dpi}")
        info.append(f"Panel render DPI: {dpi}")
        info.append(f"Transparent background: {'ON' if getattr(self.figure_set_page, 'transparent_background', False) else 'OFF'}")
        info.append(f"Transparent panels: {'ON' if getattr(self.figure_set_page, 'panel_transparent_background', False) else 'OFF'}")
        info.append(f"Metadata manifest: {'ON' if getattr(self.figure_set_page, 'export_metadata_enabled', True) else 'OFF'}")
        info.append(f"Editable set copy: {'ON' if getattr(self.figure_set_page, 'export_set_copy_enabled', True) else 'OFF'}")
        if bool(getattr(self.figure_set_page, "export_tight_bbox", False)):
            info.append(f"Tight bounding box: ON, pad {float(getattr(self.figure_set_page, 'export_padding_cm', 0.0)):g} cm")
        if bool(getattr(self.figure_set_page, "master_typography_enabled", False)):
            info.append(
                "Master typography: "
                f"{getattr(self.figure_set_page, 'master_font_display', 'Current Plot Font')}, "
                f"title {getattr(self.figure_set_page, 'master_title_size', 12)} pt / "
                f"axis {getattr(self.figure_set_page, 'master_axis_size', 10)} pt / "
                f"tick {getattr(self.figure_set_page, 'master_tick_size', 10)} pt / "
                f"legend {getattr(self.figure_set_page, 'master_legend_size', 10)} pt"
            )
        if deep_render:
            info.append("Deep render QA: ON")
            info.extend(render_info)
        return {"errors": errors, "warnings": warnings, "info": info}

    def _preflight_render_figure_set_item(self, item, idx, label):
        result = {"warnings": []}
        try:
            before_cache = len(getattr(self, "figure_set_render_cache", {}) or {})
            img = self._render_figure_set_item_image(item)
            after_cache = len(getattr(self, "figure_set_render_cache", {}) or {})
            if img is None:
                result["error"] = f"Panel {idx} '{label}' failed to render any image."
                return result
            arr = np.asarray(img)
            if arr.ndim < 2:
                result["error"] = f"Panel {idx} '{label}' rendered invalid image dimensions."
                return result
            h, w = int(arr.shape[0]), int(arr.shape[1])
            expected_w = int(round(self._cm_to_inches(max(0.2, item.width_cm)) * self._figure_set_render_dpi()))
            expected_h = int(round(self._cm_to_inches(max(0.2, item.height_cm)) * self._figure_set_render_dpi()))
            if w < max(1, expected_w * 0.5) or h < max(1, expected_h * 0.5):
                result["warnings"].append(
                    f"Panel {idx} '{label}' rendered smaller than expected: {w} x {h} px; expected about {expected_w} x {expected_h} px."
                )
            if arr.shape[-1] == 4 and not (getattr(self.figure_set_page, "transparent_background", False) or self._figure_set_panel_transparent()):
                try:
                    alpha_min = float(np.nanmin(arr[..., 3]))
                    if alpha_min < 0.99:
                        result["warnings"].append(f"Panel {idx} '{label}' contains transparent pixels while transparent export is OFF.")
                except Exception:
                    pass
            source = "rendered"
            if before_cache == after_cache and not (item.recipe if isinstance(getattr(item, "recipe", None), dict) else {}):
                source = "thumbnail"
            result["info"] = f"Panel {idx} '{label}': {w} x {h} px, {source}"
            return result
        except Exception as exc:
            return {"error": f"Panel {idx} '{label}' render QA raised an exception: {exc}", "warnings": []}

    def _format_figure_set_preflight(self, result):
        errors = result.get("errors", [])
        warnings = result.get("warnings", [])
        info = result.get("info", [])
        status = "PASS" if not errors and not warnings else "CHECK REQUIRED"
        if errors:
            status = "FAILED"
        lines = [f"Status: {status}", ""]
        if info:
            lines.append("Info")
            lines.extend(f"- {line}" for line in info)
            lines.append("")
        if errors:
            lines.append("Errors")
            lines.extend(f"- {line}" for line in errors)
            lines.append("")
        if warnings:
            lines.append("Warnings")
            lines.extend(f"- {line}" for line in warnings)
            lines.append("")
        if not errors and not warnings:
            lines.append("No export-blocking or quality-risk issues found.")
        return "\n".join(lines).strip()

    def _confirm_figure_set_preflight_before_export(self, items=None):
        result = self._collect_figure_set_preflight(items=items)
        errors = result.get("errors", [])
        warnings = result.get("warnings", [])
        if errors:
            messagebox.showerror("Figure Set Preflight Failed", self._format_figure_set_preflight(result))
            return False
        if warnings:
            return messagebox.askyesno(
                "Figure Set Preflight Warnings",
                self._format_figure_set_preflight(result) + "\n\nContinue export anyway?",
            )
        return True

    def relink_figure_set_sources(self):
        items = self._selected_figure_set_items() or list(getattr(self.figure_set_page, "items", []))
        if not items:
            messagebox.showwarning("Figure Set", "No Figure Set panels are available to relink.")
            return
        source_files = []
        for item in items:
            recipe = item.recipe if isinstance(getattr(item, "recipe", None), dict) else {}
            source_files.extend(recipe.get("source_files", []) or [])
        missing = [path for path in source_files if path not in getattr(self, "loaded_files", {})]
        if not missing:
            messagebox.showinfo("Figure Set", "All source files for the selected Figure Set panels are already loaded.")
            return

        paths = filedialog.askopenfilenames(
            title="Relink Figure Set Source Profiles",
            filetypes=PROFILE_FILE_TYPES,
        )
        if not paths:
            return
        chosen_by_base = {}
        for path in paths:
            chosen_by_base[os.path.basename(path).lower()] = path

        self._push_figure_set_undo_state()
        changed = 0
        loaded = 0
        for item in items:
            recipe = item.recipe if isinstance(getattr(item, "recipe", None), dict) else {}
            old_sources = list(recipe.get("source_files", []) or [])
            if not old_sources:
                continue
            replacements = {}
            new_sources = []
            for old in old_sources:
                new = chosen_by_base.get(os.path.basename(str(old)).lower())
                if new:
                    newly_loaded = self._ensure_figure_set_source_loaded(new)
                    if new not in getattr(self, "loaded_files", {}):
                        new_sources.append(old)
                        continue
                    replacements[str(old)] = new
                    new_sources.append(new)
                    if newly_loaded:
                        loaded += 1
                else:
                    new_sources.append(old)
            if not replacements:
                continue
            recipe["source_files"] = new_sources
            recipe["source_file_info"] = self._figure_set_source_file_info(new_sources)
            if isinstance(recipe.get("file_order"), list):
                recipe["file_order"] = [replacements.get(str(path), path) for path in recipe["file_order"]]
            files_block = recipe.get("files")
            if isinstance(files_block, dict):
                for old, new in replacements.items():
                    if old in files_block and new not in files_block:
                        files_block[new] = files_block[old]
            item.recipe = recipe
            changed += 1
        if changed:
            if hasattr(self, "_sync_loaded_files_to_project_order"):
                self._sync_loaded_files_to_project_order()
            if hasattr(self, "rebuild_layer_controls"):
                self.rebuild_layer_controls()
            self.clear_figure_set_render_cache(show_message=False)
            self.refresh_figure_set_canvas()
            messagebox.showinfo("Figure Set", f"Relinked sources for {changed} panel(s). Loaded {loaded} source file reference(s).")
        else:
            messagebox.showwarning("Figure Set", "No selected files matched the missing Figure Set source filenames.")

    def _ensure_figure_set_source_loaded(self, path):
        if path in getattr(self, "loaded_files", {}):
            return False
        try:
            loader = DataLoader(path)
            loader.load()
            if hasattr(self, "_apply_phase_name_overrides_to_loader"):
                self._apply_phase_name_overrides_to_loader(loader)
            if hasattr(self, "_apply_phase_color_overrides_to_loader"):
                self._apply_phase_color_overrides_to_loader(loader)
            self.loaded_files[path] = loader
            if hasattr(self, "file_tree") and not self.file_tree.exists(path):
                self.file_tree.insert(
                    "", "end", iid=path,
                    text=f"  {self._get_sample_display_name(loader) if hasattr(self, '_get_sample_display_name') else os.path.basename(path)}",
                    image=self._file_visibility_image(loader.global_visible),
                )
            return True
        except Exception as exc:
            messagebox.showwarning("Figure Set", f"Failed to load relinked source:\n{path}\n\n{exc}")
            return False

    def export_figure_set(self):
        if not self.figure_set_page.items:
            messagebox.showwarning("Figure Set", "Add at least one plot item before exporting.")
            return
        if not self._confirm_figure_set_preflight_before_export():
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[
                ("PDF vector page", "*.pdf"),
                ("SVG vector page", "*.svg"),
                ("PNG 600 dpi", "*.png"),
                ("TIFF 600 dpi", "*.tif;*.tiff"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return
        try:
            self._reset_figure_set_sidecar_errors()
            self._export_figure_set_to_path(path)
            companions = self._figure_set_export_companion_paths(path)
            manifest = self._write_figure_set_export_manifest(
                path,
                scope="figure_set",
                items=list(self.figure_set_page.items),
                manifest_path=companions.get("manifest"),
                set_copy_path=companions.get("set_copy"),
            )
            set_copy = self._write_figure_set_export_copy(path, set_path=companions.get("set_copy"))
            suffix = self._format_figure_set_export_suffix(manifest, set_copy)
            messagebox.showinfo("Figure Set", f"Figure Set exported:\n{path}{suffix}")
        except Exception as e:
            messagebox.showerror("Figure Set", f"Failed to export Figure Set.\n{e}")

    def export_selected_figure_set_panels(self):
        items = self._selected_figure_set_items()
        if not items:
            messagebox.showwarning("Figure Set", "Select at least one panel to export.")
            return
        if not self._confirm_figure_set_preflight_before_export(items=items):
            return
        self._export_figure_set_panels(items)

    def export_all_figure_set_panels(self):
        items = list(self.figure_set_page.items)
        if not items:
            messagebox.showwarning("Figure Set", "Add at least one panel to export.")
            return
        if not self._confirm_figure_set_preflight_before_export(items=items):
            return
        self._export_figure_set_panels(items)

    def _export_figure_set_panels(self, items):
        self._sync_figure_set_page_from_ui()
        if len(items) == 1:
            default_name = self._safe_figure_set_filename(items[0].label) or "panel"
            path = filedialog.asksaveasfilename(
                defaultextension=".png",
                initialfile=f"{default_name}.png",
                filetypes=[
                    ("PNG", "*.png"),
                    ("TIFF", "*.tif;*.tiff"),
                    ("PDF", "*.pdf"),
                    ("SVG", "*.svg"),
                    ("All files", "*.*"),
                ],
            )
            if not path:
                return
            try:
                self._reset_figure_set_sidecar_errors()
                self._export_single_figure_set_panel(items[0], path)
                companions = self._figure_set_export_companion_paths(path)
                manifest = self._write_figure_set_export_manifest(
                    path,
                    scope="single_panel",
                    items=[items[0]],
                    manifest_path=companions.get("manifest"),
                    set_copy_path=companions.get("set_copy"),
                )
                set_copy = self._write_figure_set_export_copy(path, set_path=companions.get("set_copy"))
                suffix = self._format_figure_set_export_suffix(manifest, set_copy)
                messagebox.showinfo("Figure Set", f"Panel exported:\n{path}{suffix}")
            except Exception as e:
                messagebox.showerror("Figure Set", f"Failed to export panel.\n{e}")
            return

        directory = filedialog.askdirectory(title="Export Figure Set Panels")
        if not directory:
            return
        try:
            self._reset_figure_set_sidecar_errors()
            used = set()
            for idx, item in enumerate(items, 1):
                base = self._safe_figure_set_filename(item.label) or f"panel_{idx:02d}"
                name = f"{idx:02d}_{base}"
                while name.lower() in used:
                    name = f"{idx:02d}_{base}_{len(used) + 1}"
                used.add(name.lower())
                path = os.path.join(directory, f"{name}.png")
                self._export_single_figure_set_panel(item, path)
            companions = self._figure_set_export_companion_paths(directory)
            manifest = self._write_figure_set_export_manifest(
                directory,
                scope="panel_batch",
                items=items,
                manifest_path=companions.get("manifest"),
                set_copy_path=companions.get("set_copy"),
            )
            set_copy = self._write_figure_set_export_copy(directory, set_path=companions.get("set_copy"))
            suffix = self._format_figure_set_export_suffix(manifest, set_copy)
            messagebox.showinfo("Figure Set", f"{len(items)} panels exported:\n{directory}{suffix}")
        except Exception as e:
            messagebox.showerror("Figure Set", f"Failed to export panels.\n{e}")

    def _reset_figure_set_sidecar_errors(self):
        self.figure_set_export_sidecar_errors = []

    def _append_figure_set_sidecar_error(self, message):
        if not hasattr(self, "figure_set_export_sidecar_errors"):
            self.figure_set_export_sidecar_errors = []
        self.figure_set_export_sidecar_errors.append(str(message))

    def _format_figure_set_export_suffix(self, manifest, set_copy):
        suffix_parts = []
        if manifest:
            suffix_parts.append(f"Manifest:\n{manifest}")
        if set_copy:
            suffix_parts.append(f"Editable set copy:\n{set_copy}")
        errors = list(getattr(self, "figure_set_export_sidecar_errors", []) or [])
        if errors:
            suffix_parts.append("Sidecar warnings:\n" + "\n".join(f"- {err}" for err in errors))
        return "\n\n" + "\n\n".join(suffix_parts) if suffix_parts else ""

    def _figure_set_export_companion_paths(self, output_path):
        return {
            "manifest": self._figure_set_manifest_path(output_path)
            if bool(getattr(self.figure_set_page, "export_metadata_enabled", True))
            else None,
            "set_copy": self._figure_set_export_copy_path(output_path)
            if bool(getattr(self.figure_set_page, "export_set_copy_enabled", True))
            else None,
        }

    def _write_figure_set_export_copy(self, output_path, set_path=None):
        if not bool(getattr(self.figure_set_page, "export_set_copy_enabled", True)):
            return None
        try:
            set_path = set_path or self._figure_set_export_copy_path(output_path)
            with open(set_path, "w", encoding="utf-8") as f:
                json.dump(self._figure_set_to_dict(), f, ensure_ascii=False, indent=2)
            return set_path
        except Exception as exc:
            self._append_figure_set_sidecar_error(f"Editable set copy was not written: {exc}")
            return None

    def _figure_set_export_copy_path(self, output_path):
        output_path = str(output_path)
        if os.path.isdir(output_path):
            return self._figure_set_unique_companion_path(os.path.join(output_path, "figure_set_export_copy.labxfigset.json"))
        root, _ext = os.path.splitext(output_path)
        return self._figure_set_unique_companion_path(f"{root}.labxfigset.json")

    def _write_figure_set_export_manifest(self, output_path, scope="figure_set", items=None, manifest_path=None, set_copy_path=None):
        if not bool(getattr(self.figure_set_page, "export_metadata_enabled", True)):
            return None
        try:
            items = list(items) if items is not None else list(getattr(self.figure_set_page, "items", []) or [])
            manifest_path = manifest_path or self._figure_set_manifest_path(output_path)
            manifest = {
                "type": f"{APP_NAME} - Figure Set Export Manifest",
                "version": 1,
                "scope": str(scope),
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "output": os.path.abspath(str(output_path)),
                "companions": {
                    "manifest": os.path.abspath(manifest_path),
                    "editable_set_copy": os.path.abspath(set_copy_path)
                    if set_copy_path and bool(getattr(self.figure_set_page, "export_set_copy_enabled", True))
                    else None,
                    "metadata_enabled": bool(getattr(self.figure_set_page, "export_metadata_enabled", True)),
                    "editable_set_copy_enabled": bool(getattr(self.figure_set_page, "export_set_copy_enabled", True)),
                },
                "page": self._figure_set_page_to_dict(),
                "preflight": self._collect_figure_set_preflight(items=items),
                "items": [self._figure_set_item_manifest_dict(item, idx) for idx, item in enumerate(items, 1)],
            }
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest, f, ensure_ascii=False, indent=2)
            return manifest_path
        except Exception as exc:
            self._append_figure_set_sidecar_error(f"Manifest was not written: {exc}")
            return None

    def _figure_set_manifest_path(self, output_path):
        output_path = str(output_path)
        if os.path.isdir(output_path):
            return self._figure_set_unique_companion_path(os.path.join(output_path, "figure_set_export_manifest.json"))
        root, _ext = os.path.splitext(output_path)
        return self._figure_set_unique_companion_path(f"{root}.manifest.json")

    def _figure_set_unique_companion_path(self, path):
        path = str(path)
        if not os.path.exists(path):
            return path
        root, ext = os.path.splitext(path)
        for idx in range(2, 1000):
            candidate = f"{root}_{idx}{ext}"
            if not os.path.exists(candidate):
                return candidate
        return f"{root}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"

    def _figure_set_item_manifest_dict(self, item, idx):
        entry = self._figure_set_item_to_dict(item)
        entry.pop("thumbnail_data", None)
        recipe = entry.get("recipe") if isinstance(entry.get("recipe"), dict) else {}
        source_files = recipe.get("source_files", []) if isinstance(recipe, dict) else []
        entry["index"] = int(idx)
        entry["source_files"] = [str(path) for path in source_files or []]
        entry["has_thumbnail_fallback"] = bool(getattr(item, "thumbnail_data", None))
        entry["has_render_recipe"] = bool(recipe)
        if isinstance(recipe, dict):
            entry["recipe_summary"] = {
                "source_label": recipe.get("source_label", ""),
                "figure_set_recipe_version": recipe.get("figure_set_recipe_version", None),
                "font_policy": recipe.get("font_policy", ""),
            }
            entry["recipe"] = entry["recipe_summary"]
        return entry

    def _safe_figure_set_filename(self, value):
        text = str(value or "").strip()
        text = re.sub(r"[\\/:*?\"<>|]+", "_", text)
        text = re.sub(r"\s+", "_", text)
        text = text.strip("._ ")
        return text[:80]

    def _export_single_figure_set_panel(self, item, path):
        old_override = getattr(self, "_figure_set_render_dpi_override", None)
        try:
            self._figure_set_render_dpi_override = None
            dpi = self._figure_set_render_dpi()
            transparent = bool(getattr(self.figure_set_page, "transparent_background", False))
            fig = Figure(
                figsize=(self._cm_to_inches(max(0.2, item.width_cm)), self._cm_to_inches(max(0.2, item.height_cm))),
                dpi=dpi,
                facecolor="none" if transparent else "white",
            )
            FigureCanvasAgg(fig)
            ax = fig.add_axes([0, 0, 1, 1])
            ax.set_axis_off()
            img = self._render_figure_set_item_image(item)
            if img is not None:
                img = self._fit_figure_set_image_array(img, item)
                ax.imshow(img, aspect="auto", interpolation="none")
                ax.set_xlim(0, img.shape[1])
                ax.set_ylim(img.shape[0], 0)
            else:
                ax.text(0.5, 0.5, item.label, ha="center", va="center", transform=ax.transAxes, fontsize=8, fontname=self.plot_font_family)
            self._draw_figure_set_subplot_label_on_export(ax, item)
            if getattr(self.figure_set_page, "show_item_borders", False):
                ax.add_patch(Rectangle((0, 0), 1, 1, transform=ax.transAxes, fill=False, edgecolor="#111827", linewidth=0.4))
            ext = os.path.splitext(path)[1].lower().lstrip(".")
            fmt = "tiff" if ext in {"tif", "tiff"} else ext if ext in {"png", "pdf", "svg"} else "png"
            fig.savefig(path, **self._figure_set_savefig_kwargs(fmt, dpi, transparent))
        finally:
            self._figure_set_render_dpi_override = old_override

    def _export_figure_set_to_path(self, path):
        old_override = getattr(self, "_figure_set_render_dpi_override", None)
        try:
            self._figure_set_render_dpi_override = None
            self._sync_figure_set_page_from_ui()
            page_w_cm = max(1.0, float(self.figure_set_page.width_cm))
            page_h_cm = max(1.0, float(self.figure_set_page.height_cm))
            dpi = self._figure_set_export_dpi()
            transparent = bool(getattr(self.figure_set_page, "transparent_background", False))
            fig = Figure(
                figsize=(self._cm_to_inches(page_w_cm), self._cm_to_inches(page_h_cm)),
                dpi=dpi,
                facecolor="none" if transparent else "white",
            )
            FigureCanvasAgg(fig)
            page_ax = fig.add_axes([0, 0, 1, 1])
            page_ax.set_axis_off()
            page_ax.set_xlim(0, page_w_cm)
            page_ax.set_ylim(page_h_cm, 0)
            if not transparent:
                page_ax.add_patch(
                    Rectangle(
                        (0, 0),
                        page_w_cm,
                        page_h_cm,
                        facecolor="white",
                        edgecolor="none",
                        linewidth=0,
                    )
                )

            for item in self.figure_set_page.items:
                self._render_figure_set_item_on_page(fig, item, page_w_cm, page_h_cm)

            ext = os.path.splitext(path)[1].lower().lstrip(".")
            if ext in {"tif", "tiff"}:
                fmt = "tiff"
            elif ext == "png":
                fmt = "png"
            elif ext == "svg":
                fmt = "svg"
            else:
                fmt = "pdf"
            fig.savefig(path, **self._figure_set_savefig_kwargs(fmt, dpi, transparent))
        finally:
            self._figure_set_render_dpi_override = old_override

    def _render_figure_set_item_on_page(self, fig, item, page_w_cm, page_h_cm):
        left = max(0.0, item.x_cm / page_w_cm)
        bottom = max(0.0, 1.0 - ((item.y_cm + item.height_cm) / page_h_cm))
        width = max(0.001, item.width_cm / page_w_cm)
        height = max(0.001, item.height_cm / page_h_cm)
        ax = fig.add_axes([left, bottom, width, height])
        ax.set_axis_off()

        img = self._render_figure_set_item_image(item)
        if img is not None:
            img = self._fit_figure_set_image_array(img, item)
            ax.imshow(img, aspect="auto", interpolation="none")
            ax.set_xlim(0, img.shape[1])
            ax.set_ylim(img.shape[0], 0)
        else:
            ax.text(
                0.5,
                0.5,
                item.label,
                ha="center",
                va="center",
                transform=ax.transAxes,
                fontsize=8,
                fontname=self.plot_font_family,
                color="#111827",
            )
        self._draw_figure_set_subplot_label_on_export(ax, item)
        if getattr(self.figure_set_page, "show_item_borders", False):
            ax.add_patch(
                Rectangle(
                    (0, 0),
                    1,
                    1,
                    transform=ax.transAxes,
                    fill=False,
                    edgecolor="#111827",
                    linewidth=0.4,
                )
            )

    def _figure_set_export_dpi(self):
        try:
            return max(150, min(1200, int(float(getattr(self.figure_set_page, "export_dpi", 600)))))
        except Exception:
            return 600

    def _figure_set_panel_render_scale(self):
        try:
            return max(1.0, min(3.0, float(getattr(self.figure_set_page, "panel_render_scale", 1.0))))
        except Exception:
            return 1.0

    def _figure_set_render_dpi(self):
        override = getattr(self, "_figure_set_render_dpi_override", None)
        if override is not None:
            try:
                return max(72, min(1200, int(round(float(override)))))
            except Exception:
                return 120
        return max(150, min(2400, int(round(self._figure_set_export_dpi() * self._figure_set_panel_render_scale()))))

    def _figure_set_preview_dpi(self, item=None, width_px=None, height_px=None):
        try:
            zoom = max(0.75, min(1.5, float(getattr(self.figure_set_page, "zoom_percent", 100)) / 100.0))
            dpi = float(max(180, min(360, int(round(240 * zoom)))))
            if item is not None and width_px and height_px:
                width_in = self._cm_to_inches(max(0.2, float(item.width_cm)))
                height_in = self._cm_to_inches(max(0.2, float(item.height_cm)))
                display_dpi = max(float(width_px) / width_in, float(height_px) / height_in)
                # Render above the current screen requirement so text and thin
                # diffraction lines stay clean after the final LANCZOS resize.
                dpi = max(dpi, display_dpi * 1.35)
            return max(180, min(900, int(math.ceil(dpi))))
        except Exception:
            return 240

    def _figure_set_panel_transparent(self):
        return bool(getattr(self.figure_set_page, "panel_transparent_background", False))

    def _figure_set_export_metadata(self, fmt):
        if not bool(getattr(self.figure_set_page, "export_metadata_enabled", True)):
            return None
        title = f"{APP_NAME} - Figure Set"
        creator = APP_NAME
        fmt = str(fmt or "").lower()
        if fmt == "pdf":
            return {"Title": title, "Creator": creator, "Subject": "Publication figure set"}
        if fmt == "png":
            return {"Software": creator}
        return None

    def _figure_set_savefig_kwargs(self, fmt, dpi, transparent):
        kwargs = {
            "format": fmt,
            "dpi": dpi,
            "facecolor": "none" if transparent else "white",
            "edgecolor": "none",
            "transparent": bool(transparent),
        }
        if bool(getattr(self.figure_set_page, "export_tight_bbox", False)):
            kwargs["bbox_inches"] = "tight"
            kwargs["pad_inches"] = self._cm_to_inches(max(0.0, float(getattr(self.figure_set_page, "export_padding_cm", 0.0))))
        metadata = self._figure_set_export_metadata(fmt)
        if metadata:
            kwargs["metadata"] = metadata
        return kwargs

    def _fit_figure_set_image_array(self, img, item):
        if Image is None:
            return img
        try:
            arr = np.asarray(img)
            if arr.dtype != np.uint8:
                arr = (np.clip(arr, 0.0, 1.0) * 255).astype(np.uint8)
            if arr.ndim == 2:
                pil = Image.fromarray(arr, mode="L").convert("RGBA")
            else:
                pil = Image.fromarray(arr).convert("RGBA")
            preserve_scale = self._figure_set_preserve_panel_scale(item)
            pil = self._crop_figure_set_pil_image(pil, item)
            if self._figure_set_panel_transparent() and not preserve_scale:
                pil = self._trim_transparent_figure_set_pil_image(pil)
            dpi = self._figure_set_render_dpi()
            target = (
                max(1, int(round(self._cm_to_inches(max(0.2, item.width_cm)) * dpi))),
                max(1, int(round(self._cm_to_inches(max(0.2, item.height_cm)) * dpi))),
            )
            if preserve_scale:
                out = self._paste_figure_set_panel_without_scaling(pil, target)
                return np.asarray(out) / 255.0
            fit_mode = str(getattr(item, "fit_mode", "contain") or "contain").lower()
            if fit_mode == "stretch":
                out = pil.resize(target, Image.LANCZOS)
            elif fit_mode == "fill" and ImageOps is not None:
                out = ImageOps.fit(pil, target, method=Image.LANCZOS, centering=(0.5, 0.5))
            else:
                alpha = 0 if (getattr(self.figure_set_page, "transparent_background", False) or self._figure_set_panel_transparent()) else 255
                out = Image.new("RGBA", target, (255, 255, 255, alpha))
                tmp = pil.copy()
                tmp.thumbnail(target, Image.LANCZOS)
                paste_x = max(0, (target[0] - tmp.width) // 2)
                paste_y = max(0, (target[1] - tmp.height) // 2)
                out.paste(tmp, (paste_x, paste_y), tmp)
            return np.asarray(out) / 255.0
        except Exception:
            return img

    def _figure_set_preserve_panel_scale(self, item):
        if not isinstance(getattr(item, "recipe", None), dict) or not item.recipe:
            return False
        return bool(getattr(item, "keep_font_fixed", True) or getattr(self.figure_set_page, "master_typography_enabled", False))

    def _paste_figure_set_panel_without_scaling(self, pil, target):
        """Place rendered panel pixels into the target canvas without resizing.

        This is what keeps 24 pt text physically identical across panels with
        different cm sizes. Scaling the image here would also scale the fonts.
        """
        alpha = 0 if (getattr(self.figure_set_page, "transparent_background", False) or self._figure_set_panel_transparent()) else 255
        out = Image.new("RGBA", target, (255, 255, 255, alpha))
        img = pil.convert("RGBA")
        if img.width > target[0] or img.height > target[1]:
            left = max(0, (img.width - target[0]) // 2)
            top = max(0, (img.height - target[1]) // 2)
            img = img.crop((left, top, left + min(target[0], img.width), top + min(target[1], img.height)))
        paste_x = max(0, (target[0] - img.width) // 2)
        paste_y = max(0, (target[1] - img.height) // 2)
        out.paste(img, (paste_x, paste_y), img)
        return out

    def _trim_transparent_figure_set_pil_image(self, pil, pad_px=24):
        """Remove transparent canvas margins so panel fitting ignores background."""
        if pil is None:
            return pil
        try:
            rgba = pil.convert("RGBA")
            alpha = np.asarray(rgba.getchannel("A"))
            ys, xs = np.where(alpha > 8)
            if xs.size == 0 or ys.size == 0:
                return rgba
            x0 = max(0, int(xs.min()) - int(pad_px))
            x1 = min(rgba.size[0], int(xs.max()) + int(pad_px) + 1)
            y0 = max(0, int(ys.min()) - int(pad_px))
            y1 = min(rgba.size[1], int(ys.max()) + int(pad_px) + 1)
            if x1 <= x0 + 2 or y1 <= y0 + 2:
                return rgba
            return rgba.crop((x0, y0, x1, y1))
        except Exception:
            return pil

    def _figure_set_panel_content_pad_inches(self):
        """Small safety pad used when rendering panels with tight text bounds."""
        try:
            sizes = [
                float(getattr(self.figure_set_page, "master_title_size", 12)),
                float(getattr(self.figure_set_page, "master_axis_size", 10)),
                float(getattr(self.figure_set_page, "master_tick_size", 10)),
                float(getattr(self.figure_set_page, "master_legend_size", 10)),
            ]
            return max(0.035, min(0.10, max(sizes) / 240.0))
        except Exception:
            return 0.05

    def _draw_figure_set_subplot_label_on_export(self, ax, item):
        if not getattr(item, "subplot_label_visible", True):
            return
        label = str(getattr(item, "subplot_label", "")).strip()
        if not label:
            return
        x_frac = max(0.0, min(1.0, float(getattr(item, "subplot_label_x_cm", 0.10)) / max(item.width_cm, 1e-9)))
        y_frac = 1.0 - max(0.0, min(1.0, float(getattr(item, "subplot_label_y_cm", 0.10)) / max(item.height_cm, 1e-9)))
        ax.text(
            x_frac,
            y_frac,
            label,
            transform=ax.transAxes,
            ha="left",
            va="top",
            fontsize=max(5, min(48, int(getattr(item, "subplot_label_size_pt", 10)))),
            fontname=self.plot_font_family,
            fontweight="bold" if getattr(item, "subplot_label_bold", True) else "normal",
            color=str(getattr(item, "subplot_label_color", "#111827")),
            zorder=10,
        )

    def clear_figure_set_render_cache(self, show_message=True):
        self.figure_set_render_cache = {}
        self.figure_set_render_cache_order = []
        if show_message:
            messagebox.showinfo("Figure Set", "Render cache cleared.")

    def _figure_set_source_signature(self, source_files):
        signature = []
        for path in source_files or []:
            try:
                signature.append((str(path), round(float(os.path.getmtime(path)), 3)))
            except Exception:
                signature.append((str(path), None))
        return signature

    def _figure_set_master_typography_signature(self):
        page = self.figure_set_page
        return {
            "enabled": bool(getattr(page, "master_typography_enabled", False)),
            "font": str(getattr(page, "master_font_display", "Current Plot Font")),
            "title": int(getattr(page, "master_title_size", 12)),
            "axis": int(getattr(page, "master_axis_size", 10)),
            "tick": int(getattr(page, "master_tick_size", 10)),
            "legend": int(getattr(page, "master_legend_size", 10)),
            "residual": int(getattr(page, "master_residual_size", 10)),
            "memo": int(getattr(page, "master_memo_size", 10)),
            "reference": int(getattr(page, "master_reference_size", 8)),
        }

    def _figure_set_recipe_for_render(self, item):
        base = item.recipe if isinstance(getattr(item, "recipe", None), dict) else {}
        if not base:
            return {}
        try:
            recipe = json.loads(json.dumps(base, ensure_ascii=False, default=str))
        except Exception:
            recipe = dict(base)
        settings = recipe.setdefault("settings", {})
        if not isinstance(settings, dict):
            settings = {}
            recipe["settings"] = settings
        settings["scale_text_with_ratio"] = False
        if bool(getattr(self.figure_set_page, "master_typography_enabled", False)):
            settings["plot_title_size"] = int(getattr(self.figure_set_page, "master_title_size", 12))
            settings["axis_label_size"] = int(getattr(self.figure_set_page, "master_axis_size", 10))
            settings["tick_label_size"] = int(getattr(self.figure_set_page, "master_tick_size", 10))
            settings["legend_font_size"] = int(getattr(self.figure_set_page, "master_legend_size", 10))
            settings["residual_label_size"] = int(getattr(self.figure_set_page, "master_residual_size", 10))
            settings["plot_memo_default_size"] = int(getattr(self.figure_set_page, "master_memo_size", 10))
            settings["reference_label_size"] = int(getattr(self.figure_set_page, "master_reference_size", 8))
            font_display = str(getattr(self.figure_set_page, "master_font_display", "Current Plot Font") or "Current Plot Font")
            if font_display == "Current Plot Font":
                font_display = str(getattr(self, "plot_font_display", ACTIVE_PLOT_FONT_DISPLAY))
            settings["plot_font_display"] = font_display
            settings["plot_memo_default_font"] = "Use Plot Font"
            if isinstance(settings.get("plot_memos"), list):
                for memo in settings["plot_memos"]:
                    if isinstance(memo, dict):
                        memo["size"] = int(getattr(self.figure_set_page, "master_memo_size", 10))
                        memo["font"] = "Use Plot Font"
        return recipe

    def _apply_figure_set_recipe_runtime_settings(self, recipe):
        settings = recipe.get("settings", {}) if isinstance(recipe, dict) else {}
        if not isinstance(settings, dict):
            return
        if "plot_font_display" in settings:
            try:
                self.set_plot_font(str(settings["plot_font_display"]), redraw=False)
            except TypeError:
                self.set_plot_font(str(settings["plot_font_display"]))
            except Exception:
                pass
        for key, attr, var_name in [
            ("plot_layout", "plot_layout_mode", "var_plot_layout"),
            ("plot_aspect_ratio", "plot_aspect_ratio", "var_plot_aspect_ratio"),
            ("custom_plot_aspect_ratio", "custom_plot_aspect_ratio", "var_custom_plot_aspect_ratio"),
            ("plot_size_mode", "plot_size_mode", "var_plot_size_mode"),
            ("plot_size_unit", "plot_size_unit", "var_plot_size_unit"),
        ]:
            if key in settings:
                value = str(settings[key])
                setattr(self, attr, value)
                self._set_ui_value(var_name, value)
        for key, attr, var_name in [
            ("plot_width_value", "plot_width_value", "var_plot_width_value"),
            ("plot_height_value", "plot_height_value", "var_plot_height_value"),
            ("plot_view_zoom", "plot_view_zoom", "var_plot_view_zoom"),
        ]:
            if key in settings:
                try:
                    value = float(settings[key])
                    setattr(self, attr, value)
                    self._set_ui_value(var_name, value)
                except Exception:
                    pass
        if "scale_text_with_ratio" in settings:
            value = bool(settings["scale_text_with_ratio"])
            self.scale_text_with_ratio = value
            self._set_ui_value("var_scale_text_with_ratio", value)
        if "plot_memos" in settings and isinstance(settings["plot_memos"], list):
            try:
                self.plot_memos = json.loads(json.dumps(settings["plot_memos"], ensure_ascii=False, default=str))
            except Exception:
                self.plot_memos = [dict(m) for m in settings["plot_memos"] if isinstance(m, dict)]

    def _apply_figure_set_recipe_file_visibility(self, recipe):
        """Restore the panel-local Project Files visibility snapshot.

        Template application normally restores this state too, but Figure Set
        rendering must be stricter: files loaded or made visible after the
        panel was captured must never appear in that saved panel.
        """
        if not isinstance(recipe, dict):
            return
        snapshot = recipe.get("figure_set_file_visibility")
        if not isinstance(snapshot, dict):
            # Backward compatibility for Figure Sets saved before the explicit
            # visibility snapshot was introduced.
            snapshot = {}
            files = recipe.get("files", {})
            if isinstance(files, dict):
                for path, state in files.items():
                    if isinstance(state, dict) and "global_visible" in state:
                        snapshot[str(path)] = bool(state["global_visible"])
        if not snapshot:
            return

        exact = {str(path): bool(visible) for path, visible in snapshot.items()}
        normalized = {
            os.path.normcase(os.path.normpath(str(path))): bool(visible)
            for path, visible in snapshot.items()
        }
        basename_matches = {}
        for path, visible in snapshot.items():
            basename = os.path.normcase(os.path.basename(str(path)))
            basename_matches.setdefault(basename, []).append(bool(visible))

        for path, loader in getattr(self, "loaded_files", {}).items():
            path_text = str(path)
            if path_text in exact:
                visible = exact[path_text]
            else:
                path_key = os.path.normcase(os.path.normpath(path_text))
                if path_key in normalized:
                    visible = normalized[path_key]
                else:
                    matches = basename_matches.get(os.path.normcase(os.path.basename(path_text)), [])
                    # A basename fallback is safe only when it identifies one
                    # captured file.  Unmatched/new files stay hidden.
                    visible = matches[0] if len(matches) == 1 else False
            loader.global_visible = bool(visible)

    def _figure_set_render_cache_key(self, item):
        recipe = item.recipe if isinstance(getattr(item, "recipe", None), dict) else {}
        if not recipe:
            return None
        try:
            source_files = recipe.get("source_files", []) or []
            material = {
                "recipe": recipe,
                "source_signature": self._figure_set_source_signature(source_files),
                "width_cm": round(float(item.width_cm), 4),
                "height_cm": round(float(item.height_cm), 4),
                "dpi": self._figure_set_render_dpi(),
                "panel_render_mode": "fixed_physical_canvas_v3_visibility_snapshot",
                "master_typography": self._figure_set_master_typography_signature(),
                "panel_transparent": self._figure_set_panel_transparent(),
            }
            blob = json.dumps(material, ensure_ascii=False, sort_keys=True, default=str)
            return hashlib.sha1(blob.encode("utf-8")).hexdigest()
        except Exception:
            return None

    def _get_figure_set_render_cache(self, key):
        if not key:
            return None
        value = self.figure_set_render_cache.get(key)
        if value is None:
            return None
        try:
            if key in self.figure_set_render_cache_order:
                self.figure_set_render_cache_order.remove(key)
            self.figure_set_render_cache_order.append(key)
        except Exception:
            pass
        return value

    def _put_figure_set_render_cache(self, key, value):
        if not key or value is None:
            return
        self.figure_set_render_cache[key] = value
        if key in self.figure_set_render_cache_order:
            self.figure_set_render_cache_order.remove(key)
        self.figure_set_render_cache_order.append(key)
        while len(self.figure_set_render_cache_order) > max(1, int(self.figure_set_render_cache_limit)):
            old_key = self.figure_set_render_cache_order.pop(0)
            self.figure_set_render_cache.pop(old_key, None)

    def _render_figure_set_item_image(self, item):
        cache_key = self._figure_set_render_cache_key(item)
        cached = self._get_figure_set_render_cache(cache_key)
        if cached is not None:
            return cached
        rendered = self._render_figure_set_item_from_recipe(item)
        if rendered is not None:
            self._put_figure_set_render_cache(cache_key, rendered)
            return rendered
        if not item.thumbnail_data:
            return None
        try:
            raw = base64.b64decode(item.thumbnail_data)
            return mpimg.imread(io.BytesIO(raw), format="png")
        except Exception:
            return None

    def _render_figure_set_item_preview_image(self, item, width_px=None, height_px=None):
        old_override = getattr(self, "_figure_set_render_dpi_override", None)
        try:
            self._figure_set_render_dpi_override = self._figure_set_preview_dpi(
                item,
                width_px=width_px,
                height_px=height_px,
            )
            return self._render_figure_set_item_image(item)
        finally:
            self._figure_set_render_dpi_override = old_override

    def _render_figure_set_item_from_recipe(self, item):
        recipe = self._figure_set_recipe_for_render(item)
        if not recipe:
            return None
        source_files = recipe.get("source_files", [])
        if source_files:
            missing = [p for p in source_files if p not in getattr(self, "loaded_files", {})]
            if missing:
                return None

        current_template = None
        original_fig = getattr(self, "fig", None)
        original_axes = list(getattr(self, "plot_axes", []))
        original_vlines = list(getattr(self, "vlines", []))
        original_hlines = list(getattr(self, "hlines", []))
        original_title_artist = getattr(self, "title_artist", None)
        original_title_axis = getattr(self, "title_axis", None)
        original_suspend = getattr(self, "_suspend_template_draw", False)
        original_redrawing = getattr(self, "_is_redrawing", False)
        try:
            current_template = self._collect_template_data()
            self._suspend_template_draw = True
            self._apply_template_data(recipe)
            self._apply_figure_set_recipe_file_visibility(recipe)
            self._apply_figure_set_recipe_runtime_settings(recipe)

            self._set_ui_value("var_plot_size_mode", "Fixed")
            self._set_ui_value("var_plot_size_unit", "cm")
            self._set_ui_value("var_plot_width_value", max(0.2, item.width_cm))
            self._set_ui_value("var_plot_height_value", max(0.2, item.height_cm))
            self._set_ui_value("var_scale_text_with_ratio", False)
            self.plot_size_mode = "Fixed"
            self.plot_size_unit = "cm"
            self.plot_width_value = max(0.2, item.width_cm)
            self.plot_height_value = max(0.2, item.height_cm)
            self.scale_text_with_ratio = False

            render_dpi = self._figure_set_render_dpi()
            panel_transparent = self._figure_set_panel_transparent()
            fig = Figure(
                figsize=(self._cm_to_inches(item.width_cm), self._cm_to_inches(item.height_cm)),
                dpi=render_dpi,
                facecolor="none" if panel_transparent else "white",
            )
            canvas = FigureCanvasAgg(fig)
            self.fig = fig
            self.plot_axes = []
            self.vlines = []
            self.hlines = []
            self.title_artist = None
            self.title_axis = None
            self._is_redrawing = True

            if getattr(self, "is_3d_mode", False):
                self._draw_3d()
            else:
                if getattr(self, "plot_layout_mode", "combined") == "split":
                    self._draw_2d_split_by_file()
                else:
                    self._draw_2d()
            for ax in list(getattr(self, "plot_axes", [])):
                try:
                    self._apply_axis_font(ax)
                except Exception:
                    pass
                if panel_transparent:
                    try:
                        ax.set_facecolor((1, 1, 1, 0))
                        ax.patch.set_alpha(0)
                    except Exception:
                        pass
            try:
                self._draw_plot_memos()
            except Exception:
                pass
            canvas.draw()
            buf = io.BytesIO()
            fig.savefig(
                buf,
                format="png",
                dpi=render_dpi,
                facecolor="none" if panel_transparent else "white",
                edgecolor="none",
                transparent=panel_transparent,
                bbox_inches=None,
                pad_inches=0,
            )
            buf.seek(0)
            return mpimg.imread(buf, format="png")
        except Exception:
            return None
        finally:
            self.fig = original_fig
            self.plot_axes = original_axes
            self.vlines = original_vlines
            self.hlines = original_hlines
            self.title_artist = original_title_artist
            self.title_axis = original_title_axis
            self._is_redrawing = original_redrawing
            self._suspend_template_draw = original_suspend
            if current_template is not None:
                try:
                    self._suspend_template_draw = True
                    self._apply_template_data(current_template)
                except Exception:
                    pass
                finally:
                    self._suspend_template_draw = original_suspend

    def save_figure_set(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".labxfigset.json",
            filetypes=[(f"{APP_NAME} - Figure Set", "*.labxfigset.json"), ("JSON", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._figure_set_to_dict(), f, ensure_ascii=False, indent=2)
            messagebox.showinfo("Figure Set", "Figure Set saved.")
        except Exception as e:
            messagebox.showerror("Figure Set", f"Failed to save Figure Set.\n{e}")

    def save_figure_set_page_template(self):
        self._sync_figure_set_page_from_ui()
        path = filedialog.asksaveasfilename(
            defaultextension=".labxfigpage.json",
            filetypes=[(f"{APP_NAME} - Figure Page Template", "*.labxfigpage.json"), ("JSON", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            data = {
                "version": 1,
                "type": f"{APP_NAME} - Figure Set Page Template",
                "page": self._figure_set_page_to_dict(),
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            messagebox.showinfo("Figure Set", "Page template saved.")
        except Exception as e:
            messagebox.showerror("Figure Set", f"Failed to save page template.\n{e}")

    def load_figure_set_page_template(self):
        path = filedialog.askopenfilename(
            filetypes=[(f"{APP_NAME} - Figure Page Template", "*.labxfigpage.json"), ("JSON", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            page = data.get("page", data if isinstance(data, dict) else {})
            self._push_figure_set_undo_state()
            self._apply_figure_set_page_dict(page)
            self._push_figure_set_page_to_ui()
            self.refresh_figure_set_canvas()
            messagebox.showinfo("Figure Set", "Page template loaded.")
        except Exception as e:
            messagebox.showerror("Figure Set", f"Failed to load page template.\n{e}")

    def load_figure_set(self):
        path = filedialog.askopenfilename(
            filetypes=[(f"{APP_NAME} - Figure Set", "*.labxfigset.json"), ("JSON", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._push_figure_set_undo_state()
            self._load_figure_set_data(data)
            self.clear_figure_set_render_cache(show_message=False)
            messagebox.showinfo("Figure Set", "Figure Set loaded.")
        except Exception as e:
            messagebox.showerror("Figure Set", f"Failed to load Figure Set.\n{e}")

    def _load_figure_set_data(self, data):
        data = data or {}
        page = data.get("page", {})
        self._apply_figure_set_page_dict(page)
        self.figure_set_page.items = []
        for entry in data.get("items", []):
            self.figure_set_page.items.append(self._figure_set_item_from_dict(entry))
        self._clamp_figure_set_items_to_page()
        self._set_figure_set_selection([self.figure_set_page.items[0].item_id] if self.figure_set_page.items else [])
        self._push_figure_set_page_to_ui()
        self.refresh_figure_set_canvas()

    def _push_figure_set_page_to_ui(self):
        if not hasattr(self, "var_figset_page_w"):
            return
        if self.figure_set_page.unit == "inch":
            self.var_figset_page_w.set(round(self.figure_set_page.width_cm / 2.54, 4))
            self.var_figset_page_h.set(round(self.figure_set_page.height_cm / 2.54, 4))
        else:
            self.var_figset_page_w.set(round(self.figure_set_page.width_cm, 4))
            self.var_figset_page_h.set(round(self.figure_set_page.height_cm, 4))
        if hasattr(self, "var_figset_preset"):
            self.var_figset_preset.set(getattr(self.figure_set_page, "preset_name", "Custom"))
        self.var_figset_unit.set(self.figure_set_page.unit)
        self.var_figset_zoom.set(self.figure_set_page.zoom_percent)
        self.var_figset_export_dpi.set(self.figure_set_page.export_dpi)
        self.var_figset_transparent.set(self.figure_set_page.transparent_background)
        self.var_figset_borders.set(self.figure_set_page.show_item_borders)
        if hasattr(self, "var_figset_panel_transparent"):
            self.var_figset_panel_transparent.set(bool(getattr(self.figure_set_page, "panel_transparent_background", True)))
        if hasattr(self, "var_figset_panel_scale"):
            self.var_figset_panel_scale.set(f"{float(getattr(self.figure_set_page, 'panel_render_scale', 1.0)):g}x")
        if hasattr(self, "var_figset_tight_bbox"):
            self.var_figset_tight_bbox.set(bool(getattr(self.figure_set_page, "export_tight_bbox", False)))
        if hasattr(self, "var_figset_export_padding"):
            self.var_figset_export_padding.set(float(getattr(self.figure_set_page, "export_padding_cm", 0.0)))
        if hasattr(self, "var_figset_metadata"):
            self.var_figset_metadata.set(bool(getattr(self.figure_set_page, "export_metadata_enabled", True)))
        if hasattr(self, "var_figset_set_copy"):
            self.var_figset_set_copy.set(bool(getattr(self.figure_set_page, "export_set_copy_enabled", True)))
        self.var_figset_grid.set(self.figure_set_page.show_grid)
        if hasattr(self, "var_figset_grid_step"):
            self.var_figset_grid_step.set(getattr(self.figure_set_page, "grid_step_cm", 0.5))
        self.var_figset_guides.set(self.figure_set_page.show_guides)
        if hasattr(self, "var_figset_margin_guides"):
            self.var_figset_margin_guides.set(getattr(self.figure_set_page, "show_margin_guides", True))
        if hasattr(self, "var_figset_margin_cm"):
            self.var_figset_margin_cm.set(getattr(self.figure_set_page, "margin_guide_cm", 0.5))
        if hasattr(self, "var_figset_manual_guides_x"):
            self.var_figset_manual_guides_x.set(self._format_figure_set_guides(getattr(self.figure_set_page, "manual_guides_x_cm", [])))
        if hasattr(self, "var_figset_manual_guides_y"):
            self.var_figset_manual_guides_y.set(self._format_figure_set_guides(getattr(self.figure_set_page, "manual_guides_y_cm", [])))
        self.var_figset_snap.set(self.figure_set_page.snap_enabled)
        if hasattr(self, "var_figset_master_typography"):
            self.var_figset_master_typography.set(bool(getattr(self.figure_set_page, "master_typography_enabled", False)))
        if hasattr(self, "var_figset_master_font"):
            self.var_figset_master_font.set(str(getattr(self.figure_set_page, "master_font_display", "Current Plot Font")))
        for attr, var_name, fallback in [
            ("master_title_size", "var_figset_master_title_size", 12),
            ("master_axis_size", "var_figset_master_axis_size", 10),
            ("master_tick_size", "var_figset_master_tick_size", 10),
            ("master_legend_size", "var_figset_master_legend_size", 10),
            ("master_residual_size", "var_figset_master_residual_size", 10),
            ("master_memo_size", "var_figset_master_memo_size", 10),
            ("master_reference_size", "var_figset_master_reference_size", 8),
        ]:
            if hasattr(self, var_name):
                getattr(self, var_name).set(int(getattr(self.figure_set_page, attr, fallback)))

    def _find_figure_set_item_at(self, x, y):
        for item in reversed(self.figure_set_page.items):
            box = self.figure_set_canvas_items.get(item.item_id)
            if not box:
                continue
            x0, y0, x1, y1 = box
            if x0 <= x <= x1 and y0 <= y <= y1:
                return item
        return None

    def _on_figure_set_press(self, event):
        if not hasattr(self, "figure_set_canvas"):
            return
        try:
            self.figure_set_canvas.focus_set()
        except Exception:
            pass
        x = self.figure_set_canvas.canvasx(event.x)
        y = self.figure_set_canvas.canvasy(event.y)
        item = self._find_figure_set_item_at(x, y)
        self.figure_set_drag = None
        if item:
            current = self.figure_set_canvas.find_withtag("current")
            current_id = current[0] if current else None
            label_item_id = self.figure_set_subplot_label_hits.get(current_id)
            if label_item_id and not self._is_multi_select_event(event):
                label_item = self._get_figure_set_item(label_item_id)
                if label_item:
                    self._set_figure_set_selection([label_item.item_id])
                    self.figure_set_drag = {
                        "item_id": label_item.item_id,
                        "mode": "subplot_label",
                        "start_x": x,
                        "start_y": y,
                        "start_label_x": float(getattr(label_item, "subplot_label_x_cm", 0.10)),
                        "start_label_y": float(getattr(label_item, "subplot_label_y_cm", 0.10)),
                    }
                    self.refresh_figure_set_canvas()
                    self._update_figure_set_item_bar()
                    return
            multi_select = self._is_multi_select_event(event)
            selected_ids = set(getattr(self, "figure_set_selected_ids", set()))
            if multi_select:
                if item.item_id in selected_ids:
                    selected_ids.remove(item.item_id)
                else:
                    selected_ids.add(item.item_id)
                self._set_figure_set_selection(selected_ids)
                if item.item_id not in selected_ids:
                    self.refresh_figure_set_canvas()
                    self._update_figure_set_item_bar()
                    return
            elif item.item_id not in selected_ids:
                self._set_figure_set_selection([item.item_id])

            x0, y0, _x1, _y1 = self.figure_set_canvas_items[item.item_id]
            self.figure_set_drag = {
                "item_id": item.item_id,
                "dx": x - x0,
                "dy": y - y0,
                "mode": "move",
                "start_positions": {it.item_id: (it.x_cm, it.y_cm) for it in self._selected_figure_set_items()},
                "clicked_start": (item.x_cm, item.y_cm),
            }
            current = self.figure_set_canvas.find_withtag("current")
            if current and current[0] in self.figure_set_resize_handles:
                self._set_figure_set_selection([item.item_id])
                self.figure_set_drag = {
                    "item_id": item.item_id,
                    "mode": "resize",
                    "start_x": x,
                    "start_y": y,
                    "start_w": item.width_cm,
                    "start_h": item.height_cm,
                }
        else:
            if not self._is_multi_select_event(event):
                self._set_figure_set_selection([])
        self.refresh_figure_set_canvas()
        self._update_figure_set_item_bar()

    def _on_figure_set_drag(self, event):
        if not self.figure_set_drag:
            return
        item = self._get_figure_set_item(self.figure_set_drag["item_id"])
        if not item:
            return
        if not self.figure_set_drag.get("history_pushed"):
            self._push_figure_set_undo_state()
            self.figure_set_drag["history_pushed"] = True
        force_refresh = False
        if self.figure_set_drag.get("mode") == "resize":
            x = self.figure_set_canvas.canvasx(event.x)
            y = self.figure_set_canvas.canvasy(event.y)
            dx_cm = (x - self.figure_set_drag["start_x"]) / self._figset_scale()
            dy_cm = (y - self.figure_set_drag["start_y"]) / self._figset_scale()
            new_w = self.figure_set_drag["start_w"] + dx_cm
            new_h = self.figure_set_drag["start_h"] + dy_cm
            if int(getattr(event, "state", 0) or 0) & 0x0001:
                ratio = self.figure_set_drag["start_w"] / max(1e-9, self.figure_set_drag["start_h"])
                if abs(dx_cm) >= abs(dy_cm):
                    new_h = new_w / max(1e-9, ratio)
                else:
                    new_w = new_h * ratio
            if getattr(self.figure_set_page, "snap_enabled", True) and getattr(self.figure_set_page, "show_grid", True):
                step = max(0.1, float(getattr(self.figure_set_page, "grid_step_cm", 0.5)))
                new_w = round(new_w / step) * step
                new_h = round(new_h / step) * step
            item.width_cm = max(0.2, min(self.figure_set_page.width_cm - item.x_cm, new_w))
            item.height_cm = max(0.2, min(self.figure_set_page.height_cm - item.y_cm, new_h))
        elif self.figure_set_drag.get("mode") == "subplot_label":
            x = self.figure_set_canvas.canvasx(event.x)
            y = self.figure_set_canvas.canvasy(event.y)
            dx_cm = (x - self.figure_set_drag["start_x"]) / self._figset_scale()
            dy_cm = (y - self.figure_set_drag["start_y"]) / self._figset_scale()
            item.subplot_label_x_cm = max(0.0, min(item.width_cm, self.figure_set_drag["start_label_x"] + dx_cm))
            item.subplot_label_y_cm = max(0.0, min(item.height_cm, self.figure_set_drag["start_label_y"] + dy_cm))
        else:
            x = self.figure_set_canvas.canvasx(event.x) - self.figure_set_drag["dx"]
            y = self.figure_set_canvas.canvasy(event.y) - self.figure_set_drag["dy"]
            x_cm, y_cm = self._canvas_to_cm(x, y)
            x_cm, y_cm = self._snap_figure_set_position(item, x_cm, y_cm)
            clicked_start = self.figure_set_drag.get("clicked_start", (item.x_cm, item.y_cm))
            dx_cm = x_cm - clicked_start[0]
            dy_cm = y_cm - clicked_start[1]
            dx_cm, dy_cm = self._clamp_figure_set_group_delta(self.figure_set_drag.get("start_positions", {}), dx_cm, dy_cm)
            scale = self._figset_scale()
            direct_ok = True
            for moving_item in self._selected_figure_set_items():
                start = self.figure_set_drag.get("start_positions", {}).get(moving_item.item_id, (moving_item.x_cm, moving_item.y_cm))
                new_x = start[0] + dx_cm
                new_y = start[1] + dy_cm
                ddx = (new_x - moving_item.x_cm) * scale
                ddy = (new_y - moving_item.y_cm) * scale
                moving_item.x_cm = new_x
                moving_item.y_cm = new_y
                if abs(ddx) > 1e-6 or abs(ddy) > 1e-6:
                    direct_ok = self._move_figure_set_canvas_item_directly(moving_item.item_id, ddx, ddy) and direct_ok
            if direct_ok:
                if hasattr(self, "figure_set_canvas"):
                    self.figure_set_canvas.delete("selection_bounds")
                self._draw_figure_set_selection_bounds()
                self._draw_smart_guides(item)
                return
            force_refresh = True
        now = time.perf_counter()
        if not force_refresh and now - float(getattr(self, "_figure_set_last_interactive_refresh", 0.0) or 0.0) < 0.03:
            return
        self._figure_set_last_interactive_refresh = now
        self.refresh_figure_set_canvas()
        self._draw_smart_guides(item)
        self._update_figure_set_item_bar()

    def _on_figure_set_release(self, _event):
        self.figure_set_drag = None
        if hasattr(self, "figure_set_canvas"):
            self.figure_set_canvas.delete("smartguide")
        self.refresh_figure_set_canvas()
        self._update_figure_set_item_bar()

    def _figure_set_mousewheel_steps(self, event):
        if hasattr(event, "num") and event.num in (4, 5):
            return -1 if event.num == 4 else 1
        try:
            delta = int(getattr(event, "delta", 0))
        except Exception:
            delta = 0
        if delta == 0:
            return 0
        return -1 if delta > 0 else 1

    def _on_figure_set_mousewheel(self, event):
        if not hasattr(self, "figure_set_canvas"):
            return None
        steps = self._figure_set_mousewheel_steps(event)
        if steps == 0:
            return "break"
        state = int(getattr(event, "state", 0) or 0)
        ctrl_pressed = bool(state & 0x0004)
        shift_pressed = bool(state & 0x0001)
        if ctrl_pressed:
            self._zoom_figure_set_at_event(event, zoom_in=steps < 0)
            return "break"
        if shift_pressed:
            self.figure_set_canvas.xview_scroll(steps, "units")
        else:
            self.figure_set_canvas.yview_scroll(steps, "units")
        return "break"

    def _zoom_figure_set_at_event(self, event, zoom_in=True):
        canvas = self.figure_set_canvas
        old_x = canvas.canvasx(event.x)
        old_y = canvas.canvasy(event.y)
        anchor_cm = self._canvas_to_cm(old_x, old_y)
        old_zoom = int(getattr(self.figure_set_page, "zoom_percent", 100) or 100)
        factor = 1.12 if zoom_in else 1.0 / 1.12
        new_zoom = max(10, min(800, int(round(old_zoom * factor))))
        if new_zoom == old_zoom:
            return
        self.figure_set_page.zoom_percent = new_zoom
        if hasattr(self, "var_figset_zoom"):
            self.var_figset_zoom.set(new_zoom)
        self.refresh_figure_set_canvas()
        try:
            new_x, new_y = self._cm_to_canvas(*anchor_cm)
            scroll_region = [float(v) for v in str(canvas.cget("scrollregion")).split()]
            if len(scroll_region) == 4:
                x0, y0, x1, y1 = scroll_region
                view_w = max(1.0, float(canvas.winfo_width()))
                view_h = max(1.0, float(canvas.winfo_height()))
                x_span = max(1.0, (x1 - x0) - view_w)
                y_span = max(1.0, (y1 - y0) - view_h)
                left = max(x0, min(x1 - view_w, new_x - float(event.x)))
                top = max(y0, min(y1 - view_h, new_y - float(event.y)))
                canvas.xview_moveto(max(0.0, min(1.0, (left - x0) / x_span)))
                canvas.yview_moveto(max(0.0, min(1.0, (top - y0) / y_span)))
        except Exception:
            pass

    def _on_figure_set_keypress(self, event):
        key = str(getattr(event, "keysym", ""))
        selected = self._selected_figure_set_items()
        if key in {"Delete", "BackSpace"}:
            self.delete_selected_figure_set_item()
            return "break"
        if key.lower() == "d" and self._is_multi_select_event(event):
            self.duplicate_selected_figure_set_item()
            return "break"
        if not selected:
            return None
        state = int(getattr(event, "state", 0) or 0)
        step = 0.1
        if state & 0x0001:
            step = 0.5
        if state & 0x0004:
            step = 0.02
        dx = dy = 0.0
        if key == "Left":
            dx = -step
        elif key == "Right":
            dx = step
        elif key == "Up":
            dy = -step
        elif key == "Down":
            dy = step
        else:
            return None
        if state & 0x0008:
            self._resize_figure_set_items_by_keyboard(selected, dx, dy, keep_ratio=bool(state & 0x0001))
            return "break"
        self._push_figure_set_undo_state()
        start_positions = {item.item_id: (item.x_cm, item.y_cm) for item in selected}
        dx, dy = self._clamp_figure_set_group_delta(start_positions, dx, dy)
        for item in selected:
            item.x_cm = start_positions[item.item_id][0] + dx
            item.y_cm = start_positions[item.item_id][1] + dy
        self.refresh_figure_set_canvas()
        return "break"

    def _resize_figure_set_items_by_keyboard(self, items, dx_cm, dy_cm, keep_ratio=False):
        if not items:
            return
        self._push_figure_set_undo_state()
        for item in items:
            new_w = float(item.width_cm)
            new_h = float(item.height_cm)
            if dx_cm > 0:
                new_w += abs(dx_cm)
            elif dx_cm < 0:
                new_w -= abs(dx_cm)
            if dy_cm > 0:
                new_h += abs(dy_cm)
            elif dy_cm < 0:
                new_h -= abs(dy_cm)
            if keep_ratio:
                ratio = float(item.width_cm) / max(1e-9, float(item.height_cm))
                if abs(dx_cm) >= abs(dy_cm):
                    new_h = new_w / max(1e-9, ratio)
                else:
                    new_w = new_h * ratio
            if getattr(self.figure_set_page, "snap_enabled", True) and getattr(self.figure_set_page, "show_grid", True):
                step = max(0.1, float(getattr(self.figure_set_page, "grid_step_cm", 0.5)))
                new_w = round(new_w / step) * step
                new_h = round(new_h / step) * step
            item.width_cm = max(0.2, min(self.figure_set_page.width_cm - item.x_cm, new_w))
            item.height_cm = max(0.2, min(self.figure_set_page.height_cm - item.y_cm, new_h))
        self.refresh_figure_set_canvas()
        self._update_figure_set_item_bar()

    def _get_figure_set_item(self, item_id):
        for item in self.figure_set_page.items:
            if item.item_id == item_id:
                return item
        return None

    def _clamp_figure_set_group_delta(self, start_positions, dx_cm, dy_cm):
        moving = [
            item for item in self.figure_set_page.items
            if item.item_id in start_positions
        ]
        if not moving:
            return dx_cm, dy_cm
        min_x = min(start_positions[item.item_id][0] for item in moving)
        min_y = min(start_positions[item.item_id][1] for item in moving)
        max_x = max(start_positions[item.item_id][0] + item.width_cm for item in moving)
        max_y = max(start_positions[item.item_id][1] + item.height_cm for item in moving)
        dx_cm = max(-min_x, min(self.figure_set_page.width_cm - max_x, dx_cm))
        dy_cm = max(-min_y, min(self.figure_set_page.height_cm - max_y, dy_cm))
        return dx_cm, dy_cm

    def _snap_figure_set_axis(self, position, size, targets, threshold):
        edges = [position, position + size * 0.5, position + size]
        for target in targets:
            for idx, edge in enumerate(edges):
                if abs(edge - target) <= threshold:
                    if idx == 0:
                        return target
                    if idx == 1:
                        return target - size * 0.5
                    return target - size
        return position

    def _snap_figure_set_position(self, item, x_cm, y_cm):
        if not self.figure_set_page.snap_enabled:
            return x_cm, y_cm
        threshold = 0.10

        if getattr(self.figure_set_page, "show_grid", True):
            step = max(0.1, float(getattr(self.figure_set_page, "grid_step_cm", 0.5)))
            x_cm = round(x_cm / step) * step
            y_cm = round(y_cm / step) * step

        margin = max(0.0, float(getattr(self.figure_set_page, "margin_guide_cm", 0.5)))
        x_targets = [0.0, self.figure_set_page.width_cm * 0.5, self.figure_set_page.width_cm]
        y_targets = [0.0, self.figure_set_page.height_cm * 0.5, self.figure_set_page.height_cm]
        if getattr(self.figure_set_page, "show_margin_guides", True) and margin > 0:
            if margin < self.figure_set_page.width_cm * 0.5:
                x_targets.extend([margin, self.figure_set_page.width_cm - margin])
            if margin < self.figure_set_page.height_cm * 0.5:
                y_targets.extend([margin, self.figure_set_page.height_cm - margin])
        x_targets.extend([float(value) for value in getattr(self.figure_set_page, "manual_guides_x_cm", []) or []])
        y_targets.extend([float(value) for value in getattr(self.figure_set_page, "manual_guides_y_cm", []) or []])

        x_cm = self._snap_figure_set_axis(x_cm, item.width_cm, x_targets, threshold)
        y_cm = self._snap_figure_set_axis(y_cm, item.height_cm, y_targets, threshold)

        for other in self.figure_set_page.items:
            if other.item_id == item.item_id:
                continue
            targets_x = [other.x_cm, other.x_cm + other.width_cm * 0.5, other.x_cm + other.width_cm]
            targets_y = [other.y_cm, other.y_cm + other.height_cm * 0.5, other.y_cm + other.height_cm]
            x_cm = self._snap_figure_set_axis(x_cm, item.width_cm, targets_x, threshold)
            y_cm = self._snap_figure_set_axis(y_cm, item.height_cm, targets_y, threshold)
        return x_cm, y_cm

    def _draw_smart_guides(self, item):
        if not self.figure_set_page.show_guides:
            return
        c = self.figure_set_canvas
        c.delete("smartguide")
        x0, y0 = self._cm_to_canvas(0, 0)
        x1, y1 = self._cm_to_canvas(self.figure_set_page.width_cm, self.figure_set_page.height_cm)
        ix0, iy0, ix1, iy1 = self.figure_set_canvas_items.get(item.item_id, (None, None, None, None))
        if ix0 is None:
            return
        threshold_px = 5
        x_guides = [
            x0,
            (x0 + x1) * 0.5,
            x1,
        ]
        y_guides = [
            y0,
            (y0 + y1) * 0.5,
            y1,
        ]
        if getattr(self.figure_set_page, "show_margin_guides", True):
            margin_px = max(0.0, float(getattr(self.figure_set_page, "margin_guide_cm", 0.5))) * self._figset_scale()
            if margin_px > 0:
                x_guides.extend([x0 + margin_px, x1 - margin_px])
                y_guides.extend([y0 + margin_px, y1 - margin_px])
        for x_cm in getattr(self.figure_set_page, "manual_guides_x_cm", []) or []:
            x_guides.append(x0 + float(x_cm) * self._figset_scale())
        for y_cm in getattr(self.figure_set_page, "manual_guides_y_cm", []) or []:
            y_guides.append(y0 + float(y_cm) * self._figset_scale())
        for other in self.figure_set_page.items:
            if other.item_id == item.item_id:
                continue
            box = self.figure_set_canvas_items.get(other.item_id)
            if not box:
                continue
            ox0, oy0, ox1, oy1 = box
            x_guides.extend([ox0, (ox0 + ox1) * 0.5, ox1])
            y_guides.extend([oy0, (oy0 + oy1) * 0.5, oy1])

        item_x_edges = [ix0, (ix0 + ix1) * 0.5, ix1]
        item_y_edges = [iy0, (iy0 + iy1) * 0.5, iy1]
        drawn_x = set()
        drawn_y = set()
        for guide_x in x_guides:
            if any(abs(edge - guide_x) <= threshold_px for edge in item_x_edges):
                key = round(guide_x, 1)
                if key not in drawn_x:
                    c.create_line(guide_x, y0, guide_x, y1, fill="#ef4444", dash=(4, 3), width=1.4, tags=("smartguide",))
                    drawn_x.add(key)
        for guide_y in y_guides:
            if any(abs(edge - guide_y) <= threshold_px for edge in item_y_edges):
                key = round(guide_y, 1)
                if key not in drawn_y:
                    c.create_line(x0, guide_y, x1, guide_y, fill="#ef4444", dash=(4, 3), width=1.4, tags=("smartguide",))
                    drawn_y.add(key)

    def align_figure_set_selection(self, mode):
        items = self._selected_figure_set_items()
        if not items:
            return
        self._push_figure_set_undo_state()
        min_x = min(item.x_cm for item in items)
        min_y = min(item.y_cm for item in items)
        max_x = max(item.x_cm + item.width_cm for item in items)
        max_y = max(item.y_cm + item.height_cm for item in items)
        if mode == "left":
            dx = -min_x
            for item in items:
                item.x_cm += dx
        elif mode == "hcenter":
            group_w = max_x - min_x
            dx = (self.figure_set_page.width_cm - group_w) * 0.5 - min_x
            for item in items:
                item.x_cm += dx
        elif mode == "right":
            dx = self.figure_set_page.width_cm - max_x
            for item in items:
                item.x_cm += dx
        elif mode == "top":
            dy = -min_y
            for item in items:
                item.y_cm += dy
        elif mode == "vcenter":
            group_h = max_y - min_y
            dy = (self.figure_set_page.height_cm - group_h) * 0.5 - min_y
            for item in items:
                item.y_cm += dy
        elif mode == "bottom":
            dy = self.figure_set_page.height_cm - max_y
            for item in items:
                item.y_cm += dy
        self.refresh_figure_set_canvas()
        self._update_figure_set_item_bar()

    def distribute_figure_set_items(self, orientation):
        selected = self._selected_figure_set_items()
        items = selected if len(selected) >= 3 else list(self.figure_set_page.items)
        if len(items) < 3:
            return
        self._push_figure_set_undo_state()
        if orientation == "h":
            items.sort(key=lambda item: item.x_cm)
            first = items[0]
            last = items[-1]
            start = first.x_cm
            end = last.x_cm + last.width_cm
            total_w = sum(item.width_cm for item in items)
            gap = (end - start - total_w) / max(1, len(items) - 1)
            cursor = start
            for item in items:
                item.x_cm = max(0.0, min(self.figure_set_page.width_cm - item.width_cm, cursor))
                cursor += item.width_cm + gap
        else:
            items.sort(key=lambda item: item.y_cm)
            first = items[0]
            last = items[-1]
            start = first.y_cm
            end = last.y_cm + last.height_cm
            total_h = sum(item.height_cm for item in items)
            gap = (end - start - total_h) / max(1, len(items) - 1)
            cursor = start
            for item in items:
                item.y_cm = max(0.0, min(self.figure_set_page.height_cm - item.height_cm, cursor))
                cursor += item.height_cm + gap
        self.refresh_figure_set_canvas()
