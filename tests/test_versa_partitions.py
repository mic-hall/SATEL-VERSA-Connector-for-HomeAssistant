import unittest

from custom_components.satel_versa.protocol.partitions import ArmMode, decode_partitions


class PartitionTests(unittest.TestCase):
    def test_modes_and_exit_delay(self):
        for value, mode, delay in [
            (0, ArmMode.DISARMED, False),
            (1, ArmMode.FULL, True),
            (5, ArmMode.FULL, False),
            (2, ArmMode.NIGHT, True),
            (6, ArmMode.NIGHT, False),
            (3, ArmMode.DAY, True),
            (7, ArmMode.DAY, False),
            (4, ArmMode.DISARMED, False),
        ]:
            body = bytearray(16)
            body[1] = value
            states = decode_partitions(0x71, body, [1, 2])
            self.assertEqual(states[0].arm_mode, mode)
            self.assertEqual(states[0].exit_delay, delay)
            self.assertIs(states[1].arm_mode, ArmMode.DISARMED)

    def test_alarm_types_memory_and_partition_isolation(self):
        names = [
            "tamper_alarm_memory",
            "silent_alarm_memory",
            "alarm_memory",
            "fire_alarm_memory",
            "tamper_alarm",
            "warning_alarm",
            "alarm",
            "fire_alarm",
        ]
        for number in (1, 2):
            for mask, field in zip((1, 2, 4, 8, 16, 32, 64, 128), names):
                body = bytearray(16)
                body[number + 4] = mask
                states = decode_partitions(0x71, body, [1, 2])
                self.assertEqual(
                    [name for name in names if getattr(states[number - 1], name)],
                    [field],
                )
                self.assertFalse(any(getattr(states[2 - number], name) for name in names))
                self.assertIs(states[number - 1].arm_mode, ArmMode.DISARMED)

    def test_uninterpreted_fields_do_not_create_flags_or_expose_ids(self):
        body = bytearray([0, 0, 0, 255, 255, 0, 0] + [255] * 9)
        states = decode_partitions(0x71, body, [2, 1])
        self.assertEqual([state.number for state in states], [2, 1])
        self.assertTrue(all(state.arm_mode is ArmMode.DISARMED for state in states))
        self.assertTrue(all(not state.alarm and not state.fire_alarm for state in states))
        self.assertEqual(decode_partitions(0x71, body, []), ())

    def test_entry_delay_and_acpo_flags(self):
        for value, expected in [
            (8, "entry_delay"),
            (16, "verified_alarm"),
            (32, "acpo_blocked"),
        ]:
            body = bytearray(16)
            body[2] = value
            state = decode_partitions(0x71, body, [2])[0]
            self.assertTrue(getattr(state, expected))
            self.assertIs(state.arm_mode, ArmMode.DISARMED)
            self.assertFalse(state.exit_delay)
            self.assertFalse(state.alarm)
        for value in (64, 128, 192):
            body = bytearray(16)
            body[1] = value
            state = decode_partitions(0x71, body, [1])[0]
            self.assertFalse(state.entry_delay or state.verified_alarm or state.acpo_blocked)

    def test_reject_incomplete_and_unknown_profiles(self):
        valid = bytes(16)
        for body in [valid[:n] for n in range(16)] + [
            valid + b"\x00",
            b"\x01" + bytes(15),
        ]:
            with self.assertRaises(ValueError):
                decode_partitions(0x71, body, [1])
        for numbers in [[0], [3], [True], [1.0], ["1"], [1, 1]]:
            with self.assertRaises(ValueError):
                decode_partitions(0x71, valid, numbers)
        with self.assertRaises(ValueError):
            decode_partitions(0x73, valid, [1])


if __name__ == "__main__":
    unittest.main()
