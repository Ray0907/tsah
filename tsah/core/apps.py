from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess

try:
    import psutil
except ImportError:  # pragma: no cover - exercised only when psutil is unavailable
    psutil = None


@dataclass(slots=True)
class AppInfo:
    name: str
    pid: int


def list_apps() -> list[AppInfo]:
    """Return all running processes with a real name."""
    if psutil is not None:
        return _list_apps_with_psutil()
    return _list_apps_with_ps()


def find_app(name: str) -> AppInfo:
    """Find an app by case-insensitive name match. Raises ValueError if not found."""
    apps = list_apps()
    name_lower = name.lower()

    for app in apps:
        if app.name.lower() == name_lower:
            return app

    matches = [app for app in apps if name_lower in app.name.lower()]
    if not matches:
        raise ValueError(f"No running app matching {name!r}")
    return matches[0]


def _list_apps_with_psutil() -> list[AppInfo]:
    apps: list[AppInfo] = []
    seen_pids: set[int] = set()
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            info = proc.info
            pid = int(info["pid"])
            name = info["name"]
            if name and pid not in seen_pids:
                apps.append(AppInfo(name=str(name), pid=pid))
                seen_pids.add(pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return sorted(apps, key=lambda app: app.name.lower())


def _list_apps_with_ps() -> list[AppInfo]:
    result = subprocess.run(
        ["ps", "-axo", "pid=,comm="],
        capture_output=True,
        text=True,
        check=True,
    )
    apps: list[AppInfo] = []
    seen_pids: set[int] = set()
    for line in result.stdout.splitlines():
        raw = line.strip()
        if not raw:
            continue
        pid_text, _, command = raw.partition(" ")
        if not pid_text or not command:
            continue
        pid = int(pid_text)
        name = Path(command.strip()).name
        if name and pid not in seen_pids:
            apps.append(AppInfo(name=name, pid=pid))
            seen_pids.add(pid)
    return sorted(apps, key=lambda app: app.name.lower())
