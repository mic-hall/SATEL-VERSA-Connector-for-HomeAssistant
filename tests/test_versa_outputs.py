"""Synthetic tests of the static UI reconstruction; no physical-state claim."""

import unittest

from custom_components.satel_versa.protocol.outputs import Indicator, decode_output_indicators


class OutputIndicatorTests(unittest.TestCase):
    def body(self):
        return bytearray([9]) + bytearray(15)

    def test_each_position_and_all_flag_combinations(self):
        for number in range(1, 13):
            for flags in range(256):
                body = self.body()
                body[number + 3] = flags
                states = decode_output_indicators(0x71, body, list(range(1, 13)))
                expected = (
                    Indicator.BLINKING_GREEN_RED
                    if flags & 0x10
                    else Indicator.RED
                    if flags & 0x80
                    else Indicator.GREEN
                )
                self.assertEqual(states[number - 1].indicator, expected)
                self.assertEqual(states[number - 1].raw_flags, flags)
                for state in states:
                    if state.number != number:
                        self.assertIs(state.indicator, Indicator.GREEN)

    def test_opaque_bytes_and_caller_order(self):
        body = self.body()
        body[1:4] = bytes([255, 255, 255])
        states = decode_output_indicators(0x71, body, [12, 1, 8])
        self.assertEqual([state.number for state in states], [12, 1, 8])
        self.assertTrue(all(state.indicator is Indicator.GREEN for state in states))
        self.assertEqual(decode_output_indicators(0x71, body, []), ())

    def test_reject_unknown_or_incomplete_profiles(self):
        valid = bytes(self.body())
        for length in range(len(valid)):
            with self.assertRaises(ValueError):
                decode_output_indicators(0x71, valid[:length], [1])
        for opcode, body in [(0x73, valid), (0x71, bytes(16)), (0x71, valid + b"\x00")]:
            with self.assertRaises(ValueError):
                decode_output_indicators(opcode, body, [1])
        for numbers in [[0], [13], [True], [1.0], ["1"], [1, 1]]:
            with self.assertRaises(ValueError):
                decode_output_indicators(0x71, valid, numbers)


if __name__ == "__main__":
    unittest.main()
