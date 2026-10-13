# SPDX-License-Identifier: GPL-2.0-or-later
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from xrd_rietveld_manager.common import *
from xrd_rietveld_manager.branding import APP_TITLE
from xrd_rietveld_manager.ui_runtime import UiRuntimeMixin
from xrd_rietveld_manager.ui_tabs import UiTabsMixin
from xrd_rietveld_manager.phase_manager import PhaseManagerMixin
from xrd_rietveld_manager.file_manager import FileManagerMixin
from xrd_rietveld_manager.template_manager import TemplateManagerMixin
from xrd_rietveld_manager.style_controls import StyleControlsMixin
from xrd_rietveld_manager.layers_manager import LayersManagerMixin
from xrd_rietveld_manager.tool_actions import ToolActionsMixin
from xrd_rietveld_manager.export_tools import ExportToolsMixin
from xrd_rietveld_manager.plotter import PlotterMixin
from xrd_rietveld_manager.events import EventsMixin
from xrd_rietveld_manager.studio_manager import StudioManagerMixin
from xrd_rietveld_manager.color_director import ColorDirectorMixin
from xrd_rietveld_manager.figure_set_manager import FigureSetManagerMixin
from xrd_rietveld_manager.reference_peaks import ReferencePeaksMixin
from xrd_rietveld_manager.ui_theme import LABXACE2_UI_THEME, apply_labxace_theme


class XRDVisualizerPro(
    UiRuntimeMixin,
    UiTabsMixin,
    PhaseManagerMixin,
    FileManagerMixin,
    TemplateManagerMixin,
    StyleControlsMixin,
    LayersManagerMixin,
    ToolActionsMixin,
    ExportToolsMixin,
    StudioManagerMixin,
    ColorDirectorMixin,
    FigureSetManagerMixin,
    ReferencePeaksMixin,
    PlotterMixin,
    EventsMixin,
):
    @staticmethod
    def _window_size_for_workarea(work_width, work_height):
        """Return a usable startup client size for the current monitor."""
        work_width = max(1, int(work_width))
        work_height = max(1, int(work_height))
        # Leave room for native window borders/title bar.  On smaller screens
        # the canvas then receives a real resize event instead of extending
        # below the taskbar or outside the monitor.
        width = min(1400, max(760, work_width - 32), work_width)
        height = min(900, max(560, work_height - 72), work_height)
        return width, height

    def _configure_initial_window_geometry(self):
        try:
            pointer_x, pointer_y = self.root.winfo_pointerxy()
            left, top, right, bottom = monitor_workarea_for_point(
                pointer_x,
                pointer_y,
                fallback_widget=self.root,
            )
            work_width = max(1, int(right) - int(left))
            work_height = max(1, int(bottom) - int(top))
            width, height = self._window_size_for_workarea(work_width, work_height)
            x = int(left) + max(0, (work_width - width) // 2)
            y = int(top) + max(0, (work_height - height) // 2)
            self.root.geometry(f"{width}x{height}{x:+d}{y:+d}")
            self.root.minsize(min(760, width), min(560, height))
        except Exception:
            self.root.geometry("1200x760")

    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self._configure_initial_window_geometry()
        
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.ui_theme = LABXACE2_UI_THEME
        self.ui_bg = self.ui_theme["bg"]
        self.ui_panel = self.ui_theme["panel"]
        self.ui_surface = self.ui_theme["surface"]
        self.ui_canvas_bg = self.ui_theme["canvas_bg"]
        self.ui_text = self.ui_theme["text"]
        self.ui_muted = self.ui_theme["muted"]
        self.ui_border = self.ui_theme["border"]
        self.ui_accent = self.ui_theme["accent"]
        self.ui_accent_alt = self.ui_theme["accent_alt"]
        self.ui_accent_deep = self.ui_theme["accent_deep"]
        self.ui_accent_soft = self.ui_theme["accent_soft"]
        self.ui_danger = self.ui_theme["danger"]
        self.ui_button_dark = self.ui_theme["button_dark"]
        self.ui_button_mid = self.ui_theme["button_mid"]
        self.ui_button_light = self.ui_theme["button_light"]
        self.root.configure(bg=self.ui_bg)
        apply_labxace_theme(self.root, self.style, self.ui_theme)
        
        # Data & State
        self.loaded_files = {}
        self.crosshair_enabled = False
        self.bg_sub_enabled = False
        self.is_3d_mode = False
        self.custom_xlim = None
        self.custom_ylim = None
        self.y_autoscale_to_x_range = True
        self.y_autoscale_padding_percent = 8.0
        self.normalize_y_in_x_range = True
        self.var_3d = tk.BooleanVar(master=self.root, value=False)
        self.var_show_legend = tk.BooleanVar(master=self.root, value=True)
        self.var_merge_legend = tk.BooleanVar(master=self.root, value=True)
        self.var_show_residual = tk.BooleanVar(master=self.root, value=True)
        
        # Scales & Ratios
        self.intensity_scale = 1.0
        self.depth_scale = 1.0
        self.residual_ratio = 1.0 
        
        # 2D plot defaults
        self.show_grid_x = False
        self.show_grid_y = False
        self.legend_transparent = True
        self.legend_font_size = 10
        self.legend_bold = False
        self.legend_orientation = "vertical"
        self.legend_column_mode = "auto"
        self.legend_ncol = 2
        self.legend_max_width_ratio = 0.75
        self.legend_location = "auto"
        self.show_phase_peaks_top = True
        self.show_phase_display_labels = False
        self.phase_display_label_position = "right"
        self.phase_display_label_size = 10
        self.phase_display_label_bold = True
        self.phase_label_vertical_shift = 0.0
        self.tick_direction_2d = "in"
        self.tick_length_2d = 10.0
        self.minor_tick_length_2d = 5.0
        self.tick_width_2d = 1.0
        self.tick_label_size = 20
        self.tick_label_bold = False
        self.tick_label_font = "Use Plot Font"
        self.tick_label_color = "#000000"
        self.tick_label_x_rotation = 0.0
        self.tick_label_y_rotation = 0.0
        self.max_x_tick_labels = 6
        self.max_y_tick_labels = 6
        self.show_axis_title_x_2d = True
        self.show_axis_title_y_2d = True
        self.axis_label_bold = False
        self.axis_label_font = "Use Plot Font"
        self.axis_label_color = "#000000"
        self.axis_label_x_pad = 6.0
        self.axis_label_y_pad = 10.0
        self.axis_label_y_coord = -0.075
        self.residual_scale = 1.0
        self.residual_label_color = "#1f77b4"
        self.show_tick_label_x_2d = True
        self.show_tick_label_y_2d = True
        self.show_tick_x_2d = True
        self.show_tick_y_2d = True
        self.show_minor_tick_x_2d = True
        self.show_minor_tick_y_2d = True
        self.plot_box_linewidth = 1.0
        self.fixed_plot_box_enabled = False
        self.plot_box_width_cm = 12.0
        self.plot_box_height_cm = 8.0
        self.plot_bg_enabled = False
        self.plot_bg_mode = "solid"
        self.plot_bg_color = "#FFFFFF"
        self.plot_bg_grad_start = "#FFFFFF"
        self.plot_bg_grad_end = "#DDEEFF"
        self.plot_bg_direction = "vertical"
        self.plot_bg_alpha = 1.0
        self.plot_aspect_ratio = "Auto"
        self.custom_plot_aspect_ratio = "1:2"
        self.plot_layout_mode = "combined"
        self.panel_canvas_mode = "fit"
        self.plot_title_text = ""
        self.plot_title_bold = False
        self.plot_title_drag_enabled = True
        self.plot_title_pos = [0.02, 0.98]
        self.zoom_panels_enabled = False
        self.zoom_panel_ranges = "10,11; 32,35"
        self.zoom_panel_width = 1.0
        self.zoom_panel_gap = 0.12
        self.zoom_highlight_ranges = True
        self.plot_top_space = 0.0
        self.plot_memos_enabled = False
        self.plot_memos = []
        self.plot_memo_default_font = "Use Plot Font"
        self.plot_memo_default_size = 11
        self.plot_memo_default_bold = False
        self.plot_memo_default_color = "#111827"
        self.show_sample_labels = False
        self.sample_label_position = "right"
        self.sample_label_size = 10
        self.sample_label_bold = True
        self.sample_label_vertical_shift = 0.0
        self.show_split_panel_titles = True
        self.split_arrangement = "horizontal"
        self.split_panel_title_source = "observed"
        self.split_panel_title_size = 10
        self.split_main_title_overrides = {}
        self.split_diff_title_overrides = {}
        self.split_main_title_size_overrides = {}
        self.split_diff_title_size_overrides = {}
        self.phase_name_overrides = {}
        self.phase_color_overrides = {}
        self.art_effects_enabled = False
        self.art_line_effect = "none"
        self.art_text_halo = True
        self.art_marker_depth = False
        self.art_label_adjust = False
        self.art_palette_name = "Journal Muted"
        self.color_strategy = "Hybrid Recommended"
        self.file_color_palette = "LAB×ACE² Thermal Gradient"
        self.phase_color_palette = "Editorial Ink"
        self.reverse_file_palette = False
        self.reverse_phase_palette = False
        self.lock_same_phase_colors = True
        self.preserve_manual_colors = False
        self._init_reference_peaks()
        self._init_figure_set_state()

        # Shared Tk variables must exist before any tab is built.
        # The previous single-file UI relied on tab creation order; the modular
        # layout intentionally removes that hidden dependency.
        self.var_title_size = tk.IntVar(master=self.root, value=12)
        self.var_axis_size = tk.IntVar(master=self.root, value=20)
        self.var_resid_size = tk.IntVar(master=self.root, value=10)

        # Plot Objects
        self.vlines = []; self.hlines = []; self.plot_axes = []
        self.title_artist = None
        self.title_axis = None
        self.is_dragging_title = False
        self.plot_memo_artists = []
        self.zoom_panel_axes = []
        self.is_dragging_memo = False
        self.plot_memo_drag_index = None
        self.plot_memo_drag_offset = (0.0, 0.0)
        self.layer_drag_state = None
        self._is_redrawing = False
        self._resize_after_id = None
        self._draw_after_id = None
        self._left_panel_after_id = None
        self._resize_pending_size = None
        self._last_resize_size = None
        self.left_panel_width = 350
        self.inspector_panel_width = 390
        
        # UI Font Config
        self.plot_font_display = ACTIVE_PLOT_FONT_DISPLAY
        self.plot_font_family = ACTIVE_PLOT_FONT_FAMILY
        self.plot_base_weight = ACTIVE_PLOT_BASE_WEIGHT
        self.plot_font_path = ACTIVE_PLOT_FONT_PATH
        self.ui_font_family = "Calibri"
        self.ui_font = (self.ui_font_family, 10)
        self.ui_font_bold = (self.ui_font_family, 10, "bold")
        self.ui_font_title = (self.ui_font_family, 12, "bold")
        self.paper_style = PaperStyleEngine(self)
        self.art_engine = PlotArtEngine(self)
        
        self._create_ui()


def main():
    root = tk.Tk()
    app = XRDVisualizerPro(root)
    root.mainloop()
    return app


if __name__ == "__main__":
    main()
