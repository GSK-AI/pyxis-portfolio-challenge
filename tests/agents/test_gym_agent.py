import pickle
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from aiml_pyxis_investment_game.agents.pyxie import (
    InferenceNormalizer,
    PyxieAgent,
)


class MockObsRMS:
    """Mock object mimicking Stable Baselines 3 RunningMeanStd."""

    def __init__(self, mean, var):
        self.mean = np.array(mean, dtype=np.float32)
        self.var = np.array(var, dtype=np.float32)


class MockVecNormalizeData:
    """Mock object mimicking the pickled VecNormalize object."""

    def __init__(self, mean, var, clip_obs=10.0):
        self.obs_rms = MockObsRMS(mean, var)
        self.clip_obs = clip_obs


@pytest.fixture
def dummy_vecnorm_path(tmp_path):
    """Creates a temporary pickle file with known statistics."""
    # Mean = 10, Var = 4 (std = 2)
    data = MockVecNormalizeData(mean=[10.0, 10.0], var=[4.0, 4.0],
                                clip_obs=5.0)

    file_path = tmp_path / "vecnormalize.pkl"
    with open(file_path, "wb") as f:
        pickle.dump(data, f)

    return str(file_path)


@pytest.fixture
def mock_env():
    """Creates a mock environment with the expected interface."""
    env = MagicMock()
    # Mock the nested structure: env.unwrapped.action_masks()
    env.unwrapped.action_masks.return_value = [True, False, True]
    return env


@pytest.fixture
def mock_algorithm():
    """Mocks the SB3 algorithm class (e.g. MaskablePPO)."""
    algo = MagicMock()
    model = MagicMock()
    # Setup the model to return a dummy action
    model.predict.return_value = (np.array([1, 0, 1]), None)
    algo.load.return_value = model
    return algo


# --- Tests for InferenceNormalizer ---

def test_inference_normalizer_loads_correctly(dummy_vecnorm_path):
    """Test that the normalizer loads stats from disk."""
    normalizer = InferenceNormalizer(dummy_vecnorm_path)

    assert np.allclose(normalizer.obs_rms.mean, [10.0, 10.0])
    assert np.allclose(normalizer.obs_rms.var, [4.0, 4.0])
    assert normalizer.clip_obs == 5.0


def test_inference_normalizer_math(dummy_vecnorm_path):
    """
    Test the normalization formula: (x - mean) / sqrt(var + epsilon)
    """
    normalizer = InferenceNormalizer(dummy_vecnorm_path)

    # Input: 14.0
    # Mean: 10.0
    # Var: 4.0 -> Sqrt(4) = 2.0
    # Expected: (14 - 10) / 2 = 2.0

    obs = np.array([14.0, 14.0])
    normalized = normalizer.normalize(obs)

    expected = np.array([2.0, 2.0])
    assert np.allclose(normalized, expected, atol=1e-5)


def test_inference_normalizer_clipping(dummy_vecnorm_path):
    """Test that observations are clipped based on the loaded clip_obs value."""
    normalizer = InferenceNormalizer(dummy_vecnorm_path)
    # The fixture sets clip_obs to 5.0

    # Generate a value that would result in 100.0 (way above 5.0)
    # (210 - 10) / 2 = 100
    huge_obs = np.array([210.0, -210.0])

    normalized = normalizer.normalize(huge_obs)

    # Should be clipped to [5.0, -5.0]
    assert np.allclose(normalized, [5.0, -5.0])


# --- Tests for PyxieAgent ---

@patch("aiml_pyxis_investment_game.agents.pyxie.download_file")
def test_pyxie_agent_initialization(mock_download, mock_algorithm,
                                    dummy_vecnorm_path):
    """Test that the agent initializes the model and normalizer."""
    # Setup mock to just return the path passed to it
    mock_download.side_effect = lambda x: str(x)

    agent = PyxieAgent(
        algorithm=mock_algorithm,
        model_path="dummy/model.zip",
        vecnorm_path=dummy_vecnorm_path
    )

    # Verify download_file was called
    assert mock_download.call_count == 2

    # Verify model was loaded via the algorithm class
    mock_algorithm.load.assert_called_once_with("dummy/model.zip")

    # Verify normalizer is instantiated
    assert isinstance(agent.normalizer, InferenceNormalizer)
    assert np.allclose(agent.normalizer.obs_rms.mean, [10.0, 10.0])


@patch("aiml_pyxis_investment_game.agents.pyxie.download_file")
def test_pyxie_agent_call_flow(
        mock_download,
        mock_algorithm,
        dummy_vecnorm_path,
        mock_env
):
    """
    Test the full __call__ lifecycle:
    Normalize Obs -> Get Mask -> Predict -> Return Action
    """
    mock_download.side_effect = lambda x: str(x)

    agent = PyxieAgent(
        algorithm=mock_algorithm,
        model_path="dummy/model.zip",
        vecnorm_path=dummy_vecnorm_path
    )

    agent.set_env(mock_env)

    # Input observation
    raw_obs = np.array([14.0, 14.0])  # Should normalize to [2.0, 2.0]

    # ACT
    action = agent(raw_obs)

    # ASSERT

    # 1. Check if the environment mask was accessed
    mock_env.unwrapped.action_masks.assert_called_once()

    # 2. Check if model.predict was called with the NORMALIZED obs
    # Retrieve arguments passed to predict
    call_args = agent.model.predict.call_args
    passed_obs = call_args[0][0]  # First arg
    passed_kwargs = call_args[1]

    # Expect normalized values (approx 2.0)
    assert np.allclose(passed_obs, [2.0, 2.0], atol=1e-5)

    # Expect deterministic=True
    assert passed_kwargs['deterministic'] is True

    # Expect the mask from the env
    assert passed_kwargs['action_masks'] == [True, False, True]

    # 3. Check return value
    assert np.array_equal(action, np.array([1, 0, 1]))
