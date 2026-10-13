# -*- coding: utf-8 -*-
"""forge.common — shared schema for forge-code task generators.

Domain: security policy reasoning graded by deterministic policy engines.
RNG seeds are strings ("type|seed") — Python 3.13 rejects tuples.
"""
import hashlib

TYPES = ("cors-check", "scope-check", "rate-limit-replay", "auth-header", "quota-forecast")

_SCHEMA_KEYS = ("id", "type", "difficulty", "seed", "prompt", "answer",
                "solution", "meta")


def make_id(task_type, seed):
    h = hashlib.sha1(("%s|%d" % (task_type, seed)).encode("utf-8")).hexdigest()[:10]
    return "%s-%s" % (task_type, h)


def schema_ok(problem):
    if not isinstance(problem, dict):
        return False
    for k in _SCHEMA_KEYS:
        if k not in problem:
            return False
    if problem["type"] not in TYPES:
        return False
    if not (0.0 <= float(problem["difficulty"]) <= 1.0):
        return False
    for k in ("prompt", "solution"):
        if not isinstance(problem[k], str) or len(problem[k]) < 10:
            return False
    if not isinstance(problem["answer"], dict) or not problem["answer"]:
        return False
    if not isinstance(problem["meta"], dict):
        return False
    return True


def knob(difficulty, lo, hi):
    difficulty = min(max(difficulty, 0.0), 1.0)
    return lo + (hi - lo) * difficulty


def int_knob(difficulty, lo, hi):
    return int(round(knob(difficulty, lo, hi)))



