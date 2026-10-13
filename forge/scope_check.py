# -*- coding: utf-8 -*-
"""forge.scope-check — API token scope authorization.

Problem: an endpoint requires a set of scopes R; the presented token carries
scopes T. Rule: the "admin:*" scope grants everything; otherwise the request
is allowed only when R is a subset of T.

Verification re-evaluates the rule from meta["required"] and
meta["token_scopes"] — the oracle is the scope engine, not the stored answer.
"""
import random

from .common import make_id, int_knob

TYPE = "scope-check"

POOL = ["read:users", "write:users", "read:billing", "admin:*"]
WILDCARD = "admin:*"


def _evaluate(required, token_scopes):
    """Return (allowed, missing_scopes) — missing is sorted, [] when wildcard."""
    tset = set(token_scopes)
    if WILDCARD in tset:
        return True, []
    missing = sorted(set(required) - tset)
    return (not missing), missing


def generate(seed, difficulty=0.5):
    rng = random.Random("scope-check|%d" % seed)
    required = sorted(rng.sample(POOL, int_knob(difficulty, 1, 3)))
    token = rng.sample(POOL, int_knob(difficulty, 1, 4))
    allowed, missing = _evaluate(required, token)
    return {
        "id": make_id(TYPE, seed),
        "type": TYPE,
        "difficulty": float(difficulty),
        "seed": int(seed),
        "prompt": ("An API token carries the scopes %s. The endpoint it calls "
                   "requires all of %s. Scope rule: the \"admin:*\" scope is a "
                   "wildcard that grants everything; otherwise the token must "
                   "contain every required scope. Is the request allowed, and "
                   "which required scopes are missing (empty list if none)?"
                   % (sorted(token), required)),
        "answer": {"allowed": allowed, "missing_scopes": missing},
        "solution": ("Wildcard check: %s. Subset check: required minus token "
                     "= %s. Decision: %s."
                     % ("token has admin:*, grants all" if WILDCARD in token
                        else "no wildcard, subset rule applies",
                        missing or "nothing missing",
                        "allowed" if allowed else "denied")),
        "meta": {"required": required, "token_scopes": sorted(token)},
    }


def verify(problem):
    try:
        required = list(problem["meta"]["required"])
        token = list(problem["meta"]["token_scopes"])
        allowed, missing = _evaluate(required, token)
        a = problem["answer"]
        return a["allowed"] == allowed and list(a["missing_scopes"]) == missing
    except (KeyError, TypeError, ValueError):
        return False


def self_cases():
    import copy
    cases = []
    for sd in range(5):
        cases.append(("gen-deterministic-%d" % sd,
                      lambda sd=sd: generate(sd, 0.5) == generate(sd, 0.5)))
    for d in (0.0, 0.25, 0.5, 0.75, 1.0):
        cases.append(("verify-true-d%.2f" % d,
                      lambda d=d: verify(generate(123 + int(d * 100), d))))
    base = generate(7, 0.5)
    p = copy.deepcopy(base)
    p["answer"]["allowed"] = not p["answer"]["allowed"]
    cases.append(("verify-false-flip-allowed", lambda p=p: verify(p) is False))
    p = copy.deepcopy(base)
    p["meta"]["required"].append("scope:tamper")
    cases.append(("verify-false-tampered-required",
                  lambda p=p: verify(p) is False))
    p = copy.deepcopy(base)
    p["answer"]["missing_scopes"].append("scope:tamper")
    cases.append(("verify-false-tampered-missing",
                  lambda p=p: verify(p) is False))
    from .common import schema_ok
    cases.append(("schema-ok", lambda: schema_ok(generate(42, 0.3))))
    cases.append(("wildcard-helper", lambda: _evaluate(
        ["read:users", "write:users"], [WILDCARD]) == (True, [])
        and _evaluate(["read:users"], ["write:users"]) == (False, ["read:users"])))
    return cases
