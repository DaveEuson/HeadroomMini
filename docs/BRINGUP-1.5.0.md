# Bring-up checklist — v1.5.0 (Settings + Projects screens)

Everything in this release is compile-verified and unit-tested; **nothing has
been rendered on hardware.** Three review passes went at the logic and stopped
finding structural problems, which is roughly the point at which the remaining
risk stops being the kind a reviewer can see. Layout arithmetic is the main
exposure — pitch, clipping, and text that silently shrinks to fit.

Ordered so cheap layout failures surface before you spend time on behaviour.

## 0. Flash over USB, not OTA

`v1.5.0` is not released. `/update` pulls from `releases/latest`, which is
`v1.4.0`, so OTA cannot deliver this build.

```
cd firmware && python -m platformio run -t upload
```

- [ ] Settings screen reports **v1.5.0**

If it says 1.4.0 you are looking at the old firmware and nothing below is
meaningful.

## 1. Settings layout — most likely to be wrong

- [ ] **Address renders at size 2**, not silently shrunk. Drawn at y=50;
      `drawCentered` steps the font down past 236px, so a long address drops to
      size 1 and reads noticeably smaller than the title above it.
      `192.168.1.42:8080` is comfortable; `192.168.100.100:8080` is at the edge.
- [ ] **Bottom row (Settings) is not clipped.** Eight rows at 21px pitch from
      y=132; the last ends near 287 with the footer at 304.
- [ ] **Selection highlight doesn't collide with neighbours.** The highlight is
      a 20px `fillRoundRect` on a 21px pitch — 1px of breathing room, chosen
      arithmetically and never seen.
- [ ] **Footer messages fit on one line** at size 1. Swipe through all eight
      rows and watch it swap between `tap toggles - swipe L/R exits` and the
      refusal messages.

## 2. Settings behaviour

- [ ] **The address works** — type it into a browser and land on the board's
      page. This is the entire point of the screen.
- [ ] **A toggle persists.** Turn off e.g. History → confirm the rotation skips
      it → **power-cycle** → still skipped. This exercises the migration/NVS
      write that was refactored into a single transaction.
- [ ] **Refusal: this screen.** Tap the Settings row → `Settings stays on`.
- [ ] **Refusal: the default.** Tap your power-on default → `that's the default`.
- [ ] **Refusal: the floor.** Reduce to two screens, try a third →
      `keep at least two`.
- [ ] **Re-enable path** (was a confirmed bug — exercise deliberately): uncheck
      Settings in the **web form** at `/settings`, then tap to the Settings
      screen on the device and re-enable it. It must actually toggle on. Before
      the fix it refused and stayed off.
- [ ] **Web and device agree.** Change the mask on the device, reload
      `/settings`, confirm the checkboxes match.

## 3. Projects screen

Ground truth to compare against:

```
python -c "import sys; sys.path.insert(0,'companion'); import companion; print(companion.get_project_shares())"
```

- [ ] **Names, order and percentages match** the command's output.
- [ ] **Long names clear the percentage.** Names cap at 21 chars (~126px from
      x=14); the percentage is right-aligned at x=226. Should clear, but that is
      arithmetic rather than observation.
- [ ] **`+N more` appears** when more than five projects are active in the
      window.
- [ ] **Not the wrong empty state.** Hard to force a genuine 5-hour quiet
      window; the practical check is that it never says
      `needs the companion running` while the companion is demonstrably
      running. That contradiction was fixed by splitting on `projAt` — a landed
      push shows `all quiet / no activity in the last 5h` instead.

## 4. Regressions this branch could plausibly have caused

- [ ] **Timer auto-switch** still fires when a window hits 100%
      (`checkExhaustion` moved to `SCREEN_TIMER`, and the Timer tick was edited).
- [ ] **Actions still queue** with the companion on `--actions`.
- [ ] **Double-tapping Actions sends no stray keystroke.** This is why the
      double-tap shortcut was removed: touch dispatches on finger release, so
      tap 1 fired a real Space/Esc before the double-tap code arrived.
      Double-tap should now simply advance two screens.
- [ ] **Sprocket animation and History** still redraw (both adjacent to edited
      lines).
- [ ] **Long-press** still flips % left / % used.

## 5. If something is off

Row pitch and start `y` live in `drawSettings` in `firmware/src/main.cpp`;
the Projects rows are in `drawProjects` just above it. Note what it looks like
— clipped, cramped, overlapping — rather than guessing at values, and adjust
from there.
