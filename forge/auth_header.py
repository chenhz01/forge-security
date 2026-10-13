# -*- coding: utf-8 -*-
"""forge.auth-header — HTTP Authorization header compliance.

Problem: a service validates the incoming Authorization header against a
rule set (exact scheme, minimum token length, safe token charset). Decide
whether the header is accepted and, if not, which rule it violates.

Verification re-evaluates the rules from meta["rules"] and meta["header"] —
the oracle is the header engine, not the stored answer.
"""
import random

from .common import make_id, int_knob

TYPE = "auth-header"

SCHEME = "Bearer"
SAFE_CHARS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                 "abcdefghijklmnopqrstuvwxyz0123456789._-")
VIOLATIONS = ("bad-scheme", "too-short", "bad-chars", "missing-header")


def _evaluate(rules, header):
    """Return {"accepted": bool, "violation": str|None}.

    Check order (first hit wins): missing-header, bad-scheme, bad-chars,
    too-short. The bad-chars rule also rejects the forbidden leading
    double space ("Bearer  x") because a space is outside the safe charset.
    """
    if header is None:
        return {"accepted": False, "violation": "missing-header"}
    prefix = rules["scheme"] + " "
    if not header.startswith(prefix):
        return {"accepted": False, "violation": "bad-scheme"}
    token = header[len(prefix):]
    if rules.get("charset") == "safe" and (
            not token or any(c not in SAFE_CHARS for c in token)):
        return {"accepted": False, "violation": "bad-chars"}
    if len(token) < rules["min_len"]:
        return {"accepted": False, "violation": "too-short"}
    return {"accepted": True, "violation": None}


def _rand_token(rng, length):
    alphabet = sorted(SAFE_CHARS)
    return "".join(rng.choice(alphabet) for _ in range(length))


def generate(seed, difficulty=0.5):
    rng = random.Random("auth-header|%d" % seed)
    min_len = int_knob(difficulty, 8, 32)
    charset_on = difficulty >= 0.3 and rng.random() < 0.4 + difficulty * 0.6
    rules = {"scheme": SCHEME, "min_len": min_len,
             "charset": "safe" if charset_on else "any"}

    kinds = ["valid", "valid", "bad-scheme", "too-short"]
    if charset_on:
        kinds.append("bad-chars")
    if rng.random() < 0.25:
        kinds.append("missing")
    kind = rng.choice(kinds)

    if kind == "missing":
        header = None
    elif kind == "bad-scheme":
        wrong = rng.choice(["Basic", "bearer", "Token", "BearerX"])
        header = "%s %s" % (wrong, _rand_token(rng, min_len + 4))
    elif kind == "too-short":
        header = "Bearer " + _rand_token(rng, max(1, min_len - rng.randint(1, 4)))
    elif kind == "bad-chars":
        body = _rand_token(rng, min_len + 3)
        pos = rng.randrange(len(body))
        body = body[:pos] + rng.choice([" ", "!", "@", "#", "+"]) + body[pos + 1:]
        if rng.random() < 0.3:
            header = "Bearer  " + body  # forbidden leading double space
        else:
            header = "Bearer " + body
    else:
        header = "Bearer " + _rand_token(rng, min_len + rng.randint(0, 8))

    verdict = _evaluate(rules, header)
    rule_lines = ["scheme must be exactly \"Bearer\" (case-sensitive, one space)",
                  "token length must be >= %d" % min_len]
    if charset_on:
        rule_lines.append("token characters must be limited to [A-Za-z0-9._-] "
                          "(no spaces allowed)")
    header_desc = ("no Authorization header was sent" if header is None
                   else '"%s"' % header)
    return {
        "id": make_id(TYPE, seed),
        "type": TYPE,
        "difficulty": float(difficulty),
        "seed": int(seed),
        "prompt": ("A service validates the Authorization header. Rules: %s. "
                   "Incoming request header: %s. Will the header be accepted? "
                   "If not, which rule does it violate — answer with one "
                   "violation code: bad-scheme, too-short, bad-chars, or "
                   "missing-header."
                   % ("; ".join(rule_lines), header_desc)),
        "answer": {"accepted": verdict["accepted"],
                   "violation": verdict["violation"]},
        "solution": ("Header is %s. Engine verdict: accepted=%s, violation=%s "
                     "(checked in order: missing-header, bad-scheme, "
                     "bad-chars, too-short)."
                     % ("absent" if header is None else "present",
                        verdict["accepted"], verdict["violation"])),
        "meta": {"rules": rules, "header": header},
    }


def verify(problem):
    try:
        rules = problem["meta"]["rules"]
        header = problem["meta"]["header"]
        verdict = _evaluate(rules, header)
        a = problem["answer"]
        return (a["accepted"] == verdict["accepted"]
                and a["violation"] == verdict["violation"])
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
    base = None
    for s in range(200):  # need a header whose violation is mutable by min_len
        p = generate(s, 0.5)
        if (p["meta"]["header"] is not None
                and p["answer"]["violation"] in (None, "bad-chars")):
            base = p
            break
    if base is None:
        base = generate(0, 0.5)
    p = copy.deepcopy(base)
    p["answer"]["accepted"] = not p["answer"]["accepted"]
    cases.append(("verify-false-flip-accepted", lambda p=p: verify(p) is False))
    p = copy.deepcopy(base)
    p["answer"].pop("violation")
    cases.append(("verify-false-missing-violation",
                  lambda p=p: verify(p) is False))
    p = copy.deepcopy(base)
    p["meta"]["header"] = None
    cases.append(("verify-false-tampered-header",
                  lambda p=p: verify(p) is False))
    from .common import schema_ok
    cases.append(("schema-ok", lambda: schema_ok(generate(42, 0.3))))
    cases.append(("engine-helper", lambda: (
        _evaluate({"scheme": "Bearer", "min_len": 4, "charset": "safe"}, None)
        == {"accepted": False, "violation": "missing-header"}
        and _evaluate({"scheme": "Bearer", "min_len": 4, "charset": "safe"},
                      "Basic abcdef")
        == {"accepted": False, "violation": "bad-scheme"}
        and _evaluate({"scheme": "Bearer", "min_len": 4, "charset": "safe"},
                      "Bearer  abcdef")
        == {"accepted": False, "violation": "bad-chars"}
        and _evaluate({"scheme": "Bearer", "min_len": 8, "charset": "safe"},
                      "Bearer abc")
        == {"accepted": False, "violation": "too-short"}
        and _evaluate({"scheme": "Bearer", "min_len": 4, "charset": "safe"},
                      "Bearer abc.def-1")
        == {"accepted": True, "violation": None})))
    return cases
