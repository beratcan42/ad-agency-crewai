"""Ajan paketi — 12 ajan registry'sini export eder."""

from __future__ import annotations

from .registry import (
    AGENT_TASKS,
    build_system_prompt,
    get_all_agent_ids,
    get_task_template,
)

__all__ = [
    "AGENT_TASKS",
    "build_system_prompt",
    "get_all_agent_ids",
    "get_task_template",
]
