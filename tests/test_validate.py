import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "service"))
import validate  # noqa: E402


def test_valid_output_accepted():
    raw = '{"intent": "weather_query", "date": null, "time": null, "place": "london"}'
    assert validate.parse_output(raw)["place"] == "london"


def test_not_json_rejected():
    assert validate.parse_output("not json") is None


def test_extra_key_rejected():
    raw = '{"intent": "alarm_set", "date": null, "time": null, "place": null, "x": 1}'
    assert validate.parse_output(raw) is None


def test_unknown_intent_rejected():
    raw = '{"intent": "play_music", "date": null, "time": null, "place": null}'
    assert validate.parse_output(raw) is None


def test_non_string_slot_rejected():
    raw = '{"intent": "alarm_set", "date": 5, "time": null, "place": null}'
    assert validate.parse_output(raw) is None


def test_only_first_line_is_used():
    raw = '{"intent": "alarm_set", "date": null, "time": null, "place": null}\nextra text'
    assert validate.parse_output(raw) is not None
