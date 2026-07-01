# Meeting Monitor — Firmware (MicroPython)

Compatible with both **Raspberry Pi Pico** and **Pico W**.
WiFi, MQTT, and the web UI are auto-detected at boot: on a plain Pico they
are silently disabled and the device runs fully offline. No config change
needed — just flash and go.

## Files
- `main.py` — entry point; auto-detects WiFi and assembles the task list
- `config.py` — pin map and defaults (edit if your wiring differs)
- `display.py` / `max7219.py` — drives the two 4×MAX7219 chains, scroll/blink effects
- `timers.py` — countdown / stopwatch logic
- `buzzer.py` — passive buzzer tones/alerts
- `ui.py` — encoder + 2 buttons + OLED menu; WiFi-only settings shown greyed out on plain Pico
- `mqtt_handler.py` — Home Assistant MQTT integration (Pico W only)
- `webserver.py` — WiFi STA/AP manager + settings/control web UI (Pico W only)

## Board compatibility

| Feature | Pico | Pico W |
|---|---|---|
| Timers, display, effects | ✅ | ✅ |
| Encoder / buttons / OLED | ✅ | ✅ |
| Buzzer | ✅ | ✅ |
| Battery monitoring | ✅ | ✅ |
| WiFi / AP setup web UI | — | ✅ |
| MQTT (Home Assistant) | — | ✅ |

## One-time setup

1. Flash the official **Raspberry Pi Pico / Pico W MicroPython firmware**.
   Use the Pico W build if you want WiFi (it includes the `network` module);
   use the standard Pico build for offline-only use.
2. Install dependencies (only needed on Pico W, or if you have WiFi):
   ```python
   import mip
   mip.install("ssd1306")
   mip.install("umqtt.simple")
   ```
   On a plain Pico, only `ssd1306` is needed and can be installed the same way
   or copied manually from micropython-lib.
3. Copy all `.py` files to the Pico's root (e.g. via Thonny "Save As →
   Raspberry Pi Pico", or `mpremote cp *.py :`).
4. Reset the board.
   - **Pico W (first boot, no saved credentials):** starts AP mode — connect
     to `MeetingMonitor-Setup` (password `configure123`), browse to
     `http://192.168.4.1`, enter WiFi + MQTT details, save.
   - **Plain Pico:** boots straight into offline mode, no setup needed.

## OLED settings menu (plain Pico)

WiFi-dependent items (AP Mode, MQTT Reconnect, WiFi Reset) appear with a
`-` prefix and cannot be selected — they are visible but inactive, so the
menu layout stays consistent regardless of board.

## Scroll effects (message scroller)
- `static` — text held in place
- `scroll_left` — classic marquee
- `scroll_up` — vertical scroll
- `blink` — flashing text

Set via the OLED menu, or on Pico W via the web UI / MQTT.

## MQTT (Pico W / Home Assistant)
Default topic prefix: `meetingmonitor` (change in `config.py`).
- Subscribe `meetingmonitor/cmd` — send JSON commands:
  ```json
  {"action": "countdown", "seconds": 300}
  {"action": "message", "text": "In a meeting", "effect": "scroll_left"}
  {"action": "brightness", "level": 5}
  ```
- Publishes `meetingmonitor/status` (retained) every 15 s with current
  mode/timer/battery state — usable as an HA MQTT sensor.

## Battery monitoring
A voltage divider (2×100kΩ) taps the raw LiPo+ terminal (before the boost
converter) into GP26/ADC0 — see `../wiring/` for the full diagram.

## Related
- `../case/` — 3D-printable case (fused front housing + removable back panel), STLs and OpenSCAD source.
- `../wiring/` — full parts list and wiring diagram.
