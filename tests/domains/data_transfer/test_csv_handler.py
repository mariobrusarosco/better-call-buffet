import json

import pytest

from app.domains.data_transfer.csv_handler import CSVHandler


def test_tag_names_round_trip_as_json_array():
    handler = CSVHandler()
    content = handler.generate_csv(
        [
            {
                "transaction_date": "2026-10-08",
                "transaction_amount": "42.00",
                "transaction_description": "Appointment",
                "transaction_movement_type": "expense",
                "tag_names": json.dumps(["Health", "Mother"]),
            }
        ]
    )

    rows, errors = handler.parse_csv(content)

    assert errors == []
    assert rows[0]["transaction_movement_type"] == "expense"
    assert handler.parse_tag_names(rows[0]["tag_names"]) == ["Health", "Mother"]


def test_tag_names_must_be_a_json_string_array():
    handler = CSVHandler()

    with pytest.raises(ValueError, match="tag_names must be a JSON array of strings"):
        handler.parse_tag_names("Health, Mother")


def test_tag_names_reject_case_insensitive_duplicates():
    with pytest.raises(ValueError, match="must not contain duplicates"):
        CSVHandler.parse_tag_names('["Health", "health"]')
