# SPDX-License-Identifier: GPL-2.0-or-later
"""Launch LAB×ACE²-XRD Rietveld Plot Visualizer."""

import sys
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parent / "xrd_rietveld_manager_C++"
sys.path.insert(0, str(SOURCE_ROOT))

from xrd_rietveld_manager.app_v014 import main


if __name__ == "__main__":
    main()
