#!/usr/bin/env python3
"""
xprinter.py — Full-featured XP-80T thermal printer driver.

Implements the ESC/POS command set from the 80XX Programmer Manual,
plus the proprietary network configuration protocol from
https://github.com/dantecatalfamo/xprinter-wifi/blob/master/xprinter-wifi.rb

Architecture
────────────
    XPrinter          Manages the device handle; sends raw bytes.
    ├── Phase 1       Lifecycle: initialize, status, enable/disable
    ├── Phase 2       Text formatting & print modes
    ├── Phase 3       Line spacing, paper feed & cutting
    ├── Phase 4       Barcode printing
    ├── Phase 5       Raster bit-image printing
    ├── Phase 6       Cash drawer control
    ├── Phase 7       Character sets & code pages
    ├── Phase 8       Margins, print area & motion units
    └── Phase 9       NV bit images & macros

    NetworkConfig     Static helpers for WiFi / LAN setup (standalone)

Usage
─────
    from xprinter import XPrinter, NetworkConfig

    # ── Print a receipt ──
    p = XPrinter("/dev/usb/lp0")
    p.initialize()
    p.set_justification("center")
    p.set_character_size(2, 2)
    p.println("MY STORE")
    p.set_character_size(1, 1)
    p.set_justification("left")
    p.println("Item 1          $5.00")
    p.println("Item 2          $3.50")
    p.set_emphasized(True)
    p.println("TOTAL           $8.50")
    p.set_emphasized(False)
    p.print_barcode("CODE128", "ABC-123456")
    p.feed_lines(3)
    p.cut()
    p.close()

    # ── Configure network ──
    NetworkConfig.set_wifi("/dev/usb/lp0",
        ip="192.168.1.100", mask="255.255.255.0", gateway="192.168.1.1",
        ssid="Office", key="secret", key_type=6)
"""

from __future__ import annotations

import enum
import ipaddress
import os
import struct
import sys
import time
from typing import Optional, Union


# ═══════════════════════════════════════════════════════════════════════
#  Constants
# ═══════════════════════════════════════════════════════════════════════

# ── ESC/POS control bytes ─────────────────────────────────────────────
NUL = b"\x00"
HT  = b"\x09"
LF  = b"\x0a"
FF  = b"\x0c"
CR  = b"\x0d"
CAN = b"\x18"
DLE = b"\x10"
EOT = b"\x04"
ENQ = b"\x05"
DC4 = b"\x14"
ESC = b"\x1b"
FS  = b"\x1c"
GS  = b"\x1d"
US  = b"\x1f"

# ── Network config (proprietary Xprinter protocol) ───────────────────
NET_PREAMBLE = US + ESC + US
NET_COMMAND  = b"\xb4"
NET_PORT     = 9100


# ═══════════════════════════════════════════════════════════════════════
#  Enumerations
# ═══════════════════════════════════════════════════════════════════════

class Justification(enum.IntEnum):
    LEFT   = 0
    CENTER = 1
    RIGHT  = 2


class UnderlineMode(enum.IntEnum):
    OFF       = 0
    THIN      = 1   # 1-dot
    THICK     = 2   # 2-dot


class CutMode(enum.IntEnum):
    PARTIAL       = 1    # GS V m  (m=1)
    PARTIAL_FEED  = 66   # GS V m n


class BarcodeHRI(enum.IntEnum):
    HIDDEN = 0
    ABOVE  = 1
    BELOW  = 2
    BOTH   = 3


class BarcodeSystem(enum.IntEnum):
    """Format ② values (GS k m n d1..dn)."""
    UPC_A   = 65
    UPC_E   = 66
    EAN13   = 67
    EAN8    = 68
    CODE39  = 69
    ITF     = 70
    CODABAR = 71
    CODE93  = 72
    CODE128 = 73


class RasterMode(enum.IntEnum):
    NORMAL        = 0
    DOUBLE_WIDTH  = 1
    DOUBLE_HEIGHT = 2
    QUADRUPLE     = 3


class StatusType(enum.IntEnum):
    PRINTER      = 1
    OFFLINE      = 2
    ERROR        = 3
    PAPER_SENSOR = 4


class WifiKeyType(enum.IntEnum):
    NULL               = 0
    WEP64              = 1
    WEP128             = 2
    WPA_AES_PSK        = 3
    WPA_TKIP_PSK       = 4
    WPA_TKIP_AES_PSK   = 5
    WPA2_AES_PSK       = 6
    WPA2_TKIP          = 7
    WPA2_TKIP_AES_PSK  = 8
    WPA_WPA2_MIXED     = 9


class CodePage(enum.IntEnum):
    PC437       = 0    # U.S.A. / Standard Europe
    KATAKANA    = 1
    PC850       = 2    # Multilingual
    PC860       = 3    # Portuguese
    PC863       = 4    # Canadian French
    PC865       = 5    # Nordic
    WEST_EUROPE = 6
    GREEK       = 7
    HEBREW      = 8
    PC755       = 9    # East Europe
    IRAN        = 10
    WPC1252     = 16
    PC866       = 17   # Cyrillic #2
    PC852       = 18   # Latin 2
    PC858       = 19
    IRAN_II     = 20
    LATVIAN     = 21


class InternationalCharset(enum.IntEnum):
    USA              = 0
    FRANCE           = 1
    GERMANY          = 2
    UK               = 3
    DENMARK_I        = 4
    SWEDEN           = 5
    ITALY            = 6
    SPAIN_I          = 7
    JAPAN            = 8
    NORWAY           = 9
    DENMARK_II       = 10
    SPAIN_II         = 11
    LATIN_AMERICA    = 12
    KOREA            = 13
    SLOVENIA_CROATIA = 14
    CHINESE          = 15


# ── Barcode system name → enum lookup ─────────────────────────────────
_BARCODE_NAMES = {
    "UPC-A":   BarcodeSystem.UPC_A,   "UPC_A":   BarcodeSystem.UPC_A,
    "UPC-E":   BarcodeSystem.UPC_E,   "UPC_E":   BarcodeSystem.UPC_E,
    "EAN13":   BarcodeSystem.EAN13,   "JAN13":   BarcodeSystem.EAN13,
    "EAN8":    BarcodeSystem.EAN8,    "JAN8":    BarcodeSystem.EAN8,
    "CODE39":  BarcodeSystem.CODE39,
    "ITF":     BarcodeSystem.ITF,
    "CODABAR": BarcodeSystem.CODABAR,
    "CODE93":  BarcodeSystem.CODE93,
    "CODE128": BarcodeSystem.CODE128,
}


# ═══════════════════════════════════════════════════════════════════════
#  Status Parsing Helpers
# ═══════════════════════════════════════════════════════════════════════

def parse_printer_status(byte_val: int) -> dict:
    """Parse DLE EOT n=1 response byte."""
    return {
        "drawer_closed":  bool(byte_val & 0x04),
        "offline":        bool(byte_val & 0x08),
    }


def parse_offline_status(byte_val: int) -> dict:
    """Parse DLE EOT n=2 response byte."""
    return {
        "cover_open":      bool(byte_val & 0x04),
        "feed_button":     bool(byte_val & 0x08),
        "printing_stopped": bool(byte_val & 0x20),
        "error":           bool(byte_val & 0x40),
    }


def parse_error_status(byte_val: int) -> dict:
    """Parse DLE EOT n=3 response byte."""
    return {
        "cutter_error":         bool(byte_val & 0x08),
        "unrecoverable_error":  bool(byte_val & 0x20),
        "auto_recoverable":     bool(byte_val & 0x40),
    }


def parse_paper_status(byte_val: int) -> dict:
    """Parse DLE EOT n=4 response byte."""
    return {
        "paper_near_end": bool(byte_val & 0x0C),
        "paper_end":      bool(byte_val & 0x60),
    }


_STATUS_PARSERS = {
    StatusType.PRINTER:      parse_printer_status,
    StatusType.OFFLINE:      parse_offline_status,
    StatusType.ERROR:        parse_error_status,
    StatusType.PAPER_SENSOR: parse_paper_status,
}


# ═══════════════════════════════════════════════════════════════════════
#  XPrinter — Main Driver Class
# ═══════════════════════════════════════════════════════════════════════

class XPrinter:
    """
    Full-featured driver for XP-80T (and compatible ESC/POS) thermal
    printers, communicating over a USB device file.

    All ``write`` calls go directly to the device and are flushed
    immediately so commands take effect without buffering surprises.
    """

    # ── Construction / teardown ───────────────────────────────────────

    def __init__(self, device: str, *, auto_init: bool = False):
        """
        Open the printer device for binary read/write.

        Args:
            device:    Path to the device file (e.g. ``/dev/usb/lp0``).
            auto_init: If True, send ``ESC @`` immediately after opening.
        """
        if not os.path.exists(device):
            raise FileNotFoundError(f"Device '{device}' does not exist")
        # r+b so we can both write commands and read status responses
        self._dev = open(device, "r+b", buffering=0)
        self._device_path = device
        if auto_init:
            self.initialize()

    def close(self) -> None:
        """Flush and close the device handle."""
        if self._dev and not self._dev.closed:
            self._dev.flush()
            self._dev.close()

    def __enter__(self) -> "XPrinter":
        return self

    def __exit__(self, *exc):
        self.close()

    # ── Low-level I/O ─────────────────────────────────────────────────

    def write(self, data: bytes) -> None:
        """Write raw bytes to the printer and flush."""
        self._dev.write(data)
        self._dev.flush()

    def read(self, n: int = 1, timeout: float = 1.0) -> bytes:
        """
        Read *n* bytes from the printer with a simple timeout.

        Returns whatever was read (may be less than *n* if the printer
        does not respond in time).  For status commands only.
        """
        self._dev.flush()
        # Simple blocking read — works for USB device files.
        # A production driver might use select() here.
        start = time.monotonic()
        buf = b""
        while len(buf) < n and (time.monotonic() - start) < timeout:
            try:
                chunk = self._dev.read(n - len(buf))
                if chunk:
                    buf += chunk
            except (BlockingIOError, OSError):
                time.sleep(0.01)
        return buf

    # ── Convenience text helpers ──────────────────────────────────────

    def println(self, text: str, encoding: str = "utf-8") -> None:
        """Encode *text*, write it, then send LF (print + line feed)."""
        self.write(text.encode(encoding) + LF)

    def print_text(self, text: str, encoding: str = "utf-8") -> None:
        """Write *text* to the buffer without a line feed."""
        self.write(text.encode(encoding))

    # ══════════════════════════════════════════════════════════════════
    #  PHASE 1 — Printer Lifecycle
    # ══════════════════════════════════════════════════════════════════

    def initialize(self) -> None:
        """
        ESC @  —  Reset the printer to power-on defaults.

        Clears the print buffer and resets all settings (font, spacing,
        margins, etc.) without clearing NV memory, macros, or the
        receive buffer.  Call this at the start of every print job.
        """
        self.write(ESC + b"\x40")

    def get_status(self, status_type: Union[StatusType, int] = StatusType.PRINTER) -> dict:
        """
        DLE EOT n  —  Request real-time status from the printer.

        Args:
            status_type: 1=printer, 2=offline, 3=error, 4=paper sensor

        Returns:
            A dict of parsed boolean flags (see ``parse_*_status``).
            Returns ``{"raw": None}`` if the printer does not respond.
        """
        n = int(status_type)
        if n < 1 or n > 4:
            raise ValueError(f"status_type must be 1-4, got {n}")
        self.write(DLE + EOT + bytes([n]))
        resp = self.read(1, timeout=2.0)
        if not resp:
            return {"raw": None, "error": "No response from printer"}
        parser = _STATUS_PARSERS.get(StatusType(n))
        result = parser(resp[0]) if parser else {}
        result["raw"] = resp[0]
        return result

    def set_device_enabled(self, enabled: bool = True) -> None:
        """
        ESC = n  —  Enable or disable the printer.

        When disabled the printer ignores everything except real-time
        error-recovery commands (DLE EOT, DLE ENQ, DLE DC4).
        """
        self.write(ESC + b"\x3d" + bytes([0x01 if enabled else 0x00]))

    def request_error_recovery(self, clear_buffers: bool = False) -> None:
        """
        DLE ENQ n  —  Recover from an error (e.g. auto-cutter jam).

        Args:
            clear_buffers: If False (n=1), retry from the error line.
                           If True  (n=2), clear buffers then recover.
        """
        n = 2 if clear_buffers else 1
        self.write(DLE + ENQ + bytes([n]))

    # ══════════════════════════════════════════════════════════════════
    #  PHASE 2 — Text Formatting & Print Modes
    # ══════════════════════════════════════════════════════════════════

    def set_print_mode(
        self,
        *,
        font_b: bool = False,
        emphasized: bool = False,
        double_height: bool = False,
        double_width: bool = False,
        underline: bool = False,
    ) -> None:
        """
        ESC ! n  —  Select print mode(s) in a single command.

        All flags default to off / Font A.  This overwrites previous
        mode bits — set everything you need in one call.
        """
        n = 0
        if font_b:        n |= 0x01
        if emphasized:     n |= 0x08
        if double_height:  n |= 0x10
        if double_width:   n |= 0x20
        if underline:      n |= 0x80
        self.write(ESC + b"\x21" + bytes([n]))

    def set_justification(self, align: Union[Justification, str, int] = Justification.LEFT) -> None:
        """
        ESC a n  —  Set text justification (left / center / right).

        Accepts Justification enum, int (0-2), or string
        ("left"/"center"/"right").
        """
        if isinstance(align, str):
            align = {"left": 0, "center": 1, "right": 2}[align.lower()]
        self.write(ESC + b"\x61" + bytes([int(align)]))

    def set_character_size(self, width: int = 1, height: int = 1) -> None:
        """
        GS ! n  —  Select character size (1x–8x each axis).

        Args:
            width:  Horizontal multiplier 1-8.
            height: Vertical multiplier 1-8.
        """
        if not (1 <= width <= 8 and 1 <= height <= 8):
            raise ValueError("width and height must be 1-8")
        n = ((width - 1) << 4) | (height - 1)
        self.write(GS + b"\x21" + bytes([n]))

    def set_emphasized(self, on: bool = True) -> None:
        """ESC E n  —  Turn bold / emphasized mode on or off."""
        self.write(ESC + b"\x45" + bytes([0x01 if on else 0x00]))

    def set_double_strike(self, on: bool = True) -> None:
        """ESC G n  —  Turn double-strike mode on or off."""
        self.write(ESC + b"\x47" + bytes([0x01 if on else 0x00]))

    def set_underline(self, mode: Union[UnderlineMode, int] = UnderlineMode.THIN) -> None:
        """
        ESC – n  —  Set underline mode.

        Args:
            mode: 0=off, 1=thin (1-dot), 2=thick (2-dot).
        """
        self.write(ESC + b"\x2d" + bytes([int(mode)]))

    def set_reverse(self, on: bool = True) -> None:
        """GS B n  —  White-on-black (reverse) printing mode."""
        self.write(GS + b"\x42" + bytes([0x01 if on else 0x00]))

    def set_upside_down(self, on: bool = True) -> None:
        """ESC { n  —  Upside-down printing mode (180° rotation)."""
        self.write(ESC + b"\x7b" + bytes([0x01 if on else 0x00]))

    def set_rotation_90(self, on: bool = True) -> None:
        """ESC V n  —  90° clockwise rotation mode."""
        self.write(ESC + b"\x56" + bytes([0x01 if on else 0x00]))

    def set_font(self, font_b: bool = False) -> None:
        """
        ESC M n  —  Select character font.

        Args:
            font_b: False = Font A (12×24), True = Font B (9×17).
        """
        self.write(ESC + b"\x4d" + bytes([0x01 if font_b else 0x00]))

    # ══════════════════════════════════════════════════════════════════
    #  PHASE 3 — Line Spacing, Paper Feed & Cutting
    # ══════════════════════════════════════════════════════════════════

    def feed_lines(self, n: int = 1) -> None:
        """ESC d n  —  Print the buffer and feed *n* lines."""
        if not (0 <= n <= 255):
            raise ValueError("n must be 0-255")
        self.write(ESC + b"\x64" + bytes([n]))

    def feed_dots(self, n: int = 0) -> None:
        """
        ESC J n  —  Print the buffer and feed *n* motion-unit steps.

        Fine-grained vertical feed (each unit ≈ 0.125 mm at default
        motion unit of 203 dpi).
        """
        if not (0 <= n <= 255):
            raise ValueError("n must be 0-255")
        self.write(ESC + b"\x4a" + bytes([n]))

    def set_line_spacing(self, n: Optional[int] = None) -> None:
        """
        Set the line spacing.

        Args:
            n: If None  → ESC 2 (default 1/6-inch ≈ 4.23 mm).
               If 0-255 → ESC 3 n (n × motion unit).
        """
        if n is None:
            self.write(ESC + b"\x32")                  # ESC 2
        else:
            if not (0 <= n <= 255):
                raise ValueError("n must be 0-255")
            self.write(ESC + b"\x33" + bytes([n]))     # ESC 3 n

    def cut(self, feed_n: int = 0) -> None:
        """
        GS V  —  Partial cut, optionally feeding *feed_n* motion units
        before cutting.

        Args:
            feed_n: 0 = cut at current position.
                    1-255 = feed then cut.
        """
        if feed_n == 0:
            # GS V m  (m=1  → partial cut)
            self.write(GS + b"\x56" + bytes([CutMode.PARTIAL]))
        else:
            # GS V m n  (m=66, n=feed amount)
            if not (0 <= feed_n <= 255):
                raise ValueError("feed_n must be 0-255")
            self.write(GS + b"\x56" + bytes([CutMode.PARTIAL_FEED, feed_n]))

    # ══════════════════════════════════════════════════════════════════
    #  PHASE 4 — Barcode Printing
    # ══════════════════════════════════════════════════════════════════

    def set_barcode_height(self, dots: int = 162) -> None:
        """GS h n  —  Set bar code height in dots (1-255, default 162)."""
        if not (1 <= dots <= 255):
            raise ValueError("dots must be 1-255")
        self.write(GS + b"\x68" + bytes([dots]))

    def set_barcode_width(self, n: int = 3) -> None:
        """
        GS w n  —  Set bar code module width (2-6).

        n=2: 0.25 mm, n=3: 0.375 mm, … n=6: 0.75 mm.
        """
        if not (2 <= n <= 6):
            raise ValueError("n must be 2-6")
        self.write(GS + b"\x77" + bytes([n]))

    def set_barcode_hri(self, position: Union[BarcodeHRI, int] = BarcodeHRI.BELOW) -> None:
        """
        GS H n  —  Where to print the human-readable interpretation.

        0=hidden, 1=above, 2=below, 3=both.
        """
        self.write(GS + b"\x48" + bytes([int(position)]))

    def set_barcode_hri_font(self, font_b: bool = False) -> None:
        """GS f n  —  Select font for HRI characters (A or B)."""
        self.write(GS + b"\x66" + bytes([0x01 if font_b else 0x00]))

    def print_barcode(self, system: Union[BarcodeSystem, str, int], data: str) -> None:
        """
        GS k m n d1..dn  —  Print a barcode (Format ②).

        Args:
            system: Barcode type — enum value, int (65-73), or name
                    string (e.g. "CODE128", "EAN13", "UPC-A").
            data:   The barcode payload (ASCII characters).

        Raises:
            ValueError: If system is unknown or data length is invalid.
        """
        if isinstance(system, str):
            key = system.upper().replace("-", "_").replace(" ", "_")
            # Also try the original string for names like "UPC-A"
            m = _BARCODE_NAMES.get(key) or _BARCODE_NAMES.get(system.upper())
            if m is None:
                raise ValueError(
                    f"Unknown barcode system '{system}'. "
                    f"Valid names: {sorted(_BARCODE_NAMES.keys())}"
                )
        else:
            m = int(system)

        encoded = data.encode("ascii")
        n = len(encoded)
        if n < 1 or n > 255:
            raise ValueError(f"Barcode data length must be 1-255, got {n}")

        # GS k m n d1..dn
        self.write(GS + b"\x6b" + bytes([m, n]) + encoded)

    # ══════════════════════════════════════════════════════════════════
    #  PHASE 5 — Raster Bit-Image Printing
    # ══════════════════════════════════════════════════════════════════

    def print_raster_image(
        self,
        image_data: bytes,
        width_bytes: int,
        height_dots: int,
        mode: Union[RasterMode, int] = RasterMode.NORMAL,
    ) -> None:
        """
        GS v 0 m xL xH yL yH d1..dk  —  Print a raster bit image.

        This is the *raw* interface.  Use ``print_image()`` for a
        higher-level API that accepts a PIL Image object.

        Args:
            image_data:  Raw 1-bit raster data, row-major.  Each byte
                         encodes 8 horizontal pixels (MSB = leftmost).
            width_bytes: Number of *bytes* per row (width_pixels / 8).
            height_dots: Number of pixel rows.
            mode:        0=normal, 1=double-width, 2=double-height,
                         3=quadruple.
        """
        expected = width_bytes * height_dots
        if len(image_data) != expected:
            raise ValueError(
                f"image_data length {len(image_data)} != "
                f"width_bytes({width_bytes}) × height_dots({height_dots}) = {expected}"
            )
        xL = width_bytes & 0xFF
        xH = (width_bytes >> 8) & 0xFF
        yL = height_dots & 0xFF
        yH = (height_dots >> 8) & 0xFF
        header = GS + b"\x76\x30" + bytes([int(mode), xL, xH, yL, yH])
        self.write(header + image_data)

    def print_image(
        self,
        image,
        mode: Union[RasterMode, int] = RasterMode.NORMAL,
        max_width: int = 576,
    ) -> None:
        """
        High-level raster image print from a PIL/Pillow Image.

        Converts the image to 1-bit monochrome, scales to fit the
        printable width (576 dots at 203 dpi for 80mm paper), and
        sends via ``GS v 0``.

        Args:
            image:     A ``PIL.Image.Image`` instance (any mode).
            mode:      Raster mode (see ``RasterMode``).
            max_width: Maximum width in dots (default 576 for 80mm).

        Requires:
            Pillow (``pip install Pillow``).
        """
        try:
            from PIL import Image
        except ImportError:
            raise ImportError(
                "Pillow is required for print_image(). "
                "Install with: pip install Pillow"
            )

        # Resize to fit print width, maintaining aspect ratio
        w, h = image.size
        if w > max_width:
            ratio = max_width / w
            image = image.resize((max_width, int(h * ratio)), Image.LANCZOS)
            w, h = image.size

        # Width must be a multiple of 8 for byte alignment
        if w % 8 != 0:
            new_w = ((w + 7) // 8) * 8
            padded = Image.new("RGB", (new_w, h), (255, 255, 255))
            padded.paste(image, (0, 0))
            image = padded
            w = new_w

        # Convert to 1-bit monochrome (dithered)
        bw = image.convert("1")
        pixels = bw.tobytes()

        width_bytes = w // 8
        self.print_raster_image(pixels, width_bytes, h, mode)

    # ══════════════════════════════════════════════════════════════════
    #  PHASE 6 — Cash Drawer
    # ══════════════════════════════════════════════════════════════════

    def kick_drawer(self, pin: int = 0, on_ms: int = 200, off_ms: int = 200) -> None:
        """
        ESC p m t1 t2  —  Generate a pulse on the cash drawer connector.

        Args:
            pin:    0 = connector pin 2,  1 = connector pin 5.
            on_ms:  Pulse-on time in ms (rounded to nearest 2 ms).
            off_ms: Pulse-off time in ms (rounded to nearest 2 ms).
        """
        if pin not in (0, 1):
            raise ValueError("pin must be 0 or 1")
        t1 = max(0, min(255, on_ms // 2))
        t2 = max(0, min(255, off_ms // 2))
        self.write(ESC + b"\x70" + bytes([pin, t1, t2]))

    def kick_drawer_realtime(self, pin: int = 0, pulse_units: int = 2) -> None:
        """
        DLE DC4 1 m t  —  Real-time pulse (bypasses the receive buffer).

        Args:
            pin:         0 = pin 2, 1 = pin 5.
            pulse_units: 1-8 (each unit = 100 ms on, 100 ms off).
        """
        if pin not in (0, 1):
            raise ValueError("pin must be 0 or 1")
        if not (1 <= pulse_units <= 8):
            raise ValueError("pulse_units must be 1-8")
        self.write(DLE + DC4 + b"\x01" + bytes([pin, pulse_units]))

    # ══════════════════════════════════════════════════════════════════
    #  PHASE 7 — Character Sets & Code Pages
    # ══════════════════════════════════════════════════════════════════

    def set_code_page(self, page: Union[CodePage, int] = CodePage.PC437) -> None:
        """
        ESC t n  —  Select a character code table.

        Common choices: PC437 (0), PC850 (2), WPC1252 (16), PC866 (17).
        """
        self.write(ESC + b"\x74" + bytes([int(page)]))

    def set_international_charset(
        self, charset: Union[InternationalCharset, int] = InternationalCharset.USA
    ) -> None:
        """
        ESC R n  —  Select an international character set.

        Affects only a small set of locale-specific glyphs
        (#, $, @, [, \\, ], ^, `, {, |, }, ~).
        """
        n = int(charset)
        if not (0 <= n <= 15):
            raise ValueError("charset must be 0-15")
        self.write(ESC + b"\x52" + bytes([n]))

    # ══════════════════════════════════════════════════════════════════
    #  PHASE 8 — Margins, Print Area & Motion Units
    # ══════════════════════════════════════════════════════════════════

    def set_left_margin(self, dots: int = 0) -> None:
        """
        GS L nL nH  —  Set the left margin in motion-unit dots.

        At the default motion unit (x = 1/180 inch ≈ 0.141 mm per dot).
        """
        if not (0 <= dots <= 65535):
            raise ValueError("dots must be 0-65535")
        nL = dots & 0xFF
        nH = (dots >> 8) & 0xFF
        self.write(GS + b"\x4c" + bytes([nL, nH]))

    def set_print_area_width(self, dots: int = 512) -> None:
        """
        GS W nL nH  —  Set the printable area width in motion-unit dots.

        Default is 512 (nL=0, nH=2) for 80mm paper.  For 58mm paper
        the default is 360 (nL=104, nH=1).
        """
        if not (0 <= dots <= 65535):
            raise ValueError("dots must be 0-65535")
        nL = dots & 0xFF
        nH = (dots >> 8) & 0xFF
        self.write(GS + b"\x57" + bytes([nL, nH]))

    def set_motion_units(self, x: int = 0, y: int = 0) -> None:
        """
        GS P x y  —  Set horizontal and vertical motion units.

        Horizontal unit = 25.4/x mm,  Vertical unit = 25.4/y mm.
        Default: x=180 (≈0.141 mm), y=360 (factory-set, exceeds the
        0-255 byte range — pass 0 to keep the factory default).
        Setting 0 restores the factory default for that axis.
        """
        if not (0 <= x <= 255 and 0 <= y <= 255):
            raise ValueError("x and y must be 0-255")
        self.write(GS + b"\x50" + bytes([x, y]))

    def set_absolute_position(self, dots: int = 0) -> None:
        """
        ESC $ nL nH  —  Set the absolute horizontal print position
        from the start of the line, in motion-unit dots.
        """
        if not (0 <= dots <= 65535):
            raise ValueError("dots must be 0-65535")
        nL = dots & 0xFF
        nH = (dots >> 8) & 0xFF
        self.write(ESC + b"\x24" + bytes([nL, nH]))

    def set_relative_position(self, dots: int = 0) -> None:
        """
        ESC \\ nL nH  —  Move the print position relative to the
        current position.  Negative values move left (two's complement
        of 65536).
        """
        if dots < 0:
            dots = 65536 + dots
        if not (0 <= dots <= 65535):
            raise ValueError("dots out of range")
        nL = dots & 0xFF
        nH = (dots >> 8) & 0xFF
        self.write(ESC + b"\x5c" + bytes([nL, nH]))

    def set_tab_positions(self, positions: list[int]) -> None:
        """
        ESC D n1..nk NUL  —  Set horizontal tab stops.

        Args:
            positions: Column numbers (ascending, 1-255), up to 32.
                       Pass an empty list to clear all tab stops.
        """
        if len(positions) > 32:
            raise ValueError("Maximum 32 tab positions")
        if positions and positions != sorted(positions):
            raise ValueError("Tab positions must be in ascending order")
        data = bytes(positions) + NUL
        self.write(ESC + b"\x44" + data)

    # ── Paper sensor configuration ────────────────────────────────────

    def set_paper_end_sensor(self, near_end: bool = True, end: bool = True) -> None:
        """
        ESC c 3 n  —  Select paper sensors for paper-end signals.

        Args:
            near_end: Enable the paper-roll near-end sensor.
            end:      Enable the paper-roll end sensor.
        """
        n = 0
        if near_end:  n |= 0x03
        if end:       n |= 0x0C
        self.write(ESC + b"\x63\x33" + bytes([n]))

    def set_paper_stop_sensor(self, near_end: bool = False) -> None:
        """
        ESC c 4 n  —  Select paper sensor(s) that stop printing.

        Args:
            near_end: If True, stop printing when near-end is detected.
        """
        n = 0x03 if near_end else 0x00
        self.write(ESC + b"\x63\x34" + bytes([n]))

    def set_panel_buttons(self, enabled: bool = True) -> None:
        """ESC c 5 n  —  Enable or disable the FEED button."""
        self.write(ESC + b"\x63\x35" + bytes([0x00 if enabled else 0x01]))

    # ══════════════════════════════════════════════════════════════════
    #  PHASE 9 — NV Bit Images & Macros
    # ══════════════════════════════════════════════════════════════════

    def print_nv_image(self, slot: int = 1, mode: Union[RasterMode, int] = RasterMode.NORMAL) -> None:
        """
        FS p n m  —  Print a previously-stored NV bit image.

        Args:
            slot: Image number (1-255, as defined by ``define_nv_images``).
            mode: 0=normal, 1=double-width, 2=double-height, 3=quadruple.
        """
        if not (1 <= slot <= 255):
            raise ValueError("slot must be 1-255")
        self.write(FS + b"\x70" + bytes([slot, int(mode)]))

    def define_nv_images(self, images: list[tuple[int, int, bytes]]) -> None:
        """
        FS q n [xL xH yL yH d1..dk]1..[..]n  —  Define NV bit images.

        **WARNING**: Frequent writes may degrade NV memory. Limit to
        ≤ 10 writes/day.  This command clears ALL previously defined
        NV images and triggers a hardware reset when done.

        Args:
            images: List of (width_dots, height_dots, data) tuples.
                    width_dots and height_dots must be multiples of 8.
                    Total data must fit in 64 KB.
        """
        n = len(images)
        if n < 1 or n > 255:
            raise ValueError("Must define 1-255 NV images")

        payload = FS + b"\x71" + bytes([n])
        total_data = 0

        for width_dots, height_dots, data in images:
            if width_dots % 8 != 0 or height_dots % 8 != 0:
                raise ValueError("NV image dimensions must be multiples of 8")
            x = width_dots // 8    # number of byte-columns
            y = height_dots // 8   # number of 8-dot rows
            expected = x * y * 8
            if len(data) != expected:
                raise ValueError(
                    f"Expected {expected} bytes for {width_dots}×{height_dots} image, "
                    f"got {len(data)}"
                )
            total_data += expected + 4  # 4 header bytes per image
            xL = x & 0xFF
            xH = (x >> 8) & 0xFF
            yL = y & 0xFF
            yH = (y >> 8) & 0xFF
            payload += bytes([xL, xH, yL, yH]) + data

        if total_data > 65536:
            raise ValueError(
                f"Total NV image data ({total_data} bytes) exceeds 64 KB limit"
            )
        self.write(payload)

    def start_macro(self) -> None:
        """GS :  —  Start (or end) macro definition."""
        self.write(GS + b"\x3a")

    def end_macro(self) -> None:
        """GS :  —  End macro definition (same command toggles)."""
        self.write(GS + b"\x3a")

    def execute_macro(self, repeat: int = 1, wait_100ms: int = 0, wait_for_button: bool = False) -> None:
        """
        GS ^ r t m  —  Execute a previously defined macro.

        Args:
            repeat:          Number of times to execute (0-255).
            wait_100ms:      Wait time between executions (× 100 ms).
            wait_for_button: If True, blink LED and wait for FEED
                             button press between each execution.
        """
        if not (0 <= repeat <= 255 and 0 <= wait_100ms <= 255):
            raise ValueError("repeat and wait must be 0-255")
        m = 1 if wait_for_button else 0
        self.write(GS + b"\x5e" + bytes([repeat, wait_100ms, m]))

    # ══════════════════════════════════════════════════════════════════
    #  ASB — Automatic Status Back
    # ══════════════════════════════════════════════════════════════════

    def set_auto_status_back(
        self,
        *,
        drawer: bool = False,
        online_offline: bool = False,
        error: bool = False,
        paper_sensor: bool = False,
    ) -> None:
        """
        GS a n  —  Enable/disable Automatic Status Back (ASB).

        When enabled the printer pushes 4-byte status packets whenever
        the monitored conditions change.
        """
        n = 0
        if drawer:         n |= 0x01
        if online_offline: n |= 0x02
        if error:          n |= 0x04
        if paper_sensor:   n |= 0x08
        self.write(GS + b"\x61" + bytes([n]))

    def transmit_status(self, paper: bool = True) -> Optional[int]:
        """
        GS r n  —  Transmit status (serial interface only).

        Args:
            paper: True → paper sensor status (n=1).
                   False → drawer kick-out connector status (n=2).
        Returns:
            The raw status byte, or None if no response.
        """
        n = 1 if paper else 2
        self.write(GS + b"\x72" + bytes([n]))
        resp = self.read(1, timeout=2.0)
        return resp[0] if resp else None

    # ══════════════════════════════════════════════════════════════════
    #  Convenience: common receipt patterns
    # ══════════════════════════════════════════════════════════════════

    def print_separator(self, char: str = "-", width: int = 48) -> None:
        """Print a full-width line separator."""
        self.println(char * width)

    def print_two_column(self, left: str, right: str, width: int = 48) -> None:
        """Print left-aligned and right-aligned text on the same line."""
        gap = width - len(left) - len(right)
        if gap < 1:
            gap = 1
        self.println(left + " " * gap + right)


# ═══════════════════════════════════════════════════════════════════════
#  NetworkConfig — WiFi / LAN setup (standalone, no XPrinter needed)
# ═══════════════════════════════════════════════════════════════════════

class NetworkConfig:
    """
    Static helpers for the proprietary Xprinter network-configuration
    protocol (sent as a single binary payload to the USB device file).

    These do **not** use the ESC/POS command set — they use the
    undocumented ``US ESC US 0xB4`` preamble discovered by
    dantecatalfamo's reverse-engineering work.
    """

    @staticmethod
    def _validate_ipv4(address: str, label: str) -> ipaddress.IPv4Address:
        try:
            return ipaddress.IPv4Address(address)
        except (ipaddress.AddressValueError, ValueError) as exc:
            raise ValueError(f"{label} '{address}' is not a valid IPv4 address: {exc}")

    @staticmethod
    def _build_prefix(ip: str, mask: str, gateway: str) -> bytes:
        ip_a   = NetworkConfig._validate_ipv4(ip,      "IP address")
        mask_a = NetworkConfig._validate_ipv4(mask,    "Subnet mask")
        gw_a   = NetworkConfig._validate_ipv4(gateway, "Gateway")
        return NET_PREAMBLE + NET_COMMAND + ip_a.packed + mask_a.packed + gw_a.packed

    @staticmethod
    def set_wifi(
        device: str,
        ip: str,
        mask: str,
        gateway: str,
        ssid: str,
        key: str,
        key_type: Union[WifiKeyType, int] = WifiKeyType.WPA2_AES_PSK,
    ) -> None:
        """
        Configure wireless network settings.

        Sends:
            US ESC US B4 | IP(4B) | MASK(4B) | GW(4B) |
            KEY_TYPE(1B) | SSID\\0 | KEY\\0
        """
        kt = int(key_type)
        if not (0 <= kt <= 9):
            raise ValueError(f"key_type must be 0-9, got {kt}")
        payload = (
            NetworkConfig._build_prefix(ip, mask, gateway)
            + bytes([kt])
            + ssid.encode("utf-8") + b"\x00"
            + key.encode("utf-8") + b"\x00"
        )
        with open(device, "wb") as f:
            f.write(payload)
            f.flush()
        print(f"WiFi config sent → {device}  "
              f"IP={ip}  SSID={ssid}  key_type={kt}({WifiKeyType(kt).name})")

    @staticmethod
    def set_lan(device: str, ip: str, mask: str, gateway: str) -> None:
        """
        Configure wired LAN network settings.

        Sends:
            US ESC US B4 | IP(4B) | MASK(4B) | GW(4B)
        """
        payload = NetworkConfig._build_prefix(ip, mask, gateway)
        with open(device, "wb") as f:
            f.write(payload)
            f.flush()
        print(f"LAN config sent → {device}  IP={ip}  mask={mask}  gw={gateway}")


# ═══════════════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════════════

def _demo_receipt(device: str) -> None:
    """Print a demo receipt exercising most features."""
    with XPrinter(device, auto_init=True) as p:
        # Header
        p.set_justification("center")
        p.set_character_size(2, 2)
        p.println("MY STORE")
        p.set_character_size(1, 1)
        p.println("123 Main St, Anytown")
        p.println("Tel: (555) 123-4567")
        p.print_separator("=")

        # Items
        p.set_justification("left")
        p.print_two_column("Widget A x2", "$10.00")
        p.print_two_column("Gadget B x1", "$7.50")
        p.print_two_column("Doohickey x3", "$4.50")
        p.print_separator()

        # Totals
        p.set_emphasized(True)
        p.print_two_column("SUBTOTAL", "$22.00")
        p.print_two_column("TAX (8%)", "$1.76")
        p.print_separator("=")
        p.set_character_size(1, 2)
        p.print_two_column("TOTAL", "$23.76")
        p.set_character_size(1, 1)
        p.set_emphasized(False)
        p.println("")

        # Barcode
        p.set_justification("center")
        p.set_barcode_height(80)
        p.set_barcode_width(3)
        p.set_barcode_hri(BarcodeHRI.BELOW)
        p.print_barcode("CODE128", "INV-20260401-001")
        p.println("")
        p.println("Thank you for your purchase!")
        p.feed_lines(4)
        p.cut()

    print(f"Demo receipt printed on {device}")


def _build_cli() -> "argparse.ArgumentParser":
    import argparse
    from getpass import getpass

    parser = argparse.ArgumentParser(
        description="XP-80T Thermal Printer Driver",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
examples:
  %(prog)s wifi   /dev/usb/lp0 192.168.1.100 255.255.255.0 192.168.1.1 Net pass 6
  %(prog)s lan    /dev/usb/lp0 10.0.0.50 255.255.255.0 10.0.0.1
  %(prog)s demo   /dev/usb/lp0
  %(prog)s status /dev/usb/lp0
""",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ── wifi ──
    w = sub.add_parser("wifi", help="Configure wireless network")
    w.add_argument("device"); w.add_argument("ip"); w.add_argument("mask")
    w.add_argument("gateway"); w.add_argument("ssid"); w.add_argument("password")
    w.add_argument("key_type", nargs="?", type=int, default=6)

    # ── lan ──
    la = sub.add_parser("lan", help="Configure wired LAN")
    la.add_argument("device"); la.add_argument("ip"); la.add_argument("mask")
    la.add_argument("gateway")

    # ── demo ──
    d = sub.add_parser("demo", help="Print a demo receipt")
    d.add_argument("device")

    # ── status ──
    s = sub.add_parser("status", help="Query all printer status")
    s.add_argument("device")

    # ── init ──
    i = sub.add_parser("init", help="Send ESC @ (reset to defaults)")
    i.add_argument("device")

    # ── cut ──
    c = sub.add_parser("cut", help="Feed and cut paper")
    c.add_argument("device")
    c.add_argument("--feed", type=int, default=3, help="Lines to feed before cut")

    # ── kick ──
    k = sub.add_parser("kick", help="Kick cash drawer")
    k.add_argument("device")
    k.add_argument("--pin", type=int, default=0, choices=[0, 1])

    return parser


def main() -> None:
    parser = _build_cli()
    args = parser.parse_args()

    try:
        if args.command == "wifi":
            NetworkConfig.set_wifi(
                args.device, args.ip, args.mask, args.gateway,
                args.ssid, args.password, args.key_type,
            )
        elif args.command == "lan":
            NetworkConfig.set_lan(args.device, args.ip, args.mask, args.gateway)
        elif args.command == "demo":
            _demo_receipt(args.device)
        elif args.command == "status":
            with XPrinter(args.device) as p:
                for st in StatusType:
                    result = p.get_status(st)
                    print(f"\n{st.name}:")
                    for k, v in result.items():
                        print(f"  {k}: {v}")
        elif args.command == "init":
            with XPrinter(args.device) as p:
                p.initialize()
                print(f"Printer initialized ({args.device})")
        elif args.command == "cut":
            with XPrinter(args.device) as p:
                p.feed_lines(args.feed)
                p.cut()
                print("Cut executed")
        elif args.command == "kick":
            with XPrinter(args.device) as p:
                p.kick_drawer(args.pin)
                print(f"Drawer kick sent (pin {args.pin})")
    except (ValueError, FileNotFoundError, PermissionError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
