"""Cash Drawer panel — buffered and real-time pulse controls."""
from __future__ import annotations

import customtkinter as ctk

from gui.context import AppContext


class DrawerPanel(ctk.CTkFrame):
    def __init__(self, master, ctx: AppContext):
        super().__init__(master, corner_radius=0, fg_color="transparent")
        self.ctx = ctx
        self.grid_columnconfigure((0, 1), weight=1)
        self._build()

    def _build(self) -> None:
        ctk.CTkLabel(self, text="Cash Drawer", font=ctk.CTkFont(size=20, weight="bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=24, pady=(20, 4)
        )
        ctk.CTkLabel(
            self,
            text="Control the cash drawer connected to the printer's RJ-11 port.",
            text_color="gray60",
        ).grid(row=1, column=0, columnspan=2, sticky="w", padx=24, pady=(0, 8))

        # ── Buffered pulse ───────────────────────────────────────────
        buf = ctk.CTkFrame(self)
        buf.grid(row=2, column=0, sticky="nsew", padx=(24, 8), pady=8)
        buf.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(buf, text="Buffered Pulse", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, columnspan=2, padx=12, pady=(12, 6), sticky="w"
        )
        ctk.CTkLabel(buf, text="Goes through print buffer — may be delayed.", text_color="gray60",
                     font=ctk.CTkFont(size=11)).grid(row=1, column=0, columnspan=2, padx=12, pady=(0, 6), sticky="w")

        ctk.CTkLabel(buf, text="Pin:").grid(row=2, column=0, padx=12, pady=8, sticky="w")
        self._pin_var = ctk.StringVar(value="Pin 0 (connector pin 2)")
        ctk.CTkSegmentedButton(
            buf,
            values=["Pin 0 (connector pin 2)", "Pin 1 (connector pin 5)"],
            variable=self._pin_var,
        ).grid(row=2, column=1, padx=12, pady=8, sticky="w")

        ctk.CTkLabel(buf, text="On-time (ms):").grid(row=3, column=0, padx=12, pady=8, sticky="w")
        self._on_ms = ctk.IntVar(value=100)
        ctk.CTkEntry(buf, textvariable=self._on_ms, width=80).grid(row=3, column=1, padx=12, pady=8, sticky="w")

        ctk.CTkLabel(buf, text="Off-time (ms):").grid(row=4, column=0, padx=12, pady=8, sticky="w")
        self._off_ms = ctk.IntVar(value=100)
        ctk.CTkEntry(buf, textvariable=self._off_ms, width=80).grid(row=4, column=1, padx=12, pady=8, sticky="w")

        ctk.CTkButton(buf, text="Pulse (Buffered)", command=self._do_buffered).grid(
            row=5, column=0, columnspan=2, padx=12, pady=12, sticky="w"
        )

        # ── Real-time pulse ──────────────────────────────────────────
        rt = ctk.CTkFrame(self)
        rt.grid(row=2, column=1, sticky="nsew", padx=(8, 24), pady=8)
        rt.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(rt, text="Real-Time Pulse", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, columnspan=2, padx=12, pady=(12, 6), sticky="w"
        )
        ctk.CTkLabel(rt, text="Bypasses print buffer — immediate response.", text_color="gray60",
                     font=ctk.CTkFont(size=11)).grid(row=1, column=0, columnspan=2, padx=12, pady=(0, 6), sticky="w")

        ctk.CTkLabel(rt, text="Pin:").grid(row=2, column=0, padx=12, pady=8, sticky="w")
        self._rt_pin_var = ctk.StringVar(value="Pin 0 (connector pin 2)")
        ctk.CTkSegmentedButton(
            rt,
            values=["Pin 0 (connector pin 2)", "Pin 1 (connector pin 5)"],
            variable=self._rt_pin_var,
        ).grid(row=2, column=1, padx=12, pady=8, sticky="w")

        ctk.CTkLabel(rt, text="Pulse units (1–8)\neach = 100ms on + 100ms off:").grid(
            row=3, column=0, padx=12, pady=8, sticky="w"
        )
        self._rt_units = ctk.IntVar(value=2)
        ctk.CTkSlider(rt, from_=1, to=8, number_of_steps=7, variable=self._rt_units, width=130).grid(
            row=3, column=1, padx=12, pady=8, sticky="w"
        )

        ctk.CTkButton(rt, text="Pulse (Real-Time)", command=self._do_realtime).grid(
            row=4, column=0, columnspan=2, padx=12, pady=12, sticky="w"
        )

        # ── Status query ─────────────────────────────────────────────
        status_frame = ctk.CTkFrame(self, fg_color="transparent")
        status_frame.grid(row=3, column=0, columnspan=2, sticky="w", padx=24, pady=8)
        ctk.CTkButton(status_frame, text="Query Drawer Status", command=self._do_status, width=160).grid(
            row=0, column=0
        )
        self._status_label = ctk.CTkLabel(status_frame, text="", text_color="gray60")
        self._status_label.grid(row=0, column=1, padx=12)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _pin_index(self, var: ctk.StringVar) -> int:
        return 0 if "Pin 0" in var.get() else 1

    def _do_buffered(self) -> None:
        if not self.ctx.connected:
            self.ctx.set_status("Not connected")
            return
        try:
            pin = self._pin_index(self._pin_var)
            self.ctx.printer.kick_drawer(pin, self._on_ms.get(), self._off_ms.get())
            self.ctx.set_status(f"Buffered pulse sent on pin {pin}")
        except Exception as exc:
            self.ctx.set_status(f"Error: {exc}")

    def _do_realtime(self) -> None:
        if not self.ctx.connected:
            self.ctx.set_status("Not connected")
            return
        try:
            pin = self._pin_index(self._rt_pin_var)
            units = max(1, min(8, int(self._rt_units.get())))
            self.ctx.printer.kick_drawer_realtime(pin, units)
            self.ctx.set_status(f"Real-time pulse sent on pin {pin} ({units} units)")
        except Exception as exc:
            self.ctx.set_status(f"Error: {exc}")

    def _do_status(self) -> None:
        if not self.ctx.connected:
            self.ctx.set_status("Not connected")
            return
        try:
            raw = self.ctx.printer.transmit_status(paper=False)
            if raw is None:
                self._status_label.configure(text="No response")
            else:
                drawer_open = bool(raw & 0x04)
                self._status_label.configure(
                    text=f"Drawer: {'OPEN' if drawer_open else 'CLOSED'}  (raw: 0x{raw:02X})"
                )
            self.ctx.set_status("Drawer status queried")
        except Exception as exc:
            self.ctx.set_status(f"Error: {exc}")
