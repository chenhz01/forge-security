# -*- coding: utf-8 -*-
"""forge.quota-forecast — API quota exhaustion-day forecast.

Problem: given a daily quota Q and 30 days of usage, find the first day
(1-based) on which cumulative usage first reaches or exceeds Q. Generation
guarantees exhaustion inside the 30-day window (top-up loop).

Verification recomputes the cumulative series from meta["daily_usage"] and
meta["quota"] — the oracle is the forecast engine, not the stored answer.
"""
import random

from .common import make_id, int_knob

TYPE = "quota-forecast"
DAYS = 30


def _forecast(daily_usage, quota):
    """Return (exhaust_day|None, cumulative_at_that_day). 1-based day."""
    cum = 0
    for day, usage in enumerate(daily_usage, 1):
        cum += int(usage)
        if cum >= quota:
            return day, cum
    return None, cum


def generate(seed, difficulty=0.5):
    rng = random.Random("quota-forecast|%d" % seed)
    quota = int_knob(difficulty, 50, 500)
    base = quota / rng.uniform(12.0, 25.0)  # expected exhaustion ~ day 12-25
    daily = [max(1, int(round(base * rng.uniform(0.5, 1.5))))
             for _ in range(DAYS)]
    while sum(daily) < quota:  # guarantee exhaustion inside the window
        daily[rng.randrange(DAYS)] += max(1, quota // DAYS)
    day, cum = _forecast(daily, quota)
    return {
        "id": make_id(TYPE, seed),
        "type": TYPE,
        "difficulty": float(difficulty),
        "seed": int(seed),
        "prompt": ("An API account has a usage quota of %d units. Daily "
                   "consumption for 30 days was: %s. On which day (1-based) "
                   "does cumulative consumption first reach or exceed the "
                   "quota, and what is the cumulative total on that day?"
                   % (quota, daily)),
        "answer": {"exhaust_day": day, "cumulative_at_day": cum},
        "solution": ("Cumulative usage crosses the quota on day %d with a "
                     "total of %d units (quota %d)."
                     % (day, cum, quota)),
        "meta": {"daily_usage": daily, "quota": quota},
    }


def verify(problem):
    try:
        daily = list(problem["meta"]["daily_usage"])
        quota = int(problem["meta"]["quota"])
        day, cum = _forecast(daily, quota)
        a = problem["answer"]
        if day is None:
            return a["exhaust_day"] is None
        return (a["exhaust_day"] == day
                and a["cumulative_at_day"] == cum)
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
    p["answer"]["exhaust_day"] += 1
    cases.append(("verify-false-shifted-day", lambda p=p: verify(p) is False))
    p = copy.deepcopy(base)
    p["meta"]["quota"] += 100000  # never exhausted -> day None
    cases.append(("verify-false-tampered-quota",
                  lambda p=p: verify(p) is False))
    p = copy.deepcopy(base)
    p["meta"]["daily_usage"][0] += 1  # shifts cumulative totals
    cases.append(("verify-false-tampered-usage",
                  lambda p=p: verify(p) is False))
    from .common import schema_ok
    cases.append(("schema-ok", lambda: schema_ok(generate(42, 0.3))))
    cases.append(("forecast-helper", lambda: (
        _forecast([10, 20, 30], 25) == (2, 30)
        and _forecast([1, 2], 100) == (None, 3)
        and _forecast([50], 50) == (1, 50))))
    return cases
