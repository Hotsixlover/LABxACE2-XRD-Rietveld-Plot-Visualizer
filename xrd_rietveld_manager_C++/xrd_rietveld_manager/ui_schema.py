# SPDX-License-Identifier: GPL-2.0-or-later
"""UI inventory for LAB×ACE²-XRD Rietveld Plot Visualizer.

This file is intentionally declarative. It gives the program one clear map of
where each control concept belongs, so future UI work can move controls without
changing plotting behavior.
"""

FONT_SIZE_MAX = 72
EXTENDED_FONT_SIZE_MAX = 96

UI_GROUPS = [
    {
        "id": "data",
        "label": "Data",
        "purpose": "Load files, manage project labels, templates, and raw exports.",
        "controls": [
            "load_data", "remove_file", "check_all", "uncheck_all", "file_order",
            "template_save", "template_load", "xy_export",
        ],
    },
    {
        "id": "layers",
        "label": "Layers",
        "purpose": "Show/hide and edit Observed, Calculated, Difference, and phase traces.",
        "controls": [
            "layer_visibility", "layer_name", "layer_color", "layer_style",
            "layer_offset", "phase_auto_stack", "same_phase_color",
        ],
    },
    {
        "id": "layout",
        "label": "Layout",
        "purpose": "Choose combined/split/3D views and panel geometry.",
        "controls": [
            "plot_mode", "split_mode", "split_arrangement", "plot_ratio",
            "panel_titles", "top_phase_peaks", "residual_panel_height",
        ],
    },
    {
        "id": "style",
        "label": "Style",
        "purpose": "Publication style: fonts, ticks, box, grid, title, legend, background.",
        "controls": [
            "font_family", "title_size", "axis_label_size", "tick_label_size",
            "legend_size", "tick_direction", "tick_length", "tick_width", "grid", "plot_box", "legend_layout",
            "background",
        ],
    },
    {
        "id": "art",
        "label": "Art",
        "purpose": "Optional visual art effects for presentation-quality figures.",
        "controls": [
            "line_shadow", "line_glow", "text_halo", "marker_depth",
            "auto_label_adjust", "art_palette",
        ],
    },
    {
        "id": "export",
        "label": "Export",
        "purpose": "Final output for papers, slides, and Illustrator/Inkscape.",
        "controls": [
            "save_image", "vector_export", "copy_clipboard", "transparent_background",
        ],
    },
]

CONTROL_LOCATIONS = {
    "show_legend": "Style > Legend",
    "merge_legend": "Style > Legend",
    "legend_transparent": "Style > Legend",
    "legend_font_size": "Style > Legend",
    "legend_orientation": "Style > Legend",
    "plot_layout": "Layout > Arrangement",
    "plot_aspect_ratio": "Layout > Ratio",
    "show_split_panel_titles": "Layout > Panel Titles",
    "plot_title_text": "Style > Title",
    "plot_title_size": "Style > Title",
    "plot_bg_enabled": "Style > Background",
    "grid_x": "Style > Grid",
    "grid_y": "Style > Grid",
    "tick_direction_2d": "Style > Ticks",
    "tick_length_2d": "Style > Ticks",
    "tick_width_2d": "Style > Ticks",
    "tick_label_size": "Style > Ticks",
    "axis_label_size": "Style > Axis Labels",
    "residual_ratio": "Layout > Residual",
    "residual_scale": "Layout > Residual",
    "art_effects_enabled": "Art > Effects",
    "art_palette_name": "Art > Palette",
}
