from property_spend import (
    InspectionReminder,
    MaintenanceRequest,
    PropertyWorkload,
    TenantDocument,
    decide_spend,
)


def main() -> None:
    workload = PropertyWorkload(
        maintenance=(MaintenanceRequest("3B", "leaking kitchen tap", 85.0),),
        tenant_documents=(TenantDocument("3B", "lease renewal"),),
        inspections=(InspectionReminder("3B", "2026-11-05"),),
    )
    decision = decide_spend(workload, hard_cap_usd=300.0, already_spent_usd=240.0)
    print({"approved": decision.approved, "projected_usd": decision.projected_usd})


if __name__ == "__main__":
    main()
