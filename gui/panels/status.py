"""Status dashboard — live-polling printer status readouts."""
from __future__ import annotations

import customtkinter as ctk

from gui.context import AppContext

_POLL_MS = 2000

# status_type → (label, key list from get_status dict)
_STATUS_SECTIONS = [
    (1, "Printer Status", [
        ("online", "Online"),
        ("paper_feed_button_pressed", "Feed button pressed"),
        ("paper_sensor_error", "Paper sensor error"),
        ("paper_stop_sensor_error", "Paper stop sensor error"),
        ("auto_cut_error", "Auto-cut error"),
        ("unrecoverable_error", "Unrecoverable error"),
        ("auto_recoverable_error", "Auto-recoverable error"),
    ]),
    (2, "Offline Status", [
        ("cover_open", "Cover open"),
        ("paper_feed_button_pressed", "Feed button pressed"),
        ("paper_end", "Paper end"),
        ("error", "Error occurred"),
    ]),
    (3, "Error Status", [
        ("cutter_error", "Cutter error"),
        ("unrecoverable_error", "Unrecoverable error"),
        ("auto_recoverable_error", "Auto-recoverable error"),
        ("paper_feed_error", "Paper feed error"),
    ]),
    (4, "Paper Sensor Status", [
        ("paper_roll_near_end", "Roll near-end"),
        ("paper_roll_end", "Roll end"),
        ("external_near_end", "External near-end"),
        ("external_end", "External end"),
    ]),
]


def _bool_color(val: bool) -> str:
    return "#2ecc71" if val else "#e74c3c"


class StatusPanel(ctk.CTkFrame):
    def __init__(self, master, ctx: AppContext):
        super().__init__(master, corner_radius=0, fg_color="transparent")
        self.ctx = ctx
        self.grid_columnconfigure((0, 1), weight=1)
        self._indicators: dict[tuple[int, str], ctk.CTkLabel] = {}
        self._polling = False
        self._build()
        ctx.on_connect(lambda _p: self._start_polling())
        ctx.on_disconnect(self._stop_polling)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build(self) -> None:
        ctk.CTkLabel(self, text="Printer Status", font=ctk.CTkFont(size=20, weight="bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=24, pady=(20, 4)
        )

        # ASB row
        asb_frame = ctk.CTkFrame(self)
        asb_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=24, pady=8)
        ctk.CTkLabel(asb_frame, text="Auto Status Back (ASB):", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, padx=12, pady=8, sticky="w"
        )
        self._asb_drawer = ctk.BooleanVar()
        self._asb_online = ctk.BooleanVar()
        self._asb_error = ctk.BooleanVar()
        self._asb_paper = ctk.BooleanVar()
        for col, (var, lbl) in enumerate([
            (self._asb_drawer, "Drawer"),
            (self._asb_online, "Online/Offline"),
            (self._asb_error, "Error"),
            (self._asb_paper, "Paper Sensor"),
        ], start=1):
            ctk.CTkCheckBox(asb_frame, text=lbl, variable=var, command=self._apply_asb).grid(
                row=0, column=col, padx=10, pady=8
            )

        # Status sections in a 2×2 grid
        for idx, (status_type, section_title, keys) in enumerate(_STATUS_SECTIONS):
            col = idx % 2
            row = 2 + (idx // 2)
            self._build_section(row, col, status_type, section_title, keys)

        # Refresh / poll controls
        ctrl = ctk.CTkFrame(self, fg_color="transparent")
        ctrl.grid(row=4, column=0, columnspan=2, sticky="w", padx=24, pady=12)

        ctk.CTkButton(ctrl, text="Refresh Now", command=self._poll_once, width=120).grid(
            row=0, column=0, padx=(0, 12)
        )
        self._poll_label = ctk.CTkLabel(ctrl, text="Auto-poll: off", text_color="gray60")
        self._poll_label.grid(row=0, column=1)

    def _build_section(self, row: int, col: int, status_type: int, title: str, keys: list) -> None:
        frame = ctk.CTkFrame(self)
        frame.grid(row=row, column=col, sticky="nsew", padx=(24 if col == 0 else 8, 24 if col == 1 else 8), pady=6)
        frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(frame, text=title, font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, columnspan=2, padx=12, pady=(10, 4), sticky="w"
        )
        for r, (key, label) in enumerate(keys, start=1):
            ctk.CTkLabel(frame, text=label).grid(row=r, column=0, padx=12, pady=3, sticky="w")
            dot = ctk.CTkLabel(frame, text="●", text_color="gray50", font=ctk.CTkFont(size=16))
            dot.grid(row=r, column=1, padx=12, pady=3, sticky="e")
            self._indicators[(status_type, key)] = dot

    # ------------------------------------------------------------------
    # Polling
    # ------------------------------------------------------------------

    def _start_polling(self) -> None:
        self._polling = True
        self._poll_label.configure(text=f"Auto-poll: every {_POLL_MS // 1000}s")
        self._schedule_poll()

    def _stop_polling(self) -> None:
        self._polling = False
        self._poll_label.configure(text="Auto-poll: off")
        for dot in self._indicators.values():
            dot.configure(text_color="gray50")

    def _schedule_poll(self) -> None:
        if self._polling:
            self._poll_once()
            self.after(_POLL_MS, self._schedule_poll)

    def _poll_once(self) -> None:
        if not self.ctx.connected:
            return
        for status_type, _title, keys in _STATUS_SECTIONS:
            try:
                result = self.ctx.printer.get_status(status_type)
            except Exception:
                result = {}
            for key, _label in keys:
                dot = self._indicators.get((status_type, key))
                if dot is None:
                    continue
                val = result.get(key)
                if val is None:
                    dot.configure(text_color="gray50")
                else:
                    dot.configure(text_color=_bool_color(not val if key in ("online",) else val))

    # ------------------------------------------------------------------
    # ASB
    # ------------------------------------------------------------------

    def _apply_asb(self) -> None:
        if not self.ctx.connected:
            return
        try:
            self.ctx.printer.set_auto_status_back(
                drawer=self._asb_drawer.get(),
                online_offline=self._asb_online.get(),
                error=self._asb_error.get(),
                paper_sensor=self._asb_paper.get(),
            )
            self.ctx.set_status("ASB settings applied")
        except Exception as exc:
            self.ctx.set_status(f"ASB error: {exc}")
