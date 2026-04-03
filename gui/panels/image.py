"""Image printing panel — file picker, thumbnail preview, raster mode."""
from __future__ import annotations

import customtkinter as ctk
from tkinter import filedialog

from gui.context import AppContext

_RASTER_MODES = ["Normal", "Double Width", "Double Height", "Quadruple"]
_RASTER_MAP = {"Normal": 0, "Double Width": 1, "Double Height": 2, "Quadruple": 3}


class ImagePanel(ctk.CTkFrame):
    def __init__(self, master, ctx: AppContext):
        super().__init__(master, corner_radius=0, fg_color="transparent")
        self.ctx = ctx
        self._pil_image = None
        self._tk_image = None
        self.grid_columnconfigure((0, 1), weight=1)
        self._build()

    def _build(self) -> None:
        ctk.CTkLabel(self, text="Image Printing", font=ctk.CTkFont(size=20, weight="bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=24, pady=(20, 4)
        )

        # ── Left: file selection & options ───────────────────────────
        left = ctk.CTkFrame(self)
        left.grid(row=1, column=0, sticky="nsew", padx=(24, 8), pady=8)
        left.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(left, text="Image File", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, columnspan=2, padx=12, pady=(12, 6), sticky="w"
        )

        self._path_var = ctk.StringVar(value="No file selected")
        ctk.CTkLabel(left, textvariable=self._path_var, text_color="gray60", wraplength=260).grid(
            row=1, column=0, columnspan=2, padx=12, pady=4, sticky="w"
        )
        ctk.CTkButton(left, text="Browse…", command=self._do_browse, width=100).grid(
            row=2, column=0, padx=12, pady=8, sticky="w"
        )

        # Raster mode
        ctk.CTkLabel(left, text="Raster mode:").grid(row=3, column=0, padx=12, pady=8, sticky="w")
        self._mode_var = ctk.StringVar(value="Normal")
        ctk.CTkOptionMenu(left, values=_RASTER_MODES, variable=self._mode_var, width=160).grid(
            row=3, column=1, padx=12, pady=8, sticky="w"
        )

        # Max width
        ctk.CTkLabel(left, text="Max width (dots):").grid(row=4, column=0, padx=12, pady=8, sticky="w")
        self._max_width_var = ctk.IntVar(value=576)
        ctk.CTkEntry(left, textvariable=self._max_width_var, width=80).grid(
            row=4, column=1, padx=12, pady=8, sticky="w"
        )

        ctk.CTkButton(
            left, text="Print Image", command=self._do_print,
            fg_color="#27ae60", hover_color="#1e8449"
        ).grid(row=5, column=0, columnspan=2, padx=12, pady=12, sticky="w")

        # ── Right: thumbnail preview ─────────────────────────────────
        right = ctk.CTkFrame(self)
        right.grid(row=1, column=1, sticky="nsew", padx=(8, 24), pady=8)

        ctk.CTkLabel(right, text="Preview", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, padx=12, pady=(12, 6), sticky="w"
        )
        self._preview_label = ctk.CTkLabel(
            right, text="No image loaded", text_color="gray60", width=280, height=280
        )
        self._preview_label.grid(row=1, column=0, padx=12, pady=12)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _do_browse(self) -> None:
        path = filedialog.askopenfilename(
            title="Select image",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.gif *.tiff"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            from PIL import Image, ImageTk

            img = Image.open(path)
            self._pil_image = img
            self._path_var.set(path)

            # Thumbnail for preview
            thumb = img.copy()
            thumb.thumbnail((280, 280))
            self._tk_image = ImageTk.PhotoImage(thumb)
            self._preview_label.configure(image=self._tk_image, text="")
            self.ctx.set_status(f"Loaded: {path}  ({img.width}×{img.height} px)")
        except Exception as exc:
            self.ctx.set_status(f"Image load error: {exc}")

    def _do_print(self) -> None:
        if not self.ctx.connected:
            self.ctx.set_status("Not connected")
            return
        if self._pil_image is None:
            self.ctx.set_status("No image loaded")
            return
        try:
            from xprinter import RasterMode

            mode_val = _RASTER_MAP[self._mode_var.get()]
            mode = RasterMode(mode_val)
            max_w = max(1, self._max_width_var.get())
            self.ctx.printer.print_image(self._pil_image, mode=mode, max_width=max_w)
            self.ctx.printer.feed_lines(2)
            self.ctx.set_status("Image printed")
        except Exception as exc:
            self.ctx.set_status(f"Print error: {exc}")
