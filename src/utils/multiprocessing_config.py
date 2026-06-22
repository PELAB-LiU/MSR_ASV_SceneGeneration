"""Configure multiprocessing to use the spawn start method (Windows-safe)."""

from __future__ import annotations

import multiprocessing as mp

_SPAWN_CONFIGURED = False


def configure_spawn_start_method() -> None:
    global _SPAWN_CONFIGURED
    if _SPAWN_CONFIGURED:
        return
    try:
        mp.set_start_method("spawn", force=False)
    except RuntimeError:
        pass
    _SPAWN_CONFIGURED = True


def get_spawn_context() -> mp.context.BaseContext:
    configure_spawn_start_method()
    return mp.get_context("spawn")
