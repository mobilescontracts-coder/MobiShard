"""Small safety helpers; separate from the hash-preserved scientific prototype."""
from __future__ import annotations
import hashlib
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def require_checks_enabled() -> None:
    if sys.flags.optimize:
        raise RuntimeError('Do not use Python -O or PYTHONOPTIMIZE; research assertions must remain enabled.')


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def safe_generated_dir(value: str | Path, root: Path = ROOT) -> Path:
    """Only allow generated outputs strictly below build/ or runs/, resolving links."""
    base = root.resolve()
    path = Path(value)
    candidate = (path if path.is_absolute() else base / path).resolve()
    for name in ('build', 'runs'):
        prefix = base / name
        # A symlinked output parent must not redirect outside the repository.
        if prefix.resolve() != prefix:
            continue
        if candidate != prefix and candidate.is_relative_to(prefix):
            return candidate
    raise ValueError('Output must be a subdirectory of build/ or runs/; retained source/results are protected.')


def create_fresh_run(label: str, root: Path = ROOT) -> Path:
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,79}', label) or label in ('.', '..'):
        raise ValueError('Use a 1–80 character run label: letters, digits, dots, underscores, or hyphens.')
    path = safe_generated_dir(Path('runs') / label, root)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Atomic create: never overwrite an earlier run or follow an existing path.
    path.mkdir(exist_ok=False)
    return path


def subprocess_environment() -> dict[str, str]:
    env = dict(os.environ)
    env.pop('PYTHONOPTIMIZE', None)
    env['PYTHONUNBUFFERED'] = '1'
    return env
