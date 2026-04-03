"""Paper & Cutting panel — feed, cut, line spacing, sensors, panel button."""
from __future__ import annotations

import customtkinter as ctk

from gui.context import AppContext


class PaperCutPanel(ctk.CTkFrame):
    def __init__(self, master, ctx: AppContext):
        super().__init__(master, corner_radius=0, fg_color="transparent")
        self.ctx = ctx
        self.grid_columnconfigure((0, 1), weight=1)
        self._build()

    def _build(self) -> None:
        ctk.CTkLabel(self, text="Paper & Cutting", font=ctk.CTkFont(size=20, weight="bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=24, pady=(20, 4)
        )

        # ── Feed controls ────────────────────────────────────────────
        feed_frame = ctk.CTkFrame(self)
        feed_frame.grid(row=1, column=0, sticky="nsew", padx=(24, 8), pady=8)
        feed_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(feed_frame, text="Paper Feed", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, columnspan=3, padx=12, pady=(12, 6), sticky="w"
        )

        # Feed lines
        ctk.CTkLabel(feed_frame, text="Lines (0–255):").grid(row=1, column=0, padx=12, pady=8, sticky="w")
        self._feed_lines_var = ctk.IntVar(value=3)
        ctk.CTkEntry(feed_frame, textvariable=self._feed_lines_var, width=70).grid(
            row=1, column=1, padx=8, pady=8, sticky="w"
        )
        ctk.CTkButton(feed_frame, text="Feed Lines", command=self._do_feed_lines, width=110).grid(
            row=1, column=2, padx=12, pady=8
        )

        # Feed dots
        ctk.CTkLabel(feed_frame, text="Dots (0–255):").grid(row=2, column=0, padx=12, pady=8, sticky="w")
        self._feed_dots_var = ctk.IntVar(value=24)
        ctk.CTkEntry(feed_frame, textvariable=self._feed_dots_var, width=70).grid(
            row=2, column=1, padx=8, pady=8, sticky="w"
        )
        ctk.CTkButton(feed_frame, text="Feed Dots", command=self._do_feed_dots, width=110).grid(
            row=2, column=2, padx=12, pady=8
        )

        # Line spacing
        ctk.CTkLabel(feed_frame, text="Line spacing:").grid(row=3, column=0, padx=12, pady=8, sticky="w")
        self._spacing_mode = ctk.StringVar(value="Default")
        ctk.CTkSegmentedButton(
            feed_frame, values=["Default", "Custom"], variable=self._spacing_mode
        ).grid(row=3, column=1, padx=8, pady=8, sticky="w")

        self._spacing_dots = ctk.IntVar(value=30)
        self._spacing_entry = ctk.CTkEntry(feed_frame, textvariable=self._spacing_dots, width=70)
        self._spacing_entry.grid(row=3, column=2, padx=12, pady=8)

        ctk.CTkButton(feed_frame, text="Apply Spacing", command=self._do_spacing, width=110).grid(
            row=4, column=2, padx=12, pady=(0, 12)
        )

        # ── Cut control ──────────────────────────────────────────────
        cut_frame = ctk.CTkFrame(self)
        cut_frame.grid(row=1, column=1, sticky="nsew", padx=(8, 24), pady=8)
        cut_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(cut_frame, text="Paper Cut", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, columnspan=2, padx=12, pady=(12, 6), sticky="w"
        )
        ctk.CTkLabel(cut_frame, text="Feed before cut (0=immediate):").grid(
            row=1, column=0, padx=12, pady=8, sticky="w"
        )
        self._cut_feed = ctk.IntVar(value=0)
        ctk.CTkEntry(cut_frame, textvariable=self._cut_feed, width=70).grid(
            row=1, column=1, padx=12, pady=8, sticky="w"
        )
        ctk.CTkButton(
            cut_frame, text="Cut Paper", command=self._do_cut,
            fg_color="#c0392b", hover_color="#922b21"
        ).grid(row=2, column=0, columnspan=2, padx=12, pady=8, sticky="w")

        # ── Sensors ──────────────────────────────────────────────────
        sensor_frame = ctk.CTkFrame(self)
        sensor_frame.grid(row=2, column=0, sticky="nsew", padx=(24, 8), pady=8)

        ctk.CTkLabel(sensor_frame, text="Sensors & Buttons", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, columnspan=2, padx=12, pady=(12, 6), sticky="w"
        )

        self._sens_near_end = ctk.BooleanVar(value=True)
        self._sens_end = ctk.BooleanVar(value=True)
        self._sens_stop = ctk.BooleanVar(value=False)
        self._panel_btn = ctk.BooleanVar(value=True)

        for r, (var, label) in enumerate([
            (self._sens_near_end, "Paper end sensor — near-end signal"),
            (self._sens_end, "Paper end sensor — end signal"),
            (self._sens_stop, "Stop on near-end detection"),
            (self._panel_btn, "Enable FEED button on printer"),
        ]):
            ctk.CTkCheckBox(sensor_frame, text=label, variable=var).grid(
                row=r + 1, column=0, padx=12, pady=5, sticky="w"
            )

        ctk.CTkButton(sensor_frame, text="Apply Sensor Settings", command=self._do_sensors).grid(
            row=5, column=0, padx=12, pady=12, sticky="w"
        )

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _do_feed_lines(self) -> None:
        if not self.ctx.connected:
            return
        try:
            n = max(0, min(255, self._feed_lines_var.get()))
            self.ctx.printer.feed_lines(n)
            self.ctx.set_status(f"Fed {n} lines")
        except Exception as exc:
            self.ctx.set_status(f"Error: {exc}")

    def _do_feed_dots(self) -> None:
        if not self.ctx.connected:
            return
        try:
            n = max(0, min(255, self._feed_dots_var.get()))
            self.ctx.printer.feed_dots(n)
            self.ctx.set_status(f"Fed {n} dots")
        except Exception as exc:
            self.ctx.set_status(f"Error: {exc}")

    def _do_spacing(self) -> None:
        if not self.ctx.connected:
            return
        try:
            if self._spacing_mode.get() == "Default":
                self.ctx.printer.set_line_spacing(None)
                self.ctx.set_status("Line spacing set to default (1/6 inch)")
            else:
                n = max(0, min(255, self._spacing_dots.get()))
                self.ctx.printer.set_line_spacing(n)
                self.ctx.set_status(f"Line spacing set to {n} dots")
        except Exception as exc:
            self.ctx.set_status(f"Error: {exc}")

    def _do_cut(self) -> None:
        if not self.ctx.connected:
            return
        try:
            n = max(0, min(255, self._cut_feed.get()))
            self.ctx.printer.cut(n)
            self.ctx.set_status("Cut command sent")
        except Exception as exc:
            self.ctx.set_status(f"Error: {exc}")

    def _do_sensors(self) -> None:
        if not self.ctx.connected:
            return
        try:
            self.ctx.printer.set_paper_end_sensor(
                near_end=self._sens_near_end.get(),
                end=self._sens_end.get(),
            )
            self.ctx.printer.set_paper_stop_sensor(near_end=self._sens_stop.get())
            self.ctx.printer.set_panel_buttons(enabled=self._panel_btn.get())
            self.ctx.set_status("Sensor settings applied")
        except Exception as exc:
            self.ctx.set_status(f"Error: {exc}")
