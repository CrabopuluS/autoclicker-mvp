# Contributing

Thanks for your interest in improving AutoClicker MVP.

## Development setup

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Run app:

```powershell
python main.py
```

## Coding rules

- Keep UI responsive (no blocking operations on main thread).
- Keep type hints and docstrings.
- Preserve clean separation between `ui/` and `core/`.
- Keep Windows compatibility.

## Pull request checklist

- [ ] App starts on Windows.
- [ ] Hotkeys still work globally.
- [ ] Start/Stop/Pause/Resume behavior validated.
- [ ] `python -m compileall .` passes.
- [ ] README / changelog updated if behavior changed.
