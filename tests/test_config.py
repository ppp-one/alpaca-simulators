import os
import tempfile
from pathlib import Path

import pytest
import yaml

from observatory_simulator.config import Config


@pytest.fixture(autouse=True)
def temp_config_dir(monkeypatch):
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir)
        default_config_path = config_dir / "template.yaml"
        config_path = config_dir / "config.yaml"
        default_config = {"foo": "bar", "baz": 42}
        with open(default_config_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(default_config, f)

        # Patch Config to use our temp config dir
        monkeypatch.setattr(Config, "CONFIG_DIR", config_dir)
        monkeypatch.setattr(Config, "_DEFAULT_PATH", default_config_path)

        # Reset singleton for each test
        Config._instance = None
        yield {
            "config_dir": config_dir,
            "default_config_path": default_config_path,
            "config_path": config_path,
            "default_config": default_config,
        }
        Config._instance = None


def test_singleton():
    c1 = Config()
    c2 = Config()
    assert c1 is c2


def test_loads_default_on_missing_config(temp_config_dir):
    config = Config()
    loaded = config.get()
    assert loaded == temp_config_dir["default_config"]
    assert temp_config_dir["config_path"].exists()


def test_getitem():
    config = Config()
    assert config["foo"] == "bar"
    assert config["baz"] == 42


def test_reload(temp_config_dir):
    config = Config()
    _ = config.get()
    new_config = {"foo": "changed", "baz": 99}
    with open(temp_config_dir["config_path"], "w", encoding="utf-8") as f:
        yaml.safe_dump(new_config, f)
    config.reload()
    assert config["foo"] == "changed"
    assert config["baz"] == 99


def test_missing_config_dir_raises(monkeypatch, temp_config_dir):
    bad_dir = temp_config_dir["config_dir"] / "nonexistent"
    monkeypatch.setattr(Config, "CONFIG_DIR", bad_dir)
    monkeypatch.setattr(Config, "_DEFAULT_PATH", bad_dir / "template.yaml")
    Config._instance = None
    with pytest.raises(FileNotFoundError):
        Config().get()


def test_missing_default_config_raises(temp_config_dir):
    os.remove(temp_config_dir["default_config_path"])
    Config._instance = None
    with pytest.raises(FileNotFoundError):
        Config().get()
