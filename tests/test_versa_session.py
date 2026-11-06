import unittest

from custom_components.satel_versa.protocol.session import (
    CommandRejected,
    Phase,
    SessionEvidence,
    identifier_bytes,
    parse_identity,
    parse_online_display,
)


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.panel = bytes([1, 2, 3, 4])
        self.identity = self.panel + bytes(9)
        self.body = bytes([1]) + bytes(20)

    def test_identified_does_not_mean_read_confirmed(self):
        s = SessionEvidence(self.panel, [1, 10])
        s.begin()
        s.receive(0x73, self.identity)
        self.assertEqual(s.phase, Phase.IDENTIFIED)
        self.assertIsNone(s.inputs)
        s.receive(0x71, self.body)
        self.assertEqual(s.phase, Phase.READ_CONFIRMED)
        self.assertEqual(len(s.inputs), 2)
        s.disconnect()
        self.assertIsNone(s.inputs)
        s.begin()
        self.assertEqual(s.phase, Phase.WAIT_IDENTITY)

    def test_wrong_identity_and_unsupported_profile(self):
        for opcode, body in [
            (0x73, bytes(13)),
            (0x73, self.identity[:-1]),
            (0x73, self.identity + b"X"),
            (0x74, self.identity),
        ]:
            with self.assertRaises(ValueError):
                parse_identity(opcode, body, self.panel)

    def test_reject_data_before_identity_and_clear_stale_data(self):
        s = SessionEvidence(self.panel, [10])
        s.begin()
        with self.assertRaises(ValueError):
            s.receive(0x71, self.body)
        self.assertEqual(s.phase, Phase.FAILED)
        s.disconnect()
        s.begin()
        s.receive(0x73, self.identity)
        s.receive(0x71, self.body)
        with self.assertRaises(ValueError):
            s.receive(0x71, bytes([1]))
        self.assertIsNone(s.inputs)
        self.assertEqual(s.phase, Phase.FAILED)

    def test_id_format_and_start_guard(self):
        self.assertEqual(identifier_bytes("0102aBfF"), bytes([1, 2, 171, 255]))
        for value in ["1234", "1234567G", " 12345678", 12345678]:
            with self.assertRaises(ValueError):
                identifier_bytes(value)
        s = SessionEvidence(self.panel, [1])
        s.begin()
        with self.assertRaises(ValueError):
            s.begin()

    def test_online_display_does_not_confirm_input_read(self):
        body = bytes([0x73, 0]) + b"Private display".ljust(32, b" ")
        s = SessionEvidence(self.panel, [10])
        s.begin()
        s.receive(0x73, self.identity)
        display = s.receive(0x6B, body)
        self.assertEqual(len(display.display_bytes), 32)
        self.assertNotIn("Private display", repr(display))
        self.assertEqual(s.phase, Phase.IDENTIFIED)
        self.assertIsNone(s.inputs)
        for opcode, payload in [(0x6B, body[:-1]), (0x6B, bytes(34)), (0x71, body)]:
            with self.assertRaises(ValueError):
                parse_online_display(opcode, payload)

    def test_native_command_rejections_clear_state(self):
        for opcode in (0x62, 0x64):
            s = SessionEvidence(self.panel, [10])
            s.begin()
            s.receive(0x73, self.identity)
            s.receive(0x71, self.body)
            with self.assertRaises(CommandRejected) as error:
                s.receive(opcode, b"")
            self.assertEqual(error.exception.opcode, opcode)
            self.assertEqual(s.phase, Phase.FAILED)
            self.assertIsNone(s.inputs)


if __name__ == "__main__":
    unittest.main()
