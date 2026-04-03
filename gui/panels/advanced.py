"""Advanced panel — layout, macros, NV images."""
from __future__ import annotations

import customtkinter as ctk

from gui.context import AppContext

_RASTER_MODES = ["Normal", "Double Width", "Double Height", "Quadruple"]
_RASTER_MAP = {"Normal": 0, "Double Width": 1, "Double Height": 2, "Quadruple": 3}


class AdvancedPanel(ctk.CTkFrame):
    def __init__(self, master, ctx: AppContext):
        super().__init__(master, corner_radius=0, fg_color="transparent")
        self.ctx = ctx
        self.grid_columnconfigure(0, weight=1)
        self._build()

    def _build(self) -> None:
        ctk.CTkLabel(self, text="Advanced", font=ctk.CTkFont(size=20, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=24, pady=(20, 4)
        )

        self._tabs = ctk.CTkTabview(self)
        self._tabs.grid(row=1, column=0, sticky="nsew", padx=24, pady=8)
        self.grid_rowconfigure(1, weight=1)

        self._tabs.add("Layout")
        self._tabs.add("Macros")
        self._tabs.add("NV Images")

        self._build_layout(self._tabs.tab("Layout"))
        self._build_macros(self._tabs.tab("Macros"))
        self._build_nv(self._tabs.tab("NV Images"))

    # ------------------------------------------------------------------
    # Layout tab
    # ------------------------------------------------------------------

    def _build_layout(self, parent) -> None:
        parent.grid_columnconfigure(1, weight=1)

        rows = [
            ("Left margin (dots):", "_left_margin", 0, 65535, 0),
            ("Print area width (dots):", "_print_width", 0, 65535, 512),
            ("H motion unit (0=factory):", "_motion_x", 0, 255, 0),
            ("V motion unit (0=factory):", "_motion_y", 0, 255, 0),
            ("Absolute position (dots):", "_abs_pos", 0, 65535, 0),
        ]
        self._layout_vars: dict[str, ctk.IntVar] = {}
        for r, (label, attr, lo, hi, default) in enumerate(rows):
            ctk.CTkLabel(parent, text=label).grid(row=r, column=0, padx=12, pady=8, sticky="w")
            var = ctk.IntVar(value=default)
            self._layout_vars[attr] = var
            ctk.CTkEntry(parent, textvariable=var, width=90).grid(row=r, column=1, padx=12, pady=8, sticky="w")

        # Tab stops
        r = len(rows)
        ctk.CTkLabel(parent, text="Tab stops (up to 32, ascending):").grid(
            row=r, column=0, columnspan=2, padx=12, pady=(14, 4), sticky="w"
        )
        self._tabs_entry = ctk.CTkEntry(parent, placeholder_text="e.g. 8 16 24 32", width=280)
        self._tabs_entry.grid(row=r + 1, column=0, columnspan=2, padx=12, pady=4, sticky="ew")

        btn_frame = ctk.CTkFrame(parent, fg_color="transparent")
        btn_frame.grid(row=r + 2, column=0, columnspan=2, padx=12, pady=10, sticky="w")
        ctk.CTkButton(btn_frame, text="Apply Layout", command=self._do_layout, width=120).grid(
            row=0, column=0, padx=(0, 8)
        )
        ctk.CTkButton(btn_frame, text="Apply Tabs", command=self._do_tabs, width=110).grid(row=0, column=1)

    # ------------------------------------------------------------------
    # Macros tab
    # ------------------------------------------------------------------

    def _build_macros(self, parent) -> None:
        parent.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(parent, text="Record a macro, then execute it with repeat/timing options.",
                     text_color="gray60", wraplength=380).grid(
            row=0, column=0, columnspan=2, padx=12, pady=(12, 8), sticky="w"
        )

        self._recording = False
        self._record_btn = ctk.CTkButton(
            parent, text="Start Recording", command=self._do_toggle_record,
            fg_color="#8e44ad", hover_color="#6c3483"
        )
        self._record_btn.grid(row=1, column=0, padx=12, pady=8, sticky="w")
        self._record_label = ctk.CTkLabel(parent, text="Not recording", text_color="gray60")
        self._record_label.grid(row=1, column=1, padx=12, pady=8, sticky="w")

        ctk.CTkLabel(parent, text="─" * 30, text_color="gray50").grid(
            row=2, column=0, columnspan=2, padx=12, pady=6, sticky="w"
        )

        ctk.CTkLabel(parent, text="Execute Macro", font=ctk.CTkFont(weight="bold")).grid(
            row=3, column=0, columnspan=2, padx=12, pady=(4, 8), sticky="w"
        )

        ctk.CTkLabel(parent, text="Repeat count (0–255):").grid(row=4, column=0, padx=12, pady=6, sticky="w")
        self._macro_repeat = ctk.IntVar(value=1)
        ctk.CTkEntry(parent, textvariable=self._macro_repeat, width=70).grid(row=4, column=1, padx=12, pady=6, sticky="w")

        ctk.CTkLabel(parent, text="Wait between repeats (×100ms):").grid(row=5, column=0, padx=12, pady=6, sticky="w")
        self._macro_wait = ctk.IntVar(value=0)
        ctk.CTkEntry(parent, textvariable=self._macro_wait, width=70).grid(row=5, column=1, padx=12, pady=6, sticky="w")

        self._macro_button_var = ctk.BooleanVar()
        ctk.CTkCheckBox(parent, text="Wait for FEED button press between repeats",
                        variable=self._macro_button_var).grid(
            row=6, column=0, columnspan=2, padx=12, pady=6, sticky="w"
        )

        ctk.CTkButton(parent, text="Execute Macro", command=self._do_exec_macro).grid(
            row=7, column=0, padx=12, pady=12, sticky="w"
        )

    # ------------------------------------------------------------------
    # NV Images tab
    # ------------------------------------------------------------------

    def _build_nv(self, parent) -> None:
        parent.grid_columnconfigure(1, weight=1)

        warn = ctk.CTkLabel(
            parent,
            text="WARNING: NV memory has a write limit of ~10 times per day.\n"
                 "Exceeding this degrades or destroys NV memory permanently.",
            text_color="#e74c3c",
            wraplength=380,
            justify="left",
        )
        warn.grid(row=0, column=0, columnspan=2, padx=12, pady=(12, 8), sticky="w")

        ctk.CTkLabel(parent, text="Print NV Image", font=ctk.CTkFont(weight="bold")).grid(
            row=1, column=0, columnspan=2, padx=12, pady=(8, 4), sticky="w"
        )

        ctk.CTkLabel(parent, text="Slot (1–255):").grid(row=2, column=0, padx=12, pady=8, sticky="w")
        self._nv_slot = ctk.IntVar(value=1)
        ctk.CTkEntry(parent, textvariable=self._nv_slot, width=70).grid(row=2, column=1, padx=12, pady=8, sticky="w")

        ctk.CTkLabel(parent, text="Raster mode:").grid(row=3, column=0, padx=12, pady=8, sticky="w")
        self._nv_mode_var = ctk.StringVar(value="Normal")
        ctk.CTkOptionMenu(parent, values=_RASTER_MODES, variable=self._nv_mode_var, width=160).grid(
            row=3, column=1, padx=12, pady=8, sticky="w"
        )

        ctk.CTkButton(parent, text="Print NV Image", command=self._do_print_nv).grid(
            row=4, column=0, padx=12, pady=12, sticky="w"
        )

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _do_layout(self) -> None:
        if not self.ctx.connected:
            self.ctx.set_status("Not connected")
            return
        p = self.ctx.printer
        try:
            p.set_left_margin(self._layout_vars["_left_margin"].get())
            p.set_print_area_width(self._layout_vars["_print_width"].get())
            p.set_motion_units(
                self._layout_vars["_motion_x"].get(),
                self._layout_vars["_motion_y"].get(),
            )
            p.set_absolute_position(self._layout_vars["_abs_pos"].get())
            self.ctx.set_status("Layout settings applied")
        except Exception as exc:
            self.ctx.set_status(f"Error: {exc}")

    def _do_tabs(self) -> None:
        if not self.ctx.connected:
            self.ctx.set_status("Not connected")
            return
        raw = self._tabs_entry.get().strip()
        try:
            positions = [int(x) for x in raw.split()] if raw else []
            if len(positions) > 32:
                self.ctx.set_status("Max 32 tab stops allowed")
                return
            self.ctx.printer.set_tab_positions(positions)
            self.ctx.set_status(f"Tab stops set: {positions}")
        except ValueError:
            self.ctx.set_status("Invalid tab stop values — enter integers separated by spaces")
        except Exception as exc:
            self.ctx.set_status(f"Error: {exc}")

    def _do_toggle_record(self) -> None:
        if not self.ctx.connected:
            self.ctx.set_status("Not connected")
            return
        try:
            if not self._recording:
                self.ctx.printer.start_macro()
                self._recording = True
                self._record_btn.configure(text="Stop Recording", fg_color="#c0392b", hover_color="#922b21")
                self._record_label.configure(text="Recording…", text_color="#e74c3c")
                self.ctx.set_status("Macro recording started — send print commands, then stop")
            else:
                self.ctx.printer.end_macro()
                self._recording = False
                self._record_btn.configure(text="Start Recording", fg_color="#8e44ad", hover_color="#6c3483")
                self._record_label.configure(text="Macro recorded", text_color="#2ecc71")
                self.ctx.set_status("Macro recording stopped")
        except Exception as exc:
            self.ctx.set_status(f"Error: {exc}")

    def _do_exec_macro(self) -> None:
        if not self.ctx.connected:
            self.ctx.set_status("Not connected")
            return
        try:
            self.ctx.printer.execute_macro(
                repeat=max(0, min(255, self._macro_repeat.get())),
                wait_100ms=max(0, min(255, self._macro_wait.get())),
                wait_for_button=self._macro_button_var.get(),
            )
            self.ctx.set_status("Macro execution sent")
        except Exception as exc:
            self.ctx.set_status(f"Error: {exc}")

    def _do_print_nv(self) -> None:
        if not self.ctx.connected:
            self.ctx.set_status("Not connected")
            return
        try:
            from xprinter import RasterMode

            slot = max(1, min(255, self._nv_slot.get()))
            mode = RasterMode(_RASTER_MAP[self._nv_mode_var.get()])
            self.ctx.printer.print_nv_image(slot, mode)
            self.ctx.set_status(f"NV image slot {slot} printed")
        except Exception as exc:
            self.ctx.set_status(f"Error: {exc}")
