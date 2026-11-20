from src.property_spend import (
    InfraiAccount,
    InfraiError,
    InspectionReminder,
    MaintenanceRequest,
    PropertyWorkload,
    TenantDocument,
    decide_spend,
)


def test_maintenance_request_is_rejected_when_monthly_cap_would_be_crossed() -> None:
    workload = PropertyWorkload(
        maintenance=(MaintenanceRequest("12A", "boiler inspection", 75.0),),
        tenant_documents=(TenantDocument("12A", "proof of insurance"),),
        inspections=(InspectionReminder("12A", "2026-11-12"),),
    )
    decision = decide_spend(workload, hard_cap_usd=300.0, already_spent_usd=250.0)
    assert decision.approved is False
    assert decision.projected_usd == 325.0


def test_rate_limit_error_envelopes_retry_before_success() -> None:
    from unittest.mock import Mock, patch

    limited = Mock(status_code=429, headers={"Retry-After": "0.25"})
    limited.json.return_value = {"ok": False, "error": {"code": "RATE_LIMITED"}}
    success = Mock(status_code=200)
    success.json.return_value = {"ok": True, "data": {"hard_cap_usd": 300}}
    with patch("requests.request", side_effect=[limited, success]) as request, patch("src.property_spend.time.sleep") as sleep:
        result = InfraiAccount(key="test").set_budget(300, "monthly")
    assert result == {"hard_cap_usd": 300}
    assert request.call_count == 2
    sleep.assert_called_once_with(0.25)


def test_rate_limit_error_envelopes_stop_at_retry_limit() -> None:
    from unittest.mock import Mock, call, patch

    import pytest

    limited = Mock(status_code=429, headers={})
    limited.json.return_value = {"ok": False, "error": {"code": "RATE_LIMITED"}}
    with patch("requests.request", return_value=limited) as request, patch("src.property_spend.time.sleep") as sleep:
        with pytest.raises(InfraiError) as raised:
            InfraiAccount(key="test").set_budget(300, "monthly")
    assert raised.value.code == "RETRY_LIMIT"
    assert raised.value.status == 429
    assert request.call_count == 3
    assert sleep.call_args_list == [call(1), call(2), call(4)]
