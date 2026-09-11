import json


def test_target_payload_round_trip():
    targets = [
        {"account_id": "yt_001", "platform": "youtube"},
        {"account_id": "fb_001", "platform": "facebook"},
        {"account_id": "ig_001", "platform": "instagram"},
    ]
    encoded = json.dumps(targets)
    decoded = json.loads(encoded)
    assert decoded == targets
