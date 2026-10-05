"""CR-C: atbildes termiņa pagarināšana (POST /submissions/{id}/extend)."""

import logging
from datetime import date, datetime, timezone

import pytest

from app import clock, storage
from app.main import add_months

REASON = "Jāsaņem būvvaldes atzinums"


@pytest.fixture
def received_0925(monkeypatch):
    # Saņemts 2026-09-25 (UTC), sākotnējais termiņš 2026-10-25.
    fixed = datetime(2026, 9, 25, 13, 40, tzinfo=timezone.utc)
    monkeypatch.setattr(clock, "now", lambda: fixed)


@pytest.fixture
def created(client, valid_payload, received_0925):
    return client.post("/submissions", json=valid_payload).json()


def extend(client, submission_id, new_due_date, reason=REASON):
    return client.post(
        f"/submissions/{submission_id}/extend",
        json={"newDueDate": new_due_date, "reason": reason},
    )


def due_date(client, submission_id):
    return client.get(f"/submissions/{submission_id}").json()["dueDate"]


# 1. kritērijs
@pytest.mark.parametrize("status", ["RECEIVED", "IN_PROGRESS"])
def test_extend_allowed_status_sets_due_date(client, created, status):
    storage.update_status(created["id"], status)
    response = extend(client, created["id"], "2026-12-15")
    assert response.status_code == 200
    assert response.json()["dueDate"] == "2026-12-15"
    assert due_date(client, created["id"]) == "2026-12-15"


def test_extend_can_be_repeated(client, created):
    assert extend(client, created["id"], "2026-11-15").status_code == 200
    response = extend(client, created["id"], "2026-12-15")
    assert response.status_code == 200
    assert response.json()["dueDate"] == "2026-12-15"


# 2. kritērijs
def test_extend_exactly_four_months_is_allowed(client, created):
    response = extend(client, created["id"], "2027-01-25")
    assert response.status_code == 200
    assert response.json()["dueDate"] == "2027-01-25"


# 3. kritērijs
def test_extend_beyond_four_months_is_rejected(client, created):
    response = extend(client, created["id"], "2027-01-26")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_DUE_DATE"
    assert due_date(client, created["id"]) == created["dueDate"]


# 4. kritērijs
@pytest.mark.parametrize("new_due_date", ["2026-10-25", "2026-10-24"])
def test_extend_not_later_than_current_is_rejected(client, created, new_due_date):
    assert created["dueDate"] == "2026-10-25"
    response = extend(client, created["id"], new_due_date)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_DUE_DATE"
    assert due_date(client, created["id"]) == "2026-10-25"


# 5. kritērijs
@pytest.mark.parametrize("status", ["FORWARDED", "ANSWERED", "WITHDRAWN"])
def test_extend_in_closed_status_returns_409(client, created, status):
    storage.update_status(created["id"], status)
    response = extend(client, created["id"], "2026-12-15")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INVALID_STATE"
    assert due_date(client, created["id"]) == created["dueDate"]


# 6. kritērijs
def test_extend_unknown_id_returns_404(client):
    response = extend(client, "IES-2026-999999", "2026-12-15")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


# 7. kritērijs
@pytest.mark.parametrize(
    "body",
    [
        {"reason": REASON},
        {"newDueDate": "2026-12-15"},
        {"newDueDate": "2026-13-01", "reason": REASON},
        {"newDueDate": "15.12.2026", "reason": REASON},
        {"newDueDate": 20261215, "reason": REASON},
        {"newDueDate": "2026-12-15T00:00:00", "reason": REASON},
        {"newDueDate": "2026-12-15", "reason": "a" * 9},
        {"newDueDate": "2026-12-15", "reason": "a" * 501},
        {"newDueDate": "2026-12-15", "reason": " " * 12},
    ],
)
def test_extend_invalid_request_returns_validation_error(client, created, body):
    response = client.post(f"/submissions/{created['id']}/extend", json=body)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert due_date(client, created["id"]) == created["dueDate"]


def test_extend_reason_length_bounds_are_inclusive(client, created):
    assert extend(client, created["id"], "2026-11-15", "a" * 10).status_code == 200
    assert extend(client, created["id"], "2026-12-15", "a" * 500).status_code == 200


# 8. kritērijs
def test_extend_writes_audit_entry(client, created):
    extend(client, created["id"], "2026-12-15")
    audit = client.get(f"/submissions/{created['id']}/audit").json()
    assert [e["action"] for e in audit] == ["CREATE", "EXTEND"]
    assert audit[-1]["detail"] == REASON


def test_rejected_extend_writes_no_audit_entry(client, created):
    extend(client, created["id"], "2027-01-26")
    audit = client.get(f"/submissions/{created['id']}/audit").json()
    assert [e["action"] for e in audit] == ["CREATE"]


# 9. kritērijs
def test_extend_logs_and_errors_contain_no_personal_data(
    client, valid_payload, received_0925, caplog
):
    submission_id = client.post("/submissions", json=valid_payload).json()["id"]
    caplog.clear()
    with caplog.at_level(logging.DEBUG):
        responses = [
            extend(client, submission_id, "2026-12-15"),
            extend(client, submission_id, "2027-01-26"),
            extend(client, submission_id, "bad", "a"),
            extend(client, "IES-2026-999999", "2026-12-15"),
        ]
        logs = caplog.text
        storage.update_status(submission_id, "ANSWERED")
        caplog.clear()  # update_status ir testa sagatavošana, ne CR-C kods
        responses.append(extend(client, submission_id, "2027-01-01"))
        logs += caplog.text

    assert "Termiņš pagarināts" in logs
    error_bodies = " ".join(r.text for r in responses[1:])
    for secret in ("personalCode", "fullName", "email", "body"):
        value = valid_payload[secret]
        assert value not in logs
        assert value not in error_bodies


# Mēneša beigas (precizējums, 2026-10-05): ja datuma nav, mēneša pēdējā diena.
@pytest.mark.parametrize(
    ("start", "expected"),
    [
        (date(2026, 9, 25), date(2027, 1, 25)),
        (date(2026, 10, 31), date(2027, 2, 28)),
        (date(2027, 10, 31), date(2028, 2, 29)),
        (date(2026, 5, 31), date(2026, 9, 30)),
        (date(2026, 8, 31), date(2026, 12, 31)),
    ],
)
def test_add_months(start, expected):
    assert add_months(start, 4) == expected


def test_extend_month_end_uses_last_day(client, valid_payload, monkeypatch):
    fixed = datetime(2026, 5, 31, 7, 20, tzinfo=timezone.utc)
    monkeypatch.setattr(clock, "now", lambda: fixed)
    submission_id = client.post("/submissions", json=valid_payload).json()["id"]

    assert extend(client, submission_id, "2026-10-01").status_code == 400
    assert extend(client, submission_id, "2026-09-30").status_code == 200
