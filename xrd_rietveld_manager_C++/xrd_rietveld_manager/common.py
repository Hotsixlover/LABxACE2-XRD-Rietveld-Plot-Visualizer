# SPDX-License-Identifier: GPL-2.0-or-later
import csv
import ctypes
import json
import math
import os
import platform
import re
import struct
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, Menu, simpledialog

from xrd_rietveld_manager.popup_utils import (
    enable_per_monitor_dpi_awareness,
    install_parented_native_dialogs,
    monitor_workarea_for_point,
    place_window_on_parent_monitor,
)

enable_per_monitor_dpi_awareness()
install_parented_native_dialogs(messagebox, filedialog, simpledialog)

import numpy as np
from matplotlib.gridspec import GridSpec, GridSpecFromSubplotSpec
from matplotlib.colors import LinearSegmentedColormap

from xrd_rietveld_manager.art_engine import PlotArtEngine
from xrd_rietveld_manager.chemical_formula import (
    format_chemical_formula_mathtext,
    generate_formula_color,
)
from xrd_rietveld_manager.color_picker import choose_color
from xrd_rietveld_manager.data_loader import DataLoader
from xrd_rietveld_manager.dialogs import (
    ScrollableFrame,
    RichLabelEditDialog,
    StyleDialog,
    SplitTitlesDialog,
)
from xrd_rietveld_manager.palettes import available_palette_names, get_palette_colors
from xrd_rietveld_manager.style_engine import PaperStyleEngine
from xrd_rietveld_manager.style_utils import (
    ACTIVE_PLOT_FONT_DISPLAY,
    ACTIVE_PLOT_FONT_FAMILY,
    ACTIVE_PLOT_BASE_WEIGHT,
    ACTIVE_PLOT_FONT_PATH,
    available_plot_fonts,
    get_font_spec,
)
