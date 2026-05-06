"""Unit tests for custom callbacks in RL training environment."""

from unittest.mock import Mock

from stable_baselines3.common.callbacks import BaseCallback

from pyxis_portfolio_challenge.environment.custom_callbacks import (  # noqa: E501
    VecNormSyncCallback,
)


class TestVecNormSyncCallback:
    """Test suite for VecNormSyncCallback class."""

    def test_init_with_train_and_eval_envs(self):
        """Test VecNormSyncCallback initializes correctly."""
        # Create mock environments
        mock_train_env = Mock()
        mock_eval_env = Mock()

        # Initialize callback
        callback = VecNormSyncCallback(train_env=mock_train_env, eval_env=mock_eval_env)

        # Verify initialization
        assert callback.train_env is mock_train_env
        assert callback.eval_env is mock_eval_env

    def test_init_calls_super_init(self):
        """Test that VecNormSyncCallback calls BaseCallback.__init__()."""
        # Create mock environments
        mock_train_env = Mock()
        mock_eval_env = Mock()

        # Initialize callback
        callback = VecNormSyncCallback(train_env=mock_train_env, eval_env=mock_eval_env)

        # Verify that it has attributes from BaseCallback
        # BaseCallback.__init__() sets these attributes
        assert hasattr(callback, "n_calls")
        assert hasattr(callback, "num_timesteps")
        assert hasattr(callback, "locals")
        assert hasattr(callback, "globals")

    def test_inherits_from_base_callback(self):
        """Test that VecNormSyncCallback inherits from BaseCallback."""
        # Create mock environments
        mock_train_env = Mock()
        mock_eval_env = Mock()

        # Initialize callback
        callback = VecNormSyncCallback(train_env=mock_train_env, eval_env=mock_eval_env)

        # Verify inheritance
        assert isinstance(callback, BaseCallback)
        assert issubclass(VecNormSyncCallback, BaseCallback)

    def test_on_step_copies_obs_rms_from_train_to_eval(self):
        """Test that _on_step() copies obs_rms from train_env to eval_env."""
        # Create mock environments with obs_rms attributes
        mock_train_env = Mock()
        mock_eval_env = Mock()

        # Create a mock obs_rms object to be copied
        mock_obs_rms = Mock()
        mock_train_env.obs_rms = mock_obs_rms

        # Initialize callback
        callback = VecNormSyncCallback(train_env=mock_train_env, eval_env=mock_eval_env)

        # Call _on_step
        _ = callback._on_step()

        # Verify that obs_rms was copied from train_env to eval_env
        assert mock_eval_env.obs_rms is mock_obs_rms
        assert mock_eval_env.obs_rms is mock_train_env.obs_rms

    def test_on_step_returns_true(self):
        """Test that _on_step() returns True."""
        # Create mock environments
        mock_train_env = Mock()
        mock_eval_env = Mock()
        mock_train_env.obs_rms = Mock()

        # Initialize callback
        callback = VecNormSyncCallback(train_env=mock_train_env, eval_env=mock_eval_env)

        # Call _on_step and verify return value
        result = callback._on_step()
        assert result is True

    def test_on_step_with_none_obs_rms(self):
        """Test that _on_step() handles None obs_rms correctly."""
        # Create mock environments
        mock_train_env = Mock()
        mock_eval_env = Mock()
        mock_train_env.obs_rms = None

        # Initialize callback
        callback = VecNormSyncCallback(train_env=mock_train_env, eval_env=mock_eval_env)

        # Call _on_step
        result = callback._on_step()

        # Verify that None was copied to eval_env
        assert mock_eval_env.obs_rms is None
        assert result is True

    def test_on_step_with_different_obs_rms_objects(self):
        """Test that _on_step() overwrites eval_env.obs_rms with train_env.obs_rms."""
        # Create mock environments with different obs_rms
        mock_train_env = Mock()
        mock_eval_env = Mock()

        train_obs_rms = Mock(name="train_obs_rms")
        eval_obs_rms = Mock(name="eval_obs_rms")

        mock_train_env.obs_rms = train_obs_rms
        mock_eval_env.obs_rms = eval_obs_rms

        # Initialize callback
        callback = VecNormSyncCallback(train_env=mock_train_env, eval_env=mock_eval_env)

        # Verify initial state
        assert mock_eval_env.obs_rms is eval_obs_rms
        assert mock_train_env.obs_rms is train_obs_rms

        # Call _on_step
        result = callback._on_step()

        # Verify that eval_env.obs_rms was overwritten with train_env.obs_rms
        assert mock_eval_env.obs_rms is train_obs_rms
        assert mock_eval_env.obs_rms is not eval_obs_rms
        assert result is True

    def test_multiple_on_step_calls(self):
        """Test that multiple calls to _on_step() continue to sync obs_rms correctly."""
        # Create mock environments
        mock_train_env = Mock()
        mock_eval_env = Mock()

        # Initialize callback
        callback = VecNormSyncCallback(train_env=mock_train_env, eval_env=mock_eval_env)

        # Create different obs_rms objects for multiple steps
        obs_rms_1 = Mock(name="obs_rms_1")
        obs_rms_2 = Mock(name="obs_rms_2")

        # First step
        mock_train_env.obs_rms = obs_rms_1
        result1 = callback._on_step()
        assert mock_eval_env.obs_rms is obs_rms_1
        assert result1 is True

        # Second step with different obs_rms
        mock_train_env.obs_rms = obs_rms_2
        result2 = callback._on_step()
        assert mock_eval_env.obs_rms is obs_rms_2
        assert result2 is True

    def test_init_with_positional_arguments(self):
        """Test VecNormSyncCallback can be initialized with positional arguments."""
        # Create mock environments
        mock_train_env = Mock()
        mock_eval_env = Mock()

        # Initialize callback with positional arguments
        callback = VecNormSyncCallback(mock_train_env, mock_eval_env)

        # Verify initialization
        assert callback.train_env is mock_train_env
        assert callback.eval_env is mock_eval_env

    def test_callback_has_required_methods(self):
        """Test that VecNormSyncCallback has the required callback methods."""
        # Create mock environments
        mock_train_env = Mock()
        mock_eval_env = Mock()

        # Initialize callback
        callback = VecNormSyncCallback(train_env=mock_train_env, eval_env=mock_eval_env)

        # Verify that callback has the required _on_step method
        assert hasattr(callback, "_on_step")
        assert callable(callback._on_step)

        # Verify that it inherits other callback methods from BaseCallback
        assert hasattr(callback, "_on_training_start")
        assert hasattr(callback, "_on_rollout_start")
        assert hasattr(callback, "_on_rollout_end")
        assert hasattr(callback, "_on_training_end")
