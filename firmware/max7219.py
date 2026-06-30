"""
max7219.py - Driver for daisy-chained MAX7219 8x8 LED matrix modules (FC-16 style)
Each chain is exposed as a framebuf.FrameBuffer of width (8*num_modules) x 8.
"""
from machine import Pin, SPI
import framebuf
import time

# MAX7219 registers
REG_NOOP = 0x00
REG_DIGIT0 = 0x01  # digits 0-7 follow (rows 0-7)
REG_DECODEMODE = 0x09
REG_INTENSITY = 0x0A
REG_SCANLIMIT = 0x0B
REG_SHUTDOWN = 0x0C
REG_DISPLAYTEST = 0x0F


class Max7219Chain:
    def __init__(self, spi: SPI, cs: Pin, num_modules: int):
        self.spi = spi
        self.cs = cs
        self.cs.init(Pin.OUT, value=1)
        self.num = num_modules
        self.width = 8 * num_modules
        self.height = 8
        self.buf = bytearray(self.width * self.height // 8)
        # vertical-byte framebuf doesn't map directly to MAX7219 row layout,
        # so we keep our own pixel buffer (1 byte per row per module) and
        # convert when flushing instead of using framebuf's native format.
        self._rows = [bytearray(num_modules) for _ in range(8)]
        self.fb = _ChainFrameBuffer(self)
        self._init_chips()

    def _write_all(self, reg, value):
        # Same register/value sent to every chained chip in one transaction
        self.cs.value(0)
        for _ in range(self.num):
            self.spi.write(bytearray([reg, value]))
        self.cs.value(1)

    def _init_chips(self):
        self._write_all(REG_SCANLIMIT, 7)
        self._write_all(REG_DECODEMODE, 0)
        self._write_all(REG_DISPLAYTEST, 0)
        self.brightness(3)
        self._write_all(REG_SHUTDOWN, 1)  # wake up
        self.clear()
        self.show()

    def brightness(self, level):
        # level 0-15
        level = max(0, min(15, level))
        self._write_all(REG_INTENSITY, level)

    def clear(self):
        for r in self._rows:
            for i in range(len(r)):
                r[i] = 0

    def show(self):
        # For each of the 8 rows, send that row's byte to each chip.
        # Chip closest to Pico gets clocked in last, so we send from the
        # far end of the chain first.
        for row in range(8):
            self.cs.value(0)
            for module in range(self.num - 1, -1, -1):
                self.spi.write(bytearray([REG_DIGIT0 + row, self._rows[row][module]]))
            self.cs.value(1)

    def pixel(self, x, y, value):
        if not (0 <= x < self.width and 0 <= y < self.height):
            return
        module = x // 8
        bit = 7 - (x % 8)
        if value:
            self._rows[y][module] |= (1 << bit)
        else:
            self._rows[y][module] &= ~(1 << bit)


class _ChainFrameBuffer:
    """Thin adapter exposing framebuf-like text drawing using Max7219Chain.pixel"""
    def __init__(self, chain: Max7219Chain):
        self.chain = chain
        self.width = chain.width
        self.height = chain.height
        # use a real framebuf for font rendering (MONO_HLSB 1bpp), then copy
        self._raw = bytearray(self.width * self.height // 8 + self.height)
        self._fb = framebuf.FrameBuffer(self._raw, self.width, self.height, framebuf.MONO_HLSB)

    def fill(self, c):
        self._fb.fill(c)

    def text(self, s, x, y, c=1):
        self._fb.text(s, x, y, c)

    def pixel(self, x, y, c):
        self._fb.pixel(x, y, c)

    def hline(self, x, y, w, c):
        self._fb.hline(x, y, w, c)

    def flush(self):
        for y in range(self.height):
            for x in range(self.width):
                self.chain.pixel(x, y, self._fb.pixel(x, y))
        self.chain.show()
