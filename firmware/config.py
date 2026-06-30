"""
config.py - central pin map and settings. Edit WIFI/MQTT here or via the web UI
(web UI writes to settings.json which overrides these defaults at boot).
"""

# ---- SPI chains for matrices ----
SPI0_ID = 0
SPI0_SCK = 18
SPI0_MOSI = 19
SPI0_CS = 17
ROW1_MODULES = 4  # top row

SPI1_ID = 1
SPI1_SCK = 10
SPI1_MOSI = 11
SPI1_CS = 13
ROW2_MODULES = 4  # bottom row

DEFAULT_BRIGHTNESS = 3  # 0-15, ~30% per project notes (≈3-4/15)

# ---- OLED (I2C) ----
OLED_SDA = 0
OLED_SCL = 1
OLED_I2C_ID = 0
OLED_WIDTH = 128
OLED_HEIGHT = 64
OLED_ADDR = 0x3C

# ---- Encoder ----
ENC_A = 2
ENC_B = 3
ENC_SW = 4

# ---- Buttons ----
BTN_A = 5  # Start/Pause
BTN_B = 6  # Back/Reset

# ---- Buzzer ----
BUZZER_PIN = 7

# ---- Wifi / MQTT defaults (overridden by settings.json if present) ----
WIFI_SSID = ""
WIFI_PASS = ""
AP_SSID = "MeetingMonitor-Setup"
AP_PASS = "configure123"

MQTT_BROKER = ""
MQTT_PORT = 1883
MQTT_USER = ""
MQTT_PASS = ""
MQTT_CLIENT_ID = "meeting-monitor"
MQTT_TOPIC_PREFIX = "meetingmonitor"
# Subscribes:  meetingmonitor/cmd          (JSON commands)
# Publishes:   meetingmonitor/status       (JSON state, retained)
