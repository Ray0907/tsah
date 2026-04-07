# tsah

**macOS accessibility API as a universal desktop interface for AI agents.**

Every GUI app on macOS already exposes a complete, structured UI model through the Accessibility API — the same one VoiceOver uses. `tsah` makes that model available to developers and AI agents as structured JSON, with push-based event streaming and no screenshots.

```bash
# See Safari's entire UI as structured data
tsah snapshot "Safari" --llm

# Stream UI events in real time (no polling, no sleep loops)
tsah watch "Xcode"

# Click a button by label, in any app
tsah act "Figma" press "Publish"
```

---

## Why

Screenshot-based computer use is slow, expensive, and fragile — it converts structured data into pixels and then asks an LLM to convert it back. The Accessibility API skips that entirely:

| | Screenshots | tsah |
|---|---|---|
| Input to LLM | Image tokens (~1000+) | Flat text tuples (~50 tokens) |
| Element identity | Pixel coordinates | Role + label (stable across resizes) |
| Password fields | Visible in screenshot | Blocked at OS level |
| Works with | Whatever is on screen | Any running app, in background |
| Latency | Camera → Vision API | Direct IPC, ~10ms |

The AX tree is the app's own model, not a rendering of it. You get `Button "Publish"`, not a bounding box.

---

## Requirements

- macOS (any version with Accessibility API — 10.9+)
- Python 3.11+
- Accessibility permission granted to your terminal / Python process

Grant permission once:

```
System Settings → Privacy & Security → Accessibility → add your terminal
```

Check status:

```bash
tsah trust
```

---

## Install

```bash
git clone https://github.com/Ray0907/tsah
cd tsah
pip install -e .
```

---

## CLI

### List running apps

```bash
tsah list
```

```json
[{"name": "Safari", "pid": 1234}, {"name": "Xcode", "pid": 5678}, ...]
```

### Snapshot a UI tree

```bash
# Rich terminal tree (default)
tsah snapshot "Safari"

# Full JSON tree
tsah snapshot "Safari" --json

# Flat LLM-ready tuples — [path, role, label] or [path, role, label, value]
tsah snapshot "Safari" --llm

# Filter to specific roles
tsah snapshot "Safari" --filter Button
```

The `--llm` format strips the `AX` prefix, drops empty nodes, and uses stable path indices:

```json
[
  ["0", "Window", "Safari"],
  ["0.0", "Toolbar", "Navigation"],
  ["0.0.0", "Button", "Back"],
  ["0.0.1", "Button", "Forward"],
  ["0.0.2", "TextField", "Address Bar", "https://example.com"]
]
```

### Watch UI events

```bash
# Watch with default notifications (focus, window, value, title changes)
tsah watch "Xcode"

# Watch specific notifications
tsah watch "Slack" --notification AXValueChanged
```

Events stream as newline-delimited JSON:

```json
{"type": "AXValueChanged", "ts": 1712345678.1, "pid": 1234, "role": "StaticText", "label": "Build succeeded"}
{"type": "AXFocusedUIElementChanged", "ts": 1712345679.4, "pid": 1234, "role": "TextArea", "label": ""}
```

The observer uses `AXObserver + CFRunLoopRun()` — pure push. No polling, no `sleep`, no timers.

### Act on UI elements

```bash
# Press a button (case-insensitive substring match)
tsah act "Safari" press "Reload"

# Focus a text field
tsah act "Safari" focus "Address"
```

Label matching is case-insensitive and substring-based — `"reload"` matches `"Reload This Page"`.

---

## Agent loop demo

Watch any app and react to UI changes in real time:

```bash
# Observe only — prints structured events as they happen
python examples/agent_loop.py Xcode

# Pipe events to Claude for autonomous reasoning
python examples/agent_loop.py Xcode --llm-pipe
```

Each event includes a compact snapshot of the current UI state:

```json
{
  "app": "Xcode",
  "event": "ValueChanged",
  "element_role": "StaticText",
  "element_label": "Build succeeded",
  "ts": 1712345678.123,
  "ui_snapshot": [
    ["0", "Window", "MyApp — Xcode"],
    ["0.0.0", "Button", "Run"],
    ["0.0.1", "StaticText", "Build succeeded"]
  ]
}
```

With `--llm-pipe`, each event is sent to `claude -p` with the UI snapshot as context. The agent can respond with `ACT: tsah act "Xcode" press "Run"` to drive the app.

---

## Use cases

**Xcode / build tools** — watch for build errors, test results, simulator state without parsing log files

**Figma** — read the current canvas structure (open file required), detect selection changes, automate exports

**Slack / Messages** — detect new messages, read thread content without the app's API

**Notes / Reminders** — read and write content in apps that have no API

**Any app** — the interface is universal; no per-app adapters needed

---

## Python API

```python
from tsah.core.ax import AXElement
from tsah.core.observer import AXObserver
from tsah.core.tree import build_tree
from tsah.serializer import to_llm_tuples

# Snapshot any app
app = AXElement.application(pid=1234)
root = build_tree(app)
tuples = to_llm_tuples(root)

# Watch for events
def on_event(event):
    print(event.notification, event.timestamp)

observer = AXObserver(
    pid=1234,
    callback=on_event,
    notifications=["AXFocusedUIElementChanged", "AXValueChanged"],
)
observer.run()  # blocks; use run_in_thread() for background
```

---

## Security

- **Local only** — no network calls, no WebSocket servers, no remote connections
- **OS-enforced permission** — explicit one-time grant in System Settings; revocable at any time
- **Password fields are protected** — `AXSecureTextField` returns empty value; tsah cannot read passwords
- **Read-only by default** — `act` requires an explicit command; watching and snapshotting have no side effects
- **Minimal blast radius** — even if misused, the API can only interact with UI elements; no shell execution

---

## Package layout

```
tsah/
  core/
    ax_raw.py     — ctypes bindings to CoreFoundation + ApplicationServices
    ax.py         — AXElement wrapper with error translation
    tree.py       — recursive AXNode builder with cycle detection
    observer.py   — push-based AXObserver backed by CFRunLoopRun()
  cli.py          — CLI entry point
  serializer.py   — JSON serialization + LLM flat tuple format
examples/
  agent_loop.py   — event-driven agent demo
```

---

## License

MIT
