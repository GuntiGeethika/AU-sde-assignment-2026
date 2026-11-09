"""Controller-side policy: tunables and voluntary limits that are stricter than the platform's."""

# Voluntary per-tenant limits we chose to honour (see SUBMISSION.md §3). Platform policy still applies on top.
TENANT_OVERRIDES = {
    "kestrel_finance": {"earliest_request_hour": 11, "max_requests_per_24h": 2},
}

# experiments
EXPLORE_SHARE = 0.10          # traffic share given to a single challenger arm
HOLDOUT_SHARE = 0.10          # share kept on the old control after promotion (decay detection)
MIN_ARM_CONNECTED = 250       # minimum connected calls in the challenger arm before a win can be declared
HARM_MIN_CONNECTED = 100      # earliest point we stop an arm for looking worse
HARM_Z = -2.0
FUTILITY_CONNECTED = 700      # give up after this many connected calls with no win
FAMILY_ALPHA = 0.05           # one-sided, Bonferroni-split across all challengers of a dimension
GUARDRAIL_SLACK = 0.02        # absolute drop allowed on the guardrail KPI
DECAY_WINDOW_HOURS = 36
DECAY_MIN_CONNECTED = 150
DECAY_Z = -2.0

# caller ID
DID_WINDOW_HOURS = 6
DID_MIN_DIALS = 150
DID_FLAG_Z = -3.0
DID_FLAG_RATIO = 0.75
DID_PROBE_SHARE = 0.02
DID_EXPLORE_SHARE = 0.10
DID_MIN_TV_TO_ACT = 0.05
DID_COOLDOWN_MIN = 120

# hallucination
HALLUC_WINDOW_HOURS = 8
HALLUC_MIN_CONNECTED = 150
HALLUC_Z = 3.0
VALIDATION_N = 200
CREDIT_RESERVE = 10
VERIFY_MIN_CONNECTED = 300
