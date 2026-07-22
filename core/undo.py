"""One-level, persistent rollback for file mutations."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from time import time_ns


def backup_file(path: Path, project_root: str) -> None:
    root = Path(project_root).resolve()
    relative = path.resolve().relative_to(root).as_posix()
    storage = root / ".citadex" / "backups"
    storage.mkdir(parents=True, exist_ok=True)
    token = str(time_ns())
    backup = storage / token
    existed = path.is_file()
    if existed:
        shutil.copy2(path, backup)
    manifest = {"path": relative, "backup": token, "existed": existed}
    (root / ".citadex" / "last-action.json").write_text(json.dumps(manifest), encoding="utf-8")


def undo_last_action(project_root: str) -> dict[str, str]:
    root = Path(project_root).resolve()
    manifest_path = root / ".citadex" / "last-action.json"
    if not manifest_path.is_file():
        raise FileNotFoundError("Нет действия, которое можно отменить.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    target = (root / manifest["path"]).resolve()
    target.relative_to(root)
    if manifest["existed"]:
        backup = root / ".citadex" / "backups" / manifest["backup"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(backup, target)
        status = "restored"
    else:
        if target.is_file():
            target.unlink()
        status = "removed"
    manifest_path.unlink()
    return {"status": status, "path": str(target)}


__all__ = ["backup_file", "undo_last_action"]
