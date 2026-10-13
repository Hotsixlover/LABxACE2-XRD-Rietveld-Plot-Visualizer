# SPDX-License-Identifier: GPL-2.0-or-later
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class FigureSetItem:
    item_id: str
    label: str
    x_cm: float = 1.0
    y_cm: float = 1.0
    width_cm: float = 6.0
    height_cm: float = 4.0
    recipe: Dict = field(default_factory=dict)
    thumbnail_data: Optional[str] = None
    keep_font_fixed: bool = True
    fit_mode: str = "contain"
    crop_left_pct: float = 0.0
    crop_right_pct: float = 0.0
    crop_top_pct: float = 0.0
    crop_bottom_pct: float = 0.0
    subplot_label: str = ""
    subplot_label_visible: bool = True
    subplot_label_size_pt: int = 10
    subplot_label_bold: bool = True
    subplot_label_x_cm: float = 0.10
    subplot_label_y_cm: float = 0.10
    subplot_label_color: str = "#111827"


@dataclass
class FigureSetPage:
    preset_name: str = "Custom"
    width_cm: float = 17.8
    height_cm: float = 12.0
    unit: str = "cm"
    zoom_percent: int = 100
    export_dpi: int = 600
    transparent_background: bool = False
    panel_transparent_background: bool = True
    panel_render_scale: float = 1.0
    export_tight_bbox: bool = False
    export_padding_cm: float = 0.0
    export_metadata_enabled: bool = True
    export_set_copy_enabled: bool = True
    show_item_borders: bool = False
    show_grid: bool = True
    grid_step_cm: float = 0.5
    show_guides: bool = True
    show_margin_guides: bool = True
    margin_guide_cm: float = 0.5
    manual_guides_x_cm: List[float] = field(default_factory=list)
    manual_guides_y_cm: List[float] = field(default_factory=list)
    snap_enabled: bool = True
    master_typography_enabled: bool = True
    master_font_display: str = "Current Plot Font"
    master_title_size: int = 12
    master_axis_size: int = 10
    master_tick_size: int = 10
    master_legend_size: int = 10
    master_residual_size: int = 10
    master_memo_size: int = 10
    master_reference_size: int = 8
    items: List[FigureSetItem] = field(default_factory=list)
