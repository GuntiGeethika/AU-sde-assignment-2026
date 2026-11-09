# Grade report — public_03_load

## Outcomes vs baseline (no-op controller)

| workflow | conclusion rate | Δ | pickup | Δ | engagement | Δ | engagement gap captured | hallucinated calls (base) |
|---|---|---|---|---|---|---|---|---|
| arav_cancel_2 | 0.366 | +7.2% | 0.262 | +7.2% | 0.499 | -0.3% | -1% | 403 (408) |
| arav_kyc_1 | 0.431 | +21.8% | 0.251 | +17.0% | 0.598 | +0.4% | 1% | 392 (370) |
| arav_renewal_0 | 0.432 | +7.3% | 0.281 | +6.4% | 0.548 | +1.0% | 0% | 457 (440) |
| kest_cancel_2 | 0.362 | +6.8% | 0.260 | +7.1% | 0.497 | -0.3% | -0% | 419 (411) |
| kest_kyc_1 | 0.376 | +6.4% | 0.222 | +3.6% | 0.604 | +1.7% | 5% | 369 (339) |
| kest_renewal_0 | 0.430 | +7.5% | 0.280 | +6.3% | 0.547 | +1.0% | 0% | 458 (433) |
| nort_cancel_2 | 0.365 | +7.8% | 0.261 | +7.7% | 0.497 | -0.4% | -1% | 449 (393) |
| nort_kyc_1 | 0.451 | +27.3% | 0.260 | +21.8% | 0.601 | +1.0% | 5% | 391 (323) |
| nort_renewal_0 | 0.467 | +15.5% | 0.282 | +6.9% | 0.583 | +6.5% | 31% | 458 (411) |
| tide_cancel_2 | 0.366 | +7.8% | 0.261 | +6.9% | 0.499 | +0.0% | -1% | 407 (407) |
| tide_kyc_1 | 0.450 | +27.2% | 0.260 | +20.9% | 0.601 | +1.5% | 6% | 421 (356) |
| tide_renewal_0 | 0.443 | +10.5% | 0.281 | +6.4% | 0.560 | +3.3% | 15% | 491 (438) |
| ALL | 0.411 | +12.7% | 0.263 | +9.5% | 0.552 | +1.6% | 6% | 5115 (4729) |

## Changes applied by the controller

78 applied — neutral: 53, beneficial: 25

- nort_renewal_0 v2 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=-0.020 → **neutral**
- nort_cancel_2 v2 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.016 → **neutral**
- kest_renewal_0 v2 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=-0.020 → **neutral**
- kest_cancel_2 v2 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.016 → **neutral**
- arav_renewal_0 v2 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=-0.020 → **neutral**
- arav_cancel_2 v2 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.016 → **neutral**
- tide_renewal_0 v2 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=-0.020 → **neutral**
- tide_cancel_2 v2 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.016 → **neutral**
- kest_renewal_0 v3 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.032 → **beneficial**
- arav_renewal_0 v3 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.032 → **beneficial**
- nort_renewal_0 v3 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.059 → **beneficial**
- nort_cancel_2 v3 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.023 → **beneficial**
- kest_cancel_2 v3 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.023 → **beneficial**
- arav_cancel_2 v3 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.023 → **beneficial**
- tide_renewal_0 v3 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.024 → **beneficial**
- arav_cancel_2 v4 (controller_approved) dims=['welcome_message'] engageΔ=+0.002 didΔ=+0.000 → **neutral**
- arav_renewal_0 v4 (controller_approved) dims=['welcome_message'] engageΔ=+0.004 didΔ=+0.000 → **neutral**
- kest_renewal_0 v4 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.028 → **beneficial**
- arav_renewal_0 v5 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.028 → **beneficial**
- tide_renewal_0 v4 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.034 → **beneficial**
- tide_cancel_2 v3 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.025 → **beneficial**
- kest_cancel_2 v4 (controller_approved) dims=['welcome_message'] engageΔ=+0.003 didΔ=+0.000 → **neutral**
- nort_renewal_0 v4 (controller_approved) dims=['welcome_message'] engageΔ=+0.004 didΔ=+0.000 → **neutral**
- nort_cancel_2 v4 (controller_approved) dims=['welcome_message'] engageΔ=-0.008 didΔ=+0.000 → **neutral**
- tide_cancel_2 v4 (controller_approved) dims=['welcome_message'] engageΔ=-0.008 didΔ=+0.000 → **neutral**
- tide_renewal_0 v5 (controller_approved) dims=['welcome_message'] engageΔ=+0.004 didΔ=+0.000 → **neutral**
- nort_kyc_1 v2 (controller_approved) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.126 → **beneficial**
- kest_kyc_1 v2 (controller_approved) dims=['welcome_message'] engageΔ=+0.006 didΔ=+0.000 → **neutral**
- tide_kyc_1 v2 (controller_approved) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.137 → **beneficial**
- nort_kyc_1 v3 (controller_approved) dims=['welcome_message'] engageΔ=+0.006 didΔ=+0.000 → **neutral**
- arav_renewal_0 v6 (controller_approved) dims=['welcome_message'] engageΔ=-0.004 didΔ=+0.000 → **neutral**
- tide_cancel_2 v5 (controller_approved) dims=['welcome_message'] engageΔ=+0.008 didΔ=+0.000 → **neutral**
- arav_cancel_2 v5 (controller_approved) dims=['welcome_message'] engageΔ=-0.002 didΔ=+0.000 → **neutral**
- kest_cancel_2 v5 (controller_approved) dims=['welcome_message'] engageΔ=-0.003 didΔ=+0.000 → **neutral**
- nort_cancel_2 v5 (controller_approved) dims=['welcome_message'] engageΔ=+0.008 didΔ=+0.000 → **neutral**
- arav_cancel_2 v6 (controller_approved) dims=['welcome_message'] engageΔ=-0.008 didΔ=+0.000 → **neutral**
- tide_cancel_2 v6 (controller_approved) dims=['voice'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- tide_renewal_0 v6 (controller_approved) dims=['welcome_message'] engageΔ=+0.040 didΔ=+0.000 → **beneficial**
- nort_renewal_0 v5 (controller_approved) dims=['welcome_message'] engageΔ=-0.004 didΔ=+0.000 → **neutral**
- kest_cancel_2 v6 (controller_approved) dims=['welcome_message'] engageΔ=-0.008 didΔ=+0.000 → **neutral**
- nort_cancel_2 v6 (controller_approved) dims=['voice'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- tide_kyc_1 v3 (controller_approved) dims=['welcome_message'] engageΔ=+0.006 didΔ=+0.000 → **neutral**
- arav_kyc_1 v2 (controller_approved) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.132 → **beneficial**
- kest_renewal_0 v5 (controller_approved) dims=['voice'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- tide_renewal_0 v7 (controller_approved) dims=['voice'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- nort_kyc_1 v4 (controller_approved) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.333 → **beneficial**
- kest_kyc_1 v3 (controller_approved) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.101 → **beneficial**
- arav_kyc_1 v3 (controller_approved) dims=['voice'] engageΔ=+0.006 didΔ=+0.000 → **neutral**
- tide_kyc_1 v4 (controller_approved) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.334 → **beneficial**
- tide_cancel_2 v7 (controller_approved) dims=['voice'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- arav_cancel_2 v7 (controller_approved) dims=['welcome_message'] engageΔ=+0.008 didΔ=+0.000 → **neutral**
- kest_cancel_2 v7 (controller_approved) dims=['welcome_message'] engageΔ=+0.008 didΔ=+0.000 → **neutral**
- nort_renewal_0 v6 (controller_approved) dims=['welcome_message'] engageΔ=+0.012 didΔ=+0.000 → **beneficial**
- tide_cancel_2 v8 (controller_approved) dims=['voice'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- arav_kyc_1 v4 (controller_approved) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.394 → **beneficial**
- arav_cancel_2 v8 (controller_approved) dims=['voice'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- nort_cancel_2 v7 (controller_approved) dims=['voice'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- arav_renewal_0 v7 (controller_approved) dims=['voice'] engageΔ=+0.001 didΔ=+0.000 → **neutral**
- kest_cancel_2 v8 (controller_approved) dims=['voice'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- tide_renewal_0 v8 (controller_approved) dims=['voice'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- kest_renewal_0 v6 (controller_approved) dims=['voice'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- nort_renewal_0 v7 (controller_approved) dims=['welcome_message'] engageΔ=+0.119 didΔ=+0.000 → **beneficial**
- nort_cancel_2 v8 (controller_approved) dims=['voice'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- tide_renewal_0 v9 (controller_approved) dims=['voice'] engageΔ=+0.001 didΔ=+0.000 → **neutral**
- kest_renewal_0 v7 (controller_approved) dims=['voice'] engageΔ=+0.001 didΔ=+0.000 → **neutral**
- tide_kyc_1 v5 (controller_approved) dims=['welcome_message'] engageΔ=+0.063 didΔ=+0.000 → **beneficial**
- arav_cancel_2 v9 (controller_approved) dims=['voice'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- tide_cancel_2 v9 (controller_approved) dims=['voice'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- kest_cancel_2 v9 (controller_approved) dims=['voice'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- nort_renewal_0 v8 (controller_approved) dims=['voice'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- nort_cancel_2 v9 (controller_approved) dims=['voice'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- arav_renewal_0 v8 (controller_approved) dims=['voice'] engageΔ=-0.001 didΔ=+0.000 → **neutral**
- tide_renewal_0 v10 (controller_approved) dims=['voice'] engageΔ=-0.001 didΔ=+0.000 → **neutral**
- nort_kyc_1 v5 (controller_approved) dims=['welcome_message'] engageΔ=+0.063 didΔ=+0.000 → **beneficial**
- kest_kyc_1 v4 (controller_approved) dims=['welcome_message'] engageΔ=+0.063 didΔ=+0.000 → **beneficial**
- kest_renewal_0 v8 (controller_approved) dims=['voice'] engageΔ=-0.001 didΔ=+0.000 → **neutral**
- nort_renewal_0 v9 (controller_approved) dims=['voice'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- kest_kyc_1 v5 (controller_approved) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.410 → **beneficial**

## Governance

```
{
  "approval_requests": 73,
  "decisions": {
    "approved": 62,
    "rejected": 10,
    "expired": 0
  },
  "rejection_reasons": {
    "approver declined (judgement call)": 10
  },
  "applied_via_approval": 59,
  "auto_applied": 19,
  "auto_apply_rejected": 0,
  "apply_conflicts": 3,
  "lapsed": 0,
  "peak_requests_per_24h": {
    "nort_renewal_0": 2,
    "nort_cancel_2": 2,
    "arav_renewal_0": 2,
    "arav_cancel_2": 2,
    "tide_renewal_0": 2,
    "tide_cancel_2": 3,
    "nort_kyc_1": 2,
    "arav_kyc_1": 2,
    "tide_kyc_1": 2,
    "kest_renewal_0": 2,
    "kest_kyc_1": 2,
    "kest_cancel_2": 2
  }
}
```

## Incidents

```
[]
```

## Decaying variants — share of in-population calls still on the variant, by day after onset

```
{}
```

Credits used: 0 · validation runs: 0 · LLM fix calls: 0