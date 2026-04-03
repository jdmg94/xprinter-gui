"""Root application window with sidebar navigation."""
from __future__ import annotations

import customtkinter as ctk

from gui.context import AppContext
from gui.widgets.status_dot import StatusDot
from gui.panels.connection import ConnectionPanel
from gui.panels.status import StatusPanel
from gui.panels.network import NetworkPanel
from gui.panels.print_mode import PrintModePanel
from gui.panels.paper_cut import PaperCutPanel
from gui.panels.barcode import BarcodePanel
from gui.panels.image import ImagePanel
from gui.panels.drawer import DrawerPanel
from gui.panels.advanced import AdvancedPanel

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

_NAV_ITEMS = [
    ("Connection", ConnectionPanel),
    ("Status", StatusPanel),
    ("Network", NetworkPanel),
    ("Print Mode", PrintModePanel),
    ("Paper / Cut", PaperCutPanel),
    ("Barcode", BarcodePanel),
    ("Image", ImagePanel),
    ("Cash Drawer", DrawerPanel),
    ("Advanced", AdvancedPanel),
]


class App(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("XPrinter Config Tool")
        self.geometry("1000x680")
        self.minsize(900, 600)

        self.ctx = AppContext()
        self.ctx.on_connect(lambda _p: self._on_connect())
        self.ctx.on_disconnect(self._on_disconnect)
        self.ctx.on_status(self._push_status)

        self._build_ui()
        self._active_panel: ctk.CTkFrame | None = None
        self._nav_buttons: dict[str, ctk.CTkButton] = {}
        self._panels: dict[str, ctk.CTkFrame] = {}

        self._populate_nav()
        self._show_panel("Connection")

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ── Sidebar ──────────────────────────────────────────────────
        self._sidebar = ctk.CTkFrame(self, width=180, corner_radius=0)
        self._sidebar.grid(row=0, column=0, rowspan=2, sticky="nsew")
        self._sidebar.grid_rowconfigure(20, weight=1)

        logo = ctk.CTkLabel(
            self._sidebar,
            text="XPrinter\nConfig Tool",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        logo.grid(row=0, column=0, padx=16, pady=(20, 10))

        ctk.CTkLabel(self._sidebar, text="─" * 18, text_color="gray50").grid(
            row=1, column=0, padx=8, pady=2
        )

        # nav buttons inserted in _populate_nav()

        # spacer row 20 expands — then footer buttons at bottom
        self._test_btn = ctk.CTkButton(
            self._sidebar,
            text="Test Print",
            command=self._do_test_print,
            state="disabled",
            fg_color="#2980b9",
            hover_color="#1a6a9a",
        )
        self._test_btn.grid(row=21, column=0, padx=12, pady=6, sticky="ew")

        self._init_btn = ctk.CTkButton(
            self._sidebar,
            text="Re-Initialize",
            command=self._do_initialize,
            state="disabled",
            fg_color="#7f8c8d",
            hover_color="#5d6d7e",
        )
        self._init_btn.grid(row=22, column=0, padx=12, pady=(0, 16), sticky="ew")

        # ── Main frame ───────────────────────────────────────────────
        self._main = ctk.CTkFrame(self, corner_radius=0)
        self._main.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        self._main.grid_rowconfigure(0, weight=1)
        self._main.grid_columnconfigure(0, weight=1)

        # ── Status bar ───────────────────────────────────────────────
        statusbar = ctk.CTkFrame(self, height=28, corner_radius=0, fg_color=("gray80", "gray20"))
        statusbar.grid(row=1, column=1, sticky="ew")
        statusbar.grid_columnconfigure(0, weight=1)

        self._status_label = ctk.CTkLabel(
            statusbar, text="Not connected", anchor="w", font=ctk.CTkFont(size=12)
        )
        self._status_label.grid(row=0, column=0, padx=10, sticky="ew")

        self._conn_dot = StatusDot(statusbar)
        self._conn_dot.grid(row=0, column=1, padx=(0, 10))

        self._conn_text = ctk.CTkLabel(statusbar, text="Disconnected", font=ctk.CTkFont(size=12))
        self._conn_text.grid(row=0, column=2, padx=(0, 12))

    def _populate_nav(self) -> None:
        for row_idx, (label, panel_cls) in enumerate(_NAV_ITEMS, start=2):
            btn = ctk.CTkButton(
                self._sidebar,
                text=label,
                anchor="w",
                command=lambda l=label: self._show_panel(l),
                fg_color="transparent",
                text_color=("gray10", "gray90"),
                hover_color=("gray75", "gray30"),
                corner_radius=6,
            )
            btn.grid(row=row_idx, column=0, padx=8, pady=2, sticky="ew")
            self._nav_buttons[label] = btn

            panel = panel_cls(self._main, self.ctx)
            panel.grid(row=0, column=0, sticky="nsew")
            panel.grid_remove()
            self._panels[label] = panel

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _show_panel(self, name: str) -> None:
        if self._active_panel is not None:
            self._active_panel.grid_remove()
        for label, btn in self._nav_buttons.items():
            btn.configure(
                fg_color=("gray75", "gray30") if label == name else "transparent"
            )
        panel = self._panels[name]
        panel.grid()
        self._active_panel = panel

    # ------------------------------------------------------------------
    # Connection callbacks
    # ------------------------------------------------------------------

    def _on_connect(self) -> None:
        self._conn_dot.set("green")
        self._conn_text.configure(text="Connected")
        self._test_btn.configure(state="normal")
        self._init_btn.configure(state="normal")

    def _on_disconnect(self) -> None:
        self._conn_dot.set("red")
        self._conn_text.configure(text="Disconnected")
        self._test_btn.configure(state="disabled")
        self._init_btn.configure(state="disabled")

    def _push_status(self, msg: str) -> None:
        self._status_label.configure(text=msg)

    # ------------------------------------------------------------------
    # Global actions
    # ------------------------------------------------------------------

    def _do_test_print(self) -> None:
        if not self.ctx.connected:
            return
        p = self.ctx.printer
        try:
            p.initialize()
            p.print_separator()
            p.set_justification("center")
            p.println("XPrinter Config Tool")
            p.println("Test Print")
            p.print_separator()
            p.set_justification("left")
            p.println("Left aligned text")
            p.set_justification("center")
            p.println("Center aligned text")
            p.set_justification("right")
            p.println("Right aligned text")
            p.set_justification("left")
            p.print_separator()
            p.set_barcode_hri("below")
            p.print_barcode("CODE128", "XPRINTER")
            p.feed_lines(3)
            p.cut()
            self.ctx.set_status("Test print sent")
        except Exception as exc:
            self.ctx.set_status(f"Test print error: {exc}")

    def _do_initialize(self) -> None:
        if not self.ctx.connected:
            return
        try:
            self.ctx.printer.initialize()
            self.ctx.set_status("Printer re-initialized")
        except Exception as exc:
            self.ctx.set_status(f"Initialize error: {exc}")
