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
import sys
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


class _FakeProc:
    returncode = 0


if __name__ == "__main__":
    unittest.main()
