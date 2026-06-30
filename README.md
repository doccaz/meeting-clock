# Meeting Clock

A desk-mounted meeting monitor built from 8x MAX7219 8x8 LED matrices (2 rows of 4),
running on a Raspberry Pi Pico W. Features countdown/stopwatch timers, a scrolling
message board with multiple effects, MQTT integration (Home Assistant-compatible),
an OLED + rotary encoder + 2-button control panel, a passive buzzer, and a
rechargeable LiPo battery with USB-C charging.

## Repo structure

- **`wiring/`** — parts list and full wiring diagram (pin assignments, power
  architecture, battery voltage-sense divider).
- **`firmware/`** — MicroPython firmware for the Pico W (display driver, timers,
  OLED/encoder UI, MQTT client, AP-mode web UI). See `firmware/README.md` for
  setup instructions.
- **`case/`** — parametric OpenSCAD 3D-printable case (fused front housing +
  removable back panel) plus ready-to-slice STLs and preview renders.

## Quick start

1. Read `wiring/meeting-monitor-wiring-and-parts.md` and build the hardware.
2. Flash MicroPython onto the Pico W, then follow `firmware/README.md` to install
   dependencies and copy the firmware over.
3. Print `case/front_housing.stl` and `case/back_panel.stl` (adjust `case.scad`
   first if your MAX7219 modules' mounting holes differ from the default).
4. On first boot, connect to the `MeetingMonitor-Setup` WiFi AP to configure your
   real WiFi + MQTT broker via the on-device web UI.
