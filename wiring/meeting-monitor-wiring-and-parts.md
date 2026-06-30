# Meeting Monitor — Parts List & Wiring Plan

## Parts List

| Component | Qty | Notes |
|---|---|---|
| Raspberry Pi Pico W | 1 | MicroPython firmware |
| MAX7219 FC-16 8x8 LED matrix module | 8 | 2 chains of 4, daisy-chained |
| 0.96" I2C OLED (SSD1306) | 1 | 128x64 |
| EC11 rotary encoder w/ push switch | 1 | Nav + select |
| Tactile push button | 2 | Start/Pause, Back/Reset |
| Passive piezo buzzer | 1 | PWM-driven |
| TP4056 USB-C LiPo charger board | 1 | On hand |
| LiPo battery, 2000mAh+ (1S, 3.7V) | 1 | JST connector |
| Boost converter module (5V, 1.5A+ output, e.g. MT3608) | 1 | LiPo (3.7-4.2V) → stable 5V for Pico VSYS + matrices |
| Slide switch (power on/off) | 1 | Between battery/charger and boost converter |
| Jumper wire / ribbon cable | — | For SPI chains |
| Perfboard or custom PCB | 1 | Optional, for clean wiring |
| 10kΩ resistors | 2 | Pull-ups for buttons if not using internal pull-ups (optional) |
| 100kΩ resistors | 2 | Battery voltage-sense divider (see below) |

**Note:** I added a boost converter to the list. The TP4056 outputs raw LiPo voltage (3.0–4.2V), which is NOT enough to reliably run 8 MAX7219 modules (they want 5V) or power Pico's VSYS pin cleanly. The boost converter sits between the battery/TP4056 and everything else.

---

## Power Architecture

```
[LiPo Battery] ──┬── [TP4056 charge IN/OUT] ── (charges battery via USB-C)
                  │
                  └── [Slide Switch] ── [Boost Converter 5V] ──┬── Pico W (VSYS, pin 39)
                                                                ├── MAX7219 chain 1 (VCC)
                                                                ├── MAX7219 chain 2 (VCC)
                                                                ├── OLED (VCC, via Pico 3V3 actually — see below)
                                                                └── Buzzer (via GPIO, not direct power)
```

- OLED runs on 3.3V — power it from the **Pico's 3V3 OUT pin**, not the 5V rail.
- Buzzer and encoder/buttons are logic-level — powered/driven via GPIO, not the 5V rail.
- Common ground across battery, boost converter, Pico, and all matrices — this is critical, don't skip it.

---

## SPI Chains (2x4 matrices each)

Pico W has two hardware SPI peripherals (SPI0, SPI1) — perfect for 2 independent chains.

| Chain | SPI Bus | Pico Pins (SCK / MOSI / CS) | Matrices |
|---|---|---|---|
| Row 1 (top) | SPI0 | GP18 (SCK) / GP19 (MOSI) / GP17 (CS) | 4x FC-16 daisy-chained |
| Row 2 (bottom) | SPI1 | GP10 (SCK) / GP11 (MOSI) / GP13 (CS) | 4x FC-16 daisy-chained |

Within each chain: module 1's "OUT" header connects to module 2's "IN" header, etc. Only the first module in each chain connects to the Pico's SCK/MOSI/CS; power (5V/GND) should be injected at both ends of each chain of 4 if possible to avoid voltage droop across the row.

---

## OLED (I2C)

| Pico Pin | OLED Pin |
|---|---|
| GP0 | SDA |
| GP1 | SCL |
| 3V3 OUT | VCC |
| GND | GND |

---

## Encoder (EC11)

| Pico Pin | Encoder Pin |
|---|---|
| GP2 | A |
| GP3 | B |
| GP4 | Push switch |
| GND | GND/COM |

Use internal pull-ups in software (`Pin.PULL_UP`) — no external resistors needed.

---

## Buttons

| Pico Pin | Button |
|---|---|
| GP5 | Button A (Start/Pause) |
| GP6 | Button B (Back/Reset) |

Both wired to GND with internal pull-ups enabled in software.

---

## Buzzer

| Pico Pin | Buzzer |
|---|---|
| GP7 | Signal (PWM) |
| GND | GND |

---

## Pin Budget Check

Used: GP0,1 (OLED), GP2,3,4 (encoder), GP5,6 (buttons), GP7 (buzzer), GP10,11,13 (SPI1), GP17,18,19 (SPI0) = 14 GPIO pins used. Pico W has 26 usable GPIO — plenty of headroom left for future additions (e.g. a light sensor, second buzzer, status LED).

---

## Battery Voltage Sense (for OLED % display)

Tap raw LiPo+ (before the boost converter, directly off the battery/TP4056 B+ terminal) with a 100k/100k divider into GP26 (ADC0):

```
LiPo+ ──[100kΩ]──┬──[100kΩ]── GND
                  │
                 GP26 (ADC0)
```

This halves the battery voltage (4.2V → 2.1V) so it stays safely under the Pico's 3.3V ADC max. Keep this tap separate from the 5V boost rail — it must read the raw cell voltage, not the regulated output.

---

## Open Items / Decisions Needed (resolved)

1. **Matrix brightness** — defaults to ~30% software brightness (level 3/15), adjustable via webUI/MQTT/encoder.
2. **Enclosure** — built as two printed parts: a single fused front housing (side walls + front face with all 8 module windows/standoffs printed as one continuous shell, no seam) and a removable back panel (OLED, encoder, buttons, buzzer, USB-C, power switch). See `../case/` for STLs and source.

All open items resolved — see `../case/` and `../firmware/` for the finished design.

