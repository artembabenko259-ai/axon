from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from axon_runtime import (
    default_user_workspace,
    is_axon_install_cwd,
    resolve_startup_cwd,
)


def test_is_axon_install_cwd_false_in_dev_tree() -> None:
    with patch("axon_runtime.is_frozen", return_value=False):
        assert not is_axon_install_cwd(Path("/Program Files/AXON"))


def test_resolve_startup_cwd_keeps_user_directory() -> None:
    with patch("axon_runtime.Path.cwd", return_value=Path("C:/Projects/my-app")):
        with patch("axon_runtime.is_axon_install_cwd", return_value=False):
            with patch("axon_runtime.save_last_workspace") as save:
                workspace = resolve_startup_cwd()
    assert workspace == Path("C:/Projects/my-app").resolve()
    save.assert_called_once()


def test_resolve_startup_cwd_leaves_install_dir() -> None:
    desktop = default_user_workspace()
    with patch("axon_runtime.Path.cwd", return_value=Path("C:/Program Files/AXON")):
        with patch("axon_runtime.is_axon_install_cwd", return_value=True):
            with patch("axon_runtime.get_last_workspace", return_value=None):
                with patch("axon_runtime.save_last_workspace"):
                    workspace = resolve_startup_cwd()
    assert workspace == desktop
