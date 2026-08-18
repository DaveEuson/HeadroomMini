"""Unit tests for the companion's pure logic.

Deliberately limited to functions with no network, no filesystem and no Claude
login: window parsing/labelling and the pairing HMAC. Those are the parts that
can break silently — a mislabelled window looks plausible on the board, and a
pairing MAC that drifts from the firmware's framing fails only on real
hardware, which CI can't exercise.

Run: python -m unittest discover -s companion
"""

import hashlib
import hmac
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import companion  # noqa: E402


class WindowLabelTests(unittest.TestCase):
    def test_known_windows_use_their_explicit_names(self):
        self.assertEqual(companion._window_label("five_hour"), "Session (5 hour)")
        self.assertEqual(companion._window_label("seven_day"), "Weekly (all models)")
        self.assertEqual(companion._window_label("seven_day_opus"), "Weekly (Opus)")
        self.assertEqual(companion._window_label("seven_day_fable"), "Weekly (Fable)")

    def test_unknown_model_window_is_named_after_the_model(self):
        # A model Anthropic ships later must not read as "Seven Day Haiku".
        self.assertEqual(companion._window_label("seven_day_haiku"), "Weekly (Haiku)")
        self.assertEqual(companion._window_label("seven_day_new_model"),
                         "Weekly (New Model)")

    def test_unrelated_key_falls_back_to_title_case(self):
        self.assertEqual(companion._window_label("extra_usage"), "Extra usage")
        self.assertEqual(companion._window_label("some_future_thing"),
                         "Some Future Thing")


class WindowsFromUsageTests(unittest.TestCase):
    def test_orders_known_windows_and_appends_unknown_ones(self):
        raw = {
            "seven_day_opus": {"utilization": 10},
            "five_hour": {"utilization": 20},
            "zzz_unknown": {"utilization": 30},
            "seven_day": {"utilization": 40},
        }
        keys = [w["key"] for w in companion.windows_from_usage(raw)]
        self.assertEqual(keys[:3], ["five_hour", "seven_day", "seven_day_opus"])
        self.assertEqual(keys[-1], "zzz_unknown")   # unknown sorts last, not dropped

    def test_utilization_is_clamped_and_rounded(self):
        raw = {
            "five_hour": {"utilization": 150},     # over 100
            "seven_day": {"utilization": -5},      # under 0
            "seven_day_opus": {"utilization": 33.333},
        }
        got = {w["key"]: w["utilization"] for w in companion.windows_from_usage(raw)}
        self.assertEqual(got["five_hour"], 100.0)
        self.assertEqual(got["seven_day"], 0.0)
        self.assertEqual(got["seven_day_opus"], 33.3)

    def test_skips_entries_that_are_not_usable(self):
        raw = {
            "five_hour": {"utilization": 5},
            "no_util": {"resets_at": "2026-01-01T00:00:00Z"},  # missing utilization
            "not_a_dict": 7,
            "bad_util": {"utilization": "banana"},
        }
        keys = [w["key"] for w in companion.windows_from_usage(raw)]
        self.assertEqual(keys, ["five_hour"])

    def test_accepts_either_resets_at_spelling(self):
        raw = {
            "five_hour": {"utilization": 1, "resets_at": "A"},
            "seven_day": {"utilization": 1, "resetsAt": "B"},
        }
        got = {w["key"]: w["resets_at"] for w in companion.windows_from_usage(raw)}
        self.assertEqual(got["five_hour"], "A")
        self.assertEqual(got["seven_day"], "B")

    def test_empty_or_none_input_is_not_an_error(self):
        self.assertEqual(companion.windows_from_usage(None), [])
        self.assertEqual(companion.windows_from_usage({}), [])


class PairHmacTests(unittest.TestCase):
    """The board computes HMAC-SHA256(code, message) with mbedtls and compares
    hex strings. If either side's framing drifts, pairing fails only on real
    hardware — so pin the exact bytes here."""

    def test_matches_an_independently_computed_digest(self):
        code, nonce = "SUE9HE", b"0123456789abcdef"
        expected = hmac.new(code.encode(), nonce, hashlib.sha256).hexdigest()
        self.assertEqual(companion._pair_hmac(code, nonce), expected)

    def test_is_lowercase_hex_of_the_right_length(self):
        mac = companion._pair_hmac("ABC123", b"x")
        self.assertEqual(len(mac), 64)              # sha256 -> 32 bytes -> 64 hex
        self.assertEqual(mac, mac.lower())
        int(mac, 16)                                # must parse as hex

    def test_token_mac_covers_nonce_concatenated_with_body(self):
        # Firmware: hmacSha256Hex(pairCode, nonce + body). Concatenation order
        # matters and is not otherwise exercised until a real pairing.
        code, nonce, body = "CODE12", b"NONCE", b'{"a":1}'
        self.assertEqual(companion._pair_hmac(code, nonce + body),
                         hmac.new(code.encode(), nonce + body,
                                  hashlib.sha256).hexdigest())

    def test_a_different_code_produces_a_different_mac(self):
        msg = b"same-message"
        self.assertNotEqual(companion._pair_hmac("AAAAAA", msg),
                            companion._pair_hmac("BBBBBB", msg))


class ActionKeyTests(unittest.TestCase):
    """Key combos are turned into OS calls. Getting a combo wrong types the
    wrong thing into whatever the user has focused, so parsing is pinned here
    and unknown combos must be rejected rather than half-sent."""

    def setUp(self):
        self.calls = []
        self._real_run = companion.subprocess.run
        companion.subprocess.run = lambda *a, **k: (
            self.calls.append(a[0]) or _FakeProc())

    def tearDown(self):
        companion.subprocess.run = self._real_run

    def test_macos_named_keys_and_modifiers(self):
        self.assertTrue(companion._send_keys_macos("shift+tab"))
        self.assertIn("key code 48 using {shift down}", self.calls[-1][-1])

    def test_macos_plain_character_uses_keystroke(self):
        self.assertTrue(companion._send_keys_macos("ctrl+c"))
        self.assertIn('keystroke "c" using {control down}', self.calls[-1][-1])

    def test_linux_builds_xdotool_combo(self):
        self.assertTrue(companion._send_keys_linux("shift+tab"))
        self.assertEqual(self.calls[-1], ["xdotool", "key", "shift+Tab"])

    def test_unknown_combos_are_rejected_not_partially_sent(self):
        for combo in ("bogus", "shift", "ctrl+nonsense"):
            self.calls.clear()
            self.assertFalse(companion._send_keys_macos(combo), combo)
            self.assertFalse(companion._send_keys_linux(combo), combo)
            self.assertEqual(self.calls, [], f"{combo!r} sent something")

    def test_default_actions_match_what_the_firmware_offers(self):
        # The board queues these ids; an unmapped one would silently do nothing.
        self.assertEqual(set(companion.DEFAULT_ACTION_KEYS),
                         {"voice", "mode", "cancel"})


class ProjectNameTests(unittest.TestCase):
    """Naming the project a token belongs to.

    The folder under ~/.claude/projects is path-mangled and genuinely
    ambiguous: 'H--Projects-Kiosk-Grand' could be 'Kiosk-Grand' or
    'Kiosk Grand' (it is the latter), and no amount of splitting on '-'
    recovers that. These pin the rule that `cwd` wins, because getting it
    wrong produces a plausible-looking board screen with the wrong labels.
    """

    ROOT = os.path.join("home", ".claude", "projects")

    def _name(self, entry, slug):
        key = companion._project_key(
            entry, os.path.join(self.ROOT, slug, "s.jsonl"), self.ROOT)
        return companion._project_name(key)

    def test_cwd_wins_over_the_mangled_slug(self):
        self.assertEqual(
            self._name({"cwd": r"H:\Projects\Kiosk Grand"},
                       "H--Projects-Kiosk-Grand"),
            "Kiosk Grand")

    def test_names_containing_separators_survive(self):
        for cwd, want in ((r"H:\Projects\RigMatch.AI-main", "RigMatch.AI-main"),
                          ("/home/dave/my-app", "my-app"),
                          ("/srv/Website 2", "Website 2")):
            self.assertEqual(self._name({"cwd": cwd}, "ignored"), want, cwd)

    def test_trailing_separators_dont_yield_an_empty_name(self):
        for cwd, want in ((r"H:\Projects\Thing" + "\\", "Thing"),
                          ("/home/dave/thing/", "thing")):
            self.assertEqual(self._name({"cwd": cwd}, "x--y-thing"), want, cwd)

    def test_falls_back_to_the_slug_when_cwd_is_missing_or_junk(self):
        for entry in ({}, {"cwd": ""}, {"cwd": "   "}, {"cwd": None}):
            self.assertEqual(self._name(entry, "H--Projects-Sparko"), "Sparko")


class ProjectRollupTests(unittest.TestCase):
    """Folding nested cwds into the project a person would name.

    Claude Code keys a project off the cwd, so one repo opened at three depths
    is three rows, each understating the work.
    """

    def test_nested_paths_fold_into_a_tracked_ancestor(self):
        got = companion._roll_up_nested({
            "H:/Projects/Rig": 10,
            "H:/Projects/Rig/Rig": 70,
            "H:/Projects/Rig/Rig/chat/src-tauri": 5,
        })
        self.assertEqual(got, {"H:/Projects/Rig": 85})

    def test_an_untracked_ancestor_is_not_invented(self):
        # No H:/Projects/Qibb project exists, so its children stay separate
        # rather than being grouped under a directory nobody worked in.
        totals = {"H:/Projects/Qibb/Audio to Video": 20,
                  "H:/Projects/Qibb/Video to Audio": 5}
        self.assertEqual(companion._roll_up_nested(totals), totals)

    def test_matching_is_case_insensitive(self):
        got = companion._roll_up_nested({
            "H:/Projects/sparko": 30,
            "h:/projects/SPARKO/sub": 1,
        })
        self.assertEqual(got, {"H:/Projects/sparko": 31})

    def test_tokens_are_never_lost_or_duplicated(self):
        totals = {"/a": 3, "/a/b": 5, "/a/b/c": 7, "/d": 11, "/e/f": 13}
        got = companion._roll_up_nested(totals)
        self.assertEqual(sum(got.values()), sum(totals.values()))
        self.assertEqual(got["/a"], 15)

    def test_siblings_are_left_alone(self):
        totals = {"/w/api": 1, "/w/web": 2}
        self.assertEqual(companion._roll_up_nested(totals), totals)


class ProjectLabelTests(unittest.TestCase):
    """Turning project paths into board rows.

    Two different projects must never render as the same row — a merged or
    duplicated label is a wrong number presented confidently, which is the one
    failure mode a usage display can't afford.
    """

    def test_same_basename_is_qualified_by_its_parent(self):
        got = companion._label_projects(
            ["/home/d/work/client-a/web", "/home/d/work/client-b/web"])
        self.assertEqual(set(got.values()), {"client-a/web", "client-b/web"})

    def test_unique_basenames_are_left_alone(self):
        got = companion._label_projects(["/a/sparko", "/b/ClaudeTrackerPi"])
        self.assertEqual(set(got.values()), {"sparko", "ClaudeTrackerPi"})

    def test_labels_fit_the_board_and_stay_distinct(self):
        keys = ["/x/" + "averylongprojectname%d" % i for i in range(3)]
        got = companion._label_projects(keys, width=21)
        self.assertEqual(len(set(got.values())), 3, got)
        for label in got.values():
            self.assertLessEqual(len(label), 21, label)

    def test_long_qualified_labels_keep_the_part_that_distinguishes(self):
        # Real case from a bench run: a project nested inside a directory of
        # the same name. Trimming to the last N chars kept the shared basename
        # and destroyed the parent, yielding 'main/RigMatch.AI-main' and
        # 'ects/RigMatch.AI-main' — distinct only by a mangled prefix.
        got = companion._label_projects(
            ["H:/Projects/RigMatch.AI-main/RigMatch.AI-main",
             "H:/Projects/RigMatch.AI-main"], width=21)
        labels = list(got.values())
        self.assertEqual(len(set(labels)), 2, labels)
        for label in labels:
            self.assertLessEqual(len(label), 21, label)
            head = label.split("/")[0]
            self.assertFalse(head.startswith("ects"), label)
            self.assertTrue(
                "RigMatch.AI-main".startswith(head) or "Projects".startswith(head),
                f"{head!r} is a fragment, not a prefix of a real directory")

    def test_every_key_gets_exactly_one_label(self):
        keys = ["/a/web", "/b/web", "/c/api"]
        got = companion._label_projects(keys)
        self.assertEqual(sorted(got), sorted(keys))
        self.assertEqual(len(set(got.values())), 3)


class _FakeProc:
    returncode = 0


if __name__ == "__main__":
    unittest.main()


class StaleAutostartSweepTests(unittest.TestCase):
    """The sweep runs unprompted against somebody else's Startup folder, so the
    thing worth testing is what it refuses to delete."""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)
        self._nt = os.name
        # The sweep is a no-op off Windows; pretend so the logic is reachable.
        os.name = "nt"
        self.addCleanup(lambda: setattr(os, "name", self._nt))

    def _write(self, name, body):
        p = os.path.join(self.dir, name)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(body)
        return p

    BAT = ('@echo off\nstart "" "C:\python\pythonw.exe" '
           '"H:\Projects\ClaudeTrackerPi\companion\companion.py"\n')

    def test_removes_every_older_name(self):
        stale = [self._write(n, self.BAT)
                 for n in companion._WIN_AUTOSTART_NAMES[1:]]
        removed = companion.sweep_stale_autostart(self.dir)
        self.assertCountEqual(removed, stale)
        for p in stale:
            self.assertFalse(os.path.exists(p))

    def test_keeps_the_current_name(self):
        # The live entry is what makes the companion start at all; sweeping it
        # would silently disable auto-start every single run.
        current = self._write(companion._WIN_AUTOSTART_NAMES[0], self.BAT)
        self.assertEqual(companion.sweep_stale_autostart(self.dir), [])
        self.assertTrue(os.path.exists(current))

    def test_leaves_a_same_named_file_that_is_not_ours(self):
        # Deleting an unrelated file out of Startup because it shares a name
        # would be far worse than the bug this fixes.
        other = self._write(companion._WIN_AUTOSTART_NAMES[1],
                            '@echo off\nstart "" "C:\Games\launcher.exe"\n')
        self.assertEqual(companion.sweep_stale_autostart(self.dir), [])
        self.assertTrue(os.path.exists(other))

    def test_no_op_when_nothing_is_there(self):
        self.assertEqual(companion.sweep_stale_autostart(self.dir), [])
