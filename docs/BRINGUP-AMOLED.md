# Bring-up: ESP32-S3-Touch-AMOLED-2.16

The second supported board. Hardware expected 25–27 Aug 2026; everything in §1
is doable without it and is done, everything in §3 needs the real thing.

## Confirmed specifications

From Waveshare's product page and wiki, not from memory:

| | |
|---|---|
| Panel | 2.16" AMOLED, **480×480**, 16.7M colour |
| Display driver | **CO5300** over QSPI |
| Touch | **CST9220** (the LCD board uses CST816D — different part, different driver) |
| MCU | ESP32-S3R8, 16MB flash, 8MB PSRAM |
| Also onboard | 6-axis IMU (QMI8658), RTC, audio codec, dual mics |

Pins are recorded in [`firmware/src/boards.h`](../firmware/src/boards.h).

**Three things are still unverified** and are marked as such in `boards.h`:
the CST9220 I2C address (0x5A is the usual CST92xx address, but Waveshare does
not publish it), whether the PSRAM is octal or quad, and whether any battery
divider exists. Each fails soft — a wrong touch address reads as "no touch
chip", which this firmware already survives — so none of them will announce
themselves. Check all three against the board.

## The problem this board creates

**It is square; the design space is not.** Every screen is authored against a
fixed 240×320 reference. Mapped naively onto 480×480:

```
mapX = 480/240 = 2.00        mapY = 480/320 = 1.50
```

Everything stretches a third wider than it is tall. Meters get fat, the kitsune
gets distorted, and the bitmap font — which only steps in whole multiples —
drifts out of register with the boxes it sits in. A square panel is not a bigger
portrait panel.

The intended fix: **scale uniformly by the tighter axis and centre.** That gives
×1.50, a 360×480 live area, and 60px of unused margin down each side — 75% of
the glass. Correct proportions on three quarters of the panel beat a distorted
layout on all of it. It is also the same choice the mascot already makes when it
fits itself to the glass on both axes.

Reclaiming those margins later means designing *square variants* of each screen.
That is a design job, not a scaling constant, and it should not be attempted
before the uniform mapping is proven on hardware.

## §1 — Done, no hardware needed

- [x] Specifications and pinout confirmed from the vendor, not assumed.
- [x] `firmware/src/boards.h` — both boards' pins, panel geometry, driver
      selection, and per-board OTA asset prefix in one place.
- [x] `platformio.ini` — a shared `[env]` base plus `headroom-mini` and
      `yoyu-amoled216`. Both compile.
- [x] Confirmed the pinned Arduino_GFX 1.4.9 ships both `Arduino_ESP32QSPI` and
      `Arduino_CO5300`, and their constructor signatures match these pins. No
      library bump needed.

## §2 — Blocked on `main.cpp`

`main.cpp` was being edited by another session when §1 landed, so none of this
was started. **The `yoyu-amoled216` env currently produces LCD firmware** — it
compiles the same source with a flag nothing reads yet. Same size, functionally
identical, differing only in embedded build metadata.

That is why `release.yml` and the setup page were deliberately left alone: both
would have offered people a download that cannot drive their panel.

In order:

- [ ] `main.cpp` includes `boards.h` and deletes its hardcoded pin block
      (currently around line 67).
- [ ] Display construction branches on `PANEL_IS_QSPI`: `Arduino_ESP32QSPI(CS,
      CLK, D0, D1, D2, D3)` + `Arduino_CO5300(bus, PANEL_RST, 0, true, 480, 480)`.
- [ ] Brightness: the LCD board dims a backlight pin; this panel has none. Route
      `PANEL_HAS_BACKLIGHT == 0` to `Arduino_CO5300::setBrightness()`.
- [ ] Touch: CST9220 driver alongside CST816D, selected by board.
- [ ] Uniform-scale mapping, per the section above.
- [ ] Battery gauge compiled out where `HAS_BATTERY_ADC == 0`.
- [ ] OTA URL built from `OTA_ASSET_PREFIX` so each board fetches its own image.
      **This one is a safety issue, not a nicety:** both images are validly
      signed, so the signature check will happily accept LCD firmware onto an
      AMOLED board.

## §3 — Then, and only then, distribution

- [ ] `release.yml` builds both envs and publishes `yoyu-amoled-*` alongside the
      frozen `headroom-mini-*`. Add a guard that fails the release if the two
      app images are functionally identical — that is precisely the mistake §2
      exists to prevent, and it is invisible in a green build.
- [ ] A second `docs/firmware/manifest-*.json`.
- [ ] A board picker on the setup page, **before** the flash step, since the
      image and the panel have to match. This is the highest-risk change in the
      whole feature: setup completion is the product's outranking metric, and
      this puts a new decision in front of the one step that must not lose
      people. Wrong choice = a dead screen and no obvious way back.

## §4 — On the real board

- [ ] Panel lights up, correct orientation, no tearing.
- [ ] Confirm the three unverified values above.
- [ ] Every screen at the uniform mapping: nothing clipped, nothing overlapping,
      text still legible at arm's length.
- [ ] The kitsune, all five moods, all three tail counts.
- [ ] Touch: tap, long-press, swipe in both axes.
- [ ] Brightness range, including overnight dimming, and check for AMOLED
      burn-in risk on the static meter labels — an always-on desk display with
      fixed text is exactly the burn-in case, and the LCD board never had it.
- [ ] OTA fetches `yoyu-amoled-app.bin`, not the LCD image.
