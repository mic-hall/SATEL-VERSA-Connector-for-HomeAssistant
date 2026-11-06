# Changelog

## 0.1.0-beta.1

Initial beta for VERSA input states over ETHM-1 Plus.

- UI configuration and reconfiguration; explicit input selection and poll interval.
- One binary sensor per configured input; no inferred motion/door class.
- Shared asynchronous connection, input polling and bounded reconnect backoff.
- Unavailable entities after a failed poll; STOP and socket cleanup on unload.
- English and Polish UI, diagnostics that omit credentials and input states.
- Protocol, simulated transport and Home Assistant integration tests.

Validated protocol with VERSA 15 + ETHM-1 Plus. Support for other models and
firmware, DLOADX coexistence and long-running reliability remain unverified.
