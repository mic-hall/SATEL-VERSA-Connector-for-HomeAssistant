"""Async read-only VERSA client with profile detection and bounded polling.

Only session management, input/output indicator reads and display queries are
allowed. The HA coordinator owns polling and reconnects.
"""

import asyncio
import secrets

from .codec import derive_key, parse_frame, request_record, server_record_size, transform
from .outputs import decode_output_indicators
from .session import CommandRejected, Phase, SessionEvidence, identifier_bytes, parse_identity


class VersaClient:
    """Auto-detect Ethernet profile; None selects profile timeout/display defaults.

    Explicit timeout and read_display values override these defaults. The initial
    connection/greeting budget is five seconds unless a timeout is supplied.
    """

    def __init__(
        self,
        host,
        port,
        ethm_key,
        dloadx_id,
        panel_id,
        input_numbers,
        timeout=None,
        connector=None,
        read_display=None,
        output_numbers=(),
    ):
        if timeout is not None and timeout <= 0:
            raise ValueError("Timeout must be positive")
        self.host, self.port = host, port
        self._key = derive_key(ethm_key)
        self._id = identifier_bytes(dloadx_id)
        self.evidence = SessionEvidence(identifier_bytes(panel_id), input_numbers)
        self._output_numbers = list(output_numbers)
        decode_output_indicators(0x71, b"\x09" + bytes(15), self._output_numbers)
        self.output_indicators = None
        self._configured_timeout = timeout
        self.timeout = 5 if timeout is None else timeout
        self._connector = connector or asyncio.open_connection
        self._display = read_display
        self._versa = False
        self._reader = self._writer = None
        self._token = None
        self._lock = asyncio.Lock()

    @property
    def connected(self) -> bool:
        """Whether the transport has an identified session."""
        return self._writer is not None and self.evidence.phase in (
            Phase.IDENTIFIED,
            Phase.READ_CONFIRMED,
        )

    @property
    def inputs(self):
        return self.evidence.inputs

    async def _drop(self):
        writer, self._writer = self._writer, None
        self._reader = None
        self._token = None
        self.evidence.disconnect()
        self.output_indicators = None
        if writer is not None:
            writer.close()
            try:
                await asyncio.wait_for(writer.wait_closed(), self.timeout)
            except OSError, TimeoutError:
                pass

    async def _receive(self):
        first = await self._reader.readexactly(16)
        header = transform(self._key, first, True)
        if self._versa:
            if header[1:3] != b"\x01\x01" or header[3] < 2:
                raise ValueError("Unsupported VERSA server header")
            size = ((header[3] + 6 + 15) // 16) * 16
            offset = 1
        else:
            size = server_record_size(header)
            offset = 2
        wire = first + await self._reader.readexactly(size - 16)
        plain = transform(self._key, wire, True)
        frame = parse_frame(plain, offset)
        if frame.opcode in (0x62, 0x64):
            raise CommandRejected(frame.opcode)
        self._token = plain[0]
        return frame

    async def _exchange(self, opcode, body, expected):
        nonce = secrets.randbelow(255)
        if nonce >= 0xA1:
            nonce += 1
        self._writer.write(request_record(self._key, self._token, nonce, opcode, body))
        await self._writer.drain()
        reply = await self._receive()
        if reply.opcode != expected:
            raise ValueError("Unexpected response opcode")
        return reply

    async def connect(self):
        async with self._lock:
            if self._writer is not None or self.evidence.phase != Phase.DISCONNECTED:
                raise ValueError("Already connected")

            async def operation():
                self._reader, self._writer = await self._connector(self.host, self.port)
                greeting = transform(self._key, await self._reader.readexactly(16), True)
                self._versa = greeting[1:6] == b"VERSA"
                if not self._versa and b"ETHM" not in greeting:
                    raise ValueError("Unsupported greeting or key")
                if self._versa and self._output_numbers:
                    raise ValueError("Output indicators are supported only over ETHM")
                self._token = greeting[0]
                self.evidence.begin()
                if self._versa:
                    if self._configured_timeout is None:
                        self.timeout = 15
                        deadline.reschedule(started + self.timeout)
                    await asyncio.sleep(2.5)
                reply = await self._exchange(0x53, self._id, 0x73)
                self.evidence.receive(reply.opcode, reply.body)
                if self._display is True or (self._display is None and not self._versa):
                    reply = await self._exchange(0x4B, b"\x67", 0x6B)
                    self.evidence.receive(reply.opcode, reply.body)

            try:
                self.timeout = 5 if self._configured_timeout is None else self._configured_timeout
                started = asyncio.get_running_loop().time()
                async with asyncio.timeout(self.timeout) as deadline:
                    await operation()
            except BaseException:
                await self._drop()
                raise

    async def _poll(self, selector, decode):
        async with self._lock:
            if self._writer is None:
                raise ValueError("Not connected")

            async def operation():
                if selector == 9 and self._versa:
                    raise ValueError("Output indicators are supported only over ETHM")
                # Native receiver case 71/07 routes an online notification.
                # It can take the place of a poll reply immediately after START.
                # Native dispatch accepts an embedded online opcode after 07.
                # Do not interpret its payload or publish it as input data;
                # retry the same read, with updated token, under the total timeout.
                for _ in range(4):
                    reply = await self._exchange(0x51, bytes([selector]), 0x71)
                    if len(reply.body) >= 2 and reply.body[0] == 7:
                        await asyncio.sleep(0.1)
                        continue
                    return decode(reply.opcode, reply.body)
                raise ValueError("Too many online notifications before poll data")

            try:
                return await asyncio.wait_for(operation(), self.timeout)
            except BaseException:
                await self._drop()
                raise

    async def read_inputs(self):
        return await self._poll(1, self.evidence.receive)

    async def read_outputs(self):
        """Read selected ETHM output indicators; never switch an output."""
        if not self._output_numbers:
            return ()

        def decode(opcode, body):
            states = decode_output_indicators(opcode, body, self._output_numbers)
            self.output_indicators = states
            return states

        return await self._poll(9, decode)

    async def close(self):
        async with self._lock:
            try:
                if self._writer is not None:
                    reply = await asyncio.wait_for(
                        self._exchange(0x46, self._id, 0x66), self.timeout
                    )
                    parse_identity(reply.opcode, reply.body, self.evidence.panel_id)
            finally:
                await self._drop()
