# tsah

`tsah` is a small macOS Accessibility toolkit built around the native AX APIs with `ctypes`.
It provides:

- raw AX / CoreFoundation bindings
- a higher-level `AXElement` wrapper
- recursive tree snapshots
- JSON serialization helpers
- common actions
- a notification observer that blocks on `CFRunLoopRun()` with no polling or sleep loops

## Requirements

- macOS
- Python 3.11+
- Accessibility permission for the Python process running `tsah`

Check trust status:

```bash
python -m tsah.cli trust
```

## Install

```bash
pip install -e .
```

## CLI

Dump the focused application's accessibility tree:

```bash
tsah tree --focused-application --max-depth 3 --include-actions
```

Dump the focused element instead:

```bash
tsah tree --focused-element --max-depth 1
```

List actions on the focused element:

```bash
tsah actions --focused-element
```

Perform a press action:

```bash
tsah perform --focused-element AXPress
```

Watch notifications from the focused application:

```bash
tsah watch --focused-application \
  --notification AXFocusedUIElementChanged \
  --notification AXWindowCreated
```

The observer path uses the Accessibility observer source directly and then hands control to `CFRunLoopRun()`. There is no polling loop, no `sleep`, and no timer-based wakeup.

## Demo: Event-Driven Agent Loop

Watch any app and react to UI changes in real time - no screenshots, no polling:

```bash
# Watch Xcode - see build events, errors, focus changes
python examples/agent_loop.py Xcode

# Pipe events to Claude for autonomous agent reasoning
python examples/agent_loop.py Xcode --llm-pipe
```

Output looks like:

```text
[tsah] Watching: Xcode (pid 1234)
[tsah] Mode: observe only

{"app":"Xcode","event":"ValueChanged","element_role":"StaticText","element_label":"Build succeeded","ts":1712345678.123,"ui_snapshot":[...]}
{"app":"Xcode","event":"FocusedUIElementChanged","element_role":"TextArea","element_label":"","ts":1712345679.456,"ui_snapshot":[...]}
```

## Library Example

```python
from tsah.core.ax import AXElement
from tsah.core.observer import AXObserver
from tsah.serializer import dumps

app = AXElement.focused_application()
print(dumps(app.snapshot(max_depth=2, include_actions=True)))

def on_event(event):
    print(event.notification, event.element.hex_ref())

observer = AXObserver(
    app.pid(),
    callback=on_event,
    element=app,
    notifications=["AXFocusedUIElementChanged"],
)
observer.run()
```

## Package Layout

- `tsah/core/ax_raw.py`: raw `ctypes` bindings, CF conversion, observer primitives
- `tsah/core/ax.py`: `AXElement` wrapper
- `tsah/core/tree.py`: recursive snapshot builder
- `tsah/core/observer.py`: notification observer backed by `CFRunLoopRun()`
- `tsah/core/actions.py`: convenience action helpers
- `tsah/serializer.py`: dataclass-to-JSON conversion
- `tsah/cli.py`: command line entry point
