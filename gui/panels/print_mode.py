"""Print Mode panel — text formatting, fonts, justification, character sets."""
from __future__ import annotations

import customtkinter as ctk

from gui.context import AppContext

_CODE_PAGES = [
    "PC437 (USA)", "KATAKANA", "PC850 (Multilingual)", "PC860 (Portuguese)",
    "PC863 (Canadian-French)", "PC865 (Nordic)", "West Europe", "Greek",
    "Hebrew", "PC755", "Iran", "WPC1252", "PC866 (Cyrillic)", "PC852",
    "PC858", "Iran II", "Latvian",
]
_CODE_PAGE_IDS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 16, 17, 18, 19, 20, 21]

_CHARSETS = [
    "USA", "France", "Germany", "UK", "Denmark I", "Sweden", "Italy",
    "Spain I", "Japan", "Norway", "Denmark II", "Spain II",
    "Latin America", "Korea", "Slovenia/Croatia", "Chinese",
]


class PrintModePanel(ctk.CTkFrame):
    def __init__(self, master, ctx: AppContext):
        super().__init__(master, corner_radius=0, fg_color="transparent")
        self.ctx = ctx
        self.grid_columnconfigure((0, 1), weight=1)
        self._build()

    def _build(self) -> None:
        ctk.CTkLabel(self, text="Print Mode", font=ctk.CTkFont(size=20, weight="bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=24, pady=(20, 4)
        )

        # ── Left column ──────────────────────────────────────────────
        left = ctk.CTkFrame(self)
        left.grid(row=1, column=0, sticky="nsew", padx=(24, 8), pady=8)
        left.grid_columnconfigure(0, weight=1)
        self._build_formatting(left)

        # ── Right column ─────────────────────────────────────────────
        right = ctk.CTkFrame(self)
        right.grid(row=1, column=1, sticky="nsew", padx=(8, 24), pady=8)
        right.grid_columnconfigure(0, weight=1)
        self._build_charsets(right)

        # ── Action buttons ───────────────────────────────────────────
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=2, column=0, columnspan=2, sticky="w", padx=24, pady=12)
        ctk.CTkButton(btn_frame, text="Apply All", command=self._do_apply, width=120).grid(
            row=0, column=0, padx=(0, 10)
        )
        ctk.CTkButton(
            btn_frame, text="Print Sample", command=self._do_print_sample, width=130,
            fg_color="#7f8c8d", hover_color="#5d6d7e"
        ).grid(row=0, column=1)

    # ------------------------------------------------------------------

    def _build_formatting(self, parent) -> None:
        ctk.CTkLabel(parent, text="Text Formatting", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, padx=12, pady=(12, 6), sticky="w"
        )

        # Font
        ctk.CTkLabel(parent, text="Font:").grid(row=1, column=0, padx=12, pady=4, sticky="w")
        self._font_var = ctk.StringVar(value="Font A (12×24)")
        ctk.CTkSegmentedButton(
            parent,
            values=["Font A (12×24)", "Font B (9×17)"],
            variable=self._font_var,
        ).grid(row=2, column=0, padx=12, pady=4, sticky="w")

        # Justification
        ctk.CTkLabel(parent, text="Justification:").grid(row=3, column=0, padx=12, pady=(10, 4), sticky="w")
        self._justify_var = ctk.StringVar(value="left")
        ctk.CTkSegmentedButton(
            parent,
            values=["left", "center", "right"],
            variable=self._justify_var,
        ).grid(row=4, column=0, padx=12, pady=4, sticky="w")

        # Underline
        ctk.CTkLabel(parent, text="Underline:").grid(row=5, column=0, padx=12, pady=(10, 4), sticky="w")
        self._underline_var = ctk.StringVar(value="Off")
        ctk.CTkSegmentedButton(
            parent,
            values=["Off", "Thin", "Thick"],
            variable=self._underline_var,
        ).grid(row=6, column=0, padx=12, pady=4, sticky="w")

        # Toggles
        self._emphasized = ctk.BooleanVar()
        self._double_strike = ctk.BooleanVar()
        self._reverse = ctk.BooleanVar()
        self._upside_down = ctk.BooleanVar()
        self._rotation_90 = ctk.BooleanVar()

        toggle_frame = ctk.CTkFrame(parent, fg_color="transparent")
        toggle_frame.grid(row=7, column=0, padx=12, pady=(10, 4), sticky="w")
        for r, (var, label) in enumerate([
            (self._emphasized, "Emphasized (Bold)"),
            (self._double_strike, "Double Strike"),
            (self._reverse, "Reverse (white-on-black)"),
            (self._upside_down, "Upside Down"),
            (self._rotation_90, "90° Clockwise Rotation"),
        ]):
            ctk.CTkCheckBox(toggle_frame, text=label, variable=var).grid(
                row=r, column=0, padx=0, pady=3, sticky="w"
            )

        # Character size
        ctk.CTkLabel(parent, text="Character Size:").grid(row=8, column=0, padx=12, pady=(10, 4), sticky="w")
        size_frame = ctk.CTkFrame(parent, fg_color="transparent")
        size_frame.grid(row=9, column=0, padx=12, pady=4, sticky="w")

        ctk.CTkLabel(size_frame, text="Width 1–8:").grid(row=0, column=0, padx=(0, 6))
        self._char_width = ctk.CTkSlider(size_frame, from_=1, to=8, number_of_steps=7, width=140)
        self._char_width.set(1)
        self._char_width.grid(row=0, column=1, padx=(0, 6))
        self._width_label = ctk.CTkLabel(size_frame, text="1", width=20)
        self._width_label.grid(row=0, column=2)
        self._char_width.configure(command=lambda v: self._width_label.configure(text=str(int(v))))

        ctk.CTkLabel(size_frame, text="Height 1–8:").grid(row=1, column=0, padx=(0, 6), pady=(6, 0))
        self._char_height = ctk.CTkSlider(size_frame, from_=1, to=8, number_of_steps=7, width=140)
        self._char_height.set(1)
        self._char_height.grid(row=1, column=1, padx=(0, 6), pady=(6, 0))
        self._height_label = ctk.CTkLabel(size_frame, text="1", width=20)
        self._height_label.grid(row=1, column=2, pady=(6, 0))
        self._char_height.configure(command=lambda v: self._height_label.configure(text=str(int(v))))

    # ------------------------------------------------------------------

    def _build_charsets(self, parent) -> None:
        ctk.CTkLabel(parent, text="Character Sets", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, padx=12, pady=(12, 6), sticky="w"
        )

        ctk.CTkLabel(parent, text="Code Page:").grid(row=1, column=0, padx=12, pady=(8, 2), sticky="w")
        self._code_page_var = ctk.StringVar(value=_CODE_PAGES[0])
        ctk.CTkOptionMenu(parent, values=_CODE_PAGES, variable=self._code_page_var, width=220).grid(
            row=2, column=0, padx=12, pady=4, sticky="w"
        )

        ctk.CTkLabel(parent, text="International Charset:").grid(row=3, column=0, padx=12, pady=(10, 2), sticky="w")
        self._charset_var = ctk.StringVar(value=_CHARSETS[0])
        ctk.CTkOptionMenu(parent, values=_CHARSETS, variable=self._charset_var, width=220).grid(
            row=4, column=0, padx=12, pady=4, sticky="w"
        )

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _do_apply(self) -> None:
        if not self.ctx.connected:
            self.ctx.set_status("Not connected")
            return
        p = self.ctx.printer
        try:
            p.set_font(self._font_var.get() == "Font B (9×17)")
            p.set_justification(self._justify_var.get())
            underline_map = {"Off": 0, "Thin": 1, "Thick": 2}
            p.set_underline(underline_map[self._underline_var.get()])
            p.set_emphasized(self._emphasized.get())
            p.set_double_strike(self._double_strike.get())
            p.set_reverse(self._reverse.get())
            p.set_upside_down(self._upside_down.get())
            p.set_rotation_90(self._rotation_90.get())
            p.set_character_size(int(self._char_width.get()), int(self._char_height.get()))

            cp_index = _CODE_PAGES.index(self._code_page_var.get())
            p.set_code_page(_CODE_PAGE_IDS[cp_index])
            p.set_international_charset(_CHARSETS.index(self._charset_var.get()))

            self.ctx.set_status("Print mode settings applied")
        except Exception as exc:
            self.ctx.set_status(f"Error: {exc}")

    def _do_print_sample(self) -> None:
        if not self.ctx.connected:
            self.ctx.set_status("Not connected")
            return
        self._do_apply()
        try:
            p = self.ctx.printer
            p.println("The quick brown fox jumps over the lazy dog")
            p.println("0123456789 !@#$%^&*()")
            p.feed_lines(2)
            self.ctx.set_status("Sample printed")
        except Exception as exc:
            self.ctx.set_status(f"Print error: {exc}")
