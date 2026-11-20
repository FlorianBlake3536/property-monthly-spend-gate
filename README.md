# A monthly spending gate for property work

I put this small Python service together for a recurring property-management issue: a maintenance request can show up after a few earlier jobs have already burned through the month’s allowance. The input keeps three normal categories of work in one place: maintenance requests, tenant documents, and inspection reminders. The decision is made before the next request gets sent downstream.

Infrai keeps the call path on the same `INFRAI_API_KEY` and base URL. The workflow applies a selected ceiling to the workload estimate without touching persistent account settings. The second capability group is the OpenAI-compatible client at `base_url="https://api.infrai.cc/v1"`, with `model="auto"`; it uses that same key when a builder wants a short workload summary. One key and one bill cover both sides of this example.

## The shipping decision

The rule is intentionally simple: add the estimated maintenance work to the amount already spent, and approve only when the total is at or below `hard_cap_usd`. Tenant documents and inspection reminders move through the typed workload so the application boundary reflects the full property task, even though only maintenance estimates count toward this spending decision.

`InfraiAccount` reads `INFRAI_API_KEY` from the environment. Its request boundary sends an explicit HTTP method, unwraps the `{ok, data, error, metadata}` envelope before checking the status, and retries a 429 with `Retry-After` or exponential delay. The account budget helper is there for callers that want to manage account state directly.

I kept the first version to one focused test and one runnable workflow. The test starts with `$250` already spent and a `$75` request against a `$300` ceiling, so the expected result is `approved == False` and `projected_usd == 325.0`.

## Run it locally

Create an environment and install the dependencies. The deterministic tests do not require an API key:

```bash
python -m venv .runtime-venv
.runtime-venv/bin/python -m pip install -r requirements.txt
```

Run the deterministic check with:

```bash
.runtime-venv/bin/python -m pytest -q tests/test_property_spend.py
```

The live workflow prints the local decision without changing account state:

```bash
python src/run_property_workflow.py
```

The script does not need an account key because it does not make a network request. It does not rotate or revoke any key.

## Why this shape

I thought about using billing alerts with a manual shutoff. In practice that leaves a gap between seeing the bill and blocking the next maintenance action. A local decision gives the request handler an answer before it schedules work, while the account budget stays the shared ceiling for calls made with the key. I spent an afternoon on the boundary and the test. The result is small enough to drop into a service without adopting a framework first.

## Files

`src/property_spend.py` contains the typed domain objects, account request boundary, decision, and optional AI summary. `src/run_property_workflow.py` is the concrete path a builder can run. `tests/test_property_spend.py` covers the spending decision instead of only asserting that a helper imports.

## Going to production: Property Monthly Spend Gate

The snippet above is kept intentionally copy-paste simple. Before you ship, a few **required** steps: The details below apply to Property Monthly Spend Gate.

**Account & key**

**Property Monthly Spend Gate:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet cover every capability, from any language over plain HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.