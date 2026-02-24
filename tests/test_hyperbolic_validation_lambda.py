import json

from aws.hyperbolic_validation_lambda import handler


def test_lambda_allows_near_center():
    resp = handler({"body": json.dumps({"position": [0.1, 0.1, 0.1]})}, None)
    body = json.loads(resp["body"])

    assert resp["statusCode"] == 200
    assert body["decision"] == "ALLOW"


def test_lambda_denies_far_from_center():
    resp = handler({"body": json.dumps({"position": [1.0, 1.0, 1.0]})}, None)
    body = json.loads(resp["body"])

    assert resp["statusCode"] == 200
    assert body["decision"] == "DENY"
    assert body["penalty"] > 1.0
