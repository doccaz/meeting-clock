"""
main.py - entry point. Boots WiFi (STA, falling back to AP), starts the web
server, MQTT client, OLED/encoder UI, and the matrix display loop.

Run with cooperative asyncio tasks so timers, animations, MQTT, and the web
server all stay responsive together.
"""
import uasyncio as asyncio
import time
import json
from machine import ADC, Pin

import config
from display import Display, Zone
from timers import Timer
from buzzer import Buzzer
from ui import UI
import webserver
import mqtt_handler

DEFAULT_MESSAGES = [
    "Meeting in progress",
    "Please knock",
    "Back in 5 minutes",
    "Welcome!",
]

# Battery monitoring: resistor divider from the RAW LiPo+ terminal (before
# the boost converter) into GP26 (ADC0), per the wiring doc — 100k/100k
# halves 4.2V down to 2.1V, safely under the 3.3V ADC max.
BATTERY_ADC_PIN = 26
BATTERY_DIVIDER_RATIO = 2.0  # multiply ADC voltage by this to get true batt voltage
BATTERY_MIN_V = 3.3
BATTERY_MAX_V = 4.2


class App:
    def __init__(self):
        self.display = Display()
        self.buzzer = Buzzer(config.BUZZER_PIN)
        self.wifi = webserver.WifiManager()
        self.timer = Timer("countdown")
        self.timer.on_done = self._on_timer_done
        self.mode = None  # "countdown" | "stopwatch" | "message"
        self.saved_messages = list(DEFAULT_MESSAGES)
        self.current_message = None
        self._pending_wifi_reconnect = False
        self._pending_mqtt_reconnect = False

        settings = webserver.load_settings()
        self.brightness_level = settings.get("brightness", config.DEFAULT_BRIGHTNESS)
        self.display.brightness(self.brightness_level)

        self.mqtt = mqtt_handler.MqttHandler(
            self,
            broker=settings.get("mqtt_broker", config.MQTT_BROKER),
            port=settings.get("mqtt_port", config.MQTT_PORT),
            client_id=config.MQTT_CLIENT_ID,
            prefix=config.MQTT_TOPIC_PREFIX,
            user=settings.get("mqtt_user", config.MQTT_USER),
            password=settings.get("mqtt_pass", config.MQTT_PASS),
        )

        try:
            self.battery_adc = ADC(Pin(BATTERY_ADC_PIN))
        except Exception:
            self.battery_adc = None

        self.ui = UI(self)

    # ---- boot sequence ----
    def boot_network(self):
        settings = webserver.load_settings()
        ssid = settings.get("wifi_ssid", config.WIFI_SSID)
        password = settings.get("wifi_pass", config.WIFI_PASS)
        if not self.wifi.try_connect_sta(ssid, password):
            self.wifi.start_ap()

    # ---- timer actions (called from UI, web, or MQTT) ----
    def start_countdown(self, seconds):
        self.mode = "countdown"
        self.timer = Timer("countdown")
        self.timer.on_done = self._on_timer_done
        self.timer.set_duration(seconds)
        self.timer.start()
        self.display.row2.set_text("", Zone.EFFECT_STATIC)

    def start_stopwatch(self):
        self.mode = "stopwatch"
        self.timer = Timer("stopwatch")
        self.timer.on_done = self._on_timer_done
        self.timer.start()
        self.display.row2.set_text("", Zone.EFFECT_STATIC)

    def toggle_timer(self):
        self.timer.toggle()

    def reset_timer(self):
        self.timer.reset()

    def stop_timer(self):
        self.timer.reset()
        self.mode = None

    def _on_timer_done(self):
        self.buzzer.alert_done()

    def show_message(self, text, effect="scroll_left"):
        self.mode = "message"
        self.current_message = text
        self.display.row1.set_text(text, effect, speed_ms=60)

    def clear_display(self):
        self.display.clear()
        self.mode = None

    # ---- settings actions ----
    def cycle_brightness(self):
        self.brightness_level = (self.brightness_level + 3) % 16
        self.set_brightness(self.brightness_level)

    def set_brightness(self, level):
        self.brightness_level = level
        self.display.brightness(level)
        s = webserver.load_settings()
        s["brightness"] = level
        webserver.save_settings(s)

    def toggle_ap_mode(self):
        if self.wifi.mode == "ap":
            self._pending_wifi_reconnect = True
        else:
            self.wifi.start_ap()

    def reconnect_mqtt(self):
        self._pending_mqtt_reconnect = True

    def reset_wifi_settings(self):
        s = webserver.load_settings()
        s["wifi_ssid"] = ""
        s["wifi_pass"] = ""
        webserver.save_settings(s)
        self.wifi.start_ap()

    def request_wifi_reconnect(self):
        self._pending_wifi_reconnect = True

    def request_mqtt_reconnect(self):
        self._pending_mqtt_reconnect = True

    # ---- remote (MQTT) command handling ----
    def handle_remote_command(self, cmd):
        action = cmd.get("action")
        if action == "countdown":
            self.start_countdown(int(cmd.get("seconds", 300)))
        elif action == "stopwatch_start":
            self.start_stopwatch()
        elif action == "timer_pause":
            self.timer.pause()
        elif action == "timer_resume":
            self.timer.start()
        elif action == "timer_reset":
            self.reset_timer()
        elif action == "message":
            self.show_message(cmd.get("text", ""), cmd.get("effect", "scroll_left"))
        elif action == "brightness":
            self.set_brightness(int(cmd.get("level", config.DEFAULT_BRIGHTNESS)))
        elif action == "clear":
            self.clear_display()

    def state_dict(self):
        return {
            "mode": self.mode,
            "timer_state": self.timer.state,
            "timer_display": self.timer.display_string(),
            "brightness": self.brightness_level,
            "wifi": self.wifi.status_string(),
            "battery_pct": self.battery_percent(),
        }

    # ---- status/info helpers for UI ----
    def clock_string(self):
        t = time.localtime()
        return "{:02d}:{:02d}:{:02d}".format(t[3], t[4], t[5])

    def wifi_status_string(self):
        return self.wifi.status_string()

    def mqtt_status_string(self):
        return "OK" if self.mqtt.connected else "--"

    def active_mode_label(self):
        return {"countdown": "Countdown", "stopwatch": "Stopwatch", "message": "Message"}.get(self.mode, "Idle")

    def battery_percent(self):
        if not self.battery_adc:
            return -1
        raw = self.battery_adc.read_u16()
        v_adc = (raw / 65535) * 3.3
        v_batt = v_adc * BATTERY_DIVIDER_RATIO
        pct = (v_batt - BATTERY_MIN_V) / (BATTERY_MAX_V - BATTERY_MIN_V) * 100
        return max(0, min(100, round(pct)))


async def task_display_tick(app):
    while True:
        app.display.tick()
        await asyncio.sleep_ms(20)


async def task_timer_tick(app):
    while True:
        app.timer.tick()
        if app.mode in ("countdown", "stopwatch"):
            app.display.row1.set_text(app.timer.display_string(), Zone.EFFECT_STATIC)
        await asyncio.sleep_ms(200)


async def task_ui_poll(app):
    while True:
        app.ui.update()
        await asyncio.sleep_ms(15)


async def task_mqtt_poll(app):
    while True:
        if app._pending_mqtt_reconnect:
            app._pending_mqtt_reconnect = False
            app.mqtt.connected = False
            app.mqtt.connect()
        app.mqtt.poll()
        await asyncio.sleep_ms(100)


async def task_mqtt_status_publish(app):
    while True:
        app.mqtt.publish_status()
        await asyncio.sleep(15)


async def task_wifi_watchdog(app):
    while True:
        if app._pending_wifi_reconnect:
            app._pending_wifi_reconnect = False
            settings = webserver.load_settings()
            ssid = settings.get("wifi_ssid", config.WIFI_SSID)
            password = settings.get("wifi_pass", config.WIFI_PASS)
            if not app.wifi.try_connect_sta(ssid, password):
                app.wifi.start_ap()
        await asyncio.sleep(2)


async def main():
    app = App()
    app.boot_network()
    await webserver.run_server(app, port=80)
    app.mqtt.connect()

    await asyncio.gather(
        task_display_tick(app),
        task_timer_tick(app),
        task_ui_poll(app),
        task_mqtt_poll(app),
        task_mqtt_status_publish(app),
        task_wifi_watchdog(app),
    )


if __name__ == "__main__":
    asyncio.run(main())
