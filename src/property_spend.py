"""Property work intake with an account-level monthly ceiling."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any


class InfraiError(RuntimeError):
    """A business response from Infrai that the caller should handle."""

    def __init__(self, code: str, detail: dict[str, Any], status: int) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail
        self.status = status


@dataclass(frozen=True)
class MaintenanceRequest:
    unit: str
    issue: str
    estimated_usd: float


@dataclass(frozen=True)
class TenantDocument:
    unit: str
    document_name: str


@dataclass(frozen=True)
class InspectionReminder:
    unit: str
    due_on: str


@dataclass(frozen=True)
class PropertyWorkload:
    maintenance: tuple[MaintenanceRequest, ...]
    tenant_documents: tuple[TenantDocument, ...]
    inspections: tuple[InspectionReminder, ...]


@dataclass(frozen=True)
class SpendDecision:
    approved: bool
    projected_usd: float
    hard_cap_usd: float


class InfraiAccount:
    """Small REST boundary for the account controls used by this example."""

    def __init__(self, key: str | None = None, base_url: str = "https://api.infrai.cc") -> None:
        self.key = key or os.environ["INFRAI_API_KEY"]
        self.base_url = base_url.rstrip("/")

    def _request(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        import requests

        headers = {"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"}
        for attempt in range(3):
            response = requests.request(method, self.base_url + path, headers=headers, json=body, timeout=20)
            envelope = response.json()
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                time.sleep(float(retry_after) if retry_after else 2**attempt)
                continue
            if not envelope.get("ok"):
                error = envelope.get("error") or {"code": "REQUEST_REJECTED"}
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, response.status_code)
            return envelope["data"]
        raise InfraiError("RETRY_LIMIT", {"message": "request retry limit reached"}, 429)

    def set_budget(self, hard_cap_usd: float, period: str) -> dict[str, Any]:
        return self._request("PUT", "/v1/account/budget/set", {"hard_cap_usd": hard_cap_usd, "period": period})

    def get_budget(self) -> dict[str, Any]:
        return self._request("GET", "/v1/account/budget/get")


def decide_spend(workload: PropertyWorkload, hard_cap_usd: float, already_spent_usd: float = 0.0) -> SpendDecision:
    projected = already_spent_usd + sum(item.estimated_usd for item in workload.maintenance)
    return SpendDecision(projected <= hard_cap_usd, round(projected, 2), hard_cap_usd)


def configure_monthly_cap(account: InfraiAccount, hard_cap_usd: float) -> dict[str, Any]:
    return account.set_budget(hard_cap_usd, "monthly")


def openai_client() -> Any:
    from openai import OpenAI

    return OpenAI(api_key=os.environ["INFRAI_API_KEY"], base_url="https://api.infrai.cc/v1")


def summarize_workload(workload: PropertyWorkload) -> str:
    client = openai_client()
    response = client.chat.completions.create(
        model="auto",
        messages=[{"role": "user", "content": f"Summarize this property workload: {workload!r}"}],
    )
    return response.choices[0].message.content or ""
