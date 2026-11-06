import asyncio
import unittest

from custom_components.satel_versa.protocol.client import VersaClient
from custom_components.satel_versa.protocol.codec import (
    build_frame,
    derive_key,
    parse_frame,
    transform,
)

SECRET = b"test-only"
KEY = derive_key(SECRET)
ID = bytes.fromhex("01020304")
PANEL = bytes.fromhex("aabbccdd")


class FakeModule:
    def __init__(self):
        self.reader = asyncio.StreamReader()
        self.closed = False
        self.requests = []
        self.token = 5
        self.hang_poll = False
        self.bad_identity = False
        self.eof_poll = False
        self.online_events = 0
        self.active = 0
        self.emit(transform(KEY, bytes([self.token]) + b"ETHM" + bytes(11)))

    def emit(self, wire):
        # Deliver each byte separately: no network or local listening socket.
        for byte in wire:
            asyncio.get_running_loop().call_soon(self.reader.feed_data, bytes([byte]))

    async def connector(self, host, port):
        return self.reader, self

    def write(self, wire):
        plain = transform(KEY, wire, True)
        if plain[0] != self.token:
            raise ValueError("Client failed to echo peer token")
        frame = parse_frame(plain, 1)
        self.requests.append(frame.opcode)
        if frame.opcode in (0x53, 0x46):
            if frame.body != ID:
                raise ValueError("Wrong client identifier")
            op = 0x73 if frame.opcode == 0x53 else 0x66
            body = (bytes(4) if self.bad_identity else PANEL) + bytes(9)
        elif frame.opcode == 0x4B:
            if frame.body != b"\x67":
                raise ValueError("Unsupported online command")
            op, body = 0x6B, bytes([0x73, 0]) + bytes([32]) * 32
        elif frame.opcode == 0x51:
            if self.eof_poll:
                self.reader.feed_eof()
                return
            if self.hang_poll:
                return
            if frame.body != b"\x01":
                raise ValueError("Wrong selector")
            if self.online_events:
                remaining = self.online_events
                self.online_events -= 1
                body = b"\x07\x1a\x00" if remaining % 2 == 0 else b"\x07\x71\x00\x00\x00"
            else:
                body = bytearray(25)
                body[0] = 1
                body[6] = 2
            op = 0x71
        else:
            raise ValueError("Unexpected request")
        self.token = (self.token + 19) & 255
        inner = build_frame(op, 8, body)
        plain = bytes([self.token, 0]) + inner
        size = 1 + ((len(plain) - 1 + 15) // 16) * 16
        self.emit(transform(KEY, plain.ljust(size, b"\xff")))

    async def drain(self):
        pass

    def close(self):
        self.closed = True

    async def wait_closed(self):
        pass


class ClientTests(unittest.IsolatedAsyncioTestCase):
    def client(self, module, **kwargs):
        return VersaClient(
            "unused.invalid",
            7090,
            SECRET,
            ID.hex(),
            PANEL.hex(),
            [2, 10],
            connector=module.connector,
            **kwargs,
        )

    async def test_lifecycle_and_serialized_reads(self):
        module = FakeModule()
        client = self.client(module)
        await client.connect()
        self.assertIsNone(client.inputs)
        results = await asyncio.gather(client.read_inputs(), client.read_inputs())
        self.assertTrue(all(r[1].violated and not r[0].violated for r in results))
        await client.close()
        self.assertIsNone(client.inputs)
        self.assertTrue(module.closed)
        self.assertEqual(module.requests, [0x53, 0x4B, 0x51, 0x51, 0x46])

    async def test_wrong_identity_closes(self):
        module = FakeModule()
        module.bad_identity = True
        client = self.client(module)
        with self.assertRaises(ValueError):
            await client.connect()
        self.assertTrue(module.closed)
        self.assertIsNone(client.inputs)
        self.assertEqual(module.requests, [0x53])

    async def test_timeout_and_eof_clear_prior_data(self):
        for eof in [False, True]:
            module = FakeModule()
            client = self.client(module, timeout=0.1)
            await client.connect()
            await client.read_inputs()
            module.hang_poll = True
            module.eof_poll = eof
            with self.assertRaises((TimeoutError, asyncio.IncompleteReadError)):
                await client.read_inputs()
            self.assertIsNone(client.inputs)
            self.assertTrue(module.closed)

    async def test_cancel_cleans_up(self):
        module = FakeModule()
        client = self.client(module)
        await client.connect()
        await client.read_inputs()
        module.hang_poll = True
        task = asyncio.create_task(client.read_inputs())
        await asyncio.sleep(0)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertTrue(module.closed)
        self.assertIsNone(client.inputs)

    async def test_online_notification_then_input_snapshot(self):
        module = FakeModule()
        client = self.client(module)
        module.online_events = 2
        await client.connect()
        states = await client.read_inputs()
        self.assertTrue(states[1].violated)
        self.assertEqual(module.requests.count(0x51), 3)
        await client.close()

    async def test_online_notification_limit_clears_data(self):
        module = FakeModule()
        client = self.client(module)
        module.online_events = 10
        await client.connect()
        with self.assertRaises(ValueError):
            await client.read_inputs()
        self.assertEqual(module.requests.count(0x51), 4)
        self.assertTrue(module.closed)
        self.assertIsNone(client.inputs)
