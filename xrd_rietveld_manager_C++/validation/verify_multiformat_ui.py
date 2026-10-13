# SPDX-License-Identifier: GPL-2.0-or-later
"""Exercise the actual Tk application with synthetic, mixed-format profiles."""
from pathlib import Path
import sys
import tempfile
import tkinter as tk
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from xrd_rietveld_manager.app_v014 import XRDVisualizerPro
from xrd_rietveld_manager import file_manager, export_tools


def main():
    root = tk.Tk()
    root.withdraw()
    callback_errors = []
    root.report_callback_exception = lambda *args: callback_errors.append(args)
    try:
        app = XRDVisualizerPro(root)
        root.update()
        fixture_dir = ROOT / 'tests' / 'fixtures'
        names = ['profex_profile.dia', 'gsas_ii_profile.csv', 'gsas_liveplot.csv', 'fullprof_profile.prf']
        paths = [str(fixture_dir / name) for name in names]
        with tempfile.TemporaryDirectory() as tmp:
            missing_background = Path(tmp) / 'no_background.csv'
            missing_background.write_text('x,y_obs,y_calc\n10,20,18\n11,40,35\n12,10,9', encoding='utf-8')
            invalid = Path(tmp) / 'invalid.csv'
            invalid.write_text('not a profile', encoding='utf-8')
            selected = paths + [str(missing_background), str(invalid)]
            with patch.object(file_manager.filedialog, 'askopenfilenames', return_value=selected), \
                 patch.object(file_manager.messagebox, 'showwarning') as warning:
                app.load_new_file()
                warning.assert_called_once()
                assert 'invalid.csv' in warning.call_args.args[1]
            assert len(app.loaded_files) == 5
            assert len(app.file_tree.get_children()) == 5
            root.update()
            for mode in ('combined', 'split'):
                app.var_plot_layout.set(mode)
                for subtract in (False, True):
                    app.bg_sub_enabled = subtract
                    app.draw_plot()
                    assert len(app.fig.axes) >= 1
                    assert any(ax.lines or ax.collections for ax in app.fig.axes)
                    print('Rendered', mode, 'background subtraction:', subtract)
            app.var_3d.set(True)
            app.draw_plot()
            assert app.fig.axes[0].name == '3d'
            print('Rendered 3D')
            app.var_3d.set(False)
            app.bg_sub_enabled = False
            app.var_plot_layout.set('split')
            app.draw_plot()
            # Reapplying a template must not introduce a missing background layer.
            app._apply_template_data(app._collect_template_data())
            loader = app.loaded_files[str(missing_background)]
            assert 'Background' not in app._get_loader_layer_order(loader)
            output = Path(tmp) / 'export.csv'
            with patch.object(export_tools.filedialog, 'asksaveasfilename', return_value=str(output)), \
                 patch.object(export_tools.messagebox, 'showinfo'):
                app.export_xy_data(str(missing_background))
            assert output.read_text(encoding='utf-8').startswith('2Theta,Intensity_Normalized')
            app.fig.savefig(ROOT / 'validation' / 'mixed_profiles_smoke.png', dpi=110)
            root.update()
            assert not callback_errors, callback_errors
            print('PASS: mixed import, invalid-file handling, layers, 2D/3D, template and XY export')
    finally:
        root.destroy()


if __name__ == '__main__':
    main()
