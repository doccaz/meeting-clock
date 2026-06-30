"""
display.py - drives the two MAX7219 chains (rows) as independent zones.
Each zone can show: static text, scrolling text (left or up), blinking text,
or a big countdown/stopwatch numeral string.
"""
from machine import Pin, SPI
import time
from max7219 import Max7219Chain
import config


class Zone:
    """One row of 4 chained 8x8 matrices (32x8 px), with simple text effects."""

    EFFECT_STATIC = "static"
    EFFECT_SCROLL_LEFT = "scroll_left"
    EFFECT_SCROLL_UP = "scroll_up"
    EFFECT_BLINK = "blink"

    def __init__(self, chain: Max7219Chain):
        self.chain = chain
        self.fb = chain.fb
        self.text = ""
        self.effect = self.EFFECT_STATIC
        self._scroll_x = self.fb.width
        self._scroll_y = 0
        self._blink_on = True
        self._last_tick = time.ticks_ms()
        self._speed_ms = 60  # ms per animation step

    def set_text(self, text, effect=EFFECT_STATIC, speed_ms=60):
        self.text = text
        self.effect = effect
        self._speed_ms = speed_ms
        self._scroll_x = self.fb.width
        self._scroll_y = self.fb.height
        self._blink_on = True
        self._render()

    def _text_px_width(self):
        return len(self.text) * 8

    def _render(self):
        self.fb.fill(0)
        if self.effect == self.EFFECT_STATIC:
            self.fb.text(self.text, 0, 0, 1)
        elif self.effect == self.EFFECT_SCROLL_LEFT:
            self.fb.text(self.text, self._scroll_x, 0, 1)
        elif self.effect == self.EFFECT_SCROLL_UP:
            self.fb.text(self.text, 0, self._scroll_y, 1)
        elif self.effect == self.EFFECT_BLINK:
            if self._blink_on:
                self.fb.text(self.text, 0, 0, 1)
        self.fb.flush()

    def tick(self):
        """Call frequently from the main loop; advances animation by elapsed time."""
        now = time.ticks_ms()
        if time.ticks_diff(now, self._last_tick) < self._speed_ms:
            return
        self._last_tick = now

        if self.effect == self.EFFECT_SCROLL_LEFT:
            self._scroll_x -= 1
            if self._scroll_x < -self._text_px_width():
                self._scroll_x = self.fb.width
            self._render()
        elif self.effect == self.EFFECT_SCROLL_UP:
            self._scroll_y -= 1
            if self._scroll_y < -8:
                self._scroll_y = self.fb.height
            self._render()
        elif self.effect == self.EFFECT_BLINK:
            self._blink_on = not self._blink_on
            self._render()
        # STATIC needs no per-tick work


class Display:
    def __init__(self):
        spi0 = SPI(config.SPI0_ID, baudrate=10_000_000, polarity=0, phase=0,
                   sck=Pin(config.SPI0_SCK), mosi=Pin(config.SPI0_MOSI))
        spi1 = SPI(config.SPI1_ID, baudrate=10_000_000, polarity=0, phase=0,
                   sck=Pin(config.SPI1_SCK), mosi=Pin(config.SPI1_MOSI))

        chain1 = Max7219Chain(spi0, Pin(config.SPI0_CS), config.ROW1_MODULES)
        chain2 = Max7219Chain(spi1, Pin(config.SPI1_CS), config.ROW2_MODULES)
        chain1.brightness(config.DEFAULT_BRIGHTNESS)
        chain2.brightness(config.DEFAULT_BRIGHTNESS)

        self.row1 = Zone(chain1)  # top row
        self.row2 = Zone(chain2)  # bottom row

    def brightness(self, level):
        self.row1.chain.brightness(level)
        self.row2.chain.brightness(level)

    def clear(self):
        self.row1.set_text("", Zone.EFFECT_STATIC)
        self.row2.set_text("", Zone.EFFECT_STATIC)

    def tick(self):
        self.row1.tick()
        self.row2.tick()
