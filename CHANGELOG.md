# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog and this project follows Semantic Versioning.

## [1.0.0] - 2026-03-10

### Added

- Windows desktop app on PySide6 with non-blocking architecture.
- Global hotkeys via WinAPI (`F6/F7/F8/F9`).
- Click modes: saved point and current cursor position.
- Mouse button selection (left/right/middle).
- Click count mode: finite or infinite.
- Actions: Start / Stop / Pause / Resume.
- Cursor coordinate capture.
- UI event logging and user-friendly errors.
- Single-instance protection via named mutex.
- Graceful shutdown of worker thread and hotkey hooks.
- Branding assets and app icon pack.
- GitHub Actions workflow to build and publish release EXE.

### Improved

- High-speed click engine with support for `0 ms` interval.
- Better interval timing precision on Windows using `timeBeginPeriod(1)`.
- Premium-styled desktop UI (cards, badges, themed controls, modern layout).
