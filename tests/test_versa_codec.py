import unittest

from custom_components.satel_versa.protocol.codec import (
    build_frame,
    parse_frame,
    request_record,
    server_record_size,
    transform,
)


class CodecTests(unittest.TestCase):
    def test_nist_aes192_cbc_full_block_vector(self):
        key = bytes.fromhex("8e73b0f7da0e6452c810f32b809079e562f8ead2522c6b7b")
        iv = bytes.fromhex("000102030405060708090a0b0c0d0e0f")
        # Choose first plaintext so DCP's derived IV gives NIST's first AES input.
        from custom_components.satel_versa.protocol.codec import ecb

        plain = bytes.fromhex("6bc1bee22e409f96e93d7e117393172a")
        adjusted = bytes(a ^ b ^ c for a, b, c in zip(plain, iv, ecb(key, bytes(16))))
        expected = bytes.fromhex("4f021db243bc633d7178183a9fa071e8")
        self.assertEqual(transform(key, adjusted), expected)
        self.assertEqual(transform(key, expected, True), adjusted)

    def test_partial_tail_and_corruption(self):
        key = bytes(range(24))
        for size in [1, 15, 16, 17, 31, 32, 49]:
            data = bytes(range(size))
            self.assertEqual(transform(key, transform(key, data), True), data)
        frame = build_frame(0x71, 7, b"\x01" + bytes(20))
        self.assertEqual(parse_frame(frame).body, b"\x01" + bytes(20))
        for length in range(len(frame)):
            with self.assertRaises(ValueError):
                parse_frame(frame[:length])
        for pos in range(len(frame)):
            bad = bytearray(frame)
            bad[pos] ^= 1
            with self.assertRaises(ValueError):
                parse_frame(bad)

    def test_profile_restrictions_and_length(self):
        key = bytes(24)
        with self.assertRaises(ValueError):
            request_record(key, 1, 2, 0x52, bytes(6))
        with self.assertRaises(ValueError):
            request_record(key, 1, 2, 0x4B, b"\x01")
        header = bytearray(16)
        header[1:5] = bytes([0, 1, 1, 27])
        self.assertEqual(server_record_size(header), 49)
