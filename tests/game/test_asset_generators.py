import json
import random
import uuid
from itertools import combinations

import pytest
import upath

from pyxis_portfolio_challenge import PROJECT_ROOT
from pyxis_portfolio_challenge.game.asset import DrugAsset
from pyxis_portfolio_challenge.game.asset_generators import (
    DUMMY_LIST_DATA,
    FixedListAssetGenerator,
    JSONAssetGenerator,
    generate_asset_id,
)
from pyxis_portfolio_challenge.rng import init_game_rng


def test_generate_asset_id():
    # Test with valid input
    asset_id = generate_asset_id(42, 1)
    assert isinstance(asset_id, uuid.UUID)

    # Test with different inputs
    asset_id_2 = generate_asset_id(42, 2)
    assert asset_id != asset_id_2


# Tests for FixedListAssetGenerator


@pytest.mark.parametrize(
    "global_seed,data_list,should_raise",
    [
        (42, DUMMY_LIST_DATA, False),
        (42, "invalid_data", True),
        ("invalid_seed", DUMMY_LIST_DATA, True),
        (None, DUMMY_LIST_DATA, True),
    ],
)
def test_fixed_list_asset_generator_init(global_seed, data_list, should_raise):
    if should_raise:
        with pytest.raises(TypeError):
            FixedListAssetGenerator(global_seed, data_list)
    else:
        generator = FixedListAssetGenerator(global_seed, data_list)
        assert generator.global_seed == global_seed
        assert generator.assets_data_list == data_list


def test_fixed_list_asset_generator_call():
    init_game_rng(42)
    generator = FixedListAssetGenerator(42, DUMMY_LIST_DATA)
    assets = generator(5, "initial")
    assert len(assets) == 5
    for asset in assets.values():
        assert isinstance(asset, DrugAsset)

    new_assets = generator(1, "new")
    assert len(new_assets) == 1
    for asset in new_assets.values():
        assert isinstance(asset, DrugAsset)
        assert asset.id not in assets

    with pytest.raises(ValueError):
        generator(0, "new")
    with pytest.raises(ValueError):
        generator(-1, "new")


def test_fixed_list_asset_generator_reproducibility():
    seed0 = 42
    seed1 = 1337
    generator1 = FixedListAssetGenerator(seed0, DUMMY_LIST_DATA)
    generator2 = FixedListAssetGenerator(seed0, DUMMY_LIST_DATA)
    generator3 = FixedListAssetGenerator(seed1, DUMMY_LIST_DATA)

    init_game_rng(seed0)
    assets1 = generator1(5, "initial")
    init_game_rng(seed0)
    assets2 = generator2(5, "initial")
    init_game_rng(seed1)
    assets3 = generator3(5, "initial")

    assert assets1.keys() == assets2.keys()
    for asset_id in assets1:
        assert assets1[asset_id] == assets2[asset_id]

    assert assets1.keys() != assets3.keys()

    init_game_rng(seed0)
    new_assets1 = generator1(1, "new")
    init_game_rng(seed0)
    new_assets2 = generator2(1, "new")
    init_game_rng(seed1)
    new_assets3 = generator3(1, "new")

    assert new_assets1.keys() == new_assets2.keys()
    for asset_id in new_assets1:
        assert new_assets1[asset_id] == new_assets2[asset_id]

    assert new_assets1.keys() != new_assets3.keys()


# Tests for JSONAssetGenerator


valid_path = PROJECT_ROOT / "tests" / "data" / "generated_assets"

# Default required params for JSONAssetGenerator in tests
_TEST_SPREAD = 1.5
_TEST_DRIFT = 1.0
_TEST_COST_MULT = 1.0


def _make_generator(seed, path=None, **kwargs):
    """Helper to create JSONAssetGenerator with test defaults for required params."""
    init_game_rng(seed)
    if path is None:
        path = valid_path
    kwargs.setdefault("indication_spread", _TEST_SPREAD)
    kwargs.setdefault("indication_drift_speed", _TEST_DRIFT)
    kwargs.setdefault("trial_cost_multiplier", _TEST_COST_MULT)
    return JSONAssetGenerator(seed, path, **kwargs)


@pytest.mark.parametrize(
    "global_seed,should_raise",
    [
        (42, False),
        ("invalid_seed", True),
        (None, True),
    ],
)
def test_json_asset_generator_init_seed(global_seed, should_raise):
    assets_dir = valid_path
    if should_raise:
        with pytest.raises(TypeError):
            _make_generator(global_seed, assets_dir)
    else:
        generator = _make_generator(global_seed, assets_dir)
        assert generator.global_seed == global_seed
        assert generator.assets_dir == assets_dir


@pytest.mark.parametrize(
    "assets_dir,raises",
    [
        (valid_path, None),
        (upath.UPath("invalid/path"), FileNotFoundError),
        (None, TypeError),
    ],
)
def test_json_asset_generator_init_assets_dir(assets_dir, raises):
    global_seed = 42
    if raises is not None:
        with pytest.raises(raises):
            JSONAssetGenerator(
                global_seed, assets_dir,
                indication_spread=_TEST_SPREAD,
                indication_drift_speed=_TEST_DRIFT,
                trial_cost_multiplier=_TEST_COST_MULT,
            )
    else:
        generator = _make_generator(global_seed, assets_dir)
        assert generator.global_seed == global_seed
        assert generator.assets_dir == assets_dir


def test_json_asset_generator_parse_on_market_asset(tmp_path):
    # Arrange: create a fake asset file structure
    assets_dir = upath.UPath(tmp_path / "assets")
    stage_initial_dir = upath.UPath(assets_dir / "initial")
    stage_new_dir = upath.UPath(assets_dir / "new")

    stage_initial_dir.mkdir(parents=True)
    stage_new_dir.mkdir(parents=True)
    asset_initial_path = stage_initial_dir / "asset_0.json"
    asset_initial_json = {
        "name": "CystiClear",
        "therapeutic_area": "respiratory and immunology",
        "type": "BD",
        "description": "...",
        "max_revenue": 2200000000,
        "time_until_max_revenue": 6,
        "time_until_patent_expiry": 14,
        "trials": {
            "pre_clinical": {"cost_remaining": 0, "time_remaining": 0, "ptrs": 1.0},
            "phase_1": {"cost_remaining": 0, "time_remaining": 0, "ptrs": 1.0},
            "phase_2": {"cost_remaining": 0, "time_remaining": 0, "ptrs": 1.0},
            "phase_3": {"cost_remaining": 0, "time_remaining": 0, "ptrs": 1.0},
            "registration": {"cost_remaining": 0, "time_remaining": 0, "ptrs": 1.0},
        },
        "state": "On Market",
        "pending_trial_phase": None,
        "time_on_market": 6,
    }
    with open(asset_initial_path, "w") as f:
        json.dump(asset_initial_json, f)

    asset_new_path = stage_new_dir / "asset_0.json"
    asset_new_json = {
        "name": "BronchoMax",
        "therapeutic_area": "respiratory and immunology",
        "type": "BD",
        "description": "...",
        "max_revenue": 1200000000,
        "time_until_max_revenue": 4,
        "time_until_patent_expiry": 12,
        "trials": {
            "pre_clinical": {"cost_remaining": 0, "time_remaining": 0, "ptrs": 1.0},
            "phase_1": {"cost_remaining": 0, "time_remaining": 0, "ptrs": 1.0},
            "phase_2": {"cost_remaining": 0, "time_remaining": 0, "ptrs": 1.0},
            "phase_3": {"cost_remaining": 0, "time_remaining": 0, "ptrs": 1.0},
            "registration": {"cost_remaining": 0, "time_remaining": 0, "ptrs": 1.0},
        },
        "state": "On Market",
        "pending_trial_phase": None,
        "time_on_market": 6,
    }
    with open(asset_new_path, "w") as f:
        json.dump(asset_new_json, f)

    # Act: instantiate and call the generator
    generator = _make_generator(42, assets_dir)
    assets_initial = generator(1, "initial")

    # Assert: check the loaded asset initial
    assert len(assets_initial) == 1
    asset_initial = list(assets_initial.values())[0]
    assert asset_initial.name == "CystiClear"
    assert asset_initial.state == "On Market"

    assets_new = generator(1, "new")

    # Assert: check the loaded asset new
    assert len(assets_new) == 1
    asset_new = list(assets_new.values())[0]
    assert asset_new.name == "BronchoMax"
    assert asset_new.state == "On Market"


def lists_equal_unordered(list1: list[dict], list2: list[dict]) -> bool:
    """Check if two lists of dicts have same elements, ignoring order."""
    if len(list1) != len(list2):
        return False

    # Sort by JSON representation
    sorted1 = sorted(list1, key=lambda d: json.dumps(d, sort_keys=True))
    sorted2 = sorted(list2, key=lambda d: json.dumps(d, sort_keys=True))

    return sorted1 == sorted2


@pytest.mark.parametrize("stage", ["initial", "new"])
def test_json_asset_generator__reset_available_assets(stage):
    generator = _make_generator(42)
    assert lists_equal_unordered(
        generator._all_assets[stage], generator.available_assets[stage]
    )

    # generate one asset to reduce available assets
    generator(1, stage)
    assert (
        len(generator.available_assets[stage]) == len(generator._all_assets[stage]) - 1
    )
    assert not lists_equal_unordered(
        generator._all_assets[stage], generator.available_assets[stage]
    )

    # reset available assets and check they match all assets again
    generator._reset_available_assets(stage)
    assert lists_equal_unordered(
        generator._all_assets[stage], generator.available_assets[stage]
    )


def test_json_asset_generator__generate_single_asset():
    generator = _make_generator(42)
    num_initial_assets = len(generator.available_assets["initial"])
    asset = generator._generate_single_asset("initial")
    assert isinstance(asset, DrugAsset)
    assert generator.asset_count == 1
    assert len(generator.available_assets["initial"]) == num_initial_assets - 1

    num_new_assets = len(generator.available_assets["new"])
    asset_new = generator._generate_single_asset("new")
    assert isinstance(asset_new, DrugAsset)

    assert asset.id != asset_new.id
    assert generator.asset_count == 2
    assert len(generator.available_assets["new"]) == num_new_assets - 1


def test_json_asset_generator_call():
    generator = _make_generator(42)
    assets = generator(5, "initial")
    assert len(assets) == 5
    for asset in assets.values():
        assert isinstance(asset, DrugAsset)

    new_assets = generator(1, "new")
    assert len(new_assets) == 1
    for asset in new_assets.values():
        assert isinstance(asset, DrugAsset)
        assert asset.id not in assets

    with pytest.raises(ValueError):
        generator(0, "new")
    with pytest.raises(ValueError):
        generator(-1, "new")


def test_json_asset_generator_call_reuse():
    generator = _make_generator(42)
    num_saved_assets = len(generator._all_assets["initial"])

    assets_0 = generator(3, "initial")
    assets_1 = generator(num_saved_assets, "initial")

    assert len(assets_0) == 3
    assert len(assets_1) == num_saved_assets

    combined_assets = {**assets_0, **assets_1}
    combined_assets_list = list(combined_assets.values())

    count = 0
    for i, j in combinations(range(len(combined_assets_list)), 2):
        if combined_assets_list[i] == combined_assets_list[j]:
            count += 1
    assert count == 3


def test_json_asset_generator_call_too_many():
    generator = _make_generator(42)

    with pytest.raises(ValueError):
        num_saved_assets_initial = len(generator._all_assets["initial"])
        generator(num_saved_assets_initial + 1, "initial")

    with pytest.raises(ValueError):
        num_saved_assets_new = len(generator._all_assets["new"])
        generator(num_saved_assets_new + 1, "new")


def test_file_not_found_error():
    with pytest.raises(FileNotFoundError):
        generator = _make_generator(42, valid_path / "invalid")
        generator(num_assets=1, stage="initial")


def test_json_asset_generator_reproducibility():
    for _ in range(100):
        # Generate seed0 and seed1 randomly
        seed0 = random.randint(0, 2**32 - 1)
        seed1 = random.randint(0, 2**32 - 1)
        generator1 = _make_generator(seed0)
        generator2 = _make_generator(seed0)
        generator3 = _make_generator(seed1)

        assets1 = generator1(5, "initial")
        assets2 = generator2(5, "initial")
        assets3 = generator3(5, "initial")

        assert assets1.keys() == assets2.keys()
        assert list(assets1.values()) == list(assets2.values())

        assert assets1.keys() != assets3.keys()
        assert list(assets1.values()) != list(assets3.values())

        new_assets1 = generator1(1, "new")
        new_assets2 = generator2(1, "new")
        new_assets3 = generator3(1, "new")

        assert new_assets1.keys() == new_assets2.keys()
        assert list(new_assets1.values()) == list(new_assets2.values())

        assert assets1.keys() != new_assets3.keys()
        assert list(assets1.values()) != list(new_assets3.values())


class TestIndicationDrift:
    """Test that _sample_indication drifts over episode progress."""

    def _make_generator(self, seed=42):
        return _make_generator(seed)

    def _sample_many(self, gen, num_indications, progress, n=1000, ta=""):
        """Sample n indications at a given progress and return counts."""
        gen._current_episode_progress = progress
        counts = [0] * num_indications
        for _ in range(n):
            idx = gen._sample_indication(num_indications, ta)
            counts[idx] += 1
        return counts

    def test_no_drift_without_progress(self):
        """Without episode_progress, sampling is uniform."""
        gen = self._make_generator()
        gen._current_episode_progress = None
        counts = self._sample_many(gen, 5, None, n=2000)
        # All indications should get roughly equal samples
        for c in counts:
            assert c > 100, f"Expected uniform but got {counts}"

    def test_drift_early_favours_low_indices(self):
        """At progress=0, indication 0 should be most frequent."""
        gen = self._make_generator()
        counts = self._sample_many(gen, 5, progress=0.0)
        assert counts[0] > counts[-1], (
            f"Early episode should favour low indices: {counts}"
        )

    def test_drift_late_favours_high_indices(self):
        """Near end of episode, the last indication should be most frequent."""
        gen = self._make_generator()
        # Use 0.99 instead of 1.0 because (1.0 * drift_speed) % 1.0 = 0.0 wraps
        counts = self._sample_many(gen, 5, progress=0.99)
        assert counts[-1] > counts[0], (
            f"Late episode should favour high indices: {counts}"
        )

    def test_drift_mid_favours_middle(self):
        """At progress=0.5, middle indications should dominate."""
        gen = self._make_generator()
        counts = self._sample_many(gen, 6, progress=0.5)
        middle = counts[2] + counts[3]
        edges = counts[0] + counts[-1]
        assert middle > edges, (
            f"Mid episode should favour middle: {counts}"
        )

    def test_drift_with_two_indications(self):
        """With 2 indications, drift should still apply."""
        gen = self._make_generator()
        early = self._sample_many(gen, 2, progress=0.0, n=2000)
        late = self._sample_many(gen, 2, progress=0.99, n=2000)
        # Early should favour 0, late should favour 1
        assert early[0] > early[1], (
            f"Early should favour ind 0: {early}"
        )
        assert late[1] > late[0], (
            f"Late should favour ind 1: {late}"
        )

    def test_distribution_shifts_over_time(self):
        """Mean sampled indication should increase with progress."""
        gen = self._make_generator()
        num_ind = 8
        means = []
        for progress in [0.0, 0.25, 0.5, 0.75, 0.99]:
            counts = self._sample_many(gen, num_ind, progress, n=2000)
            mean = sum(i * c for i, c in enumerate(counts)) / sum(counts)
            means.append(mean)
        # Means should be monotonically increasing
        for i in range(len(means) - 1):
            assert means[i] < means[i + 1], (
                f"Mean should increase: {means}"
            )

    def test_permutation_scrambles_output(self):
        """With a permutation, the drift maps through shuffled indices."""
        ta = "oncology"
        num_ind = 5
        # Reversed permutation: drift-order 0→4, 1→3, 2→2, 3→1, 4→0
        perm = {ta: [4, 3, 2, 1, 0]}

        gen = self._make_generator()
        gen.set_indication_permutation(perm)

        # At progress=0, drift favours raw index 0, which maps to 4
        early = self._sample_many(
            gen, num_ind, progress=0.0, n=2000, ta=ta
        )
        assert early[4] > early[0], (
            f"Reversed perm: early should favour obs 4: {early}"
        )

        # At progress≈1, drift favours raw index 4, which maps to 0
        late = self._sample_many(
            gen, num_ind, progress=0.99, n=2000, ta=ta
        )
        assert late[0] > late[4], (
            f"Reversed perm: late should favour obs 0: {late}"
        )

    def test_permutation_varies_across_episodes(self):
        """Different permutations produce different distributions."""
        ta = "oncology"
        num_ind = 5

        gen1 = self._make_generator(seed=42)
        gen1.set_indication_permutation({ta: [0, 1, 2, 3, 4]})
        counts_identity = self._sample_many(
            gen1, num_ind, progress=0.0, n=2000, ta=ta
        )

        gen2 = self._make_generator(seed=42)
        gen2.set_indication_permutation({ta: [4, 3, 2, 1, 0]})
        counts_reversed = self._sample_many(
            gen2, num_ind, progress=0.0, n=2000, ta=ta
        )

        # With identity, peak is at index 0; with reversed, peak at 4
        peak_identity = counts_identity.index(max(counts_identity))
        peak_reversed = counts_reversed.index(max(counts_reversed))
        assert peak_identity != peak_reversed, (
            f"Different perms should shift peak: "
            f"identity peak={peak_identity}, reversed peak={peak_reversed}"
        )
