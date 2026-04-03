# xprinter

A pure-Python driver for XP-80T (and compatible ESC/POS) thermal receipt printers over USB. Zero dependencies for core functionality — just Python 3.10+ and a Linux device file.

Implements the full command set from the [80XX Programmer Manual](https://blog.lambda.cx/posts/xprinter-wifi/80XX_Programmer_Manual.pdf), plus the proprietary WiFi/LAN network configuration protocol reverse-engineered by [dantecatalfamo](https://github.com/dantecatalfamo/xprinter-wifi).

---

## Table of Contents

- [Features](#features)
- [Compatibility](#compatibility)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [CLI Usage](#cli-usage)
- [Library API Reference](#library-api-reference)
  - [XPrinter](#xprinter-class)
  - [NetworkConfig](#networkconfig-class)
  - [Enumerations](#enumerations)
- [Device Permissions](#device-permissions)
- [Protocol Reference](#protocol-reference)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [License](#license)
- [Acknowledgements](#acknowledgements)

---

## Features

| Category | Capabilities |
|---|---|
| **Text** | Fonts A/B, bold, underline (1-dot/2-dot), double-strike, reverse (white-on-black), upside-down, 90° rotation, 1×–8× character scaling, left/center/right justification |
| **Barcodes** | UPC-A, UPC-E, EAN13, EAN8, CODE39, ITF, CODABAR, CODE93, CODE128 — configurable height, width, and HRI text position |
| **Images** | Raw raster bit-images (`GS v 0`) and a high-level PIL/Pillow helper that handles scaling, dithering, and byte-packing automatically |
| **Paper** | Line feed, dot feed, custom line spacing, partial cut with optional pre-feed |
| **Cash Drawer** | Pulse kick on pin 2 or pin 5 with configurable timing, plus a real-time variant that bypasses the receive buffer |
| **Character Sets** | 22 code pages (PC437, PC850, WPC1252, Cyrillic, Latin-2, …) and 16 international character-variant sets |
| **Layout** | Left margin, print-area width, horizontal/vertical motion units, absolute/relative print positioning, tab stops |
| **Status** | Real-time status queries (printer, offline, error, paper sensor) with parsed boolean dicts |
| **NV Storage** | Define and print non-volatile bit images (survive power cycles) |
| **Macros** | Record, store, and replay command sequences |
| **Network** | Proprietary WiFi and wired-LAN configuration (static IP, subnet, gateway, SSID, WPA/WPA2 key) |
| **Sensors** | Paper near-end / paper-end sensor configuration, FEED button enable/disable |

---

## Compatibility

**Printers** — tested on the XP-80T. Should work with any Xprinter 80mm thermal printer that uses the ESC/POS command set documented in the 80XX Programmer Manual, including the XP-58, XP-76, XP-80C, and similar models. Many Epson TM-series compatible printers also share this command set.

**Platform** — Linux only (communicates via USB device files like `/dev/usb/lp0`). Requires Python 3.10+.

**Dependencies** — none for core functionality. [Pillow](https://pypi.org/project/Pillow/) is needed only if you use the `print_image()` method.

---

## Installation

Clone the repository and copy `xprinter.py` into your project, or add the repo root to your `PYTHONPATH`:

```bash
git clone https://github.com/YOUR_USER/xprinter.git
cd xprinter
```

Optional — install Pillow for image printing:

```bash
pip install Pillow
```

There is no `setup.py` or `pyproject.toml` to install — `xprinter.py` is a single self-contained file with no third-party imports. Drop it wherever you need it.

---

## Quick Start

### Print a receipt

```python
from xprinter import XPrinter, BarcodeHRI

with XPrinter("/dev/usb/lp0", auto_init=True) as p:
    # Store header
    p.set_justification("center")
    p.set_character_size(2, 2)
    p.println("MY STORE")
    p.set_character_size(1, 1)
    p.println("123 Main St, Anytown")
    p.println("Tel: (555) 123-4567")
    p.print_separator("=")

    # Line items
    p.set_justification("left")
    p.print_two_column("Espresso x2", "$7.00")
    p.print_two_column("Muffin x1", "$3.50")
    p.print_separator()

    # Total
    p.set_emphasized(True)
    p.set_character_size(1, 2)
    p.print_two_column("TOTAL", "$10.50")
    p.set_character_size(1, 1)
    p.set_emphasized(False)

    # Barcode
    p.set_justification("center")
    p.set_barcode_height(80)
    p.set_barcode_hri(BarcodeHRI.BELOW)
    p.print_barcode("CODE128", "INV-20260401-001")

    p.feed_lines(4)
    p.cut()
```

### Print an image

```python
from PIL import Image
from xprinter import XPrinter

with XPrinter("/dev/usb/lp0", auto_init=True) as p:
    logo = Image.open("logo.png")
    p.print_image(logo)       # auto-scales, dithers, prints
    p.feed_lines(2)
    p.cut()
```

### Configure WiFi

```python
from xprinter import NetworkConfig

NetworkConfig.set_wifi(
    device="/dev/usb/lp0",
    ip="192.168.1.100",
    mask="255.255.255.0",
    gateway="192.168.1.1",
    ssid="OfficeNetwork",
    key="supersecretpassword",
    key_type=6,                # WPA2_AES_PSK (default)
)
```

### Configure wired LAN

```python
from xprinter import NetworkConfig

NetworkConfig.set_lan(
    device="/dev/usb/lp0",
    ip="10.0.0.50",
    mask="255.255.255.0",
    gateway="10.0.0.1",
)
```

---

## CLI Usage

The script doubles as a command-line tool:

```bash
# Print a demo receipt
python3 xprinter.py demo /dev/usb/lp0

# Query all printer status
python3 xprinter.py status /dev/usb/lp0

# Reset printer to factory defaults
python3 xprinter.py init /dev/usb/lp0

# Feed 5 lines and cut
python3 xprinter.py cut /dev/usb/lp0 --feed 5

# Kick cash drawer (pin 0)
python3 xprinter.py kick /dev/usb/lp0 --pin 0

# Configure WiFi
python3 xprinter.py wifi /dev/usb/lp0 192.168.1.100 255.255.255.0 192.168.1.1 MyNetwork secret 6

# Configure LAN
python3 xprinter.py lan /dev/usb/lp0 10.0.0.50 255.255.255.0 10.0.0.1
```

### WiFi Key Types

| Value | Encryption |
|-------|------------|
| 0 | NULL (open) |
| 1 | WEP64 |
| 2 | WEP128 |
| 3 | WPA_AES_PSK |
| 4 | WPA_TKIP_PSK |
| 5 | WPA_TKIP_AES_PSK |
| 6 | **WPA2_AES_PSK** (default) |
| 7 | WPA2_TKIP |
| 8 | WPA2_TKIP_AES_PSK |
| 9 | WPA/WPA2 Mixed Mode |

---

## Library API Reference

### `XPrinter` class

```python
XPrinter(device: str, *, auto_init: bool = False)
```

Opens the printer device file for binary read/write. Use as a context manager for automatic cleanup:

```python
with XPrinter("/dev/usb/lp0", auto_init=True) as p:
    p.println("Hello, World!")
```

#### Lifecycle (Phase 1)

| Method | ESC/POS Command | Description |
|--------|----------------|-------------|
| `initialize()` | `ESC @` | Reset printer to power-on defaults. Call at the start of every print job. |
| `get_status(status_type)` | `DLE EOT n` | Query real-time status. Returns a dict of parsed boolean flags. `status_type`: `PRINTER` (1), `OFFLINE` (2), `ERROR` (3), `PAPER_SENSOR` (4). |
| `set_device_enabled(enabled)` | `ESC = n` | Enable/disable the printer. When disabled, only real-time error-recovery commands are accepted. |
| `request_error_recovery(clear_buffers)` | `DLE ENQ n` | Recover from errors (e.g. cutter jam). Set `clear_buffers=True` to also flush the receive/print buffers. |

#### Text Formatting (Phase 2)

| Method | ESC/POS Command | Description |
|--------|----------------|-------------|
| `set_print_mode(*, font_b, emphasized, double_height, double_width, underline)` | `ESC !` | Set all print mode bits in one call. All flags default to `False` / Font A. |
| `set_justification(align)` | `ESC a` | `"left"`, `"center"`, `"right"` — or use the `Justification` enum. |
| `set_character_size(width, height)` | `GS !` | Scale characters 1×–8× on each axis independently. |
| `set_emphasized(on)` | `ESC E` | Bold on/off. |
| `set_double_strike(on)` | `ESC G` | Double-strike on/off (similar to bold). |
| `set_underline(mode)` | `ESC –` | `OFF` (0), `THIN` (1, 1-dot), `THICK` (2, 2-dot). |
| `set_reverse(on)` | `GS B` | White-on-black reverse printing. |
| `set_upside_down(on)` | `ESC {` | 180° rotation. |
| `set_rotation_90(on)` | `ESC V` | 90° clockwise rotation. |
| `set_font(font_b)` | `ESC M` | Font A (12×24) or Font B (9×17). |

#### Paper Feed & Cutting (Phase 3)

| Method | ESC/POS Command | Description |
|--------|----------------|-------------|
| `feed_lines(n)` | `ESC d` | Print buffer and advance `n` lines (0–255). |
| `feed_dots(n)` | `ESC J` | Print buffer and advance `n` motion-unit steps (fine control). |
| `set_line_spacing(n)` | `ESC 2` / `ESC 3` | `None` = default (1/6 inch). `0–255` = custom spacing in motion units. |
| `cut(feed_n)` | `GS V` | Partial cut. `feed_n=0` cuts immediately; `1–255` feeds first, then cuts. |

#### Barcode Printing (Phase 4)

| Method | ESC/POS Command | Description |
|--------|----------------|-------------|
| `set_barcode_height(dots)` | `GS h` | Bar height in dots (1–255, default 162). |
| `set_barcode_width(n)` | `GS w` | Module width 2–6 (default 3 = 0.375 mm). |
| `set_barcode_hri(position)` | `GS H` | HRI text: `HIDDEN`, `ABOVE`, `BELOW`, `BOTH`. |
| `set_barcode_hri_font(font_b)` | `GS f` | Font A or B for HRI characters. |
| `print_barcode(system, data)` | `GS k` | Print a barcode. `system` accepts a string name (`"CODE128"`, `"EAN13"`, `"UPC-A"`, …), a `BarcodeSystem` enum, or raw int (65–73). |

**Supported barcode systems:** UPC-A, UPC-E, EAN13 (JAN13), EAN8 (JAN8), CODE39, ITF, CODABAR, CODE93, CODE128.

#### Image Printing (Phase 5)

| Method | ESC/POS Command | Description |
|--------|----------------|-------------|
| `print_raster_image(image_data, width_bytes, height_dots, mode)` | `GS v 0` | Low-level: send pre-packed 1-bit raster bytes. |
| `print_image(image, mode, max_width)` | `GS v 0` | High-level: pass a PIL `Image` object. Handles resize, dither, byte-pack. Requires Pillow. |

**Raster modes:** `NORMAL` (0), `DOUBLE_WIDTH` (1), `DOUBLE_HEIGHT` (2), `QUADRUPLE` (3).

#### Cash Drawer (Phase 6)

| Method | ESC/POS Command | Description |
|--------|----------------|-------------|
| `kick_drawer(pin, on_ms, off_ms)` | `ESC p` | Pulse pin 0 (connector pin 2) or pin 1 (pin 5). Timing in milliseconds. |
| `kick_drawer_realtime(pin, pulse_units)` | `DLE DC4` | Real-time variant (bypasses buffer). Each unit = 100 ms on + 100 ms off. |

#### Character Sets (Phase 7)

| Method | ESC/POS Command | Description |
|--------|----------------|-------------|
| `set_code_page(page)` | `ESC t` | Select from 22 code pages: PC437, PC850, WPC1252, PC866 (Cyrillic), etc. |
| `set_international_charset(charset)` | `ESC R` | 16 locale-specific character variants (USA, France, Germany, Japan, …). |

#### Layout & Margins (Phase 8)

| Method | ESC/POS Command | Description |
|--------|----------------|-------------|
| `set_left_margin(dots)` | `GS L` | Left margin in motion-unit dots. |
| `set_print_area_width(dots)` | `GS W` | Printable area width (default 512 for 80mm paper). |
| `set_motion_units(x, y)` | `GS P` | Redefine horizontal/vertical motion units. Pass 0 to keep factory default. |
| `set_absolute_position(dots)` | `ESC $` | Set print position from start of line. |
| `set_relative_position(dots)` | `ESC \` | Move print position relative to current (negative = left). |
| `set_tab_positions(positions)` | `ESC D` | Set horizontal tab stops (ascending list, max 32). Empty list clears all. |
| `set_paper_end_sensor(near_end, end)` | `ESC c 3` | Enable/disable paper-end signal sensors. |
| `set_paper_stop_sensor(near_end)` | `ESC c 4` | Enable/disable auto-stop on paper near-end. |
| `set_panel_buttons(enabled)` | `ESC c 5` | Enable/disable the FEED button on the printer. |

#### NV Images & Macros (Phase 9)

| Method | ESC/POS Command | Description |
|--------|----------------|-------------|
| `define_nv_images(images)` | `FS q` | Store images in non-volatile memory. **Limit writes to ≤10/day** to protect NV memory. Triggers hardware reset. |
| `print_nv_image(slot, mode)` | `FS p` | Print a previously stored NV image by slot number. |
| `start_macro()` / `end_macro()` | `GS :` | Toggle macro recording on/off. |
| `execute_macro(repeat, wait_100ms, wait_for_button)` | `GS ^` | Play back a recorded macro, optionally looping and waiting for button presses. |

#### Status Monitoring

| Method | ESC/POS Command | Description |
|--------|----------------|-------------|
| `set_auto_status_back(*, drawer, online_offline, error, paper_sensor)` | `GS a` | Enable/disable Automatic Status Back. When enabled, the printer pushes 4-byte status packets on state changes. |
| `transmit_status(paper)` | `GS r` | Request paper sensor or drawer connector status (serial interface). |

#### Convenience Helpers

| Method | Description |
|--------|-------------|
| `println(text, encoding)` | Encode text + send LF (print and line feed). |
| `print_text(text, encoding)` | Write text to buffer without line feed. |
| `print_separator(char, width)` | Print a full-width separator line (e.g. `"----..."`). |
| `print_two_column(left, right, width)` | Print left-aligned and right-aligned text on the same line. |

---

### `NetworkConfig` class

Static methods for the proprietary Xprinter network configuration protocol. These bypass the ESC/POS command set entirely and use the `US ESC US 0xB4` preamble.

```python
NetworkConfig.set_wifi(device, ip, mask, gateway, ssid, key, key_type=6)
NetworkConfig.set_lan(device, ip, mask, gateway)
```

Both methods open the device file, write the binary payload, flush, and close. They do not require an `XPrinter` instance.

---

### Enumerations

All enums are `IntEnum` subclasses, so you can use them interchangeably with plain integers:

| Enum | Values |
|------|--------|
| `Justification` | `LEFT` (0), `CENTER` (1), `RIGHT` (2) |
| `UnderlineMode` | `OFF` (0), `THIN` (1), `THICK` (2) |
| `BarcodeHRI` | `HIDDEN` (0), `ABOVE` (1), `BELOW` (2), `BOTH` (3) |
| `BarcodeSystem` | `UPC_A` (65), `UPC_E` (66), `EAN13` (67), `EAN8` (68), `CODE39` (69), `ITF` (70), `CODABAR` (71), `CODE93` (72), `CODE128` (73) |
| `RasterMode` | `NORMAL` (0), `DOUBLE_WIDTH` (1), `DOUBLE_HEIGHT` (2), `QUADRUPLE` (3) |
| `StatusType` | `PRINTER` (1), `OFFLINE` (2), `ERROR` (3), `PAPER_SENSOR` (4) |
| `WifiKeyType` | `NULL` (0) through `WPA_WPA2_MIXED` (9) |
| `CodePage` | `PC437` (0), `KATAKANA` (1), `PC850` (2), … `LATVIAN` (21) |
| `InternationalCharset` | `USA` (0), `FRANCE` (1), … `CHINESE` (15) |

---

## Device Permissions

By default, `/dev/usb/lp0` requires root access. You have two options:

### Option A: Run with `sudo`

```bash
sudo python3 xprinter.py demo /dev/usb/lp0
```

### Option B: udev rule (recommended)

Create a persistent rule so your user can always write to the printer:

```bash
# Find vendor/product IDs
lsusb | grep -i printer

# Create udev rule (adjust idVendor/idProduct to match your printer)
sudo tee /etc/udev/rules.d/99-xprinter.rules << 'EOF'
SUBSYSTEM=="usb", ATTR{idVendor}=="0416", ATTR{idProduct}=="5011", MODE="0666"
SUBSYSTEM=="usbmisc", KERNEL=="lp[0-9]*", MODE="0666"
EOF

# Reload rules
sudo udevadm control --reload-rules
sudo udevadm trigger
```

After this, any user can write to the printer device without `sudo`.

---

## Protocol Reference

### ESC/POS Command Set

The driver implements commands from the 80XX Programmer Manual. Every method docstring includes the command name, hex code, and parameter ranges.

Key command prefixes:

| Prefix | Hex | Purpose |
|--------|-----|---------|
| `ESC` | `1B` | Standard formatting & control commands |
| `GS` | `1D` | Graphics, barcodes, layout, status |
| `FS` | `1C` | Kanji and NV bit-image commands |
| `DLE` | `10` | Real-time commands (bypass receive buffer) |

### Network Configuration Protocol

The WiFi/LAN configuration uses an undocumented proprietary protocol:

```
┌────────────┬─────┬──────────┬──────────┬──────────┬──────────┬──────┬─────┐
│  Preamble  │ Cmd │  IP (4B) │ Mask(4B) │  GW (4B) │ KeyType  │ SSID │ Key │
│  1F 1B 1F  │ B4  │ network  │ network  │ network  │  (1 byte)│ + \0 │+ \0 │
│            │     │  order   │  order   │  order   │  WiFi    │ WiFi │WiFi │
│            │     │          │          │          │  only    │ only │only │
└────────────┴─────┴──────────┴──────────┴──────────┴──────────┴──────┴─────┘
```

For LAN configuration, the payload ends after the gateway bytes — no key type, SSID, or key fields are sent.

---

## Testing

The test suite verifies every command produces byte-correct output without needing a physical printer:

```bash
python3 test_xprinter.py
```

```
═══ Phase 1: Printer Lifecycle ═══
  ✓ ESC @ (initialize)
  ✓ ESC = 1 (enable)
  ...
═══ Phase 9: NV Images & Macros ═══
  ✓ FS p 1 0
  ✓ GS ^ 3 5 0
  ...
══════════════════════════════════════════════════
  Results: 78 passed, 0 failed
══════════════════════════════════════════════════
```

Tests use a temporary file as a fake device, capturing all writes and comparing the raw hex bytes against the programmer manual specifications.

---

## Troubleshooting

**"Device does not exist"**
Check that the printer is connected and powered on. Run `ls /dev/usb/lp*` to find the device path. If nothing shows up, try `dmesg | tail -20` after plugging in the USB cable.

**"Device is not writable"**
See [Device Permissions](#device-permissions). Either use `sudo` or set up a udev rule.

**Garbled output or no response**
Run `p.initialize()` (ESC @) before sending any other commands — leftover state from a previous session can cause unexpected behavior.

**Paper feeds but nothing prints**
Ensure you're calling `println()` (which sends LF) rather than `print_text()` (which only buffers). The printer only renders buffered data when it receives a line feed, cut command, or explicit feed.

**Barcode doesn't print**
Barcodes require an empty print buffer. Make sure you're not mixing text and barcode commands on the same line. Call `println("")` or `feed_lines(1)` before `print_barcode()` if you're mid-line.

**`print_image()` raises ImportError**
Install Pillow: `pip install Pillow`. The core driver has no dependencies, but image printing needs the PIL library for format conversion and dithering.

**Network config sent but printer doesn't connect**
The printer needs a power cycle after receiving a network configuration command. Unplug it, wait 5 seconds, and plug it back in. Verify the SSID and password are correct — there's no error feedback for WiFi credentials.

---

## License

MIT

---

## Acknowledgements

- **[dantecatalfamo/xprinter-wifi](https://github.com/dantecatalfamo/xprinter-wifi)** — reverse-engineered the proprietary WiFi configuration protocol that this driver's `NetworkConfig` class is based on.
- **80XX Programmer Manual** — the ESC/POS command reference used to implement every printing command. Available [here](https://blog.lambda.cx/posts/xprinter-wifi/80XX_Programmer_Manual.pdf).
