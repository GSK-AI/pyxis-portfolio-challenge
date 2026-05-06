from pyxis_portfolio_challenge import PROJECT_ROOT, config


def test_config_loading():
    cfg = config.from_yaml()
    assert cfg.equilibrium_num_assets > 0
    assert cfg.max_num_assets >= cfg.equilibrium_num_assets
    assert cfg.starting_cash > 0
    assert cfg.horizon > 0
    assert isinstance(cfg.shuffle_order, bool)
    assert "_target_" in cfg.reward_fn
    assert cfg.training_data_dir and cfg.evaluation_data_dir != ""


def test_from_yaml_default_arg_loads_correct_file():
    default_path = f"{PROJECT_ROOT}/pyxis_portfolio_challenge/config.yaml"
    cfg1 = config.from_yaml()
    cfg2 = config.from_yaml(path=default_path)
    assert cfg1 == cfg2


def test_instantiate_from_config_args():
    sample_config = {
        "_target_": "builtins.list",
        "": [1, 2, 3],
    }
    instantiated_obj = config.instantiate_from_config(sample_config)
    assert isinstance(instantiated_obj, list)
    assert instantiated_obj == [1, 2, 3]


def test_instantiate_from_config_kwargs():
    sample_config = {
        "_target_": "collections.Counter",
        "a": 2,
        "b": 3,
    }
    instantiated_obj = config.instantiate_from_config(sample_config)
    from collections import Counter

    assert isinstance(instantiated_obj, Counter)
    assert instantiated_obj == Counter(a=2, b=3)


def test_instantiate_from_config_mixed():
    sample_config = {
        "_target_": "collections.defaultdict",
        "": int,
        "a": 5,
    }
    instantiated_obj = config.instantiate_from_config(sample_config)
    from collections import defaultdict

    assert isinstance(instantiated_obj, defaultdict)
    assert instantiated_obj["a"] == 5
    assert instantiated_obj["b"] == 0  # default factory is int
