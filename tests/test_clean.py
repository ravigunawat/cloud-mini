import os
import sys

os.environ.setdefault("S3_ACCESS_KEY", "x")
os.environ.setdefault("S3_SECRET_KEY", "y")
sys.path.insert(0, "worker")
import clean  # noqa: E402


def rec(text, raw):
    return {"id": "C1", "text": text, "teacher_raw": raw}


def test_invalid_json_is_rejected_a():
    assert clean.reject_reason(rec("x", "not json")) == "a"


def test_wrong_keys_rejected_b():
    assert clean.reject_reason(rec("x", '{"intent": "alarm_set"}')) == "b"


def test_unknown_intent_rejected_c():
    raw = '{"intent": "play", "date": null, "time": null, "place": null}'
    assert clean.reject_reason(rec("x", raw)) == "c"


def test_slot_not_in_command_rejected_d():
    raw = '{"intent": "alarm_set", "date": "monday", "time": null, "place": null}'
    assert clean.reject_reason(rec("set alarm", raw)) == "d"


def test_good_record_kept():
    raw = '{"intent": "alarm_set", "date": "monday", "time": null, "place": null}'
    assert clean.reject_reason(rec("alarm on monday", raw)) is None
