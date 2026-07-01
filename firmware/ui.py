"""
ui.py - encoder, buttons, and OLED menu state machine.

Requires ssd1306.py on the device (standard MicroPython driver). Install with:
    import mip; mip.install("ssd1306")
or copy ssd1306.py from micropython-lib into the project folder.

WiFi-dependent settings items are shown greyed out (prefixed with a dash
rather than selectable) when running on a plain Pico without wireless.
"""
from machine import Pin, I2C
import time
import config

try:
    import ssd1306
except ImportError:
    ssd1306 = None  # UI will run "headless" (no OLED) if driver missing

# Wifi capability flag - mirrors the check in main.py, done independently
# here so ui.py has no circular import dependency on main.
try:
    import network as _net  # noqa: F401
    _WIFI_CAPABLE = True
except ImportError:
    _WIFI_CAPABLE = False


class Encoder:
    """Quadrature rotary encoder with interrupt-driven step counting."""

    def __init__(self, pin_a, pin_b, pin_sw):
        self.pa = Pin(pin_a, Pin.IN, Pin.PULL_UP)
        self.pb = Pin(pin_b, Pin.IN, Pin.PULL_UP)
        self.sw = Pin(pin_sw, Pin.IN, Pin.PULL_UP)
        self._pos = 0
        self._last_state = (self.pa.value() << 1) | self.pb.value()
        self.pa.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=self._on_change)
        self.pb.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=self._on_change)
        self._sw_last = 1
        self._sw_last_change = time.ticks_ms()

    def _on_change(self, pin):
        state = (self.pa.value() << 1) | self.pb.value()
        transitions = {
            (0b00, 0b01): 1, (0b01, 0b11): 1, (0b11, 0b10): 1, (0b10, 0b00): 1,
            (0b00, 0b10): -1, (0b10, 0b11): -1, (0b11, 0b01): -1, (0b01, 0b00): -1,
        }
        delta = transitions.get((self._last_state, state), 0)
        self._pos += delta
        self._last_state = state

    def read_steps(self):
        steps = self._pos // 4
        self._pos -= steps * 4
        return steps

    def pressed(self):
        now = time.ticks_ms()
        val = self.sw.value()
        if val != self._sw_last and time.ticks_diff(now, self._sw_last_change) > 30:
            self._sw_last_change = now
            self._sw_last = val
            if val == 0:
                return True
        return False


class Button:
    def __init__(self, pin_num):
        self.pin = Pin(pin_num, Pin.IN, Pin.PULL_UP)
        self._last = 1
        self._last_change = time.ticks_ms()
        self._press_start = 0

    def short_press(self):
        return self._poll() == "short"

    def long_press(self):
        return self._poll() == "long"

    def _poll(self):
        now = time.ticks_ms()
        val = self.pin.value()
        result = None
        if val != self._last and time.ticks_diff(now, self._last_change) > 30:
            self._last_change = now
            if val == 0:
                self._press_start = now
            else:
                held = time.ticks_diff(now, self._press_start)
                result = "long" if held >= 600 else "short"
            self._last = val
        return result


# Settings menu items: (label, wifi_required)
_SETTINGS_ITEMS = [
    ("Brightness",      False),
    ("AP Mode",         True),
    ("MQTT Reconnect",  True),
    ("WiFi Reset",      True),
    ("Back",            False),
]


class UI:
    SCREEN_HOME = "home"
    SCREEN_MODE_SELECT = "mode_select"
    SCREEN_COUNTDOWN_SET = "countdown_set"
    SCREEN_RUNNING = "running"
    SCREEN_MESSAGE_SELECT = "message_select"
    SCREEN_SETTINGS = "settings"

    MODES = ["Countdown", "Stopwatch", "Message", "Settings"]

    def __init__(self, app):
        self.app = app
        self.encoder = Encoder(config.ENC_A, config.ENC_B, config.ENC_SW)
        self.btn_a = Button(config.BTN_A)
        self.btn_b = Button(config.BTN_B)

        self.oled = None
        if ssd1306:
            i2c = I2C(config.OLED_I2C_ID, sda=Pin(config.OLED_SDA),
                      scl=Pin(config.OLED_SCL), freq=400_000)
            self.oled = ssd1306.SSD1306_I2C(config.OLED_WIDTH, config.OLED_HEIGHT,
                                             i2c, addr=config.OLED_ADDR)

        self.screen = self.SCREEN_HOME
        self.menu_index = 0
        self.countdown_minutes = 5
        self._dirty = True

    def _settings_items(self):
        """Returns list of (label, enabled) for the settings screen."""
        return [(label, not wifi_req or _WIFI_CAPABLE)
                for label, wifi_req in _SETTINGS_ITEMS]

    def _settings_labels(self):
        return [label for label, _ in _SETTINGS_ITEMS]

    # ---- input handling ----
    def update(self):
        steps = self.encoder.read_steps()
        enc_press = self.encoder.pressed()
        a_short = self.btn_a.short_press()
        a_long = self.btn_a.long_press()
        b_short = self.btn_b.short_press()
        b_long = self.btn_b.long_press()

        if steps or enc_press or a_short or a_long or b_short or b_long:
            self.app.buzzer.beep()
            self._dirty = True
            self._handle_input(steps, enc_press, a_short, a_long, b_short, b_long)

        if self._dirty:
            self._render()
            self._dirty = False

    def _handle_input(self, steps, enc_press, a_short, a_long, b_short, b_long):
        items = self._settings_items()

        if self.screen == self.SCREEN_HOME:
            if enc_press or b_short:
                self.screen = self.SCREEN_MODE_SELECT
                self.menu_index = 0

        elif self.screen == self.SCREEN_MODE_SELECT:
            self.menu_index = (self.menu_index + steps) % len(self.MODES)
            if b_short:
                self.screen = self.SCREEN_HOME
            elif enc_press:
                choice = self.MODES[self.menu_index]
                if choice == "Countdown":
                    self.screen = self.SCREEN_COUNTDOWN_SET
                elif choice == "Stopwatch":
                    self.app.start_stopwatch()
                    self.screen = self.SCREEN_RUNNING
                elif choice == "Message":
                    self.menu_index = 0
                    self.screen = self.SCREEN_MESSAGE_SELECT
                elif choice == "Settings":
                    self.menu_index = 0
                    self.screen = self.SCREEN_SETTINGS

        elif self.screen == self.SCREEN_COUNTDOWN_SET:
            self.countdown_minutes = max(1, min(180, self.countdown_minutes + steps))
            if b_short:
                self.screen = self.SCREEN_MODE_SELECT
            elif enc_press or a_short:
                self.app.start_countdown(self.countdown_minutes * 60)
                self.screen = self.SCREEN_RUNNING

        elif self.screen == self.SCREEN_RUNNING:
            if a_short:
                self.app.toggle_timer()
            elif a_long:
                self.app.reset_timer()
            elif b_short or b_long:
                self.app.stop_timer()
                self.screen = self.SCREEN_HOME

        elif self.screen == self.SCREEN_MESSAGE_SELECT:
            msgs = self.app.saved_messages
            if msgs:
                self.menu_index = (self.menu_index + steps) % len(msgs)
            if b_short:
                self.screen = self.SCREEN_MODE_SELECT
            elif enc_press or a_short:
                if msgs:
                    self.app.show_message(msgs[self.menu_index])
                self.screen = self.SCREEN_HOME

        elif self.screen == self.SCREEN_SETTINGS:
            self.menu_index = (self.menu_index + steps) % len(items)
            if b_short:
                self.screen = self.SCREEN_MODE_SELECT
            elif enc_press:
                label, enabled = items[self.menu_index]
                if not enabled:
                    return  # greyed-out: ignore press silently
                if label == "Brightness":
                    self.app.cycle_brightness()
                elif label == "AP Mode":
                    self.app.toggle_ap_mode()
                elif label == "MQTT Reconnect":
                    self.app.reconnect_mqtt()
                elif label == "WiFi Reset":
                    self.app.reset_wifi_settings()
                elif label == "Back":
                    self.screen = self.SCREEN_MODE_SELECT

    # ---- rendering ----
    def _render(self):
        if not self.oled:
            return
        o = self.oled
        o.fill(0)

        if self.screen == self.SCREEN_HOME:
            o.text(self.app.clock_string(), 0, 0)
            if _WIFI_CAPABLE:
                o.text("WiFi: " + self.app.wifi_status_string(), 0, 16)
                o.text("MQTT: " + self.app.mqtt_status_string(), 0, 28)
                o.text("Batt: {}%".format(self.app.battery_percent()), 0, 40)
            else:
                o.text("No WiFi (Pico)", 0, 16)
                o.text("Batt: {}%".format(self.app.battery_percent()), 0, 28)
            o.text("Press to menu", 0, 54)

        elif self.screen == self.SCREEN_MODE_SELECT:
            o.text("-- Mode --", 0, 0)
            for i, m in enumerate(self.MODES):
                prefix = ">" if i == self.menu_index else " "
                o.text("{}{}".format(prefix, m), 0, 16 + i * 12)

        elif self.screen == self.SCREEN_COUNTDOWN_SET:
            o.text("Set countdown", 0, 0)
            o.text("{} min".format(self.countdown_minutes), 30, 24)
            o.text("Rotate=adjust", 0, 48)
            o.text("Press=start", 0, 56)

        elif self.screen == self.SCREEN_RUNNING:
            o.text(self.app.active_mode_label(), 0, 0)
            o.text(self.app.timer.display_string(), 20, 24)
            o.text(self.app.timer.state, 0, 48)

        elif self.screen == self.SCREEN_MESSAGE_SELECT:
            o.text("-- Messages --", 0, 0)
            for i, m in enumerate(self.app.saved_messages[:4]):
                prefix = ">" if i == self.menu_index else " "
                o.text("{}{}".format(prefix, m[:14]), 0, 16 + i * 12)

        elif self.screen == self.SCREEN_SETTINGS:
            o.text("-- Settings --", 0, 0)
            for i, (label, enabled) in enumerate(self._settings_items()):
                if i == self.menu_index and enabled:
                    prefix = ">"
                elif not enabled:
                    prefix = "-"  # greyed out
                else:
                    prefix = " "
                o.text("{}{}".format(prefix, label), 0, 16 + i * 9)

        o.show()
