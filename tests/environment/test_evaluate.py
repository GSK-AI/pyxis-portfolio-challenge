from unittest.mock import ANY, patch

import numpy as np
import pytest

from aiml_pyxis_investment_game import PROJECT_ROOT, evaluate
from aiml_pyxis_investment_game.environment.metrics import report_all_metrics

TEST_ASSETS_DIR = PROJECT_ROOT / "tests/data/generated_assets"


@pytest.fixture
def patched_config(monkeypatch):
    """Patch config.from_yaml to always return a patched cfg object"""
    from aiml_pyxis_investment_game.config import config as config_mod

    return config_mod.model_copy(
        update={
            "evaluation_data_dir": TEST_ASSETS_DIR,
            "num_eval_episodes": 2,
            "equilibrium_num_assets": 5,  # Test data only has 20 assets
            "max_num_assets": 20,
        }
    )


@pytest.fixture
def do_nothing_agent():
    def dna(observation):
        """A dumb agent that does nothing."""
        num_assets = len(observation["assets"])
        return np.zeros(num_assets)

    return dna


def test_evaluate_deterministic(patched_config, do_nothing_agent):
    """
    Test that evaluate produces deterministic results for a given agent.
    On consecutive calls with the same random seed, the results should be identical.
    """
    with patch(
        "aiml_pyxis_investment_game.environment.evaluate.config", patched_config
    ):
        # Disable warmup for deterministic test
        results1 = report_all_metrics(
            evaluate(
                do_nothing_agent, worker_id=1, episodes_per_worker=1, flatten_obs=False,
                warmup_on_reset_steps=0
            )
        )
        results2 = report_all_metrics(
            evaluate(
                do_nothing_agent, worker_id=1, episodes_per_worker=1, flatten_obs=False,
                warmup_on_reset_steps=0
            )
        )

    # not ideal assert, assumes info about the metrics that are saved. Good enough for now
    assert list(results1[2]["PerStepMetrics"][0]["PerStepCash"].values()) == list(
        results2[2]["PerStepMetrics"][0]["PerStepCash"].values()
    ), "Evaluate results are not deterministic!"


def test_evaluate_calls_collect_metrics(patched_config, do_nothing_agent):
    with (
        patch("aiml_pyxis_investment_game.environment.evaluate.config", patched_config),
        patch(
            "aiml_pyxis_investment_game.environment.evaluate.collect_metrics"
        ) as collect_metrics,
    ):
        _ = evaluate(
            do_nothing_agent, worker_id=1, episodes_per_worker=1, flatten_obs=False
        )
        collect_metrics.assert_any_call(
            collection_fn="on_evaluation_begin", metrics=ANY, context=ANY
        )
        collect_metrics.assert_any_call(
            collection_fn="on_evaluation_end", metrics=ANY, context=ANY
        )


def test_evaluate_with_warmup_enabled(patched_config, do_nothing_agent):
    """Test that evaluate applies warmup wrapper when warmup_on_reset_steps > 0."""
    with (
        patch("aiml_pyxis_investment_game.environment.evaluate.config", patched_config),
        patch(
            "aiml_pyxis_investment_game.environment.evaluate.WarmupOnResetWrapper"
        ) as mock_warmup_wrapper,
        patch(
            "aiml_pyxis_investment_game.environment.evaluate.InvestmentGameEnv"
        ) as mock_env,
    ):
        # Setup mock environment with dict observation (flatten_obs=False)
        mock_obs = {"cash": np.array([1.0]), "time": np.array([0.0]), "assets": ()}
        mock_env_instance = mock_env.return_value
        mock_env_instance.reset.return_value = (mock_obs, {})
        mock_env_instance.step.return_value = (mock_obs, 0.0, True, False, {})

        # Setup warmup wrapper mock
        mock_wrapped_env = mock_warmup_wrapper.return_value
        mock_wrapped_env.reset.return_value = (mock_obs, {})
        mock_wrapped_env.step.return_value = (mock_obs, 0.0, True, False, {})

        _ = evaluate(
            do_nothing_agent,
            worker_id=1,
            episodes_per_worker=1,
            flatten_obs=False,
            warmup_on_reset_steps=10,
            warmup_on_reset_policy="do_nothing",
        )

        # Verify warmup wrapper was called
        mock_warmup_wrapper.assert_called_once_with(
            ANY, warmup_steps=10, policy="do_nothing", verbose=False
        )


def test_evaluate_with_warmup_disabled(patched_config, do_nothing_agent):
    """Test that evaluate does NOT apply warmup wrapper when warmup_on_reset_steps = 0."""
    # Add warmup config to patched_config
    patched_config_with_warmup = patched_config.model_copy(
        update={
            "warmup_on_reset_steps": 0,
            "warmup_on_reset_policy": "do_nothing",
        }
    )

    with (
        patch(
            "aiml_pyxis_investment_game.environment.evaluate.config",
            patched_config_with_warmup,
        ),
        patch(
            "aiml_pyxis_investment_game.environment.evaluate.WarmupOnResetWrapper"
        ) as mock_warmup_wrapper,
    ):
        _ = evaluate(
            do_nothing_agent, worker_id=1, episodes_per_worker=1, flatten_obs=False
        )

        # Verify warmup wrapper was NOT called
        mock_warmup_wrapper.assert_not_called()


def test_evaluate_warmup_from_config(patched_config, do_nothing_agent):
    """Test that evaluate uses warmup parameters from config when not explicitly provided."""
    # Add warmup config
    patched_config_with_warmup = patched_config.model_copy(
        update={
            "warmup_on_reset_steps": 20,
            "warmup_on_reset_policy": "random",
        }
    )

    with (
        patch(
            "aiml_pyxis_investment_game.environment.evaluate.config",
            patched_config_with_warmup,
        ),
        patch(
            "aiml_pyxis_investment_game.environment.evaluate.WarmupOnResetWrapper"
        ) as mock_warmup_wrapper,
        patch(
            "aiml_pyxis_investment_game.environment.evaluate.InvestmentGameEnv"
        ) as mock_env,
    ):
        # Setup mock environment with dict observation (flatten_obs=False)
        mock_obs = {"cash": np.array([1.0]), "time": np.array([0.0]), "assets": ()}
        mock_env_instance = mock_env.return_value
        mock_env_instance.reset.return_value = (mock_obs, {})
        mock_env_instance.step.return_value = (mock_obs, 0.0, True, False, {})

        # Setup warmup wrapper mock
        mock_wrapped_env = mock_warmup_wrapper.return_value
        mock_wrapped_env.reset.return_value = (mock_obs, {})
        mock_wrapped_env.step.return_value = (mock_obs, 0.0, True, False, {})

        # Call without explicit warmup parameters
        _ = evaluate(
            do_nothing_agent, worker_id=1, episodes_per_worker=1, flatten_obs=False
        )

        # Verify warmup wrapper was called with config values
        mock_warmup_wrapper.assert_called_once_with(
            ANY, warmup_steps=20, policy="random", verbose=False
        )
