"""
buzzer.py - passive piezo buzzer driver using PWM tones.
"""
from machine import Pin, PWM
import time


class Buzzer:
    def __init__(self, pin_num):
        self.pwm = PWM(Pin(pin_num))
        self.pwm.duty_u16(0)

    def tone(self, freq, duration_ms):
        self.pwm.freq(max(20, freq))
        self.pwm.duty_u16(32768)  # 50% duty
        time.sleep_ms(duration_ms)
        self.pwm.duty_u16(0)

    def beep(self):
        """Short UI feedback beep (button press)."""
        self.tone(2000, 40)

    def alert_done(self):
        """Countdown-complete alert pattern."""
        for f in (1500, 1900, 1500, 1900):
            self.tone(f, 120)
            time.sleep_ms(40)

    def alert_error(self):
        self.tone(300, 250)

    def silence(self):
        self.pwm.duty_u16(0)
