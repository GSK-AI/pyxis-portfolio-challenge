import json

from aiml_pyxis_investment_game import PROJECT_ROOT
from aiml_pyxis_investment_game.file_io import _load_bytes_bulk, load_json_bulk

TEST_JSON_DIR = PROJECT_ROOT / "tests" / "data" / "file_io"


def test_load_bytes_bulk_preserves_order():
    """Test that _load_bytes_bulk preserves the order of input URIs."""
    uris = [TEST_JSON_DIR / f"test_file_{i}.json" for i in range(10)]

    expected_byte_contents = []
    for uri in uris:
        with open(str(uri), "rb") as f:
            expected_byte_contents.append(f.read())

    bulk_loaded_bytes = _load_bytes_bulk(uris)
    assert bulk_loaded_bytes == expected_byte_contents


def test_load_json_bulk_preserves_order():
    """Test that load_json_bulk preserves the order of input URIs."""
    uris = [TEST_JSON_DIR / f"test_file_{i}.json" for i in range(10)]

    expected_json_contents = []
    for uri in uris:
        with open(str(uri), "r") as f:
            expected_json_contents.append(json.load(f))

    bulk_loaded_contents = load_json_bulk(uris)
    assert bulk_loaded_contents == expected_json_contents
