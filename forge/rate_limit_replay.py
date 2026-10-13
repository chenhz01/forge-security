# -*- coding: utf-8 -*-
"""forge.rate-limit-replay — fixed-window rate limiter replay.

Problem: a limiter allows N requests per 1-second fixed window (the window
is the unix second of the request). Requests arrive in order at unix-second
timestamps; replaying in order, requests after the Nth within a window are
rate-limited (HTTP 429).

Verification replays the exact same rule from meta["events"] and
meta["limit"] — the oracle is the replay engine, not the stored answer.
"""
import random

from .common import make_id, int_knob

TYPE = "rate-limit-replay"

_BASE_SECOND = 1700000000


def _replay(events, limit):
    """Replay in order; return [(status, window_count_at_decision), ...].

    window_count_at_decision = number of previously *allowed* requests in
    the same window when this request is evaluated (== limit for rejects).
    """
    results = []
    counts = {}
    for ts in events:
        c = counts.get(ts, 0)
        if c < limit:
            counts[ts] = c + 1
            results.append(("allowed", c))
        else:
            results.append(("rate-limited", c))
    return results


def generate(seed, difficulty=0.5):
    rng = random.Random("rate-limit-replay|%d" % seed)
    limit = int_knob(difficulty, 3, 8)
    n_windows = int_knob(difficulty, 2, 4)
    events = []
    for w in range(n_windows):
        if difficulty > 0.4:
            k = rng.randint(max(1, limit - 2), limit + 2)
        else:
            k = rng.randint(1, limit)
        events.extend([_BASE_SECOND + w] * k)
    probe_index = rng.randrange(len(events)) + 1  # 1-indexed
    status, count = _replay(events, limit)[probe_index - 1]
    return {
        "id": make_id(TYPE, seed),
        "type": TYPE,
        "difficulty": float(difficulty),
        "seed": int(seed),
        "prompt": ("A fixed-window rate limiter allows %d requests per "
                   "1-second window (the window is the unix second of the "
                   "request). Requests arrive in order at unix-second "
                   "timestamps: %s. Replaying in order, what is the status "
                   "of request #%d (1-indexed): \"allowed\" or "
                   "\"rate-limited\" (HTTP 429)? Also report the number of "
                   "previously allowed requests in that window at the moment "
                   "of the decision."
                   % (limit, events, probe_index)),
        "answer": {"status": status, "window_count_at_decision": count},
        "solution": ("Window %d had %d request(s) before this one within the "
                     "same second; with limit %d the request is %s."
                     % (events[probe_index - 1], count, limit,
                        "allowed" if status == "allowed" else "rate-limited")),
        "meta": {"events": events, "limit": limit, "probe_index": probe_index},
    }


def verify(problem):
    try:
        events = [int(t) for t in problem["meta"]["events"]]
        limit = int(problem["meta"]["limit"])
        idx = int(problem["meta"]["probe_index"])
        results = _replay(events, limit)
        if not (1 <= idx <= len(results)):
            return False
        status, count = results[idx - 1]
        a = problem["answer"]
        return (a["status"] == status
                and a["window_count_at_decision"] == count)
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
    p["answer"]["status"] = ("rate-limited" if p["answer"]["status"] == "allowed"
                             else "allowed")
    cases.append(("verify-false-flip-status", lambda p=p: verify(p) is False))
    p = copy.deepcopy(base)
    p["answer"]["window_count_at_decision"] += 1
    cases.append(("verify-false-tampered-count",
                  lambda p=p: verify(p) is False))
    p = copy.deepcopy(base)
    p["meta"]["limit"] = 0
    cases.append(("verify-false-tampered-limit",
                  lambda p=p: verify(p) is False))
    from .common import schema_ok
    cases.append(("schema-ok", lambda: schema_ok(generate(42, 0.3))))
    cases.append(("replay-helper", lambda: _replay([1, 1, 1, 1, 2], 3) == [
        ("allowed", 0), ("allowed", 1), ("allowed", 2),
        ("rate-limited", 3), ("allowed", 0)]))
    return cases
