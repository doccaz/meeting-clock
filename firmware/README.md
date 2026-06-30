# Meeting Monitor — Firmware (MicroPython, Pico W)

## Files
- `main.py` — entry point, ties everything together
- `config.py` — pin map and defaults (edit if your wiring differs)
- `display.py` / `max7219.py` — drives the two 4x MAX7219 chains, scroll/blink effects
- `timers.py` — countdown / stopwatch logic
- `buzzer.py` — passive buzzer tones/alerts
- `ui.py` — encoder + 2 buttons + OLED menu
- `mqtt_handler.py` — Home Assistant MQTT integration
- `webserver.py` — WiFi STA/AP manager + settings/control web UI

## One-time setup on the Pico W

1. Flash the official **Raspberry Pi Pico W MicroPython firmware** (not the plain Pico build — it must include `network`/`rp2` WiFi support).
2. Install two standard MicroPython packages over WiFi or USB (using `mip`, run from the MicroPython REPL once the Pico has any network, or via Thonny's package manager):
   ```python
   import mip
   mip.install("ssd1306")
   mip.install("umqtt.simple")
   ```
   If the Pico has no WiFi yet, you can instead copy `ssd1306.py` and the `umqtt` folder onto the device manually from micropython-lib.
3. Copy all files in this folder onto the Pico's root (e.g. via Thonny "Save As → Raspberry Pi Pico", or `mpremote cp *.py :`).
4. Reset the Pico. On first boot (no saved WiFi credentials), it will start in **AP mode**: connect to WiFi network `MeetingMonitor-Setup` (password `configure123`), browse to `http://192.168.4.1`, and enter your real WiFi + MQTT details. It reboots into normal station mode after saving.

## Effects available for message scroller
- `static` — text held in place
- `scroll_left` — classic marquee
- `scroll_up` — vertical scroll
- `blink` — flashing text

Set via the web UI dropdown, the OLED menu, or MQTT (`"effect"` field in the `message` command).

## MQTT (Home Assistant)
Default topic prefix: `meetingmonitor` (change in `config.py`).
- Subscribe `meetingmonitor/cmd` — send JSON commands, e.g.:
  ```json
  {"action": "countdown", "seconds": 300}
  {"action": "message", "text": "In a meeting", "effect": "scroll_left"}
  ```
- Publishes `meetingmonitor/status` (retained) every 15s with current mode/timer/battery state — usable as an HA MQTT sensor.

## Battery monitoring
A voltage divider (2x 100kΩ) taps the raw LiPo+ terminal (before the boost converter) into GP26/ADC0 — see the wiring doc for the diagram. This keeps the reading independent of the regulated 5V rail.

## Next steps
- 3D printable case (front matrix panel + rear electronics bay) — in progress.
