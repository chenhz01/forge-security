# -*- coding: utf-8 -*-
"""forge.cors-check — reference implementation.

Problem: given a CORS policy (allowed origins, allowed methods,
allow-credentials) and an incoming request (origin, method), decide whether
the request is allowed. Verification re-evaluates the policy from meta —
the oracle is the policy engine, not the stored answer.
"""
import random

from .common import make_id, int_knob, knob

TYPE = "cors-check"

ORIGINS = ["https://app.example.com", "https://admin.example.com",
           "https://partner.io", "https://evil.example.net", "null"]
METHODS = ["GET", "POST", "PUT", "DELETE"]


def _evaluate(policy, req):
    origin, method = req
    if origin not in policy["allowed_origins"] and "*" not in policy["allowed_origins"]:
        return False
    if method not in policy["allowed_methods"] and "*" not in policy["allowed_methods"]:
        return False
    if method == "DELETE" and not policy["allow_credentials"] and policy["delete_needs_credentials"]:
        return False
    return True


def generate(seed, difficulty=0.5):
    rng = random.Random("cors-check|%d" % seed)
    n_origins = int_knob(difficulty, 2, 4)
    allowed_origins = rng.sample(ORIGINS[:4], n_origins)
    if difficulty > 0.6 and rng.random() < 0.5:
        allowed_origins = ["*"]
    allowed_methods = rng.sample(METHODS, int_knob(difficulty, 2, 4))
    policy = {"allowed_origins": allowed_origins,
              "allowed_methods": allowed_methods,
              "allow_credentials": rng.random() < 0.6,
              "delete_needs_credentials": True}
    req_origin = rng.choice(ORIGINS)
    req_method = rng.choice(METHODS)
    allowed = _evaluate(policy, (req_origin, req_method))
    reason = ("origin allowed" if req_origin in allowed_origins or "*" in allowed_origins
              else "origin not in allowlist")
    return {
        "id": make_id(TYPE, seed),
        "type": TYPE,
        "difficulty": float(difficulty),
        "seed": int(seed),
        "prompt": ("CORS policy: allowed_origins=%s, allowed_methods=%s, "
                   "allow_credentials=%s. A request arrives with Origin=%s, "
                   "method=%s. Is it allowed by the policy?"
                   % (allowed_origins, allowed_methods,
                      policy["allow_credentials"], req_origin, req_method)),
        "answer": {"allowed": allowed, "reason": reason},
        "solution": "Origin check: %s. Method check: %s. Decision: %s."
                    % (reason, method if (method := req_method) else "",
                       "allowed" if allowed else "denied"),
        "meta": {"policy": policy, "request": [req_origin, req_method]},
    }


def verify(problem):
    try:
        policy = problem["meta"]["policy"]
        origin, method = problem["meta"]["request"]
        allowed = _evaluate(policy, (origin, method))
        reason = ("origin allowed" if origin in policy["allowed_origins"] or "*" in policy["allowed_origins"]
                  else "origin not in allowlist")
        a = problem["answer"]
        return (a["allowed"] == allowed and a["reason"] == reason)
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
    cases.append(("verify-false-flip", lambda p=p: verify(p) is False))
    p = copy.deepcopy(base)
    off = [o for o in ORIGINS if o not in base["meta"]["policy"]["allowed_origins"]]
    p["meta"]["request"][0] = off[0] if off else "null"
    cases.append(("verify-false-tampered-origin", lambda p=p: verify(p) is False))
    p = copy.deepcopy(base)
    p["answer"].pop("reason")
    cases.append(("verify-false-missing-reason", lambda p=p: verify(p) is False))
    from .common import schema_ok
    cases.append(("schema-ok", lambda: schema_ok(generate(42, 0.3))))
    cases.append(("wildcard-origin", lambda: _evaluate(
        {"allowed_origins": ["*"], "allowed_methods": ["GET"],
         "allow_credentials": True, "delete_needs_credentials": False},
        ("https://anything.tld", "GET"))))
    return cases
