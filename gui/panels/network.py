"""Network configuration panel — WiFi and LAN tabs."""
from __future__ import annotations

import customtkinter as ctk

from gui.context import AppContext
from gui.widgets.ip_field import IPField

_WIFI_KEY_TYPES = [
    "NULL (open)",
    "WEP64",
    "WEP128",
    "WPA_AES_PSK",
    "WPA_TKIP_PSK",
    "WPA_TKIP_AES_PSK",
    "WPA2_AES_PSK",
    "WPA2_TKIP",
    "WPA2_TKIP_AES_PSK",
    "WPA_WPA2_MIXED",
]


class NetworkPanel(ctk.CTkFrame):
    def __init__(self, master, ctx: AppContext):
        super().__init__(master, corner_radius=0, fg_color="transparent")
        self.ctx = ctx
        self.grid_columnconfigure(0, weight=1)
        self._build()

    def _build(self) -> None:
        ctk.CTkLabel(self, text="Network Configuration", font=ctk.CTkFont(size=20, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=24, pady=(20, 4)
        )
        ctk.CTkLabel(
            self,
            text="Configure WiFi or wired LAN. A power cycle is required after applying.",
            text_color="gray60",
        ).grid(row=1, column=0, sticky="w", padx=24, pady=(0, 8))

        self._tabs = ctk.CTkTabview(self)
        self._tabs.grid(row=2, column=0, sticky="nsew", padx=24, pady=8)
        self.grid_rowconfigure(2, weight=1)

        self._tabs.add("WiFi")
        self._tabs.add("LAN")

        self._build_wifi(self._tabs.tab("WiFi"))
        self._build_lan(self._tabs.tab("LAN"))

    # ------------------------------------------------------------------
    # WiFi tab
    # ------------------------------------------------------------------

    def _build_wifi(self, parent) -> None:
        parent.grid_columnconfigure(1, weight=1)

        fields = [
            ("SSID:", "ssid", False),
            ("Password / Key:", "key", True),
        ]
        self._wifi_vars: dict[str, ctk.StringVar] = {}

        for row, (label, name, masked) in enumerate(fields):
            ctk.CTkLabel(parent, text=label).grid(row=row, column=0, padx=12, pady=10, sticky="w")
            var = ctk.StringVar()
            self._wifi_vars[name] = var
            entry = ctk.CTkEntry(parent, textvariable=var, show="●" if masked else "", width=240)
            entry.grid(row=row, column=1, padx=12, pady=10, sticky="ew")

        # Key type
        ctk.CTkLabel(parent, text="Security type:").grid(row=2, column=0, padx=12, pady=10, sticky="w")
        self._key_type_var = ctk.StringVar(value=_WIFI_KEY_TYPES[6])
        ctk.CTkOptionMenu(parent, values=_WIFI_KEY_TYPES, variable=self._key_type_var, width=240).grid(
            row=2, column=1, padx=12, pady=10, sticky="ew"
        )

        # IP fields
        for row, (label, attr) in enumerate([
            ("IP Address:", "_wifi_ip"),
            ("Subnet Mask:", "_wifi_mask"),
            ("Gateway:", "_wifi_gw"),
        ], start=3):
            ctk.CTkLabel(parent, text=label).grid(row=row, column=0, padx=12, pady=10, sticky="w")
            field = IPField(parent)
            field.grid(row=row, column=1, padx=12, pady=10, sticky="w")
            setattr(self, attr, field)

        warn = ctk.CTkLabel(
            parent,
            text="Power cycle the printer after applying WiFi settings.",
            text_color="#e67e22",
            font=ctk.CTkFont(size=12),
        )
        warn.grid(row=6, column=0, columnspan=2, padx=12, pady=(12, 4), sticky="w")

        ctk.CTkButton(parent, text="Apply WiFi Settings", command=self._do_apply_wifi).grid(
            row=7, column=0, columnspan=2, padx=12, pady=12, sticky="w"
        )

    # ------------------------------------------------------------------
    # LAN tab
    # ------------------------------------------------------------------

    def _build_lan(self, parent) -> None:
        parent.grid_columnconfigure(1, weight=1)

        for row, (label, attr) in enumerate([
            ("IP Address:", "_lan_ip"),
            ("Subnet Mask:", "_lan_mask"),
            ("Gateway:", "_lan_gw"),
        ]):
            ctk.CTkLabel(parent, text=label).grid(row=row, column=0, padx=12, pady=10, sticky="w")
            field = IPField(parent)
            field.grid(row=row, column=1, padx=12, pady=10, sticky="w")
            setattr(self, attr, field)

        warn = ctk.CTkLabel(
            parent,
            text="Power cycle the printer after applying LAN settings.",
            text_color="#e67e22",
            font=ctk.CTkFont(size=12),
        )
        warn.grid(row=3, column=0, columnspan=2, padx=12, pady=(12, 4), sticky="w")

        ctk.CTkButton(parent, text="Apply LAN Settings", command=self._do_apply_lan).grid(
            row=4, column=0, columnspan=2, padx=12, pady=12, sticky="w"
        )

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _current_device(self) -> str | None:
        """Return the device path from the connection panel via the printer's _device attr, or None."""
        if self.ctx.connected and hasattr(self.ctx.printer, "_device"):
            return self.ctx.printer._device
        return None

    def _do_apply_wifi(self) -> None:
        from xprinter import NetworkConfig

        for field in (self._wifi_ip, self._wifi_mask, self._wifi_gw):
            if not field.valid():
                self.ctx.set_status("Invalid IP address — check WiFi fields")
                return

        device = self._current_device()
        if device is None:
            self.ctx.set_status("Connect to printer first to know device path")
            return

        key_index = _WIFI_KEY_TYPES.index(self._key_type_var.get())
        try:
            NetworkConfig.set_wifi(
                device,
                ip=self._wifi_ip.value(),
                mask=self._wifi_mask.value(),
                gateway=self._wifi_gw.value(),
                ssid=self._wifi_vars["ssid"].get(),
                key=self._wifi_vars["key"].get(),
                key_type=key_index,
            )
            self.ctx.set_status("WiFi settings applied — power cycle the printer")
        except Exception as exc:
            self.ctx.set_status(f"WiFi error: {exc}")

    def _do_apply_lan(self) -> None:
        from xprinter import NetworkConfig

        for field in (self._lan_ip, self._lan_mask, self._lan_gw):
            if not field.valid():
                self.ctx.set_status("Invalid IP address — check LAN fields")
                return

        device = self._current_device()
        if device is None:
            self.ctx.set_status("Connect to printer first to know device path")
            return

        try:
            NetworkConfig.set_lan(
                device,
                ip=self._lan_ip.value(),
                mask=self._lan_mask.value(),
                gateway=self._lan_gw.value(),
            )
            self.ctx.set_status("LAN settings applied — power cycle the printer")
        except Exception as exc:
            self.ctx.set_status(f"LAN error: {exc}")
