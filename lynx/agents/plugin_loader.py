"""Dynamic plugin loader for third-party Lynx agents.

Scans a plugins/ directory for .py files, imports them, and discovers
classes that inherit from BaseAgent. Returns validated agent instances."""

import importlib.util
import inspect
import logging
import sys
from pathlib import Path

from lynx.agents.base import BaseAgent

logger = logging.getLogger(__name__)

PLUGIN_DIR = Path("plugins")


def discover_plugins(plugin_dir: str | Path = PLUGIN_DIR) -> list[BaseAgent]:
    """Scan plugin_dir for .py files, import them, and return BaseAgent instances."""
    plugin_path = Path(plugin_dir)
    if not plugin_path.exists():
        logger.info("plugin_dir_not_found", path=str(plugin_path))
        return []

    agents: list[BaseAgent] = []
    for py_file in sorted(plugin_path.glob("*.py")):
        if py_file.name.startswith("_"):
            continue
        try:
            agent = _load_plugin(py_file)
            if agent is not None:
                agents.append(agent)
                logger.info("plugin_loaded", name=agent.name, source=py_file.name)
        except Exception as exc:
            logger.warning("plugin_load_failed", file=py_file.name, error=str(exc))

    return agents


def _load_plugin(py_file: Path) -> BaseAgent | None:
    spec = importlib.util.spec_from_file_location(py_file.stem, py_file)
    if spec is None or spec.loader is None:
        return None

    module = importlib.util.module_from_spec(spec)
    sys.modules[py_file.stem] = module
    spec.loader.exec_module(module)

    for _, obj in inspect.getmembers(module, inspect.isclass):
        if issubclass(obj, BaseAgent) and obj is not BaseAgent:
            instance = obj()
            _validate_agent(instance)
            return instance

    logger.warning("no_agent_class_found", file=py_file.name)
    return None


def _validate_agent(agent: BaseAgent) -> None:
    assert isinstance(agent.name, str) and len(agent.name) > 0, "Agent must have a non-empty .name"
    assert callable(agent.evaluate), "Agent must implement .evaluate()"
