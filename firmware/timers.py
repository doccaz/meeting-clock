"""
timers.py - Countdown and count-up (stopwatch) timers, independent of display.
"""
import time


class Timer:
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    DONE = "done"

    def __init__(self, mode="countdown"):
        self.mode = mode  # "countdown" or "stopwatch"
        self.state = self.IDLE
        self.duration_s = 0       # set for countdown
        self._elapsed_at_pause = 0
        self._start_ms = 0
        self.on_done = None       # callback, set externally

    def set_duration(self, seconds):
        self.duration_s = seconds
        self._elapsed_at_pause = 0
        self.state = self.IDLE

    def start(self):
        if self.state in (self.IDLE, self.PAUSED):
            self._start_ms = time.ticks_ms()
            self.state = self.RUNNING

    def pause(self):
        if self.state == self.RUNNING:
            self._elapsed_at_pause = self._elapsed_ms()
            self.state = self.PAUSED

    def toggle(self):
        if self.state == self.RUNNING:
            self.pause()
        else:
            self.start()

    def reset(self):
        self._elapsed_at_pause = 0
        self.state = self.IDLE

    def _elapsed_ms(self):
        if self.state == self.RUNNING:
            return self._elapsed_at_pause + time.ticks_diff(time.ticks_ms(), self._start_ms)
        return self._elapsed_at_pause

    def remaining_s(self):
        """For countdown mode."""
        elapsed = self._elapsed_ms() // 1000
        rem = max(0, self.duration_s - elapsed)
        return rem

    def elapsed_s(self):
        """For stopwatch mode."""
        return self._elapsed_ms() // 1000

    def tick(self):
        """Call regularly; flips state to DONE for countdown reaching zero."""
        if self.mode == "countdown" and self.state == self.RUNNING:
            if self.remaining_s() <= 0:
                self.state = self.DONE
                if self.on_done:
                    self.on_done()

    def display_string(self):
        secs = self.remaining_s() if self.mode == "countdown" else self.elapsed_s()
        m, s = divmod(secs, 60)
        if m >= 100:
            h, m = divmod(m, 60)
            return "{:02d}:{:02d}:{:02d}".format(h, m, s)
        return "{:02d}:{:02d}".format(m, s)
