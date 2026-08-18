#!/usr/bin/env python3
"""Yoyu tray — the companion as a menubar / system-tray app.

Sits quietly in your menubar (macOS) or system tray (Windows/Linux): it finds
your Yoyu board, feeds it your Claude usage, and gives you one-click
**Pair** (make the board self-contained) and **Open board page**. The icon's
colour tells you at a glance whether it's feeding (green), searching (amber), or
stuck (red).

All the Claude-usage logic is reused from companion.py — this file is just the
tray shell.

Run from source:
    pip install pystray pillow certifi        # + pyobjc-framework-Cocoa on macOS
    python tray.py
"""

import os
import sys
import threading
import time
import webbrowser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import companion  # noqa: E402  (reuse discover/pair/feed logic)

try:
    import pystray
    from PIL import Image, ImageDraw
except ImportError:
    sys.stderr.write(
        "The tray app needs two small libraries. Install them and re-run:\n"
        "  pip install pystray pillow certifi"
        + ("  pyobjc-framework-Cocoa\n" if sys.platform == "darwin" else "\n"))
    sys.exit(1)

INTERVAL = 120  # seconds between feeds

# Shared state. Python's GIL makes these simple dict updates safe enough here.
# url may be pinned up front via the HEADROOM_PI env var or a saved config, so
# a fussy network (VPNs, work laptops) doesn't have to be auto-discovered.
state = {"color": "amber", "status": "Starting…", "url": None, "swept": None,
         "feeding": True, "fixed": False}


def initial_url():
    u = os.environ.get("HEADROOM_PI", "").strip()
    if not u:
        try:
            u = (companion.load_config().get("pi") or "").split(",")[0].strip()
        except Exception:  # noqa: BLE001
            u = ""
    return u.rstrip("/") or None

COLORS = {"green": (94, 170, 100), "amber": (230, 164, 23),
          "red": (221, 77, 77), "grey": (140, 140, 140)}


# The kitsune's head — the same cells the board draws, cropped to the head and
# ruff. The full sprite carries a fan of tails that says how much headroom is
# left, which is the board's job; a 64px tray icon has room for the animal or
# the gauge, not both. The ear interiors are tinted by feed state (green
# feeding / amber busy / red stuck) so the icon still reports status at a glance.
KITSUNE_HEAD = [".K.......K.", ".KSK...KSK.", "KBSSK.KSSBK", "KBBBKKKBBBK",
                "KBBBBBBBBBK", "KBBBBBBBBBK", ".KBBBBBBBK.", "..KBWWWBK..",
                "...KWWWK...", ".KBBBBBBBK.", ".KBBWWWBBK.", ".KBBWWWBBK.",
                "..KK...KK.."]
_SPRK = {"K": (26, 24, 22), "W": (250, 247, 239),
         "B": (201, 96, 63), "S": (158, 68, 41)}


def make_icon(color):
    """Draw the kitsune, its ears tinted by feed state."""
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([2, 2, 61, 61], radius=14, fill=(38, 38, 36, 255))
    status = COLORS.get(color, COLORS["grey"])
    U = 4                       # cell size; 11x13 cells centred in 64
    padx, pady = (64 - 11 * U) // 2, (64 - 13 * U) // 2

    def cell(cx, cy, rgb):
        x0, y0 = padx + cx * U, pady + cy * U
        d.rectangle([x0, y0, x0 + U - 1, y0 + U - 1], fill=rgb)

    for y, row in enumerate(KITSUNE_HEAD):
        for x, ch in enumerate(row):
            if ch in _SPRK:
                cell(x, y, _SPRK[ch])
    for x in (2, 8):                                          # ears, in status
        cell(x, 1, status)
    for x in (2, 7):                                          # slanted eyes
        cell(x, 4, _SPRK["K"])
    cell(5, 7, _SPRK["K"])                                    # nose
    cell(4, 8, _SPRK["K"]); cell(6, 8, _SPRK["K"])            # mouth
    return img


def feed_once(url):
    """One poll+push. Returns (color, status text, rate_limited)."""
    try:
        live = companion.get_live_windows()
    except companion.LiveUnavailable as exc:
        if getattr(exc, "rate_limited", False):
            return "amber", "Rate limited by Anthropic — backing off", True
        return "amber", "Usage temporarily unreadable", False
    if not live:
        return "red", "No Claude login on this computer", False
    windows, plan = live
    payload = {"windows": windows, "plan": plan, "source": "live"}
    try:
        res = companion.push(url, "", payload)
    except Exception:  # noqa: BLE001 - any network error means "board unreachable"
        return "red", "Can't reach the board", False
    if res.get("ok"):
        summary = ", ".join(f"{w['label'].split(' (')[0]} {w['utilization']:.0f}%"
                            for w in windows[:3])
        return "green", "Feeding · " + summary, False
    return "amber", "Board rejected: " + str(res.get("error")), False


def refresh(icon):
    icon.icon = make_icon(state["color"])
    icon.update_menu()


def worker(icon):
    rl_backoff = 0   # extra seconds added while Anthropic is rate-limiting us
    while True:
        if not state["feeding"]:
            state.update(color="grey", status="Paused")
            refresh(icon)
            time.sleep(2)
            continue
        if not state["url"]:
            state.update(color="amber", status="Looking for your board…")
            refresh(icon)
            state["url"] = companion.discover_pi()
            if not state["url"]:
                state.update(color="red", status="No board found on this network")
                refresh(icon)
                time.sleep(15)
                continue
        color, status, rate_limited = feed_once(state["url"])
        if color == "green":
            companion.save_pi(state["url"])            # remember it for next time
            ensure_autostart()                         # persist a working setup
        elif color == "red" and "reach" in status and not state["fixed"]:
            state["url"] = None                        # lost it -> rediscover
        # Rate-limited: back off exponentially (cap 30 min) so we stop pounding
        # the usage endpoint. A good read snaps us back to the normal cadence.
        if rate_limited:
            rl_backoff = min(1800, rl_backoff * 2 or INTERVAL)
            status = f"{status} (next try ~{(INTERVAL + rl_backoff) // 60}m)"
        else:
            rl_backoff = 0
        state.update(color=color, status=status)
        refresh(icon)
        time.sleep(INTERVAL + rl_backoff)


# ---------------------------------------------------------------- menu actions

def _ask_pair_code():
    """Pop a small dialog for the code the board shows during pairing. The tray
    has no console, so companion.pair_device() can't fall back to input()."""
    try:
        import tkinter as tk
        from tkinter import simpledialog
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        code = simpledialog.askstring(
            "Pair board",
            "Look at your Yoyu board — it's showing a 6-character code.\n"
            "Enter it here to finish pairing:")
        root.destroy()
        return code or ""
    except Exception:
        return ""


def do_pair(icon, item):
    def run():
        url = state["url"] or companion.discover_pi()
        if not url:
            state["status"] = "Pair failed: board not found"
        else:
            ok = companion.pair_device(url, ask_code=_ask_pair_code)
            state["status"] = ("Paired — the board runs on its own now"
                               if ok else "Pair failed (wrong code, or no Claude "
                               "login here?)")
        icon.update_menu()
    threading.Thread(target=run, daemon=True).start()


def do_open(icon, item):
    if state["url"]:
        webbrowser.open(state["url"])


def open_path(path):
    """A menu callback that opens one of the board's config pages in a browser.
    Rich forms (screen toggles, timezone, alert thresholds) live on the board so
    they work even when this computer is off — the tray just deep-links to them."""
    def _cb(icon, item):
        if state["url"]:
            webbrowser.open(state["url"].rstrip("/") + path)
    return _cb


def toggle_feeding(icon, item):
    state["feeding"] = not state["feeding"]


def is_autostarted():
    return os.path.isfile(companion.INSTALLED_MARKER)


def ensure_autostart():
    """Install the login item once, quietly. Called after the first good feed
    so we only persist a setup that actually works."""
    if is_autostarted():
        return
    try:
        companion.install_autostart()
        with open(companion.INSTALLED_MARKER, "w", encoding="utf-8") as fh:
            fh.write(state.get("url") or "")
    except Exception:  # noqa: BLE001 - autostart is a nicety, never fatal
        pass


def toggle_autostart(icon, item):
    try:
        if is_autostarted():
            companion.uninstall_autostart()
        else:
            companion.install_autostart()
            with open(companion.INSTALLED_MARKER, "w", encoding="utf-8") as fh:
                fh.write(state.get("url") or "")
    except Exception:  # noqa: BLE001
        pass


def build_menu():
    return pystray.Menu(
        pystray.MenuItem(lambda *a: state["status"], None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Feeding", toggle_feeding,
                         checked=lambda item: state["feeding"]),
        pystray.MenuItem("Start at login", toggle_autostart,
                         checked=lambda item: is_autostarted()),
        pystray.MenuItem("Pair board (run without this computer)", do_pair),
        pystray.MenuItem("Open board page", do_open,
                         enabled=lambda item: bool(state["url"])),
        pystray.MenuItem("Settings", pystray.Menu(
            pystray.MenuItem("Screens, clock & auto-rotate…", open_path("/settings")),
            pystray.MenuItem("Phone alerts…", open_path("/alerts")),
            pystray.MenuItem("Update firmware…", open_path("/update")),
        ), enabled=lambda item: bool(state["url"])),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit", lambda icon, item: icon.stop()),
    )


def main():
    # The tray app has its own entry point and never runs companion.main(), so
    # the stale-auto-start sweep that lives there was never reaching the build
    # that most people actually download. Caught by running the packaged binary
    # rather than the source: the CLI swept, the tray did not.
    #
    # There is no console here to print to, so anything removed has to be said
    # in the UI. It goes in the menu's status line, and is offered as a desktop
    # notification too where the backend supports one.
    swept = companion.sweep_stale_autostart()
    if swept:
        state["status"] = ("Removed %d leftover auto-start %s from an older "
                           "version" % (len(swept),
                                        "entry" if len(swept) == 1 else "entries"))
        state["swept"] = swept

    pinned = initial_url()
    if pinned:
        state["url"] = pinned
        state["fixed"] = True
    icon = pystray.Icon("Yoyu", make_icon("amber"), "Yoyu", build_menu())
    threading.Thread(target=worker, args=(icon,), daemon=True).start()
    if state.get("swept"):
        try:
            icon.notify("An older version was still starting a second copy at "
                        "login. Removed it — two of them fight over your Claude "
                        "account and the board stops showing numbers.",
                        "Yoyu")
        except Exception:      # noqa: BLE001 — not every backend has notify()
            pass
    icon.run()   # blocks on the main thread (required on macOS)


if __name__ == "__main__":
    main()
