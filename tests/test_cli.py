import subprocess
from functools import partial

import pytest
from pydantic import BaseModel

from aiml_pyxis_investment_game.cli import load_agent, resolve_cfg_args, takes_kwargs


def test_takes_kwargs():
    def func_with_kwargs(a, b, **kwargs):
        pass

    def func_without_kwargs(a, b):
        pass

    assert takes_kwargs(func_with_kwargs) is True
    assert takes_kwargs(func_without_kwargs) is False


@pytest.fixture
def dummy_config():
    class DummyConfig(BaseModel):
        param1: int
        param2: int

        class Config:
            frozen = True

    return DummyConfig(param1=10, param2=20)


def test_resolve_cfg_args_correct_kwargs(dummy_config):
    updated_cfg = resolve_cfg_args(dummy_config, param1=30)

    assert updated_cfg.param1 == 30
    assert updated_cfg.param2 == 20


def test_resolve_cfg_args_no_kwargs(dummy_config):
    updated_cfg = resolve_cfg_args(dummy_config)

    assert updated_cfg.param1 == 10
    assert updated_cfg.param2 == 20


@pytest.fixture
def custom_agent_file():
    return "tests/data/custom_agents/custom_agent.py"


@pytest.fixture
def custom_agent_kwargs_file():
    return "tests/data/custom_agents/custom_agent_kwargs.py"


def test_load_agent_from_file(custom_agent_file):
    agent = load_agent(custom_agent_file)
    assert callable(agent)


def test_load_agent_from_file_with_kwargs(custom_agent_kwargs_file):
    agent = load_agent(custom_agent_kwargs_file, extra_param=42)
    assert isinstance(agent, partial)
    assert agent.keywords["extra_param"] == 42


def test_load_agent_file_not_found():
    with pytest.raises(FileNotFoundError):
        load_agent("non_existent_file.py")


def test_load_agent_no_main_function(tmp_path):
    custom_agent_path = tmp_path / "custom_agent_no_main.py"
    custom_agent_path.write_text("def not_main(): pass")

    with pytest.raises(AttributeError):
        load_agent(str(custom_agent_path))


def test_main_cli_seeded_is_reproducible(custom_agent_file):
    cmd = [
        "python",
        "aiml_pyxis_investment_game/cli.py",
        "--agent",
        custom_agent_file,
        "--seed",
        "123",
    ]

    result1 = subprocess.run(cmd, capture_output=True, text=True)
    result2 = subprocess.run(cmd, capture_output=True, text=True)

    assert result1.stdout == result2.stdout
