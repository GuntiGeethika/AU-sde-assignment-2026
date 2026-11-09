# Grade report — public_03_load

## Outcomes vs baseline (no-op controller)

| workflow | conclusion rate | Δ | pickup | Δ | engagement | Δ | engagement gap captured | hallucinated calls (base) |
|---|---|---|---|---|---|---|---|---|
| arav_cancel_2 | 0.362 | +6.1% | 0.260 | +6.6% | 0.498 | -0.5% | -1% | 420 (408) |
| arav_kyc_1 | 0.479 | +35.3% | 0.275 | +28.0% | 0.600 | +0.7% | 2% | 488 (370) |
| arav_renewal_0 | 0.452 | +12.5% | 0.280 | +6.2% | 0.572 | +5.3% | 23% | 447 (440) |
| kest_cancel_2 | 0.361 | +6.5% | 0.260 | +7.0% | 0.496 | -0.5% | -0% | 426 (411) |
| kest_kyc_1 | 0.400 | +13.3% | 0.237 | +10.9% | 0.594 | +0.0% | 1% | 396 (339) |
| kest_renewal_0 | 0.468 | +17.1% | 0.280 | +6.2% | 0.587 | +8.2% | 36% | 471 (433) |
| nort_cancel_2 | 0.370 | +9.2% | 0.261 | +7.6% | 0.506 | +1.4% | 13% | 439 (393) |
| nort_kyc_1 | 0.475 | +34.2% | 0.274 | +28.5% | 0.597 | +0.2% | 1% | 445 (323) |
| nort_renewal_0 | 0.463 | +14.4% | 0.280 | +6.4% | 0.585 | +6.8% | 39% | 466 (411) |
| tide_cancel_2 | 0.362 | +6.7% | 0.260 | +6.6% | 0.495 | -0.9% | -1% | 427 (407) |
| tide_kyc_1 | 0.482 | +36.5% | 0.275 | +28.3% | 0.602 | +1.6% | 6% | 444 (356) |
| tide_renewal_0 | 0.460 | +14.9% | 0.282 | +6.8% | 0.574 | +5.8% | 25% | 439 (438) |
| ALL | 0.428 | +17.3% | 0.269 | +11.8% | 0.559 | +2.9% | 14% | 5308 (4729) |

## Changes applied by the controller

75 applied — neutral: 46, beneficial: 29

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
- tide_cancel_2 v3 (controller_approved) dims=['welcome_message', 'caller_id'] engageΔ=+0.002 didΔ=+0.025 → **beneficial**
- kest_renewal_0 v4 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.028 → **beneficial**
- arav_renewal_0 v4 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.028 → **beneficial**
- nort_cancel_2 v4 (controller_approved) dims=['welcome_message'] engageΔ=+0.002 didΔ=+0.000 → **neutral**
- kest_cancel_2 v4 (controller_approved) dims=['welcome_message'] engageΔ=+0.002 didΔ=+0.000 → **neutral**
- arav_cancel_2 v4 (controller_approved) dims=['welcome_message'] engageΔ=+0.002 didΔ=+0.000 → **neutral**
- tide_renewal_0 v4 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.034 → **beneficial**
- arav_kyc_1 v2 (controller_approved) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.109 → **beneficial**
- nort_kyc_1 v2 (controller_approved) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.113 → **beneficial**
- arav_renewal_0 v5 (controller_approved) dims=['welcome_message'] engageΔ=+0.004 didΔ=+0.000 → **neutral**
- nort_renewal_0 v4 (controller_approved) dims=['welcome_message'] engageΔ=+0.012 didΔ=+0.000 → **beneficial**
- arav_kyc_1 v3 (controller_approved) dims=['welcome_message'] engageΔ=+0.006 didΔ=+0.000 → **neutral**
- tide_kyc_1 v2 (controller_approved) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.131 → **beneficial**
- tide_renewal_0 v5 (controller_approved) dims=['welcome_message'] engageΔ=+0.004 didΔ=+0.000 → **neutral**
- nort_kyc_1 v3 (controller_approved) dims=['welcome_message'] engageΔ=+0.006 didΔ=+0.000 → **neutral**
- kest_kyc_1 v2 (controller_approved) dims=['voice', 'caller_id'] engageΔ=+0.006 didΔ=+0.099 → **beneficial**
- tide_kyc_1 v3 (controller_approved) dims=['welcome_message'] engageΔ=+0.006 didΔ=+0.000 → **neutral**
- nort_cancel_2 v5 (controller_approved) dims=['welcome_message'] engageΔ=+0.025 didΔ=+0.000 → **beneficial**
- arav_cancel_2 v5 (controller_approved) dims=['welcome_message'] engageΔ=-0.002 didΔ=+0.000 → **neutral**
- tide_cancel_2 v4 (controller_approved) dims=['welcome_message'] engageΔ=-0.002 didΔ=+0.000 → **neutral**
- tide_cancel_2 v5 (controller_approved) dims=['welcome_message'] engageΔ=-0.008 didΔ=+0.000 → **neutral**
- kest_cancel_2 v5 (controller_approved) dims=['welcome_message'] engageΔ=-0.002 didΔ=+0.000 → **neutral**
- nort_cancel_2 v6 (controller_approved) dims=['voice'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- kest_renewal_0 v5 (controller_approved) dims=['welcome_message'] engageΔ=+0.012 didΔ=+0.000 → **beneficial**
- arav_renewal_0 v6 (controller_approved) dims=['welcome_message'] engageΔ=-0.004 didΔ=+0.000 → **neutral**
- nort_renewal_0 v5 (controller_approved) dims=['welcome_message'] engageΔ=+0.120 didΔ=+0.000 → **beneficial**
- arav_cancel_2 v6 (controller_approved) dims=['welcome_message'] engageΔ=-0.008 didΔ=+0.000 → **neutral**
- kest_cancel_2 v6 (controller_approved) dims=['welcome_message'] engageΔ=-0.008 didΔ=+0.000 → **neutral**
- tide_kyc_1 v4 (controller_approved) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.436 → **beneficial**
- nort_kyc_1 v4 (controller_approved) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.439 → **beneficial**
- tide_renewal_0 v6 (controller_approved) dims=['welcome_message'] engageΔ=-0.004 didΔ=+0.000 → **neutral**
- arav_kyc_1 v4 (controller_approved) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.450 → **beneficial**
- nort_renewal_0 v6 (controller_approved) dims=['voice'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- arav_renewal_0 v7 (controller_approved) dims=['welcome_message'] engageΔ=+0.012 didΔ=+0.000 → **beneficial**
- tide_renewal_0 v7 (controller_approved) dims=['welcome_message'] engageΔ=+0.012 didΔ=+0.000 → **beneficial**
- kest_renewal_0 v6 (controller_approved) dims=['welcome_message'] engageΔ=+0.120 didΔ=+0.000 → **beneficial**
- nort_cancel_2 v7 (controller_approved) dims=['voice'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- kest_cancel_2 v7 (controller_approved) dims=['welcome_message'] engageΔ=+0.008 didΔ=+0.000 → **neutral**
- arav_cancel_2 v7 (controller_approved) dims=['welcome_message'] engageΔ=+0.008 didΔ=+0.000 → **neutral**
- tide_cancel_2 v6 (controller_approved) dims=['welcome_message'] engageΔ=+0.008 didΔ=+0.000 → **neutral**
- nort_cancel_2 v8 (controller_approved) dims=['voice'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- arav_cancel_2 v8 (controller_approved) dims=['voice'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- nort_renewal_0 v7 (controller_approved) dims=['voice'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- tide_cancel_2 v7 (controller_approved) dims=['voice'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- kest_cancel_2 v8 (controller_approved) dims=['voice'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- arav_kyc_1 v5 (controller_approved) dims=['welcome_message'] engageΔ=-0.006 didΔ=+0.000 → **neutral**
- nort_renewal_0 v8 (controller_approved) dims=['voice'] engageΔ=+0.001 didΔ=+0.000 → **neutral**
- kest_renewal_0 v7 (controller_approved) dims=['voice'] engageΔ=+0.001 didΔ=+0.000 → **neutral**
- tide_kyc_1 v5 (controller_approved) dims=['welcome_message'] engageΔ=+0.063 didΔ=+0.000 → **beneficial**
- arav_kyc_1 v6 (controller_approved) dims=['voice'] engageΔ=+0.006 didΔ=+0.000 → **neutral**
- tide_renewal_0 v8 (controller_approved) dims=['welcome_message'] engageΔ=+0.120 didΔ=+0.000 → **beneficial**
- arav_cancel_2 v9 (controller_approved) dims=['voice'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- nort_cancel_2 v9 (controller_approved) dims=['voice'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- kest_cancel_2 v9 (controller_approved) dims=['voice'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- arav_renewal_0 v8 (controller_approved) dims=['welcome_message'] engageΔ=+0.119 didΔ=+0.000 → **beneficial**
- tide_cancel_2 v8 (controller_approved) dims=['voice'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- kest_kyc_1 v3 (controller_approved) dims=['voice', 'caller_id'] engageΔ=-0.006 didΔ=+0.387 → **beneficial**
- nort_kyc_1 v5 (controller_approved) dims=['welcome_message'] engageΔ=-0.006 didΔ=+0.000 → **neutral**
- kest_renewal_0 v8 (controller_approved) dims=['voice'] engageΔ=-0.000 didΔ=+0.000 → **neutral**
- nort_renewal_0 v9 (controller_approved) dims=['voice'] engageΔ=-0.000 didΔ=+0.000 → **neutral**

## Governance

```
{
  "approval_requests": 70,
  "decisions": {
    "approved": 60,
    "rejected": 10,
    "expired": 0
  },
  "rejection_reasons": {
    "approver declined (judgement call)": 10
  },
  "applied_via_approval": 57,
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
    "tide_cancel_2": 2,
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
  "nort_renewal_0:welcome_message=W3": {
    "3": 0.902,
    "4": 0.899
  },
  "kest_renewal_0:welcome_message=W3": {
    "4": 0.901
  },
  "arav_renewal_0:welcome_message=W3": {
    "4": 0.9
  }
}
```

Credits used: 0 · validation runs: 0 · LLM fix calls: 0