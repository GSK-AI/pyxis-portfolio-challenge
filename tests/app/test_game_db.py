import uuid
from datetime import datetime, timedelta

import pytest

from app.game_db import (
    GameMetricsData,
    create_game_analytics_db,
    get_global_leaderboard_data,
    get_level_id_of_game_id,
    get_level_leaderboard_data,
    get_user_game_metrics,
    get_user_level_metrics,
    has_user_completed_level,
    insert_game_metrics,
)


@pytest.fixture(scope="function")
def db(monkeypatch, tmp_path):
    db_file = tmp_path / "game_metrics.sqlite"
    monkeypatch.setenv("TESTING", "1")
    monkeypatch.setenv("PORTFOLIO_DB_PATH", str(db_file))
    create_game_analytics_db(overwrite=True)
    yield


@pytest.fixture
def sample_data(db):
    test_user = "test_user"
    game_id_1 = str(uuid.uuid4())
    game_id_2 = str(uuid.uuid4())
    game_id_3 = str(uuid.uuid4())

    rows = [
        GameMetricsData(
            user_id=test_user,
            level_id=1,
            game_id=game_id_1,
            final_enpv=10.0,
            final_eroi=0.12,
            realised_roi=0.1,
            final_capital=1000.0,
            eroi_over_time=[0.0, 1000.0],
            enpv_over_time=[0, 10.0],
            av_enpv=5.0,
            timestamp=datetime.now(),
        ),
        GameMetricsData(
            user_id=test_user,
            level_id=1,
            game_id=game_id_2,
            final_enpv=0.0,
            final_eroi=0.08,
            realised_roi=0.07,
            final_capital=5000.0,
            eroi_over_time=[0.0, 5000.0],
            enpv_over_time=[0, 0.0],
            av_enpv=0.0,
            timestamp=datetime.now(),
        ),
        GameMetricsData(
            user_id=test_user,
            level_id=2,
            game_id=game_id_3,
            final_enpv=20.0,
            final_eroi=0.15,
            realised_roi=0.14,
            final_capital=2000.0,
            eroi_over_time=[0.0, 2000.0],
            enpv_over_time=[0, 20.0],
            av_enpv=10.0,
            timestamp=datetime.now(),
        ),
        GameMetricsData(
            user_id="another_user",
            level_id=1,
            game_id=str(uuid.uuid4()),
            final_enpv=5.0,
            final_eroi=0.10,
            realised_roi=0.09,
            final_capital=3000.0,
            eroi_over_time=[0.0, 3000.0],
            enpv_over_time=[0, 5.0],
            av_enpv=2.5,
            timestamp=datetime.now(),
        ),
    ]
    for r in rows:
        insert_game_metrics(data=r)
    return {
        "test_user": test_user,
        "game_id_1": game_id_1,
        "game_id_2": game_id_2,
        "game_id_3": game_id_3,
    }


def test_insert_and_get_game_metrics(db):
    game_id = str(uuid.uuid4())
    data = GameMetricsData(
        user_id="u1",
        level_id=3,
        game_id=game_id,
        final_enpv=15.0,
        final_eroi=0.14,
        realised_roi=0.13,
        final_capital=2500.0,
        eroi_over_time=[0.0, 2500.0],
        enpv_over_time=[0, 15.0],
        av_enpv=7.5,
        timestamp=datetime.now(),
    )
    insert_game_metrics(data=data)
    got = get_user_game_metrics(user_id="u1", game_id=game_id)
    assert got is not None
    assert got.model_dump() == data.model_dump()


def test_insert_dict_format(db):
    game_id = str(uuid.uuid4())
    insert_game_metrics(
        data={
            "user_id": "dict_user",
            "level_id": 4,
            "game_id": game_id,
            "final_enpv": 25.0,
            "final_eroi": 0.20,
            "realised_roi": 0.19,
            "final_capital": 3500.0,
            "eroi_over_time": [0.0, 3500.0],
            "enpv_over_time": [0, 25.0],
            "av_enpv": 12.5,
            "timestamp": datetime.now(),
        }
    )
    got = get_user_game_metrics(user_id="dict_user", game_id=game_id)
    assert got is not None
    assert got.final_enpv == 25.0
    assert got.final_eroi == 0.20
    assert got.final_capital == 3500.0


def test_get_user_level_metrics(sample_data):
    rows = get_user_level_metrics(user_id=sample_data["test_user"], level_id=1)
    assert len(rows) == 2
    ids = {r.game_id for r in rows}
    assert {sample_data["game_id_1"], sample_data["game_id_2"]} <= ids


def test_has_user_completed_level(sample_data):
    assert (
        has_user_completed_level(user_id=sample_data["test_user"], level_id=1) is True
    )
    assert (
        has_user_completed_level(user_id=sample_data["test_user"], level_id=2) is True
    )
    assert (
        has_user_completed_level(user_id=sample_data["test_user"], level_id=3) is False
    )
    assert has_user_completed_level(user_id="no_user", level_id=1) is False


@pytest.fixture
def sample_data_multiple_plays(db):
    test_user = "test_user"
    game_id_1 = str(uuid.uuid4())
    game_id_2 = str(uuid.uuid4())
    game_id_3 = str(uuid.uuid4())

    # Base time for consistent ordering
    base_time = datetime.now()

    rows = [
        # test_user's FIRST attempt at level 0 (this should be in leaderboard)
        GameMetricsData(
            user_id=test_user,
            level_id=0,
            game_id=game_id_1,
            final_enpv=10.0,
            final_eroi=0.12,
            realised_roi=0.11,
            final_capital=1000.0,
            eroi_over_time=[0.0, 1000.0],
            enpv_over_time=[0, 10.0],
            av_enpv=5.0,
            timestamp=base_time,
        ),
        # test_user's second attempt at level 0 (better score, but shouldn't be in
        # leaderboard)
        GameMetricsData(
            user_id=test_user,
            level_id=0,
            game_id=str(uuid.uuid4()),
            final_enpv=90.0,
            final_eroi=0.12,
            realised_roi=0.11,
            final_capital=1000.0,
            eroi_over_time=[0.0, 1000.0],
            enpv_over_time=[0, 90.0],
            av_enpv=45.0,
            timestamp=base_time + timedelta(hours=1),
        ),
        # test_user's third attempt at level 0 (even better score, but shouldn't be in
        # leaderboard)
        GameMetricsData(
            user_id=test_user,
            level_id=0,
            game_id=str(uuid.uuid4()),
            final_enpv=90.0,
            final_eroi=0.12,
            realised_roi=0.11,
            final_capital=2000.0,
            eroi_over_time=[0.0, 2000.0],
            enpv_over_time=[0, 90.0],
            av_enpv=45.0,
            timestamp=base_time + timedelta(hours=2),
        ),
        # test_user's FIRST (and only) attempt at level 1
        GameMetricsData(
            user_id=test_user,
            level_id=1,
            game_id=game_id_2,
            final_enpv=0.0,
            final_eroi=0.08,
            realised_roi=0.07,
            final_capital=5000.0,
            eroi_over_time=[0.0, 5000.0],
            enpv_over_time=[0, 0.0],
            av_enpv=0.0,
            timestamp=base_time + timedelta(hours=3),
        ),
        # test_user's FIRST (and only) attempt at level 2
        GameMetricsData(
            user_id=test_user,
            level_id=2,
            game_id=game_id_3,
            final_enpv=20.0,
            final_eroi=0.15,
            realised_roi=0.14,
            final_capital=2000.0,
            eroi_over_time=[0.0, 2000.0],
            enpv_over_time=[0, 20.0],
            av_enpv=10.0,
            timestamp=base_time + timedelta(hours=4),
        ),
        # another_user's FIRST (and only) attempt at level 0
        GameMetricsData(
            user_id="another_user",
            level_id=0,
            game_id=str(uuid.uuid4()),
            final_enpv=5.0,
            final_eroi=0.10,
            realised_roi=0.09,
            final_capital=3000.0,
            eroi_over_time=[0.0, 3000.0],
            enpv_over_time=[0, 5.0],
            av_enpv=2.5,
            timestamp=base_time + timedelta(hours=5),
        ),
        # another_user at level -1 (should be excluded from global leaderboard logic)
        GameMetricsData(
            user_id="another_user",
            level_id=-1,
            game_id=str(uuid.uuid4()),
            final_enpv=5.0,
            final_eroi=0.10,
            realised_roi=0.09,
            final_capital=3000.0,
            eroi_over_time=[0.0, 3000.0],
            enpv_over_time=[0, 5.0],
            av_enpv=2.5,
            timestamp=base_time + timedelta(hours=6),
        ),
        # another_user's FIRST (and only) attempt at level 1
        GameMetricsData(
            user_id="another_user",
            level_id=1,
            game_id=str(uuid.uuid4()),
            final_enpv=5.0,
            final_eroi=0.10,
            realised_roi=0.09,
            final_capital=3000.0,
            eroi_over_time=[0.0, 3000.0],
            enpv_over_time=[0, 5.0],
            av_enpv=2.5,
            timestamp=base_time + timedelta(hours=7),
        ),
        # good_user at level -1 (should be excluded from global leaderboard logic)
        GameMetricsData(
            user_id="good_user",
            level_id=-1,
            game_id=str(uuid.uuid4()),
            final_enpv=5.0,
            final_eroi=0.10,
            realised_roi=0.09,
            final_capital=3000.0,
            eroi_over_time=[0.0, 3000.0],
            enpv_over_time=[0, 5.0],
            av_enpv=2.5,
            timestamp=base_time + timedelta(hours=8),
        ),
        # good_user's FIRST (and only) attempt at level 0
        GameMetricsData(
            user_id="good_user",
            level_id=0,
            game_id=str(uuid.uuid4()),
            final_enpv=5.0,
            final_eroi=0.10,
            realised_roi=0.09,
            final_capital=3000.0,
            eroi_over_time=[0.0, 3000.0],
            enpv_over_time=[0, 5.0],
            av_enpv=2.5,
            timestamp=base_time + timedelta(hours=9),
        ),
        # good_user's FIRST (and only) attempt at level 1
        GameMetricsData(
            user_id="good_user",
            level_id=1,
            game_id=str(uuid.uuid4()),
            final_enpv=5.0,
            final_eroi=0.10,
            realised_roi=0.09,
            final_capital=3000.0,
            eroi_over_time=[0.0, 3000.0],
            enpv_over_time=[0, 5.0],
            av_enpv=2.5,
            timestamp=base_time + timedelta(hours=10),
        ),
        # good_user's FIRST (and only) attempt at level 2
        GameMetricsData(
            user_id="good_user",
            level_id=2,
            game_id=str(uuid.uuid4()),
            final_enpv=5.0,
            final_eroi=0.10,
            realised_roi=0.09,
            final_capital=3000.0,
            eroi_over_time=[0.0, 3000.0],
            enpv_over_time=[0, 5.0],
            av_enpv=2.5,
            timestamp=base_time + timedelta(hours=11),
        ),
    ]
    for r in rows:
        insert_game_metrics(data=r)
    return {
        "test_user": test_user,
        "game_id_1": game_id_1,
        "game_id_2": game_id_2,
        "game_id_3": game_id_3,
    }


def test_get_level_leaderboard_data(sample_data_multiple_plays):
    leaderboard = get_level_leaderboard_data(level_id=0)
    assert len(leaderboard) == 3
    test_user_entry = next(
        entry for entry in leaderboard if entry.user_id == "test_user"
    )
    # Should now use first attempt: av_enpv=5.0 (not the best score of 45.0)
    assert test_user_entry.av_enpv == 5.0
    user_ids = {entry.user_id for entry in leaderboard}
    assert {
        sample_data_multiple_plays["test_user"],
        "another_user",
        "good_user",
    } <= user_ids


def test_get_global_leaderboard_data(sample_data_multiple_plays):
    leaderboard = get_global_leaderboard_data()
    assert len(leaderboard) == 2
    test_user_entry = next(
        entry for entry in leaderboard if entry.user_id == "test_user"
    )
    # Should now use first attempts: (5.0 + 0.0 + 10.0) / 3 = 5.0
    assert test_user_entry.av_enpv == pytest.approx((5.0 + 0.0 + 10.0) / 3)
    good_user_entry = next(
        entry for entry in leaderboard if entry.user_id == "good_user"
    )
    # good_user's first attempts: (2.5 + 2.5 + 2.5) / 3 = 2.5
    assert good_user_entry.av_enpv == pytest.approx(2.5)

    # another_user should not be in global leaderboard (hasn't completed level 2)
    assert "another_user" not in {entry.user_id for entry in leaderboard}


def test_get_level_id_of_game_id(sample_data):
    # Test with existing game_id
    level_id = get_level_id_of_game_id(game_id=sample_data["game_id_1"])
    assert level_id == 1

    level_id = get_level_id_of_game_id(game_id=sample_data["game_id_3"])
    assert level_id == 2

    # Test with non-existent game_id
    with pytest.raises(Exception):
        get_level_id_of_game_id(game_id="non_existent_game_id")
