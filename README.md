# Meeting Clock

A desk-mounted meeting monitor built from 8× MAX7219 8×8 LED matrices (2 rows of 4),
running on a Raspberry Pi Pico or **Pico W**. Features countdown/stopwatch timers,
a scrolling message board with multiple effects, an OLED + rotary encoder +
2-button control panel, a passive buzzer, and a rechargeable LiPo battery with
USB-C charging.

WiFi, MQTT (Home Assistant), and the web UI are **auto-detected** at boot —
a plain Pico runs fully offline with no config change needed.

## Repo structure

- **`wiring/`** — parts list and full wiring diagram (pin assignments, power
  architecture, battery voltage-sense divider).
- **`firmware/`** — MicroPython firmware. See `firmware/README.md` for setup
  instructions and board compatibility table.
- **`case/`** — parametric OpenSCAD 3D-printable case (fused front housing +
  removable back panel) plus ready-to-slice STLs and preview renders.

## Quick start

1. Read `wiring/meeting-monitor-wiring-and-parts.md` and build the hardware.
2. Flash MicroPython onto the Pico (or Pico W), then follow `firmware/README.md`.
3. Print `case/front_housing.stl` and `case/back_panel.stl`.
4. **Pico W only:** on first boot connect to the `MeetingMonitor-Setup` WiFi AP
   to configure WiFi + MQTT via the on-device web UI at `http://192.168.4.1`.
   Plain Pico boots straight into offline mode — no setup needed.
