# SPDX-License-Identifier: GPL-2.0-or-later
from xrd_rietveld_manager.common import *
from xrd_rietveld_manager.ui2_widgets import (
    ModernScale,
    build_antialiased_color_dot,
    build_ui2_indicator_images,
)
from xrd_rietveld_manager.popup_utils import move_toplevel_to_pointer


class LayersManagerMixin:
    def _get_loader_layer_order(self, loader):
        valid = ["Observed", "Calculated", "Background", "Difference"] + list(loader.phase_names)
        available = getattr(loader, "available_layers", None)
        if available is not None:
            valid = [key for key in valid if key in available]
        valid_set = set(valid)
        ordered, seen = [], set()
        for key in list(getattr(loader, "layer_order", []) or []):
            if key in valid_set and key not in seen:
                ordered.append(key)
                seen.add(key)
        for key in valid:
            if key not in seen:
                ordered.append(key)
                seen.add(key)
        loader.layer_order = ordered
        return ordered

    def _get_loader_phase_order(self, loader, visible_only=False):
        phase_set = set(loader.phase_names)
        ordered = [key for key in self._get_loader_layer_order(loader) if key in phase_set]
        if visible_only:
            ordered = [key for key in ordered if loader.visibility.get(key, True)]
        return ordered

    def _get_global_phase_order(self, loaders, visible_only=True):
        ordered, seen = [], set()
        for loader in loaders:
            for phase in self._get_loader_phase_order(loader, visible_only=visible_only):
                if phase not in seen:
                    ordered.append(phase)
                    seen.add(phase)
        return ordered

    def _sync_offsets_to_layer_order(self, loader, previous_order):
        previous = [key for key in previous_order if key != "Difference" and key in loader.offsets]
        current = [key for key in self._get_loader_layer_order(loader) if key != "Difference" and key in loader.offsets]
        if not previous or not current:
            return
        slots = sorted((float(loader.offsets.get(key, 0.0)) for key in previous), reverse=True)
        if len(slots) < len(current):
            slots.extend([slots[-1]] * (len(current) - len(slots)))
        for key, value in zip(current, slots):
            loader.offsets[key] = value

    def _find_layer_drag_row(self, widget):
        current = widget
        while current is not None:
            if hasattr(current, "_xrd_layer_drag_key"):
                return current
            try:
                current = current.master
            except Exception:
                return None
        return None

    def _create_layer_drag_ghost(self, state, event):
        row, loader, key = state["row"], state["loader"], state["key"]
        row.update_idletasks()
        width = max(220, min(520, row.winfo_width()))
        height = max(34, row.winfo_height() + 8)
        ghost = tk.Toplevel(self.root)
        ghost.withdraw()
        ghost.overrideredirect(True)
        ghost.configure(bg="#4285f4")
        try:
            ghost.transient(self.root)
            ghost.attributes("-alpha", 0.94)
            ghost.attributes("-topmost", True)
        except Exception:
            pass
        body = tk.Frame(ghost, bg="#ffffff", highlightbackground="#a8c7fa", highlightthickness=1)
        body.pack(fill="both", expand=True, padx=2, pady=2)
        dot = tk.Canvas(body, width=16, height=16, bg="#ffffff", highlightthickness=0, bd=0)
        color = loader.styles.get(key, {}).get("color", "#5f6368")
        dot_image = build_antialiased_color_dot(dot, color, size=12)
        if dot_image is not None:
            dot._ui2_color_dot_image = dot_image
            dot.create_image(8, 8, image=dot_image)
        else:
            dot.create_oval(3, 3, 13, 13, fill=color, outline=color)
        dot.pack(side="left", padx=(7, 5))
        name = loader.display_names.get(key, key)
        tk.Label(
            body, text=self._truncate_label(name, max_chars=34), bg="#ffffff", fg="#202124",
            font=("Arial", 10, "bold"), anchor="w"
        ).pack(side="left", fill="x", expand=True, padx=(0, 8))
        state.update(ghost=ghost, ghost_width=width, ghost_height=height)
        self._move_layer_drag_ghost(state, event)
        ghost.deiconify()
        ghost.lift()

    def _move_layer_drag_ghost(self, state, event):
        ghost = state.get("ghost")
        if ghost is None or not ghost.winfo_exists():
            return
        width = int(state.get("ghost_width", 320))
        height = int(state.get("ghost_height", 42))
        native_position = move_toplevel_to_pointer(
            ghost,
            width,
            height,
            fallback_widget=self.root,
        )
        if native_position is not None:
            ghost.deiconify()
            ghost.lift()
            return
        x, y = int(event.x_root + 14), int(event.y_root - height / 2)
        left, top, right, bottom = monitor_workarea_for_point(event.x_root, event.y_root, self.root)
        x = max(left, min(right - width, x))
        y = max(top, min(bottom - height, y))
        ghost.geometry(f"{width}x{height}{x:+d}{y:+d}")
        ghost.deiconify()
        ghost.lift()

    def _clear_layer_drop_indicator(self, state):
        indicator = state.get("indicator")
        if indicator is not None:
            try:
                indicator.destroy()
            except Exception:
                pass
        state["indicator"] = None
        target = state.get("target_row")
        if target is not None:
            try:
                target.configure(bg=self.ui_surface, highlightthickness=0)
            except Exception:
                pass
        state["target_row"] = None

    def _show_layer_drop_indicator(self, state, target_row, insert_after):
        if state.get("target_row") is target_row and state.get("insert_after") == insert_after and state.get("indicator") is not None:
            return
        self._clear_layer_drop_indicator(state)
        try:
            parent = target_row.master
            parent.update_idletasks()
            target_row.update_idletasks()
            indicator = tk.Frame(parent, bg="#4285f4", height=3)
            y = target_row.winfo_y() + (target_row.winfo_height() - 1 if insert_after else 0)
            indicator.place(x=4, y=y, relwidth=1.0, width=-8, height=3)
            indicator.lift()
            target_row.configure(bg="#f3f7ff", highlightbackground="#a8c7fa", highlightthickness=1)
            state.update(indicator=indicator, target_row=target_row, insert_after=insert_after,
                         target_key=getattr(target_row, "_xrd_layer_drag_key", None))
        except Exception:
            self._clear_layer_drop_indicator(state)

    def _begin_layer_drag_visual(self, state, event):
        if state.get("drag_started"):
            return
        state["drag_started"] = True
        try:
            state["row"].configure(bg="#eef3fb", relief="sunken", bd=1,
                                   highlightbackground="#dadce0", highlightthickness=1)
            state["source_widget"].configure(cursor="fleur")
        except Exception:
            pass
        self._create_layer_drag_ghost(state, event)

    def _cleanup_layer_drag_visuals(self, state):
        self._clear_layer_drop_indicator(state)
        ghost = state.get("ghost")
        if ghost is not None:
            try:
                ghost.destroy()
            except Exception:
                pass
        try:
            state["row"].configure(bg=self.ui_surface, relief="flat", bd=0, highlightthickness=0)
            state["source_widget"].configure(cursor=state.get("original_cursor", ""))
        except Exception:
            pass

    def _start_layer_drag(self, event, loader, key, row, click_action=None):
        try:
            cursor = event.widget.cget("cursor")
        except Exception:
            cursor = ""
        self.layer_drag_state = {
            "loader": loader, "key": key, "row": row, "source_widget": event.widget,
            "original_cursor": cursor, "click_action": click_action,
            "start_root_x": event.x_root, "start_root_y": event.y_root,
            "drag_started": False, "target_row": None, "target_key": None,
            "insert_after": False, "indicator": None, "ghost": None,
        }
        return "break"

    def _move_layer_drag(self, event):
        state = self.layer_drag_state
        if not state:
            return "break"
        delta = max(abs(event.x_root - state["start_root_x"]), abs(event.y_root - state["start_root_y"]))
        if not state["drag_started"] and delta >= 7:
            self._begin_layer_drag_visual(state, event)
        if not state["drag_started"]:
            return "break"
        self._move_layer_drag_ghost(state, event)
        try:
            target = self._find_layer_drag_row(self.root.winfo_containing(event.x_root, event.y_root))
        except Exception:
            target = None
        if target is None or getattr(target, "_xrd_layer_drag_loader", None) is not state["loader"] or target is state["row"]:
            self._clear_layer_drop_indicator(state)
            return "break"
        insert_after = event.y_root > target.winfo_rooty() + target.winfo_height() / 2
        self._show_layer_drop_indicator(state, target, insert_after)
        return "break"

    def _finish_layer_drag(self, _event=None):
        state = self.layer_drag_state
        self.layer_drag_state = None
        if not state:
            return "break"
        if not state.get("drag_started"):
            click_action = state.get("click_action")
            self._cleanup_layer_drag_visuals(state)
            if click_action is not None:
                self.root.after_idle(click_action)
            return "break"
        loader = state["loader"]
        source, target = state["key"], state.get("target_key")
        insert_after = bool(state.get("insert_after"))
        self._cleanup_layer_drag_visuals(state)
        if target is None or target == source:
            return "break"
        previous = list(self._get_loader_layer_order(loader))
        new_order = list(previous)
        if source not in new_order or target not in new_order:
            return "break"
        new_order.remove(source)
        new_order.insert(new_order.index(target) + (1 if insert_after else 0), source)
        loader.layer_order = new_order
        self._sync_offsets_to_layer_order(loader, previous)
        loader.phase_auto_stack_order = self._get_loader_phase_order(loader)
        loader.phase_auto_stack_offsets = {
            key: float(loader.offsets.get(key, 0.0))
            for key in ["Observed", "Calculated", "Background"] + list(loader.phase_names)
        }
        self.rebuild_layer_controls()
        self.draw_plot()
        return "break"

    def rebuild_layer_controls(self):
        if not hasattr(self, "_ui2_indicator_images"):
            self._ui2_indicator_images = build_ui2_indicator_images(
                self.root,
                accent=self.ui_accent,
                border="#9AA0A6",
            )
        indicators = self._ui2_indicator_images
        for widget in self.layer_frame.winfo_children():
            widget.destroy()
        
        # Project tree order is the single source of truth:
        # Project = Layers = plot order.
        loader_iter = self._ordered_loaders(visible_only=True) if hasattr(self, "_ordered_loaders") else self.loaded_files.items()
        for path, loader in loader_iter:
            
            wrapper = tk.Frame(
                self.layer_frame,
                bg=self.ui_surface,
                highlightbackground=self.ui_border,
                highlightthickness=1,
                bd=0,
            )
            wrapper.pack(fill=tk.X, pady=(0, 6))

            header_bg = "#EAF2FF"
            hdr = tk.Frame(wrapper, bg=header_bg, height=30)
            hdr.pack(fill=tk.X)
            hdr.pack_propagate(False)
            content_frame = tk.Frame(wrapper, bg=self.ui_surface)
            
            def toggle(l=loader, btn=None, cf=content_frame):
                l.is_expanded = not l.is_expanded
                if l.is_expanded:
                    cf.pack(fill=tk.X)
                    btn.configure(text="▼")
                else:
                    cf.pack_forget()
                    btn.configure(text="▶")

            def toggle_whole_file(l=loader, var=None):
                value = bool(var.get())
                for layer_key in l.visibility:
                    l.visibility[layer_key] = value
                self.rebuild_layer_controls()
                self._request_draw_plot()

            btn_toggle = tk.Button(
                hdr,
                text="▼" if loader.is_expanded else "▶",
                bg=header_bg,
                fg=self.ui_accent,
                activebackground=header_bg,
                activeforeground=self.ui_accent_deep,
                relief=tk.FLAT,
                bd=0,
                width=2,
                font=("Calibri", 8, "bold"),
                cursor="hand2",
            )
            btn_toggle.configure(
                command=lambda l=loader, b=btn_toggle, c=content_frame: toggle(l, b, c)
            )
            btn_toggle.pack(side=tk.LEFT, padx=(2, 0))

            m_var = tk.BooleanVar(
                value=bool(loader.visibility) and all(loader.visibility.values())
            )
            chk_master = tk.Checkbutton(
                hdr,
                text=" All",
                variable=m_var,
                command=lambda l=loader, v=m_var: toggle_whole_file(l, v),
                bg=header_bg,
                fg=self.ui_text,
                activebackground=header_bg,
                activeforeground=self.ui_text,
                selectcolor=header_bg,
                font=self.ui_font_bold,
                cursor="hand2",
                bd=0,
                highlightthickness=0,
                padx=0,
                indicatoron=False,
                image=indicators["check_off"],
                selectimage=indicators["check_on"],
                compound=tk.LEFT,
                relief=tk.FLAT,
                offrelief=tk.FLAT,
                overrelief=tk.FLAT,
            )
            chk_master.pack(side=tk.LEFT)

            tk.Label(
                hdr,
                text=self._truncate_label(self._get_sample_display_name(loader), max_chars=26),
                bg=header_bg,
                fg=self.ui_text,
                font=self.ui_font_bold,
                anchor="w",
            ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(7, 6))
            
            if loader.is_expanded:
                content_frame.pack(fill=tk.X)

            def add_row(key, label_text, can_shift=True):
                row = tk.Frame(content_frame, bg=self.ui_surface, height=34)
                row.pack(fill=tk.X, padx=4)
                row.pack_propagate(False)
                row.grid_columnconfigure(2, weight=1)
                row._xrd_layer_drag_loader = loader
                row._xrd_layer_drag_key = key

                var = tk.BooleanVar(value=loader.visibility.get(key, True))

                def on_check(v=var, k=key, l=loader):
                    l.visibility[k] = bool(v.get())
                    self._request_draw_plot()

                tk.Checkbutton(
                    row,
                    variable=var,
                    command=lambda v=var, k=key, l=loader: on_check(v, k, l),
                    bg=self.ui_surface,
                    activebackground=self.ui_surface,
                    selectcolor=self.ui_surface,
                    cursor="hand2",
                    bd=0,
                    highlightthickness=0,
                    padx=0,
                    indicatoron=False,
                    image=indicators["check_off"],
                    selectimage=indicators["check_on"],
                    relief=tk.FLAT,
                    offrelief=tk.FLAT,
                    overrelief=tk.FLAT,
                ).grid(row=0, column=0, sticky="w")

                col = loader.styles.get(key, {}).get("color", "black")
                col_swatch = tk.Canvas(
                    row,
                    width=14,
                    height=18,
                    bg=self.ui_surface,
                    highlightthickness=0,
                    bd=0,
                    cursor="hand2",
                )
                dot_image = build_antialiased_color_dot(col_swatch, col, size=12)
                if dot_image is not None:
                    col_swatch._ui2_color_dot_image = dot_image
                    col_swatch.create_image(7, 9, image=dot_image)
                else:
                    col_swatch.create_oval(2, 4, 12, 14, fill=col, outline=col)
                col_swatch.grid(row=0, column=1, sticky="w", padx=(5, 5))

                disp = loader.display_names.get(key, label_text)
                lbl_name = tk.Label(
                    row,
                    text=self._truncate_label(disp, max_chars=18),
                    bg=self.ui_surface,
                    fg=self.ui_text,
                    anchor="w",
                    justify="left",
                    font=self.ui_font,
                    cursor="hand2",
                )
                lbl_name.grid(row=0, column=2, sticky="ew", padx=(0, 4))

                # Layer swatches are intentionally retained as per-layer manual overrides.
                # Use Inspector > Colors for global file/phase color systems.
                col_swatch.bind("<Button-1>", lambda e, l=loader, k=key: self.pick_color(l, k))
                for drag_widget in (row,):
                    drag_widget.bind(
                        "<ButtonPress-1>",
                        lambda event, l=loader, k=key, r=row: self._start_layer_drag(event, l, k, r),
                    )
                    drag_widget.bind("<B1-Motion>", self._move_layer_drag)
                    drag_widget.bind("<ButtonRelease-1>", self._finish_layer_drag)
                lbl_name.bind(
                    "<ButtonPress-1>",
                    lambda event, l=loader, k=key, r=row: self._start_layer_drag(
                        event, l, k, r, click_action=lambda: self.rename_layer(l, k)
                    ),
                )
                lbl_name.bind("<B1-Motion>", self._move_layer_drag)
                lbl_name.bind("<ButtonRelease-1>", self._finish_layer_drag)
                lbl_name.bind("<Button-3>", lambda e, l=loader, k=key: self.open_style_dialog(l, k))

                if can_shift:
                    current_offset = loader.offsets.get(key, 0.0)
                    slider_bound = max(2.0, abs(current_offset) * 1.2)
                    offset_var = tk.DoubleVar(value=current_offset)

                    def on_slide(_value, l=loader, k=key, ov=offset_var):
                        self.set_layer_offset_deferred(l, k, ov.get())
                        if self._preview_layer_offset(l, k, ov.get()):
                            # Keep one deferred full render for keyboard moves
                            # and for drags that pause before button release.
                            self._request_draw_plot(delay_ms=180)
                        else:
                            self._request_draw_plot(delay_ms=16)

                    def finish_slide(_value, l=loader, k=key, ov=offset_var):
                        self.set_layer_offset_deferred(l, k, ov.get())
                        self._request_draw_plot(delay_ms=1)

                    def nudge(sign, l=loader, k=key, ov=offset_var):
                        step = self._get_offset_step()
                        new_val = ov.get() + (sign * step)
                        ov.set(round(new_val, 4))
                        self.set_layer_offset_deferred(l, k, ov.get())
                        self._request_draw_plot(delay_ms=1)

                    small_button = dict(
                        bg=self.ui_button_light,
                        fg=self.ui_muted,
                        activebackground="#E3E6EA",
                        activeforeground=self.ui_text,
                        relief=tk.FLAT,
                        bd=0,
                        font=("Calibri", 8),
                        width=2,
                        cursor="hand2",
                    )
                    tk.Button(
                        row,
                        text="−",
                        command=lambda: nudge(-1),
                        **small_button,
                    ).grid(row=0, column=3, padx=(0, 4))

                    ModernScale(
                        row,
                        from_=-slider_bound,
                        to=slider_bound,
                        resolution=0.01,
                        orient=tk.HORIZONTAL,
                        variable=offset_var,
                        command=on_slide,
                        releasecommand=finish_slide,
                        length=100,
                        showvalue=False,
                        bg=self.ui_surface,
                        accent=self.ui_accent,
                        activebackground=self.ui_accent,
                        troughcolor="#DADCE0",
                        sliderrelief=tk.FLAT,
                        sliderlength=14,
                        width=7,
                        bd=0,
                        highlightthickness=0,
                    ).grid(row=0, column=4)

                    tk.Button(
                        row,
                        text="+",
                        command=lambda: nudge(+1),
                        **small_button,
                    ).grid(row=0, column=5, padx=(4, 0))
                else:
                    tk.Label(
                        row,
                        text="Residual panel",
                        bg=self.ui_surface,
                        fg="#9AA0A6",
                        anchor="e",
                        font=("Calibri", 8),
                    ).grid(row=0, column=3, columnspan=3, sticky="e", padx=(4, 2))

            for layer_key in self._get_loader_layer_order(loader):
                add_row(layer_key, layer_key, can_shift=(layer_key != "Difference"))

    def pick_color(self, loader, key):
        current = loader.styles.get(key, {}).get("color", "#1f77b4")
        c = choose_color(self.root, title=f"Color for {key}", initial_color=current)
        if c:
            loader.styles[key]["color"] = c
            if key == "Observed":
                loader.styles[key]["observed_custom_color"] = True
            elif key in loader.phase_names and self._phase_color_link_enabled():
                self._apply_phase_group_color(self._phase_color_group_key(loader, key), c)
            self.rebuild_layer_controls() # Updates visual, not plot
            self._request_draw_plot()

    def rename_layer(self, loader, key):
        cur = loader.display_names.get(key, key)
        def on_ok(new_name):
            final_name = (new_name or "").strip()
            if not final_name:
                final_name = loader.filename if key == "Observed" else key

            # Phase names are synchronized across all loaded files.
            if key in loader.phase_names:
                if final_name == key:
                    self.phase_name_overrides.pop(key, None)
                else:
                    self.phase_name_overrides[key] = final_name

                for ldr in self.loaded_files.values():
                    if key in ldr.phase_names:
                        ldr.display_names[key] = final_name
                if self._phase_color_link_enabled():
                    self.sync_phase_colors_by_name(redraw=False, rebuild=False)
            else:
                loader.display_names[key] = final_name
                if key == "Observed":
                    self.split_main_title_overrides.pop(loader.filepath, None)
                    if hasattr(self, "file_tree"):
                        try:
                            self._refresh_file_tree_visibility_item(loader.filepath, loader)
                        except Exception:
                            pass

            self.rebuild_layer_controls()
            self._request_draw_plot()
        RichLabelEditDialog(self.root, "Rename", cur, on_ok)

    def open_style_dialog(self, loader, key):
        def on_ok(new_settings):
            merged = dict(loader.styles.get(key, {}))
            merged.update(new_settings)
            if key == "Observed":
                user_changed = str(merged.get("color", loader.project_color)).lower() != str(loader.project_color).lower()
                merged["observed_custom_color"] = user_changed or bool(merged.get("observed_custom_color", False))
            loader.styles[key] = merged
            if key in loader.phase_names and self._phase_color_link_enabled() and "color" in merged:
                self._apply_phase_group_color(self._phase_color_group_key(loader, key), merged["color"])
            self.rebuild_layer_controls()
            self._request_draw_plot()
        StyleDialog(self.root, key, loader.styles[key], on_ok)

    def set_layer_offset_deferred(self, loader, key, value):
        if getattr(loader, "phase_auto_stack_order", []):
            automatic_offsets = getattr(loader, "phase_auto_stack_offsets", None)
            if not isinstance(automatic_offsets, dict):
                automatic_offsets = {}
                loader.phase_auto_stack_offsets = automatic_offsets
            # Templates from older versions do not have this baseline. Capture
            # the pre-drag value before changing it so the first move works too.
            automatic_offsets.setdefault(key, float(loader.offsets.get(key, 0.0)))
        if key in loader.offsets:
            loader.offsets[key] = float(value)
        elif key in loader.phase_names:
            loader.offsets[key] = float(value)

    # ========================================================
    # Logic: Plotting
    # ========================================================

