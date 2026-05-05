"""Unit tests for environment factory in RL training environment."""

from unittest.mock import Mock, patch

from aiml_pyxis_investment_game.environment.env_factory import (  # noqa: E501
    _prepare_envs,
    _prepare_level_envs,
    make_train_env,
)


class TestPrepareEnvs:
    """
    Test suite for _prepare_envs function.

    _prepare_envs now reads all env params from the config singleton.
    We mock the config and only pass training-specific params.
    """

    @patch("aiml_pyxis_investment_game.environment.env_factory.VecNormalize")
    @patch("aiml_pyxis_investment_game.environment.env_factory.SubprocVecEnv")
    @patch("aiml_pyxis_investment_game.environment.env_factory.InvestmentGameEnv")
    def test__prepare_envs_basic_functionality(
        self,
        mock_investment_game_env,
        mock_subproc_vec_env,
        mock_vec_normalize,
    ):
        """Test basic functionality of _prepare_envs function."""
        mock_env_instance = Mock()
        mock_investment_game_env.return_value = mock_env_instance

        mock_train_vec_env = Mock()
        mock_eval_vec_env = Mock()
        mock_subproc_vec_env.side_effect = [mock_train_vec_env, mock_eval_vec_env]

        mock_normalized_train_env = Mock()
        mock_normalized_eval_env = Mock()
        mock_vec_normalize.side_effect = [
            mock_normalized_train_env,
            mock_normalized_eval_env,
        ]

        n_envs = 4
        norm_obs = True
        norm_reward = True

        train_env, eval_env = _prepare_envs(
            n_envs=n_envs,
            norm_obs=norm_obs,
            norm_reward=norm_reward,
        )

        assert mock_subproc_vec_env.call_count == 2
        train_env_fns = mock_subproc_vec_env.call_args_list[0][0][0]
        eval_env_fns = mock_subproc_vec_env.call_args_list[1][0][0]
        assert len(train_env_fns) == n_envs
        assert len(eval_env_fns) == n_envs

        assert mock_vec_normalize.call_count == 2
        mock_vec_normalize.assert_any_call(
            mock_train_vec_env, norm_obs=norm_obs, norm_reward=norm_reward
        )
        mock_vec_normalize.assert_any_call(
            mock_eval_vec_env, norm_obs=norm_obs, norm_reward=False, training=False
        )

        assert train_env == mock_normalized_train_env
        assert eval_env == mock_normalized_eval_env

    @patch("aiml_pyxis_investment_game.environment.env_factory.VecNormalize")
    @patch("aiml_pyxis_investment_game.environment.env_factory.SubprocVecEnv")
    @patch("aiml_pyxis_investment_game.environment.env_factory.InvestmentGameEnv")
    def test__prepare_envs_eval_env_never_normalizes_rewards(
        self,
        mock_investment_game_env,
        mock_subproc_vec_env,
        mock_vec_normalize,
    ):
        """Test that evaluation environment never normalizes rewards."""
        mock_investment_game_env.return_value = Mock()
        mock_subproc_vec_env.return_value = Mock()
        mock_vec_normalize.return_value = Mock()

        _prepare_envs(n_envs=2, norm_obs=True, norm_reward=True)

        eval_call = mock_vec_normalize.call_args_list[1]
        assert eval_call[1]["norm_reward"] is False
        assert eval_call[1]["training"] is False

        mock_vec_normalize.reset_mock()
        mock_subproc_vec_env.reset_mock()

        _prepare_envs(n_envs=2, norm_obs=False, norm_reward=False)

        eval_call = mock_vec_normalize.call_args_list[1]
        assert eval_call[1]["norm_reward"] is False
        assert eval_call[1]["training"] is False

    @patch("aiml_pyxis_investment_game.environment.env_factory.VecNormalize")
    @patch("aiml_pyxis_investment_game.environment.env_factory.SubprocVecEnv")
    @patch("aiml_pyxis_investment_game.environment.env_factory.InvestmentGameEnv")
    def test__prepare_envs_with_single_environment(
        self,
        mock_investment_game_env,
        mock_subproc_vec_env,
        mock_vec_normalize,
    ):
        """Test _prepare_envs with n_envs=1."""
        mock_investment_game_env.return_value = Mock()
        mock_subproc_vec_env.return_value = Mock()
        mock_vec_normalize.return_value = Mock()

        _prepare_envs(n_envs=1, norm_obs=True, norm_reward=True)

        train_env_fns = mock_subproc_vec_env.call_args_list[0][0][0]
        eval_env_fns = mock_subproc_vec_env.call_args_list[1][0][0]
        assert len(train_env_fns) == 1
        assert len(eval_env_fns) == 1

    @patch("aiml_pyxis_investment_game.environment.env_factory.VecNormalize")
    @patch("aiml_pyxis_investment_game.environment.env_factory.SubprocVecEnv")
    @patch("aiml_pyxis_investment_game.environment.env_factory.InvestmentGameEnv")
    def test__prepare_envs_with_multiple_environments(
        self,
        mock_investment_game_env,
        mock_subproc_vec_env,
        mock_vec_normalize,
    ):
        """Test _prepare_envs with multiple environments."""
        mock_investment_game_env.return_value = Mock()
        mock_subproc_vec_env.return_value = Mock()
        mock_vec_normalize.return_value = Mock()

        n_envs = 16
        _prepare_envs(n_envs=n_envs, norm_obs=True, norm_reward=True)

        train_env_fns = mock_subproc_vec_env.call_args_list[0][0][0]
        eval_env_fns = mock_subproc_vec_env.call_args_list[1][0][0]
        assert len(train_env_fns) == n_envs
        assert len(eval_env_fns) == n_envs

    @patch("aiml_pyxis_investment_game.environment.env_factory.VecNormalize")
    @patch("aiml_pyxis_investment_game.environment.env_factory.SubprocVecEnv")
    @patch("aiml_pyxis_investment_game.environment.env_factory.InvestmentGameEnv")
    def test__prepare_envs_returns_correct_types(
        self,
        mock_investment_game_env,
        mock_subproc_vec_env,
        mock_vec_normalize,
    ):
        """Test that _prepare_envs returns the correct types."""
        mock_investment_game_env.return_value = Mock()
        mock_subproc_vec_env.return_value = Mock()

        mock_normalized_train_env = Mock()
        mock_normalized_eval_env = Mock()
        mock_vec_normalize.side_effect = [
            mock_normalized_train_env,
            mock_normalized_eval_env,
        ]

        train_env, eval_env = _prepare_envs(
            n_envs=2, norm_obs=True, norm_reward=True
        )

        assert train_env == mock_normalized_train_env
        assert eval_env == mock_normalized_eval_env


class TestPrepareLevelEnvs:
    """Test suite for _prepare_level_envs function."""

    @patch("aiml_pyxis_investment_game.environment.env_factory.VecNormalize")
    @patch("aiml_pyxis_investment_game.environment.env_factory.SubprocVecEnv")
    @patch("aiml_pyxis_investment_game.environment.env_factory.LevelsInvestmentGameEnv")
    def test__prepare_level_envs_basic_functionality(
        self,
        mock_levels_env,
        mock_subproc_vec_env,
        mock_vec_normalize,
    ):
        """Test basic functionality of _prepare_level_envs function."""
        mock_env_instance = Mock()
        mock_levels_env.return_value = mock_env_instance

        mock_train_vec_env = Mock()
        mock_subproc_vec_env.return_value = mock_train_vec_env

        mock_normalized_train_env = Mock()
        mock_vec_normalize.return_value = mock_normalized_train_env

        level_idx = 2
        reward_fn = Mock()
        n_envs = 3
        norm_obs = True
        norm_reward = True
        shuffle_order = False

        train_env = _prepare_level_envs(
            level_idx=level_idx,
            reward_fn=reward_fn,
            n_envs=n_envs,
            norm_obs=norm_obs,
            norm_reward=norm_reward,
            shuffle_order=shuffle_order,
            flatten_obs=False,
            warmup_on_reset_steps=0,
            warmup_on_reset_policy="do_nothing",
        )

        assert mock_subproc_vec_env.call_count == 1
        train_env_fns = mock_subproc_vec_env.call_args_list[0][0][0]
        assert len(train_env_fns) == n_envs

        assert mock_vec_normalize.call_count == 1
        mock_vec_normalize.assert_called_once_with(
            mock_train_vec_env, norm_obs=norm_obs, norm_reward=norm_reward
        )

        assert train_env == mock_normalized_train_env

        # Check LevelsInvestmentGameEnv calls for train envs
        for fn in train_env_fns:
            fn()
        mock_levels_env.assert_any_call(
            level_idx=level_idx,
            reward_fn=reward_fn,
            shuffle_order=shuffle_order,
            flatten_obs=False,
            uncertain_ptrs_config=None,
            investment_levels_config=None,
            interim_trial_observations_config=None,
            distributional_ptrs_config=None,
        )


def test_make_train_env():
    """Test that make_train_env calls InvestmentGameEnv correctly."""
    with (
        patch(
            "aiml_pyxis_investment_game.environment.env_factory.InvestmentGameEnv"
        ) as mock_investment_game_env,
        patch(
            "aiml_pyxis_investment_game.environment.env_factory.WarmupOnResetWrapper"
        ) as mock_warmup_wrapper,
        patch(
            "aiml_pyxis_investment_game.environment.env_factory.AutoCenterWrapper"
        ) as mock_autocenter_wrapper,
    ):
        mock_env_instance = Mock()
        mock_investment_game_env.return_value = mock_env_instance
        mock_autocenter_wrapper.return_value = mock_env_instance
        mock_warmup_wrapper.return_value = mock_env_instance

        result = make_train_env(flatten_obs=True)

        mock_investment_game_env.assert_called_once()
        assert result in [mock_investment_game_env(), mock_autocenter_wrapper(), mock_warmup_wrapper()]
