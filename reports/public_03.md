# Grade report — public_03_load

## Outcomes vs baseline (no-op controller)

| workflow | conclusion rate | Δ | pickup | Δ | engagement | Δ | engagement gap captured | hallucinated calls (base) |
|---|---|---|---|---|---|---|---|---|
| arav_cancel_2 | 0.363 | +6.3% | 0.262 | +7.1% | 0.495 | -1.1% | -1% | 426 (408) |
| arav_kyc_1 | 0.475 | +34.1% | 0.274 | +27.6% | 0.595 | -0.1% | 1% | 451 (370) |
| arav_renewal_0 | 0.462 | +14.9% | 0.280 | +6.1% | 0.582 | +7.2% | 31% | 448 (440) |
| kest_cancel_2 | 0.365 | +7.7% | 0.262 | +7.7% | 0.497 | -0.3% | -0% | 440 (411) |
| kest_kyc_1 | 0.472 | +33.6% | 0.273 | +27.5% | 0.594 | +0.0% | 2% | 446 (339) |
| kest_renewal_0 | 0.445 | +11.4% | 0.281 | +6.6% | 0.561 | +3.5% | 15% | 469 (433) |
| nort_cancel_2 | 0.377 | +11.3% | 0.263 | +8.4% | 0.510 | +2.1% | 14% | 429 (393) |
| nort_kyc_1 | 0.449 | +26.6% | 0.259 | +21.5% | 0.598 | +0.5% | 2% | 399 (323) |
| nort_renewal_0 | 0.471 | +16.5% | 0.282 | +6.9% | 0.589 | +7.5% | 35% | 453 (411) |
| tide_cancel_2 | 0.387 | +14.1% | 0.261 | +7.1% | 0.524 | +4.9% | 35% | 388 (407) |
| tide_kyc_1 | 0.471 | +33.2% | 0.274 | +27.5% | 0.592 | +0.1% | 1% | 498 (356) |
| tide_renewal_0 | 0.465 | +16.0% | 0.279 | +5.8% | 0.588 | +8.5% | 39% | 452 (438) |
| ALL | 0.433 | +18.7% | 0.271 | +12.6% | 0.561 | +3.2% | 15% | 5299 (4729) |

## Changes applied by the controller

85 applied — neutral: 56, beneficial: 29

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
- tide_cancel_2 v3 (controller_approved) dims=['welcome_message', 'caller_id'] engageΔ=+0.002 didΔ=+0.024 → **beneficial**
- nort_renewal_0 v4 (controller_approved) dims=['welcome_message'] engageΔ=+0.004 didΔ=+0.000 → **neutral**
- kest_renewal_0 v4 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.028 → **beneficial**
- arav_renewal_0 v4 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.028 → **beneficial**
- nort_cancel_2 v4 (controller_approved) dims=['welcome_message'] engageΔ=+0.002 didΔ=+0.000 → **neutral**
- kest_cancel_2 v4 (controller_approved) dims=['welcome_message'] engageΔ=+0.002 didΔ=+0.000 → **neutral**
- tide_renewal_0 v4 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.034 → **beneficial**
- arav_kyc_1 v2 (controller_approved) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.118 → **beneficial**
- tide_renewal_0 v5 (controller_approved) dims=['welcome_message'] engageΔ=+0.012 didΔ=+0.000 → **beneficial**
- nort_kyc_1 v2 (controller_approved) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.124 → **beneficial**
- tide_cancel_2 v4 (controller_approved) dims=['welcome_message'] engageΔ=+0.025 didΔ=+0.000 → **beneficial**
- kest_kyc_1 v2 (controller_approved) dims=['welcome_message', 'caller_id'] engageΔ=+0.006 didΔ=+0.127 → **beneficial**
- arav_renewal_0 v5 (controller_approved) dims=['welcome_message'] engageΔ=+0.004 didΔ=+0.000 → **neutral**
- arav_kyc_1 v3 (controller_approved) dims=['welcome_message'] engageΔ=+0.006 didΔ=+0.000 → **neutral**
- tide_kyc_1 v2 (controller_approved) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.135 → **beneficial**
- nort_kyc_1 v3 (controller_approved) dims=['welcome_message'] engageΔ=+0.006 didΔ=+0.000 → **neutral**
- nort_cancel_2 v5 (controller_approved) dims=['welcome_message'] engageΔ=+0.025 didΔ=+0.000 → **beneficial**
- tide_cancel_2 v5 (controller_approved) dims=['voice'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- kest_renewal_0 v5 (controller_approved) dims=['welcome_message'] engageΔ=+0.004 didΔ=+0.000 → **neutral**
- tide_cancel_2 v6 (controller_approved) dims=['voice'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- nort_cancel_2 v6 (controller_approved) dims=['voice'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- arav_cancel_2 v5 (controller_approved) dims=['welcome_message'] engageΔ=-0.002 didΔ=+0.000 → **neutral**
- kest_renewal_0 v6 (controller_approved) dims=['welcome_message'] engageΔ=+0.040 didΔ=+0.000 → **beneficial**
- nort_renewal_0 v5 (controller_approved) dims=['welcome_message'] engageΔ=-0.004 didΔ=+0.000 → **neutral**
- kest_cancel_2 v5 (controller_approved) dims=['welcome_message'] engageΔ=-0.002 didΔ=+0.000 → **neutral**
- arav_renewal_0 v6 (controller_approved) dims=['welcome_message'] engageΔ=-0.004 didΔ=+0.000 → **neutral**
- tide_renewal_0 v6 (controller_approved) dims=['welcome_message'] engageΔ=+0.119 didΔ=+0.000 → **beneficial**
- arav_cancel_2 v6 (controller_approved) dims=['welcome_message'] engageΔ=-0.008 didΔ=+0.000 → **neutral**
- tide_kyc_1 v3 (controller_approved) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.405 → **beneficial**
- kest_kyc_1 v3 (controller_approved) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.412 → **beneficial**
- arav_kyc_1 v4 (controller_approved) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.419 → **beneficial**
- tide_cancel_2 v7 (controller_approved) dims=['voice'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- nort_renewal_0 v6 (controller_approved) dims=['welcome_message'] engageΔ=+0.012 didΔ=+0.000 → **beneficial**
- kest_cancel_2 v6 (controller_approved) dims=['welcome_message'] engageΔ=-0.008 didΔ=+0.000 → **neutral**
- tide_kyc_1 v4 (controller_approved) dims=['welcome_message'] engageΔ=+0.006 didΔ=+0.000 → **neutral**
- kest_renewal_0 v7 (controller_approved) dims=['voice'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- arav_renewal_0 v7 (controller_approved) dims=['welcome_message'] engageΔ=+0.012 didΔ=+0.000 → **beneficial**
- tide_renewal_0 v7 (controller_approved) dims=['voice'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- nort_cancel_2 v7 (controller_approved) dims=['voice'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- arav_cancel_2 v7 (controller_approved) dims=['welcome_message'] engageΔ=+0.008 didΔ=+0.000 → **neutral**
- nort_renewal_0 v7 (controller_approved) dims=['welcome_message'] engageΔ=+0.119 didΔ=+0.000 → **beneficial**
- nort_cancel_2 v8 (controller_approved) dims=['voice'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- kest_cancel_2 v7 (controller_approved) dims=['welcome_message'] engageΔ=+0.008 didΔ=+0.000 → **neutral**
- nort_kyc_1 v4 (controller_approved) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.365 → **beneficial**
- arav_kyc_1 v5 (controller_approved) dims=['welcome_message'] engageΔ=-0.006 didΔ=+0.000 → **neutral**
- tide_cancel_2 v8 (controller_approved) dims=['voice'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- kest_renewal_0 v8 (controller_approved) dims=['voice'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- arav_cancel_2 v8 (controller_approved) dims=['voice'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- tide_renewal_0 v8 (controller_approved) dims=['voice'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- tide_cancel_2 v9 (controller_approved) dims=['voice'] engageΔ=+0.007 didΔ=+0.000 → **neutral**
- arav_renewal_0 v8 (controller_approved) dims=['welcome_message'] engageΔ=+0.119 didΔ=+0.000 → **beneficial**
- kest_cancel_2 v8 (controller_approved) dims=['voice'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- tide_renewal_0 v9 (controller_approved) dims=['voice'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- kest_kyc_1 v4 (controller_approved) dims=['welcome_message'] engageΔ=-0.006 didΔ=+0.000 → **neutral**
- arav_renewal_0 v9 (controller_approved) dims=['voice'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- kest_renewal_0 v9 (controller_approved) dims=['voice'] engageΔ=+0.001 didΔ=+0.000 → **neutral**
- nort_kyc_1 v5 (controller_approved) dims=['welcome_message'] engageΔ=-0.006 didΔ=+0.000 → **neutral**
- kest_kyc_1 v5 (controller_approved) dims=['voice'] engageΔ=+0.006 didΔ=+0.000 → **neutral**
- nort_cancel_2 v9 (controller_approved) dims=['voice'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- arav_cancel_2 v9 (controller_approved) dims=['voice'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- tide_cancel_2 v10 (controller_approved) dims=['voice'] engageΔ=+0.070 didΔ=+0.000 → **beneficial**
- nort_renewal_0 v8 (controller_approved) dims=['voice'] engageΔ=+0.001 didΔ=+0.000 → **neutral**
- kest_cancel_2 v9 (controller_approved) dims=['voice'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- arav_renewal_0 v10 (controller_approved) dims=['voice'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- tide_kyc_1 v5 (controller_approved) dims=['welcome_message'] engageΔ=-0.006 didΔ=+0.000 → **neutral**
- tide_renewal_0 v10 (controller_approved) dims=['voice'] engageΔ=-0.000 didΔ=+0.000 → **neutral**
- kest_renewal_0 v10 (controller_approved) dims=['voice'] engageΔ=-0.001 didΔ=+0.000 → **neutral**
- nort_renewal_0 v9 (controller_approved) dims=['voice'] engageΔ=-0.000 didΔ=+0.000 → **neutral**
- kest_kyc_1 v6 (controller_approved) dims=['voice'] engageΔ=-0.006 didΔ=+0.000 → **neutral**

## Governance

```
{
  "approval_requests": 73,
  "decisions": {
    "approved": 69,
    "rejected": 4,
    "expired": 0
  },
  "rejection_reasons": {
    "approver declined (judgement call)": 4
  },
  "applied_via_approval": 67,
  "auto_applied": 18,
  "auto_apply_rejected": 0,
  "apply_conflicts": 0,
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
{
  "tide_renewal_0:welcome_message=W3": {
    "3": 0.901,
    "4": 0.898
  },
  "nort_renewal_0:welcome_message=W3": {
    "4": 0.899
  },
  "arav_renewal_0:welcome_message=W3": {
    "4": 0.899
  }
}
```

Credits used: 0 · validation runs: 0 · LLM fix calls: 0