"""Barcode panel — system selection, data, height/width/HRI configuration."""
from __future__ import annotations

import customtkinter as ctk

from gui.context import AppContext

_SYSTEMS = ["UPC-A", "UPC-E", "EAN13", "EAN8", "CODE39", "ITF", "CODABAR", "CODE93", "CODE128"]
_SYSTEM_MAP = {
    "UPC-A": "UPC_A", "UPC-E": "UPC_E", "EAN13": "EAN13", "EAN8": "EAN8",
    "CODE39": "CODE39", "ITF": "ITF", "CODABAR": "CODABAR",
    "CODE93": "CODE93", "CODE128": "CODE128",
}
_HRI_OPTIONS = ["Hidden", "Above", "Below", "Both"]
_HRI_MAP = {"Hidden": "hidden", "Above": "above", "Below": "below", "Both": "both"}


class BarcodePanel(ctk.CTkFrame):
    def __init__(self, master, ctx: AppContext):
        super().__init__(master, corner_radius=0, fg_color="transparent")
        self.ctx = ctx
        self.grid_columnconfigure((0, 1), weight=1)
        self._build()

    def _build(self) -> None:
        ctk.CTkLabel(self, text="Barcode", font=ctk.CTkFont(size=20, weight="bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=24, pady=(20, 4)
        )

        # ── Left: data & system ──────────────────────────────────────
        left = ctk.CTkFrame(self)
        left.grid(row=1, column=0, sticky="nsew", padx=(24, 8), pady=8)
        left.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(left, text="Barcode System & Data", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, columnspan=2, padx=12, pady=(12, 6), sticky="w"
        )

        ctk.CTkLabel(left, text="System:").grid(row=1, column=0, padx=12, pady=8, sticky="w")
        self._system_var = ctk.StringVar(value=_SYSTEMS[-1])
        ctk.CTkOptionMenu(left, values=_SYSTEMS, variable=self._system_var, width=160).grid(
            row=1, column=1, padx=12, pady=8, sticky="w"
        )

        ctk.CTkLabel(left, text="Data:").grid(row=2, column=0, padx=12, pady=8, sticky="w")
        self._data_var = ctk.StringVar(value="XPRINTER123")
        ctk.CTkEntry(left, textvariable=self._data_var, width=200).grid(
            row=2, column=1, padx=12, pady=8, sticky="ew"
        )

        ctk.CTkButton(
            left, text="Print Barcode", command=self._do_print,
            fg_color="#27ae60", hover_color="#1e8449"
        ).grid(row=3, column=0, columnspan=2, padx=12, pady=12, sticky="w")

        # ── Right: appearance ────────────────────────────────────────
        right = ctk.CTkFrame(self)
        right.grid(row=1, column=1, sticky="nsew", padx=(8, 24), pady=8)
        right.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(right, text="Barcode Appearance", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, columnspan=2, padx=12, pady=(12, 6), sticky="w"
        )

        # Height
        ctk.CTkLabel(right, text="Height (1–255 dots):").grid(row=1, column=0, padx=12, pady=8, sticky="w")
        self._height_var = ctk.IntVar(value=162)
        ctk.CTkEntry(right, textvariable=self._height_var, width=70).grid(
            row=1, column=1, padx=12, pady=8, sticky="w"
        )

        # Width
        ctk.CTkLabel(right, text="Width (2–6):").grid(row=2, column=0, padx=12, pady=8, sticky="w")
        self._width_var = ctk.IntVar(value=3)
        ctk.CTkSlider(
            right, from_=2, to=6, number_of_steps=4,
            variable=self._width_var, width=140,
        ).grid(row=2, column=1, padx=12, pady=8, sticky="w")

        # HRI position
        ctk.CTkLabel(right, text="HRI text position:").grid(row=3, column=0, padx=12, pady=8, sticky="w")
        self._hri_var = ctk.StringVar(value="Below")
        ctk.CTkOptionMenu(right, values=_HRI_OPTIONS, variable=self._hri_var, width=120).grid(
            row=3, column=1, padx=12, pady=8, sticky="w"
        )

        # HRI font
        ctk.CTkLabel(right, text="HRI font:").grid(row=4, column=0, padx=12, pady=8, sticky="w")
        self._hri_font_var = ctk.StringVar(value="Font A")
        ctk.CTkSegmentedButton(
            right, values=["Font A", "Font B"], variable=self._hri_font_var
        ).grid(row=4, column=1, padx=12, pady=8, sticky="w")

        ctk.CTkButton(right, text="Apply Appearance", command=self._do_apply_appearance).grid(
            row=5, column=0, columnspan=2, padx=12, pady=12, sticky="w"
        )

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _do_apply_appearance(self) -> None:
        if not self.ctx.connected:
            self.ctx.set_status("Not connected")
            return
        try:
            h = max(1, min(255, self._height_var.get()))
            w = max(2, min(6, int(self._width_var.get())))
            self.ctx.printer.set_barcode_height(h)
            self.ctx.printer.set_barcode_width(w)
            self.ctx.printer.set_barcode_hri(_HRI_MAP[self._hri_var.get()])
            self.ctx.printer.set_barcode_hri_font(self._hri_font_var.get() == "Font B")
            self.ctx.set_status("Barcode appearance applied")
        except Exception as exc:
            self.ctx.set_status(f"Error: {exc}")

    def _do_print(self) -> None:
        if not self.ctx.connected:
            self.ctx.set_status("Not connected")
            return
        self._do_apply_appearance()
        try:
            system = _SYSTEM_MAP[self._system_var.get()]
            data = self._data_var.get().strip()
            if not data:
                self.ctx.set_status("Barcode data is empty")
                return
            self.ctx.printer.print_barcode(system, data)
            self.ctx.printer.feed_lines(2)
            self.ctx.set_status(f"Barcode printed ({system})")
        except Exception as exc:
            self.ctx.set_status(f"Print error: {exc}")
