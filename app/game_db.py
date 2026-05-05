import json
import logging
import sqlite3
import uuid
from datetime import datetime
from typing import List, Optional

from psycopg2.errors import DatabaseError
from pydantic import BaseModel, ConfigDict

from aiml_pyxis_investment_game.game.constants import LEVELS
from aiml_pyxis_investment_game.game.metrics import GameMetricsData
from app.connect_to_postgresql import get_db_cursor

logger = logging.getLogger(__name__)

# Schema and table constants
GAME_SCHEMA_NAME = "rdfn_game_analytics"
TABLE_NAME = f"{GAME_SCHEMA_NAME}.game_metrics"
TABLE_NAME_TESTS = "game_metrics"


def ser_dump_game_metrics_data(
    game_metrics_data: GameMetricsData, for_sqlite: bool = False
) -> dict:
    """
    Serialize GameMetricsData to dictionary.

    Parameters
    ----------
    game_metrics_data : GameMetricsData
        The game metrics data to serialize
    for_sqlite : bool
        If True, convert lists to JSON strings for SQLite compatibility

    """
    data = game_metrics_data.model_dump()
    if for_sqlite:
        # Convert lists to JSON strings for SQLite compatibility
        data["eroi_over_time"] = json.dumps(data["eroi_over_time"])
        data["enpv_over_time"] = json.dumps(data["enpv_over_time"])
        # Convert datetime to ISO string for SQLite compatibility
        data["timestamp"] = data["timestamp"].isoformat()
    return data


class LeaderboardEntry(BaseModel):
    """
    Data model for a single entry in a leaderboard (level or global).

    Similar to GameMetricsData, but without level_id and user_id.
    """

    model_config = ConfigDict(extra="forbid")
    game_id: str
    user_id: str
    av_enpv: float


def _deserialize_sqlite_row(row_dict: dict) -> dict:
    """Deserialize a SQLite row by converting JSON strings back to lists."""
    if "eroi_over_time" in row_dict and isinstance(row_dict["eroi_over_time"], str):
        row_dict["eroi_over_time"] = json.loads(row_dict["eroi_over_time"])
    if "enpv_over_time" in row_dict and isinstance(row_dict["enpv_over_time"], str):
        row_dict["enpv_over_time"] = json.loads(row_dict["enpv_over_time"])
    if "timestamp" in row_dict and isinstance(row_dict["timestamp"], str):
        row_dict["timestamp"] = datetime.fromisoformat(row_dict["timestamp"])
    return row_dict


def create_game_analytics_db(
    overwrite: bool = False,
    *,
    raise_on_error: bool = False,
) -> None:
    """
    Create a table for game analytics in the database, if it does not exist.

    The schema of the table:
    user_id: TEXT
    level_id: TEXT
    game_id: TEXT
    final_enpv: FLOAT
    final_eroi: FLOAT
    realised_roi: FLOAT
    final_capital: FLOAT
    eroi_over_time: FLOAT[] (PostgreSQL) or TEXT (SQLite with JSON)
    enpv_over_time: FLOAT[] (PostgreSQL) or TEXT (SQLite with JSON)
    av_enpv: FLOAT
    timestamp: TIMESTAMP (PostgreSQL) or TEXT (SQLite with ISO format)
    """
    cursor, connection = get_db_cursor()
    try:
        if isinstance(connection, sqlite3.Connection):
            table_name = TABLE_NAME_TESTS
        else:
            cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {GAME_SCHEMA_NAME}")
            table_name = TABLE_NAME

        if overwrite:
            cursor.execute(f"DROP TABLE IF EXISTS {table_name}")

        if isinstance(connection, sqlite3.Connection):
            # SQLite doesn't support arrays, use TEXT to store JSON
            cursor.execute(
                f"CREATE TABLE IF NOT EXISTS {table_name} "
                "(user_id TEXT, level_id INTEGER, game_id TEXT, "
                "final_enpv FLOAT, final_eroi FLOAT, realised_roi FLOAT, "
                "final_capital FLOAT, eroi_over_time TEXT, enpv_over_time TEXT, "
                "av_enpv FLOAT, timestamp TEXT)"
            )
        else:
            # PostgreSQL supports arrays
            cursor.execute(
                f"CREATE TABLE IF NOT EXISTS {table_name} "
                "(user_id TEXT, level_id INTEGER, game_id TEXT, "
                "final_enpv FLOAT, final_eroi FLOAT, realised_roi FLOAT, "
                "final_capital FLOAT, eroi_over_time FLOAT[], "
                "enpv_over_time FLOAT[], av_enpv FLOAT, timestamp TIMESTAMP)"
            )
        connection.commit()
    except DatabaseError as err:
        if raise_on_error:
            raise err
        logger.error(err)
    finally:
        cursor.close()
        connection.close()


def insert_game_metrics(
    *,
    data: GameMetricsData | dict,
    raise_on_error: bool = False,
):
    """
    Add game metrics to the database.

    Parameters
    ----------
    data : GameMetricsData or dict
        The metrics data to insert
    raise_on_error : bool, optional
        Whether to raise exceptions, by default False

    """
    if isinstance(data, dict):
        data = GameMetricsData.model_validate(data)

    cursor, connection = get_db_cursor()

    try:
        if isinstance(connection, sqlite3.Connection):
            table_name = TABLE_NAME_TESTS
            data_dict = ser_dump_game_metrics_data(
                game_metrics_data=data, for_sqlite=True
            )
            cursor.execute(
                f"INSERT INTO {table_name} "
                "(user_id, level_id, game_id, final_enpv, final_eroi, realised_roi, "
                "final_capital, eroi_over_time, enpv_over_time, av_enpv, timestamp) "
                "VALUES (:user_id, :level_id, :game_id, :final_enpv, :final_eroi, "
                ":realised_roi, :final_capital, :eroi_over_time, :enpv_over_time, "
                ":av_enpv, :timestamp)",
                data_dict,
            )
        else:
            table_name = TABLE_NAME
            data_dict = ser_dump_game_metrics_data(
                game_metrics_data=data, for_sqlite=False
            )
            cursor.execute(
                f"INSERT INTO {table_name} "
                "(user_id, level_id, game_id, final_enpv, final_eroi, realised_roi, "
                "final_capital, eroi_over_time, enpv_over_time, av_enpv, timestamp) "
                "VALUES (%(user_id)s, %(level_id)s, %(game_id)s, "
                "%(final_enpv)s, %(final_eroi)s, %(realised_roi)s, %(final_capital)s, "
                "%(eroi_over_time)s, %(enpv_over_time)s, %(av_enpv)s, %(timestamp)s)",
                data_dict,
            )
        connection.commit()
    except DatabaseError as err:
        if raise_on_error:
            raise err
        logger.error(f"Error inserting game metrics: {err}")
    finally:
        cursor.close()
        connection.close()


def get_user_game_metrics(
    *,
    user_id: str,
    game_id: str,
    raise_on_error: bool = False,
) -> Optional[GameMetricsData]:
    """
    Get metrics for a specific user and game.

    Parameters
    ----------
    user_id : str
        The user ID
    game_id : str
        The game ID
    raise_on_error : bool, optional
        Whether to raise exceptions, by default False

    Returns
    -------
    Optional[GameMetricsData]
        The metrics data if found, None otherwise

    """
    cursor, connection = get_db_cursor()
    try:
        if isinstance(connection, sqlite3.Connection):
            table_name = TABLE_NAME_TESTS
            cursor.execute(
                f"SELECT * FROM {table_name} WHERE user_id=? AND game_id=?",
                (user_id, game_id),
            )
        else:
            table_name = TABLE_NAME
            cursor.execute(
                f"SELECT * FROM {table_name} WHERE user_id=%s AND game_id=%s",
                (user_id, game_id),
            )

        result = cursor.fetchone()
        if result:
            row_dict = dict(result)
            if isinstance(connection, sqlite3.Connection):
                row_dict = _deserialize_sqlite_row(row_dict)
            return GameMetricsData.model_validate(row_dict)
        return None
    except DatabaseError as err:
        if raise_on_error:
            raise err
        logger.error(f"Error retrieving game metrics: {err}")
        return None
    finally:
        cursor.close()
        connection.close()


def get_user_level_metrics(
    *,
    user_id: str,
    level_id: int,
    raise_on_error: bool = False,
) -> List[GameMetricsData]:
    """
    Get all metrics for a user at a specific level.

    Parameters
    ----------
    user_id : str
        The user ID
    level_id : str
        The level ID
    raise_on_error : bool, optional
        Whether to raise exceptions, by default False

    Returns
    -------
    List[GameMetricsData]
        List of metrics data for the user at the specified level

    """
    cursor, connection = get_db_cursor()
    try:
        if isinstance(connection, sqlite3.Connection):
            table_name = TABLE_NAME_TESTS
            cursor.execute(
                f"SELECT * FROM {table_name} WHERE user_id=? AND level_id=?",
                (user_id, level_id),
            )
        else:
            table_name = TABLE_NAME
            cursor.execute(
                f"SELECT * FROM {table_name} WHERE user_id=%s AND level_id=%s",
                (user_id, level_id),
            )

        results = cursor.fetchall()
        metrics_list = []
        for row in results:
            row_dict = dict(row)
            if isinstance(connection, sqlite3.Connection):
                row_dict = _deserialize_sqlite_row(row_dict)
            metrics_list.append(GameMetricsData.model_validate(row_dict))
        return metrics_list
    except DatabaseError as err:
        if raise_on_error:
            raise err
        logger.error(f"Error retrieving level metrics: {err}")
        return []
    finally:
        cursor.close()
        connection.close()


def has_user_completed_level(
    *,
    user_id: str,
    level_id: int,
    raise_on_error: bool = False,
) -> bool:
    """
    Check if a user has completed a specific level.

    Since analytics are only added after game completion, the presence
    of any record for this user and level indicates completion.

    Parameters
    ----------
    user_id : str
        The user ID
    level_id : str
        The level ID to check completion status for
    raise_on_error : bool, optional
        Whether to raise exceptions, by default False

    Returns
    -------
    bool
        True if the user has completed the level, False otherwise

    """
    cursor, connection = get_db_cursor()
    try:
        if isinstance(connection, sqlite3.Connection):
            table_name = TABLE_NAME_TESTS
            cursor.execute(
                f"SELECT COUNT(*) as count FROM {table_name} "
                f"WHERE user_id=? AND level_id=?",
                (user_id, level_id),
            )
        else:
            table_name = TABLE_NAME
            cursor.execute(
                f"SELECT COUNT(*) as count FROM {table_name} "
                f"WHERE user_id=%s AND level_id=%s",
                (user_id, level_id),
            )

        result = cursor.fetchone()
        return result["count"] > 0 if result else False

    except DatabaseError as err:
        if raise_on_error:
            raise err
        logger.error(f"Error checking level completion: {err}")
        return False
    finally:
        cursor.close()
        connection.close()


def get_level_leaderboard_data(
    *,
    level_id: int,
    raise_on_error: bool = False,
) -> list[LeaderboardEntry]:
    """
    Get leaderboard data for a specific level, with the first attempt for each user.

    Parameters
    ----------
    level_id : int
        The level ID
    raise_on_error : bool, optional
        Whether to raise exceptions, by default False

    Returns
    -------
    list[LeaderboardEntry]
        The leaderboard data for the specified level (first attempts only)

    """
    cursor, connection = get_db_cursor()
    base_query = """
        WITH first_attempts AS (
            SELECT
                user_id, game_id, av_enpv,
                ROW_NUMBER() OVER(
                    PARTITION BY user_id ORDER BY timestamp ASC
                ) as rn
            FROM {table_name}
            WHERE level_id = %s
        )
        SELECT user_id, game_id, av_enpv
        FROM first_attempts
        WHERE rn = 1
        ORDER BY av_enpv DESC
    """
    try:
        if isinstance(connection, sqlite3.Connection):
            table_name = TABLE_NAME_TESTS
            sql_query = base_query.format(table_name=table_name).replace("%s", "?")
            cursor.execute(sql_query, (level_id,))
        else:
            table_name = TABLE_NAME
            sql_query = base_query.format(table_name=table_name)
            cursor.execute(sql_query, (level_id,))

        results = cursor.fetchall()
        leaderboard_data = [
            LeaderboardEntry.model_validate(dict(row)) for row in results
        ]
        return leaderboard_data
    except DatabaseError as err:
        if raise_on_error:
            raise err
        logger.error(f"Error retrieving level leaderboard: {err}")
        return []
    finally:
        cursor.close()
        connection.close()


def get_global_leaderboard_data(
    *,
    raise_on_error: bool = False,
) -> list[LeaderboardEntry]:
    """
    Get global leaderboard data, averaging users' first attempt eNPV across levels.

    A user is only entered into the global leaderboard if they have completed all
    levels.

    Parameters
    ----------
    raise_on_error : bool, optional
        Whether to raise exceptions, by default False

    Returns
    -------
    list[LeaderboardEntry]
        The global leaderboard data (first attempts only)

    """
    cursor, connection = get_db_cursor()
    base_query = """
        WITH first_attempts_per_level AS (
            SELECT
                user_id,
                level_id,
                game_id,
                av_enpv
            FROM (
                SELECT
                    user_id,
                    level_id,
                    game_id,
                    av_enpv,
                    ROW_NUMBER() OVER(
                        PARTITION BY user_id, level_id ORDER BY timestamp ASC
                    ) as rn
                FROM {table_name}
                WHERE level_id != -1
            ) ranked_scores
            WHERE rn = 1
        ),
        users_completed_all_levels AS (
            SELECT user_id
            FROM first_attempts_per_level
            GROUP BY user_id
            HAVING COUNT(DISTINCT level_id) = %s
               AND MIN(level_id) = 0
               AND MAX(level_id) = %s
        )
        SELECT
            bs.user_id,
            'global_average' as game_id,
            AVG(bs.av_enpv) as av_enpv
        FROM first_attempts_per_level bs
        JOIN users_completed_all_levels u ON bs.user_id = u.user_id
        GROUP BY bs.user_id
        ORDER BY av_enpv DESC
    """
    try:
        num_levels = len(LEVELS)
        max_level_id = num_levels - 1
        if isinstance(connection, sqlite3.Connection):
            table_name = TABLE_NAME_TESTS
            sql_query = base_query.format(table_name=table_name).replace("%s", "?")
            cursor.execute(sql_query, (num_levels, max_level_id))
        else:
            table_name = TABLE_NAME
            sql_query = base_query.format(table_name=table_name)
            cursor.execute(sql_query, (num_levels, max_level_id))

        results = cursor.fetchall()
        leaderboard_data = [
            LeaderboardEntry.model_validate(dict(row)) for row in results
        ]
        return leaderboard_data
    except DatabaseError as err:
        if raise_on_error:
            raise err
        logger.error(f"Error retrieving global leaderboard: {err}")
        return []
    finally:
        cursor.close()
        connection.close()


def get_user_best_level_metrics(
    *,
    user_id: str,
    level_id: int,
    raise_on_error: bool = False,
) -> Optional[LeaderboardEntry]:
    """
    Get the user's highest eNPV playthrough for a specific level.

    Parameters
    ----------
    user_id : str
        The ID of the user
    level_id : int
        The ID of the level
    raise_on_error : bool, optional
        Whether to raise exceptions, by default False

    Returns
    -------
    Optional[LeaderboardEntry]
        The best leaderboard entry for the user at the specified level, or None if not
        found

    """
    cursor, connection = get_db_cursor()
    base_query = """
        SELECT user_id, game_id, av_enpv
        FROM {table_name}
        WHERE user_id = %s AND level_id = %s
        ORDER BY av_enpv DESC
        LIMIT 1
    """
    try:
        if isinstance(connection, sqlite3.Connection):
            table_name = TABLE_NAME_TESTS
            sql_query = base_query.format(table_name=table_name).replace("%s", "?")
            cursor.execute(sql_query, (user_id, level_id))
        else:
            table_name = TABLE_NAME
            sql_query = base_query.format(table_name=table_name)
            cursor.execute(sql_query, (user_id, level_id))

        result = cursor.fetchone()
        if result:
            return LeaderboardEntry.model_validate(dict(result))
        return None
    except DatabaseError as err:
        if raise_on_error:
            raise err
        logger.error(f"Error retrieving user's best level metric: {err}")
        return None
    finally:
        cursor.close()
        connection.close()


def get_level_id_of_game_id(
    *,
    game_id: str,
    raise_on_error: bool = False,
) -> int:
    """Return the level_id of a given game_id."""
    cursor, connection = get_db_cursor()
    try:
        if isinstance(connection, sqlite3.Connection):
            sql_query = """
                SELECT level_id
                FROM {table_name}
                WHERE game_id = ?
            """.format(table_name=TABLE_NAME_TESTS)
            cursor.execute(sql_query, (game_id,))
        else:
            sql_query = """
                SELECT level_id
                FROM {table_name}
                WHERE game_id = %s
            """.format(table_name=TABLE_NAME)
            cursor.execute(sql_query, (game_id,))

        result = cursor.fetchone()
        if result:
            return result[0]
        raise ValueError(f"Game id {game_id} not found")
    except DatabaseError as err:
        if raise_on_error:
            raise err
        logger.error(f"Error retrieving level ID for game ID {game_id}: {err}")
    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    # Example usage
    create_game_analytics_db()

    # Example data
    metrics_data1 = GameMetricsData(
        user_id="test_user",
        level_id=1,
        game_id=str(uuid.uuid4()),
        final_enpv=10,
        final_eroi=0.12,
        realised_roi=0.1,
        final_capital=1000.0,
        eroi_over_time=[],
        enpv_over_time=[],
        av_enpv=10,
        timestamp=datetime.now(),
    )
    metrics_data2 = GameMetricsData(
        user_id="test_user",
        level_id=1,
        game_id=str(uuid.uuid4()),
        final_enpv=0,
        final_eroi=0.12,
        realised_roi=0.11,
        final_capital=5000.0,
        eroi_over_time=[],
        enpv_over_time=[],
        av_enpv=0,
        timestamp=datetime.now(),
    )

    # Insert example metrics
    insert_game_metrics(data=metrics_data1)
    insert_game_metrics(data=metrics_data2)

    # Testing all functions
    user_metrics = get_user_game_metrics(
        user_id="test_user", game_id=metrics_data1.game_id
    )
    print(f"Retrieved metrics: {user_metrics}")

    level_metrics = get_user_level_metrics(user_id="test_user", level_id=1)
    print(f"Retrieved level metrics: {level_metrics}")

    user_completed_level1 = has_user_completed_level(user_id="test_user", level_id=1)
    print(f"User completed level 1: {user_completed_level1}")

    user_completed_level2 = has_user_completed_level(user_id="test_user", level_id=2)
    print(f"User completed level 2: {user_completed_level2}")

    # NOTE: Get level/global leaderboard data methods not currently shown in example
    # usage
