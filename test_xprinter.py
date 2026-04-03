#!/usr/bin/env python3
"""
Test suite for xprinter.py — verifies every command produces
the correct byte sequences per the 80XX Programmer Manual.

Uses a FakeDevice that captures writes instead of a real printer.
"""

import os
import sys
import tempfile

# ── Fake device that captures writes ──────────────────────────────────

class FakeDevice:
    """Intercepts all writes so we can inspect the raw bytes."""

    def __init__(self):
        self._tmp = tempfile.NamedTemporaryFile(delete=False)
        self.path = self._tmp.name
        self._tmp.close()

    def cleanup(self):
        os.unlink(self.path)

    def read_bytes(self) -> bytes:
        with open(self.path, "rb") as f:
            return f.read()

    def clear(self):
        open(self.path, "wb").close()


def hexstr(b: bytes) -> str:
    return " ".join(f"{x:02x}" for x in b)


# ── Import the module ─────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))
from xprinter import (
    XPrinter, NetworkConfig,
    Justification, UnderlineMode, BarcodeHRI, BarcodeSystem,
    RasterMode, StatusType, WifiKeyType, CodePage, InternationalCharset,
)

# ── Test runner ───────────────────────────────────────────────────────

passed = 0
failed = 0

def assert_bytes(label: str, actual: bytes, expected: bytes):
    global passed, failed
    if actual == expected:
        passed += 1
        print(f"  ✓ {label}")
    else:
        failed += 1
        print(f"  ✗ {label}")
        print(f"    expected: {hexstr(expected)}")
        print(f"    actual:   {hexstr(actual)}")


def assert_startswith(label: str, actual: bytes, prefix: bytes):
    global passed, failed
    if actual[:len(prefix)] == prefix:
        passed += 1
        print(f"  ✓ {label} (prefix match, {len(actual)} bytes total)")
    else:
        failed += 1
        print(f"  ✗ {label}")
        print(f"    expected prefix: {hexstr(prefix)}")
        print(f"    actual start:    {hexstr(actual[:len(prefix)])}")


# ── Setup ─────────────────────────────────────────────────────────────
dev = FakeDevice()

def fresh_printer() -> XPrinter:
    """Get a printer with a clean capture buffer."""
    dev.clear()
    return XPrinter(dev.path)


# ══════════════════════════════════════════════════════════════════════
print("\n═══ Phase 1: Printer Lifecycle ═══")
# ══════════════════════════════════════════════════════════════════════

p = fresh_printer()
p.initialize()
assert_bytes("ESC @ (initialize)", dev.read_bytes(), b"\x1b\x40")

p = fresh_printer()
p.set_device_enabled(True)
assert_bytes("ESC = 1 (enable)", dev.read_bytes(), b"\x1b\x3d\x01")

p = fresh_printer()
p.set_device_enabled(False)
assert_bytes("ESC = 0 (disable)", dev.read_bytes(), b"\x1b\x3d\x00")

p = fresh_printer()
p.request_error_recovery(clear_buffers=False)
assert_bytes("DLE ENQ 1 (recover)", dev.read_bytes(), b"\x10\x05\x01")

p = fresh_printer()
p.request_error_recovery(clear_buffers=True)
assert_bytes("DLE ENQ 2 (recover+clear)", dev.read_bytes(), b"\x10\x05\x02")

# Status: only verify the command sent (can't read response from fake)
p = fresh_printer()
p.write(b"\x10\x04\x01")  # manual DLE EOT 1
assert_bytes("DLE EOT 1 (status cmd)", dev.read_bytes(), b"\x10\x04\x01")


# ══════════════════════════════════════════════════════════════════════
print("\n═══ Phase 2: Text Formatting ═══")
# ══════════════════════════════════════════════════════════════════════

p = fresh_printer()
p.set_print_mode(font_b=True, emphasized=True, double_height=True,
                 double_width=True, underline=True)
# bit0=1(fontB) | bit3=8(emph) | bit4=16(dblH) | bit5=32(dblW) | bit7=128(uline) = 0xB9
assert_bytes("ESC ! 0xB9 (all modes)", dev.read_bytes(), b"\x1b\x21\xb9")

p = fresh_printer()
p.set_print_mode()  # all defaults = 0
assert_bytes("ESC ! 0x00 (defaults)", dev.read_bytes(), b"\x1b\x21\x00")

p = fresh_printer()
p.set_justification("left")
assert_bytes("ESC a 0 (left)", dev.read_bytes(), b"\x1b\x61\x00")

p = fresh_printer()
p.set_justification("center")
assert_bytes("ESC a 1 (center)", dev.read_bytes(), b"\x1b\x61\x01")

p = fresh_printer()
p.set_justification("right")
assert_bytes("ESC a 2 (right)", dev.read_bytes(), b"\x1b\x61\x02")

p = fresh_printer()
p.set_justification(Justification.CENTER)
assert_bytes("ESC a 1 (enum)", dev.read_bytes(), b"\x1b\x61\x01")

p = fresh_printer()
p.set_character_size(1, 1)  # normal
assert_bytes("GS ! 0x00 (1x1)", dev.read_bytes(), b"\x1d\x21\x00")

p = fresh_printer()
p.set_character_size(2, 2)  # double both
assert_bytes("GS ! 0x11 (2x2)", dev.read_bytes(), b"\x1d\x21\x11")

p = fresh_printer()
p.set_character_size(4, 8)  # 4 wide, 8 tall
# width: (4-1)<<4 = 0x30, height: (8-1) = 0x07 → 0x37
assert_bytes("GS ! 0x37 (4x8)", dev.read_bytes(), b"\x1d\x21\x37")

p = fresh_printer()
p.set_emphasized(True)
assert_bytes("ESC E 1 (bold on)", dev.read_bytes(), b"\x1b\x45\x01")

p = fresh_printer()
p.set_emphasized(False)
assert_bytes("ESC E 0 (bold off)", dev.read_bytes(), b"\x1b\x45\x00")

p = fresh_printer()
p.set_double_strike(True)
assert_bytes("ESC G 1", dev.read_bytes(), b"\x1b\x47\x01")

p = fresh_printer()
p.set_underline(UnderlineMode.OFF)
assert_bytes("ESC - 0 (uline off)", dev.read_bytes(), b"\x1b\x2d\x00")

p = fresh_printer()
p.set_underline(UnderlineMode.THIN)
assert_bytes("ESC - 1 (uline thin)", dev.read_bytes(), b"\x1b\x2d\x01")

p = fresh_printer()
p.set_underline(UnderlineMode.THICK)
assert_bytes("ESC - 2 (uline thick)", dev.read_bytes(), b"\x1b\x2d\x02")

p = fresh_printer()
p.set_reverse(True)
assert_bytes("GS B 1 (reverse on)", dev.read_bytes(), b"\x1d\x42\x01")

p = fresh_printer()
p.set_reverse(False)
assert_bytes("GS B 0 (reverse off)", dev.read_bytes(), b"\x1d\x42\x00")

p = fresh_printer()
p.set_upside_down(True)
assert_bytes("ESC { 1 (upsidedown)", dev.read_bytes(), b"\x1b\x7b\x01")

p = fresh_printer()
p.set_rotation_90(True)
assert_bytes("ESC V 1 (90° rot)", dev.read_bytes(), b"\x1b\x56\x01")

p = fresh_printer()
p.set_font(font_b=True)
assert_bytes("ESC M 1 (font B)", dev.read_bytes(), b"\x1b\x4d\x01")

p = fresh_printer()
p.set_font(font_b=False)
assert_bytes("ESC M 0 (font A)", dev.read_bytes(), b"\x1b\x4d\x00")


# ══════════════════════════════════════════════════════════════════════
print("\n═══ Phase 3: Feed & Cut ═══")
# ══════════════════════════════════════════════════════════════════════

p = fresh_printer()
p.feed_lines(5)
assert_bytes("ESC d 5 (feed 5 lines)", dev.read_bytes(), b"\x1b\x64\x05")

p = fresh_printer()
p.feed_dots(100)
assert_bytes("ESC J 100 (feed dots)", dev.read_bytes(), b"\x1b\x4a\x64")

p = fresh_printer()
p.set_line_spacing()  # default
assert_bytes("ESC 2 (default spacing)", dev.read_bytes(), b"\x1b\x32")

p = fresh_printer()
p.set_line_spacing(50)
assert_bytes("ESC 3 50 (custom spacing)", dev.read_bytes(), b"\x1b\x33\x32")

p = fresh_printer()
p.cut()
assert_bytes("GS V 1 (partial cut)", dev.read_bytes(), b"\x1d\x56\x01")

p = fresh_printer()
p.cut(feed_n=30)
assert_bytes("GS V 66 30 (feed+cut)", dev.read_bytes(), b"\x1d\x56\x42\x1e")


# ══════════════════════════════════════════════════════════════════════
print("\n═══ Phase 4: Barcodes ═══")
# ══════════════════════════════════════════════════════════════════════

p = fresh_printer()
p.set_barcode_height(80)
assert_bytes("GS h 80", dev.read_bytes(), b"\x1d\x68\x50")

p = fresh_printer()
p.set_barcode_width(3)
assert_bytes("GS w 3", dev.read_bytes(), b"\x1d\x77\x03")

p = fresh_printer()
p.set_barcode_hri(BarcodeHRI.BELOW)
assert_bytes("GS H 2 (HRI below)", dev.read_bytes(), b"\x1d\x48\x02")

p = fresh_printer()
p.set_barcode_hri_font(font_b=True)
assert_bytes("GS f 1 (HRI font B)", dev.read_bytes(), b"\x1d\x66\x01")

# CODE128 barcode with "ABC"
p = fresh_printer()
p.print_barcode("CODE128", "ABC")
# GS k 73 3 A B C
assert_bytes("GS k CODE128 'ABC'", dev.read_bytes(),
             b"\x1d\x6b\x49\x03\x41\x42\x43")

# EAN13 barcode
p = fresh_printer()
p.print_barcode(BarcodeSystem.EAN13, "4006381333931")
data = dev.read_bytes()
assert_startswith("GS k EAN13 (prefix)", data, b"\x1d\x6b\x43\x0d")

# CODE39 by name string
p = fresh_printer()
p.print_barcode("CODE39", "HELLO")
assert_bytes("GS k CODE39 'HELLO'", dev.read_bytes(),
             b"\x1d\x6b\x45\x05HELLO")


# ══════════════════════════════════════════════════════════════════════
print("\n═══ Phase 5: Raster Images ═══")
# ══════════════════════════════════════════════════════════════════════

# 16x8 black image (2 bytes wide × 8 rows = 16 bytes of 0xFF)
p = fresh_printer()
img_data = b"\xff" * 16
p.print_raster_image(img_data, width_bytes=2, height_dots=8, mode=RasterMode.NORMAL)
data = dev.read_bytes()
# GS v 0 0 xL=2 xH=0 yL=8 yH=0 + 16 data bytes
expected_prefix = b"\x1d\x76\x30\x00\x02\x00\x08\x00"
assert_startswith("GS v 0 (raster 16x8)", data, expected_prefix)
assert_bytes("  raster data length", bytes([len(data) - 8]), bytes([16]))


# ══════════════════════════════════════════════════════════════════════
print("\n═══ Phase 6: Cash Drawer ═══")
# ══════════════════════════════════════════════════════════════════════

p = fresh_printer()
p.kick_drawer(pin=0, on_ms=200, off_ms=200)
# t1 = 200//2 = 100 = 0x64, t2 = 100 = 0x64
assert_bytes("ESC p 0 100 100", dev.read_bytes(), b"\x1b\x70\x00\x64\x64")

p = fresh_printer()
p.kick_drawer(pin=1, on_ms=100, off_ms=400)
assert_bytes("ESC p 1 50 200", dev.read_bytes(), b"\x1b\x70\x01\x32\xc8")

p = fresh_printer()
p.kick_drawer_realtime(pin=0, pulse_units=3)
assert_bytes("DLE DC4 1 0 3", dev.read_bytes(), b"\x10\x14\x01\x00\x03")


# ══════════════════════════════════════════════════════════════════════
print("\n═══ Phase 7: Character Sets ═══")
# ══════════════════════════════════════════════════════════════════════

p = fresh_printer()
p.set_code_page(CodePage.WPC1252)
assert_bytes("ESC t 16 (WPC1252)", dev.read_bytes(), b"\x1b\x74\x10")

p = fresh_printer()
p.set_code_page(CodePage.PC437)
assert_bytes("ESC t 0 (PC437)", dev.read_bytes(), b"\x1b\x74\x00")

p = fresh_printer()
p.set_international_charset(InternationalCharset.FRANCE)
assert_bytes("ESC R 1 (France)", dev.read_bytes(), b"\x1b\x52\x01")

p = fresh_printer()
p.set_international_charset(InternationalCharset.JAPAN)
assert_bytes("ESC R 8 (Japan)", dev.read_bytes(), b"\x1b\x52\x08")


# ══════════════════════════════════════════════════════════════════════
print("\n═══ Phase 8: Margins & Layout ═══")
# ══════════════════════════════════════════════════════════════════════

p = fresh_printer()
p.set_left_margin(0)
assert_bytes("GS L 0 0", dev.read_bytes(), b"\x1d\x4c\x00\x00")

p = fresh_printer()
p.set_left_margin(100)  # nL=100, nH=0
assert_bytes("GS L 100 0", dev.read_bytes(), b"\x1d\x4c\x64\x00")

p = fresh_printer()
p.set_left_margin(300)  # 300 = 0x012C → nL=0x2C, nH=0x01
assert_bytes("GS L 300", dev.read_bytes(), b"\x1d\x4c\x2c\x01")

p = fresh_printer()
p.set_print_area_width(512)  # nL=0, nH=2
assert_bytes("GS W 512", dev.read_bytes(), b"\x1d\x57\x00\x02")

p = fresh_printer()
p.set_motion_units(180, 180)
assert_bytes("GS P 180 180", dev.read_bytes(), b"\x1d\x50\xb4\xb4")

p = fresh_printer()
p.set_motion_units(0, 0)  # restore defaults
assert_bytes("GS P 0 0 (defaults)", dev.read_bytes(), b"\x1d\x50\x00\x00")

p = fresh_printer()
p.set_absolute_position(200)  # nL=200, nH=0
assert_bytes("ESC $ 200 0", dev.read_bytes(), b"\x1b\x24\xc8\x00")

p = fresh_printer()
p.set_relative_position(50)
assert_bytes("ESC \\ 50 0", dev.read_bytes(), b"\x1b\x5c\x32\x00")

p = fresh_printer()
p.set_relative_position(-50)  # 65536-50 = 65486 = 0xFFCE → nL=0xCE, nH=0xFF
assert_bytes("ESC \\ -50", dev.read_bytes(), b"\x1b\x5c\xce\xff")

p = fresh_printer()
p.set_tab_positions([9, 17, 25])
assert_bytes("ESC D 9,17,25,NUL", dev.read_bytes(), b"\x1b\x44\x09\x11\x19\x00")

p = fresh_printer()
p.set_tab_positions([])  # clear tabs
assert_bytes("ESC D NUL (clear)", dev.read_bytes(), b"\x1b\x44\x00")


# ══════════════════════════════════════════════════════════════════════
print("\n═══ Phase 8b: Sensors & Buttons ═══")
# ══════════════════════════════════════════════════════════════════════

p = fresh_printer()
p.set_paper_end_sensor(near_end=True, end=True)
assert_bytes("ESC c 3 0x0F", dev.read_bytes(), b"\x1b\x63\x33\x0f")

p = fresh_printer()
p.set_paper_end_sensor(near_end=False, end=False)
assert_bytes("ESC c 3 0x00", dev.read_bytes(), b"\x1b\x63\x33\x00")

p = fresh_printer()
p.set_paper_stop_sensor(near_end=True)
assert_bytes("ESC c 4 0x03", dev.read_bytes(), b"\x1b\x63\x34\x03")

p = fresh_printer()
p.set_panel_buttons(enabled=True)
assert_bytes("ESC c 5 0 (enabled)", dev.read_bytes(), b"\x1b\x63\x35\x00")

p = fresh_printer()
p.set_panel_buttons(enabled=False)
assert_bytes("ESC c 5 1 (disabled)", dev.read_bytes(), b"\x1b\x63\x35\x01")


# ══════════════════════════════════════════════════════════════════════
print("\n═══ Phase 9: NV Images & Macros ═══")
# ══════════════════════════════════════════════════════════════════════

p = fresh_printer()
p.print_nv_image(slot=1, mode=RasterMode.NORMAL)
assert_bytes("FS p 1 0", dev.read_bytes(), b"\x1c\x70\x01\x00")

p = fresh_printer()
p.print_nv_image(slot=3, mode=RasterMode.DOUBLE_WIDTH)
assert_bytes("FS p 3 1", dev.read_bytes(), b"\x1c\x70\x03\x01")

p = fresh_printer()
p.start_macro()
assert_bytes("GS : (start macro)", dev.read_bytes(), b"\x1d\x3a")

p = fresh_printer()
p.end_macro()
assert_bytes("GS : (end macro)", dev.read_bytes(), b"\x1d\x3a")

p = fresh_printer()
p.execute_macro(repeat=3, wait_100ms=5, wait_for_button=False)
assert_bytes("GS ^ 3 5 0", dev.read_bytes(), b"\x1d\x5e\x03\x05\x00")

p = fresh_printer()
p.execute_macro(repeat=1, wait_100ms=10, wait_for_button=True)
assert_bytes("GS ^ 1 10 1", dev.read_bytes(), b"\x1d\x5e\x01\x0a\x01")


# ══════════════════════════════════════════════════════════════════════
print("\n═══ ASB & Status Transmit ═══")
# ══════════════════════════════════════════════════════════════════════

p = fresh_printer()
p.set_auto_status_back(drawer=True, online_offline=True, error=True, paper_sensor=True)
assert_bytes("GS a 0x0F (all ASB)", dev.read_bytes(), b"\x1d\x61\x0f")

p = fresh_printer()
p.set_auto_status_back()  # all off
assert_bytes("GS a 0x00 (ASB off)", dev.read_bytes(), b"\x1d\x61\x00")


# ══════════════════════════════════════════════════════════════════════
print("\n═══ NetworkConfig ═══")
# ══════════════════════════════════════════════════════════════════════

dev.clear()
NetworkConfig.set_wifi(dev.path, "192.168.1.100", "255.255.255.0",
                       "192.168.1.1", "TestSSID", "pass1234", 6)
data = dev.read_bytes()
expected_wifi = (
    b"\x1f\x1b\x1f\xb4"              # preamble + cmd
    b"\xc0\xa8\x01\x64"              # 192.168.1.100
    b"\xff\xff\xff\x00"              # 255.255.255.0
    b"\xc0\xa8\x01\x01"              # 192.168.1.1
    b"\x06"                           # key_type 6
    b"TestSSID\x00"                   # SSID + NUL
    b"pass1234\x00"                   # key + NUL
)
assert_bytes("WiFi payload", data, expected_wifi)

dev.clear()
NetworkConfig.set_lan(dev.path, "10.0.0.50", "255.255.255.0", "10.0.0.1")
data = dev.read_bytes()
expected_lan = (
    b"\x1f\x1b\x1f\xb4"
    b"\x0a\x00\x00\x32"
    b"\xff\xff\xff\x00"
    b"\x0a\x00\x00\x01"
)
assert_bytes("LAN payload", data, expected_lan)


# ══════════════════════════════════════════════════════════════════════
print("\n═══ Convenience: println / text ═══")
# ══════════════════════════════════════════════════════════════════════

p = fresh_printer()
p.println("Hello")
assert_bytes("println 'Hello'", dev.read_bytes(), b"Hello\x0a")

p = fresh_printer()
p.print_text("No newline")
assert_bytes("print_text (no LF)", dev.read_bytes(), b"No newline")


# ══════════════════════════════════════════════════════════════════════
print("\n═══ Context Manager ═══")
# ══════════════════════════════════════════════════════════════════════

dev.clear()
with XPrinter(dev.path) as p2:
    p2.initialize()
    p2.println("test")
# Should not raise after close
assert_startswith("context manager", dev.read_bytes(), b"\x1b\x40")


# ══════════════════════════════════════════════════════════════════════
#  Summary
# ══════════════════════════════════════════════════════════════════════

dev.cleanup()

print(f"\n{'═' * 50}")
print(f"  Results: {passed} passed, {failed} failed")
print(f"{'═' * 50}")

sys.exit(1 if failed else 0)
