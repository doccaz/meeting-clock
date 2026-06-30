"""
mqtt_handler.py - MQTT integration.

Requires umqtt.simple on the device (standard MicroPython package). Install with:
    import mip; mip.install("umqtt.simple")

Topics (prefix configurable in config.py / settings.json):
  <prefix>/cmd       - subscribe, JSON commands, see _handle_command()
  <prefix>/status     - publish, JSON state, retained

Example commands published to <prefix>/cmd:
  {"action": "countdown", "seconds": 300}
  {"action": "stopwatch_start"}
  {"action": "timer_pause"}
  {"action": "timer_reset"}
  {"action": "message", "text": "Meeting starts soon", "effect": "scroll_left"}
  {"action": "brightness", "level": 5}
"""
import json
import time

try:
    from umqtt.simple import MQTTClient
except ImportError:
    MQTTClient = None


class MqttHandler:
    def __init__(self, app, broker, port, client_id, prefix, user=None, password=None):
        self.app = app
        self.broker = broker
        self.port = port
        self.client_id = client_id
        self.prefix = prefix
        self.user = user or None
        self.password = password or None
        self.client = None
        self.connected = False
        self._last_attempt = 0

    def connect(self):
        if not MQTTClient or not self.broker:
            return False
        try:
            self.client = MQTTClient(
                self.client_id, self.broker, port=self.port,
                user=self.user, password=self.password, keepalive=60,
            )
            self.client.set_callback(self._on_message)
            self.client.connect()
            self.client.subscribe(self._topic("cmd"))
            self.connected = True
            self.publish_status()
            return True
        except Exception:
            self.connected = False
            return False

    def _topic(self, suffix):
        return "{}/{}".format(self.prefix, suffix)

    def _on_message(self, topic, msg):
        try:
            cmd = json.loads(msg)
        except ValueError:
            return
        self.app.handle_remote_command(cmd)

    def publish_status(self):
        if not self.connected:
            return
        state = self.app.state_dict()
        try:
            self.client.publish(self._topic("status"), json.dumps(state), retain=True)
        except Exception:
            self.connected = False

    def poll(self):
        """Call frequently from the main loop. Non-blocking message check + reconnect logic."""
        if not self.connected:
            now = time.ticks_ms()
            if time.ticks_diff(now, self._last_attempt) > 10_000:
                self._last_attempt = now
                self.connect()
            return
        try:
            self.client.check_msg()
        except Exception:
            self.connected = False
