"""
webserver.py - WiFi connection management (STA + AP fallback) and a small
async HTTP server providing a settings/control web UI.

Settings persist to settings.json on the Pico's flash filesystem.
"""
import network
import json
import uasyncio as asyncio
import time
import config

SETTINGS_FILE = "settings.json"


def load_settings():
    try:
        with open(SETTINGS_FILE) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_settings(d):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(d, f)


class WifiManager:
    def __init__(self):
        self.sta = network.WLAN(network.STA_IF)
        self.ap = network.WLAN(network.AP_IF)
        self.sta.active(True)
        self.mode = "none"  # "sta", "ap"

    def try_connect_sta(self, ssid, password, timeout_s=15):
        if not ssid:
            return False
        self.sta.active(True)
        self.sta.connect(ssid, password)
        t0 = time.time()
        while not self.sta.isconnected() and time.time() - t0 < timeout_s:
            time.sleep_ms(250)
        if self.sta.isconnected():
            self.mode = "sta"
            return True
        return False

    def start_ap(self):
        self.ap.active(True)
        self.ap.config(essid=config.AP_SSID, password=config.AP_PASS)
        self.mode = "ap"

    def status_string(self):
        if self.mode == "sta" and self.sta.isconnected():
            return "Connected " + self.sta.ifconfig()[0]
        if self.mode == "ap":
            return "AP " + config.AP_SSID
        return "Disconnected"

    def ip(self):
        if self.mode == "sta" and self.sta.isconnected():
            return self.sta.ifconfig()[0]
        if self.mode == "ap":
            return self.ap.ifconfig()[0]
        return "0.0.0.0"


PAGE_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Meeting Monitor</title>
<style>
  body {{ font-family: -apple-system, sans-serif; background:#111; color:#eee; margin:0; padding:20px; }}
  h1 {{ font-size:20px; color:#4fd1c5; }}
  fieldset {{ border:1px solid #333; border-radius:8px; margin-bottom:16px; padding:12px; }}
  legend {{ color:#4fd1c5; padding:0 6px; }}
  label {{ display:block; margin-top:8px; font-size:13px; color:#aaa; }}
  input, select {{ width:100%; box-sizing:border-box; padding:8px; margin-top:4px;
                    background:#1c1c1c; border:1px solid #333; color:#eee; border-radius:6px; }}
  button {{ background:#4fd1c5; color:#111; border:none; padding:10px 16px; border-radius:6px;
            font-weight:bold; margin-top:12px; cursor:pointer; }}
  .row {{ display:flex; gap:8px; }}
  .row > div {{ flex:1; }}
  .status {{ font-size:13px; color:#888; }}
</style>
</head>
<body>
<h1>Meeting Monitor</h1>
<p class="status">{status}</p>

<form method="POST" action="/save_wifi">
<fieldset><legend>WiFi</legend>
<label>SSID</label><input name="ssid" value="{ssid}">
<label>Password</label><input name="password" type="password">
<button type="submit">Save & Reconnect</button>
</fieldset>
</form>

<form method="POST" action="/save_mqtt">
<fieldset><legend>MQTT (Home Assistant)</legend>
<label>Broker IP/host</label><input name="broker" value="{broker}">
<label>Port</label><input name="port" value="{port}">
<label>Username</label><input name="mqtt_user" value="{mqtt_user}">
<label>Password</label><input name="mqtt_pass" type="password">
<button type="submit">Save</button>
</fieldset>
</form>

<form method="POST" action="/control">
<fieldset><legend>Quick Control</legend>
<div class="row">
<div><label>Countdown (min)</label><input name="minutes" value="5"></div>
<div style="align-self:flex-end"><button type="submit" name="action" value="countdown">Start</button></div>
</div>
<label>Message</label><input name="message" placeholder="Type a message">
<label>Effect</label>
<select name="effect">
<option value="scroll_left">Scroll Left</option>
<option value="scroll_up">Scroll Up</option>
<option value="static">Static</option>
<option value="blink">Blink</option>
</select>
<button type="submit" name="action" value="message">Show Message</button>
<button type="submit" name="action" value="stop">Stop / Clear</button>
</fieldset>
</form>

<form method="POST" action="/save_brightness">
<fieldset><legend>Brightness ({brightness}/15)</legend>
<input name="brightness" type="range" min="0" max="15" value="{brightness}" oninput="this.nextElementSibling.value=this.value">
<output>{brightness}</output>
<button type="submit">Save</button>
</fieldset>
</form>

</body>
</html>
"""


def render_page(app):
    s = load_settings()
    return PAGE_TEMPLATE.format(
        status=app.wifi.status_string() + " | MQTT: " + app.mqtt_status_string(),
        ssid=s.get("wifi_ssid", config.WIFI_SSID),
        broker=s.get("mqtt_broker", config.MQTT_BROKER),
        port=s.get("mqtt_port", config.MQTT_PORT),
        mqtt_user=s.get("mqtt_user", config.MQTT_USER),
        brightness=s.get("brightness", config.DEFAULT_BRIGHTNESS),
    )


def parse_form(body):
    out = {}
    for pair in body.split("&"):
        if "=" in pair:
            k, v = pair.split("=", 1)
            out[_urldecode(k)] = _urldecode(v)
    return out


def _urldecode(s):
    s = s.replace("+", " ")
    out = ""
    i = 0
    while i < len(s):
        if s[i] == "%" and i + 2 < len(s):
            out += chr(int(s[i + 1:i + 3], 16))
            i += 3
        else:
            out += s[i]
            i += 1
    return out


async def handle_client(reader, writer, app):
    try:
        req_line = await reader.readline()
        method, path, _ = req_line.decode().split(" ", 2)
        headers = {}
        content_length = 0
        while True:
            line = await reader.readline()
            if line in (b"\r\n", b""):
                break
            k, v = line.decode().split(":", 1)
            headers[k.strip().lower()] = v.strip()
            if k.strip().lower() == "content-length":
                content_length = int(v.strip())

        body = ""
        if content_length:
            body = (await reader.readexactly(content_length)).decode()

        response_body = ""
        status = "200 OK"

        if path == "/" and method == "GET":
            response_body = render_page(app)
        elif path == "/save_wifi" and method == "POST":
            form = parse_form(body)
            s = load_settings()
            s["wifi_ssid"] = form.get("ssid", "")
            s["wifi_pass"] = form.get("password", "") or s.get("wifi_pass", "")
            save_settings(s)
            app.request_wifi_reconnect()
            response_body = render_page(app)
        elif path == "/save_mqtt" and method == "POST":
            form = parse_form(body)
            s = load_settings()
            s["mqtt_broker"] = form.get("broker", "")
            s["mqtt_port"] = int(form.get("port", "1883") or 1883)
            s["mqtt_user"] = form.get("mqtt_user", "")
            if form.get("mqtt_pass"):
                s["mqtt_pass"] = form.get("mqtt_pass")
            save_settings(s)
            app.request_mqtt_reconnect()
            response_body = render_page(app)
        elif path == "/save_brightness" and method == "POST":
            form = parse_form(body)
            s = load_settings()
            level = int(form.get("brightness", config.DEFAULT_BRIGHTNESS))
            s["brightness"] = level
            save_settings(s)
            app.set_brightness(level)
            response_body = render_page(app)
        elif path == "/control" and method == "POST":
            form = parse_form(body)
            action = form.get("action", "")
            if action == "countdown":
                minutes = int(form.get("minutes", "5") or 5)
                app.start_countdown(minutes * 60)
            elif action == "message":
                app.show_message(form.get("message", ""), form.get("effect", "scroll_left"))
            elif action == "stop":
                app.stop_timer()
                app.clear_display()
            response_body = render_page(app)
        else:
            status = "404 Not Found"
            response_body = "Not found"

        writer.write("HTTP/1.1 {}\r\nContent-Type: text/html\r\nConnection: close\r\n\r\n".format(status).encode())
        writer.write(response_body.encode())
        await writer.drain()
    except Exception:
        pass
    finally:
        await writer.aclose()


async def run_server(app, port=80):
    async def _handler(reader, writer):
        await handle_client(reader, writer, app)
    server = await asyncio.start_server(_handler, "0.0.0.0", port)
    return server
