# -*- coding: utf-8 -*-
"""forge-security: security-policy reasoning graded by deterministic engines."""
MODULES = {}
for _name in ("cors_check", "scope_check", "rate_limit_replay",
              "auth_header", "quota_forecast"):
    try:
        _m = __import__("forge." + _name, fromlist=["x"])
        MODULES[_m.TYPE] = _m
    except ImportError:
        pass
