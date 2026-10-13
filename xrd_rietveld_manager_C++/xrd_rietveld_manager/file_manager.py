# SPDX-License-Identifier: GPL-2.0-or-later
from xrd_rietveld_manager.common import *
from xrd_rietveld_manager.profile_parsers import PROFILE_FILE_TYPES


# Compact transparent eye icons used by the Project Files tree.  Keeping the
# PNG data embedded makes the UI portable without a separate asset directory.
_FILE_VISIBLE_EYE_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAABIAAAASCAYAAABWzo5XAAACwElEQVR4nM1TO4hUSRQ9tz7vve5+3a2NjkZGi4GB7KLowA688QcamKg9G4iBuIjJbqLRjFrTIuMvEEEEQUFBA7sRjQXtadDdEQXRQMFNRANhdWd6+uObfp+6G7iz+GkmMvCEt+qeOnXvOcD3BupXLJdZ/r0KNAzYT+uTgBh4Dq7VKF2Q1RgWYO5L/hmYqVxm2VdRucqyNvLxpY0no3XE6U6Ahmya9AhgksoD6A8wVe+OOo8+Kq/KWm0k/Z8oMKwaFUqC450fteud0a7cDAHMNTvTUrkloTXisDPtZP2ScIC4E03aXnTsnsnX5wXQPOvweHO34/uXQNJLot5VpMkNFjwshbufOfGJxE2bxhdBYhuR+E3nPG9utv3r5JHC5XKVJQGgTZXmWulnHzDjbTQX/tI4XJwaPt7+PVPwz/XaXWZm6xV8OTfbvVU/4u8ITneWK6tue0V3fedda2/jaPEKbTnDuSTqPlGuzoXt7rb7ldKzoRPNxY5VL0nqEicRQCQAJNLJqTgKhybHsg8GzeuSnxu4TUIMJh96P4m2gCVAcZq+T1qdvwAAVigwXLaW5+fIbEEEEFEOAKYqK6ZtFL9SjtYgWxRTBylkxriTz6z2lw/UB02zdH+s8I7BVa/oSSYws7Wun1dxr/uiPpq5s2b/Y71x4sOF3DJ/TzjbOl8/XPjzk2G39mWX5C/1utEbm1qTJvGU1nocJLaDUy2U8ziNwqNCOkstpyZbyqwM/+levDvqHzCGxX/rr6tGZUMSHGvt0p53ws3rH8KZbsKpbZCUP5NQno17D4nEquySXD6cjVucJKfujWUnjGFRGQd/ZcjA1JXOrB9hyN3gdLNNbQiwFUL6IHpKJK/HSl9rHKL3YCYQ8VfOL1c/t31g2A/O8qLAzCzaeo4LC93tFyQKTF0Zw6L/Gat+eVw4oF829PvGt8a/3jZTdhrelBkAAAAASUVORK5CYII="
)
_FILE_HIDDEN_EYE_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAABIAAAASCAYAAABWzo5XAAADqElEQVR4nJWU70+TVxTHz7nPU9pSkIh9yo8q6IybYzNgtuhGluwNyX4Fl2geNLAIWxhhiaaoJRRLvX2AINgYXmxzYYyVVgpZ67DF8gf4YtmvF8vMsuhkMco2J1B+FKgr7fOcvRglLnNk+745N+fcc/PNufdzAf6niIhl1pxzttnezQ4R1+NBIqp9NCc+rkGWZaGsrAwBQMvk3G43Q8Q0EZUDwFhgLLTr1erDOYj48T+ccc4ZEeEmjiqIaGpo+HLqjTdlrcXeTnenp5uIiG04koNBQampURVFge7eiwc0giME8BJDTMZXlvGZvXuTALDT6xvZFZ6IQmFhgXqm5YS43Vr8VCgUQnHdiajU1KR594WKLH2Wx2A0ViEirMTj88m1VP6e3buh7tiRFa8/IF6diKLFYkl1cWeiqLCgHxE7iYgxWQ4KiqKkne6eOoPR8KUgiFWrqyu+RGL19cWl5aEd262xdxvqfh0JfKaFJ6IGiySpisuRmp2LbWk8ceruxvwAAF09nudNBsMXmkb3k38kjiodjq9O2s+2PLe/or++Vv7N6wvkRa5NmiTJnHa1t7KSkh2e1g7lhdLSnS/PPvj9nU6Xw4tnPB5TTgq+0+v1puX48mvnFecNADB9NDj8U3Njfdbw5YA+HJnMNUvmtNLhSFqtxYOIeKqtrTdvi9kYRYYHE6uJ/UxjTAMgUU2n516sfmUKAGB6evrZ5sZ65vWNGq9GJnMlyaz1dp17MDe/aDja0HgFEaGvz7G0tpa8o9frdQKKeX9d+/kLxz8YHKY2V+fXt279XEVEN72+kbVDh49RY/NJbWZm9v6NH34ku9N9EwCgaWBA19l78dKHn/jpXFff+0SEKMuyEAqF1Pds9uMV5eUDTW+/lfD6A6ZwJKq3SGatp5vPxBYWRf9o8I6oE5wGnUFSNY1vzc9/cj42N8Db7c2cc4ZExBBRI6I9ADA57A9YxyPR7AKLpHa5nUuzsYWssdB4jk6n+4Yhe3qbeVvu0uJCXE1pfdxp7+GcM7fbTbj+kg8AwOinvpHS8ESUFVgkze06+3A18TA25AvkZRuNxBjmAOD3TGCBFFNHFLt9jogQESnDGgOAluCV8BOfj0dSRcVFWkd7q2gtLrpUXVvrqaysJGM6R2UsrtlstniGhGAwKCCi+je+mppOm2vqGr61nW6je/d+SRGR519wQ865+FgeM+SW7Nu39fbtqetE1L8OqLBeQ6KNEWyuzGdFRNkAwP5z4yP6Ewz6vmYAnhEHAAAAAElFTkSuQmCC"
)


class FileManagerMixin:
    def _initialize_file_visibility_icons(self):
        if hasattr(self, "file_visibility_images"):
            return
        self.file_visibility_images = {
            True: tk.PhotoImage(master=self.root, data=_FILE_VISIBLE_EYE_PNG_B64, format="png"),
            False: tk.PhotoImage(master=self.root, data=_FILE_HIDDEN_EYE_PNG_B64, format="png"),
        }

    def _file_visibility_image(self, visible):
        self._initialize_file_visibility_icons()
        return self.file_visibility_images[bool(visible)]

    def _refresh_file_tree_visibility_item(self, item, loader):
        self.file_tree.item(
            item,
            text=f"  {self._get_sample_display_name(loader)}",
            image=self._file_visibility_image(loader.global_visible),
        )

    def _project_file_ids(self):
        """Return the canonical project order shown in the Project tree."""
        ordered = []
        if hasattr(self, "file_tree"):
            try:
                ordered = [iid for iid in self.file_tree.get_children("") if iid in self.loaded_files]
            except Exception:
                ordered = []
        ordered.extend([path for path in self.loaded_files.keys() if path not in ordered])
        return ordered

    def _ordered_loaders(self, visible_only=False):
        for path in self._project_file_ids():
            loader = self.loaded_files.get(path)
            if loader is None:
                continue
            if visible_only and not loader.global_visible:
                continue
            yield path, loader

    def _sync_loaded_files_to_project_order(self):
        """Keep dict iteration order aligned with the Project tree.

        Plotting already uses the tree directly, but other managers sometimes
        iterate loaded_files. Reordering the dict removes that hidden split.
        """
        self.loaded_files = {path: self.loaded_files[path] for path in self._project_file_ids() if path in self.loaded_files}

    def _refresh_after_project_order_change(self):
        self._sync_loaded_files_to_project_order()
        self.rebuild_layer_controls()
        self.draw_plot()

    def load_new_file(self):
        filepaths = filedialog.askopenfilenames(filetypes=PROFILE_FILE_TYPES)
        if not filepaths: return
	        
        errors = []
        for filepath in filepaths:
            if filepath in self.loaded_files: continue
            
            loader = DataLoader(filepath)
            try:
                loader.load()
            except (ValueError, OSError) as exc:
                errors.append(f"{os.path.basename(filepath)}: {exc}")
                continue
            self._apply_phase_name_overrides_to_loader(loader)
            self._apply_phase_color_overrides_to_loader(loader)
            self.loaded_files[filepath] = loader
            self.file_tree.insert(
                "", "end", iid=filepath,
                text=f"  {self._get_sample_display_name(loader)}",
                image=self._file_visibility_image(loader.global_visible),
            )
	            
        if self._phase_color_link_enabled():
            self.sync_phase_colors_by_name(redraw=False, rebuild=False)
        self._sync_loaded_files_to_project_order()
        self.rebuild_layer_controls()
        self.draw_plot()
        if errors:
            messagebox.showwarning("Profile import", "Some files could not be loaded:\n\n" + "\n\n".join(errors))

    def remove_selected_file(self):
        sel = self.file_tree.selection()
        if not sel: return
        path = sel[0]
        if path in self.loaded_files:
            del self.loaded_files[path]
            self.split_main_title_overrides.pop(path, None)
            self.split_diff_title_overrides.pop(path, None)
            self.split_main_title_size_overrides.pop(path, None)
            self.split_diff_title_size_overrides.pop(path, None)
            self.file_tree.delete(path)
            self.rebuild_layer_controls()
            self.draw_plot()

    def set_all_visibility(self, visible):
        for iid in self.file_tree.get_children():
            path = iid
            if path in self.loaded_files:
                loader = self.loaded_files[path]
                loader.global_visible = visible
                self._refresh_file_tree_visibility_item(iid, loader)
        self.rebuild_layer_controls()
        self.draw_plot()

    def move_file_up(self):
        rows = self.file_tree.selection()
        moved = False
        for row in rows:
            i = self.file_tree.index(row)
            if i > 0:
                self.file_tree.move(row, self.file_tree.parent(row), i-1)
                moved = True
        if moved:
            self.file_tree.selection_set(*rows)
            self._refresh_after_project_order_change()

    def move_file_down(self):
        rows = self.file_tree.selection()
        moved = False
        for row in reversed(rows):
            i = self.file_tree.index(row)
            if i < len(self.file_tree.get_children()) - 1:
                self.file_tree.move(row, self.file_tree.parent(row), i+1)
                moved = True
        if moved:
            self.file_tree.selection_set(*rows)
            self._refresh_after_project_order_change()

    def on_file_click(self, event):
        item = self.file_tree.identify_row(event.y)
        if not item: return
        
        clicked_element = self.file_tree.identify_element(event.x, event.y)
        clicked_visibility_icon = (
            "image" in str(clicked_element).lower()
            or event.x < 36
        )

        if clicked_visibility_icon:
            path = item
            if path in self.loaded_files:
                l = self.loaded_files[path]
                l.global_visible = not l.global_visible
                self._refresh_file_tree_visibility_item(item, l)
                self.rebuild_layer_controls()
                self.draw_plot()

    def on_file_right_click(self, event):
        item = self.file_tree.identify_row(event.y)
        if not item: return
        self.file_tree.selection_set(item)
        path = item
        
        menu = Menu(self.root, tearoff=0)
        menu.add_command(label="Calculate Lattice (Cubic)", command=lambda: self.calc_lattice(path))
        menu.add_command(label="Export XY Data", command=lambda: self.export_xy_data(path))
        menu.add_separator()
        menu.add_command(label="Remove", command=self.remove_selected_file)
        menu.post(event.x_root, event.y_root)

    def calc_lattice(self, path):
        loader = self.loaded_files[path]
        if not loader.obs: return
        x_data = getattr(loader, "x_np", np.asarray(loader.x, dtype=float))
        y_data = getattr(loader, "obs_np", np.asarray(loader.obs, dtype=float))
        max_idx = np.argmax(y_data)
        peak = x_data[max_idx]
        
        hkl = simpledialog.askstring("Lattice", f"Max Peak: {peak:.2f} deg\nEnter h k l (e.g., 1 1 1):")
        if hkl:
            try:
                h, k, l = map(int, hkl.split())
                lam = 1.5406
                rad = math.radians(peak / 2)
                d = lam / (2 * math.sin(rad))
                a = d * math.sqrt(h**2 + k**2 + l**2)
                self.file_tree.insert(path, "end", text=f"a = {a:.4f} A")
                self.file_tree.item(path, open=True)
            except ValueError:
                messagebox.showerror("Error", "Invalid Input")

