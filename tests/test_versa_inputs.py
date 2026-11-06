import unittest

from custom_components.satel_versa.protocol.inputs import decode_inputs


class InputTests(unittest.TestCase):
    def test_boundaries_and_distinct_flags(self):
        body = bytearray(25)
        body[0] = 1
        body[1] = 1  # input 1 blocked
        body[5] = 128  # input 8 violated
        body[6] = 1  # input 9 violated
        body[12] = 32  # input 30 alarm memory
        body[13] = 1  # input 1 armed
        body[18] = 1  # input 9 monitoring delay
        states = {s.number: s for s in decode_inputs(body, [1, 8, 9, 30])}
        self.assertTrue(states[1].blocked)
        self.assertTrue(states[1].armed)
        self.assertFalse(states[1].violated)
        self.assertTrue(states[8].violated)
        self.assertTrue(states[9].violated)
        self.assertTrue(states[9].monitoring_delay)
        self.assertTrue(states[30].alarm_memory)
        self.assertFalse(states[30].violated)

    def test_all_bits_individually(self):
        for number in range(1, 31):
            body = bytearray(21)
            body[0] = 1
            body[5 + (number - 1) // 8] = 1 << ((number - 1) % 8)
            states = decode_inputs(body, list(range(1, 31)))
            self.assertEqual([s.number for s in states if s.violated], [number])

    def test_invalid_and_missing(self):
        for body, numbers in [
            (b"", [1]),
            (bytes(21), [1]),
            (bytes([1]) + bytes(20), [0]),
            (bytes([1]) + bytes(20), [31]),
            (bytes([1]) + bytes(20), [True]),
            (bytes([1]) + bytes(20), [1, 1]),
        ]:
            with self.assertRaises(ValueError):
                decode_inputs(body, numbers)
        self.assertEqual(decode_inputs(bytes([1]) + bytes(20), []), ())


if __name__ == "__main__":
    unittest.main()
