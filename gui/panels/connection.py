"""Connection panel — device path, connect/disconnect, basic controls."""
from __future__ import annotations

import glob

import customtkinter as ctk

from gui.context import AppContext


def _detect_devices() -> list[str]:
    candidates = glob.glob("/dev/usb/lp*") + glob.glob("/dev/ttyUSB*") + glob.glob("/dev/ttyS*")
    return sorted(candidates) or ["/dev/usb/lp0"]


class ConnectionPanel(ctk.CTkFrame):
    def __init__(self, master, ctx: AppContext):
        super().__init__(master, corner_radius=0, fg_color="transparent")
        self.ctx = ctx
        self.grid_columnconfigure(0, weight=1)
        self._build()
        ctx.on_connect(lambda _p: self._on_connect())
        ctx.on_disconnect(self._on_disconnect)

    def _build(self) -> None:
        pad = {"padx": 24, "pady": 8}

        ctk.CTkLabel(self, text="Printer Connection", font=ctk.CTkFont(size=20, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=24, pady=(20, 4)
        )
        ctk.CTkLabel(self, text="Configure and open the printer device file.", text_color="gray60").grid(
            row=1, column=0, sticky="w", **pad
        )

        # ── Device path ──────────────────────────────────────────────
        frame = ctk.CTkFrame(self)
        frame.grid(row=2, column=0, sticky="ew", padx=24, pady=16)
        frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(frame, text="Device path:").grid(row=0, column=0, padx=12, pady=12, sticky="w")

        self._device_var = ctk.StringVar(value=_detect_devices()[0])
        self._device_entry = ctk.CTkEntry(frame, textvariable=self._device_var, width=240)
        self._device_entry.grid(row=0, column=1, padx=8, pady=12, sticky="ew")

        self._detect_btn = ctk.CTkButton(frame, text="Detect", width=80, command=self._do_detect)
        self._detect_btn.grid(row=0, column=2, padx=(0, 12), pady=12)

        # ── Connect/Disconnect ───────────────────────────────────────
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=3, column=0, sticky="w", padx=24, pady=8)

        self._connect_btn = ctk.CTkButton(
            btn_frame,
            text="Connect",
            width=120,
            command=self._do_connect,
            fg_color="#27ae60",
            hover_color="#1e8449",
        )
        self._connect_btn.grid(row=0, column=0, padx=(0, 8))

        self._disconnect_btn = ctk.CTkButton(
            btn_frame,
            text="Disconnect",
            width=120,
            command=self._do_disconnect,
            fg_color="#c0392b",
            hover_color="#922b21",
            state="disabled",
        )
        self._disconnect_btn.grid(row=0, column=1)

        # ── Printer controls ─────────────────────────────────────────
        ctrl_frame = ctk.CTkFrame(self)
        ctrl_frame.grid(row=4, column=0, sticky="ew", padx=24, pady=16)

        ctk.CTkLabel(ctrl_frame, text="Printer Controls", font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, columnspan=3, padx=12, pady=(12, 6), sticky="w"
        )

        self._enable_var = ctk.BooleanVar(value=True)
        self._enable_switch = ctk.CTkSwitch(
            ctrl_frame,
            text="Printer Enabled",
            variable=self._enable_var,
            command=self._do_set_enabled,
            state="disabled",
        )
        self._enable_switch.grid(row=1, column=0, padx=12, pady=8, sticky="w")

        self._recover_btn = ctk.CTkButton(
            ctrl_frame,
            text="Error Recovery",
            command=self._do_recover,
            state="disabled",
            fg_color="#e67e22",
            hover_color="#ca6f1e",
        )
        self._recover_btn.grid(row=1, column=1, padx=12, pady=8)

        self._clear_buf_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(ctrl_frame, text="Clear buffers on recovery", variable=self._clear_buf_var).grid(
            row=1, column=2, padx=12, pady=8
        )

        # ── Info box ─────────────────────────────────────────────────
        info = ctk.CTkFrame(self, fg_color=("gray85", "gray18"))
        info.grid(row=5, column=0, sticky="ew", padx=24, pady=8)
        ctk.CTkLabel(
            info,
            text=(
                "On Linux, the USB device is usually  /dev/usb/lp0.\n"
                "Run  ls /dev/usb/  or  ls /dev/ttyUSB*  to list available devices.\n"
                "You may need to be in the  lp  group:  sudo usermod -aG lp $USER"
            ),
            justify="left",
            text_color="gray60",
            font=ctk.CTkFont(size=12),
        ).grid(padx=14, pady=10)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _do_detect(self) -> None:
        devices = _detect_devices()
        self._device_var.set(devices[0])
        self.ctx.set_status(f"Detected devices: {', '.join(devices)}")

    def _do_connect(self) -> None:
        from xprinter import XPrinter

        path = self._device_var.get().strip()
        if not path:
            self.ctx.set_status("Device path is empty")
            return
        try:
            printer = XPrinter(path)
            self.ctx.connect(printer)
            self.ctx.set_status(f"Connected to {path}")
        except Exception as exc:
            self.ctx.set_status(f"Connection failed: {exc}")

    def _do_disconnect(self) -> None:
        self.ctx.disconnect()
        self.ctx.set_status("Disconnected")

    def _do_set_enabled(self) -> None:
        if not self.ctx.connected:
            return
        try:
            self.ctx.printer.set_device_enabled(self._enable_var.get())
            self.ctx.set_status(f"Printer {'enabled' if self._enable_var.get() else 'disabled'}")
        except Exception as exc:
            self.ctx.set_status(f"Error: {exc}")

    def _do_recover(self) -> None:
        if not self.ctx.connected:
            return
        try:
            self.ctx.printer.request_error_recovery(self._clear_buf_var.get())
            self.ctx.set_status("Error recovery sent")
        except Exception as exc:
            self.ctx.set_status(f"Error: {exc}")

    # ------------------------------------------------------------------
    # Context callbacks
    # ------------------------------------------------------------------

    def _on_connect(self) -> None:
        self._connect_btn.configure(state="disabled")
        self._disconnect_btn.configure(state="normal")
        self._enable_switch.configure(state="normal")
        self._recover_btn.configure(state="normal")

    def _on_disconnect(self) -> None:
        self._connect_btn.configure(state="normal")
        self._disconnect_btn.configure(state="disabled")
        self._enable_switch.configure(state="disabled")
        self._recover_btn.configure(state="disabled")
