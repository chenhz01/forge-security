# forge-security

> **The policy engine is the judge.** Security-reasoning problems (CORS, token scopes, rate limits, auth headers, quota exhaustion) graded by deterministic policy re-evaluation — the same way a real gateway would.

Part of the [forge family](https://github.com/chenhz01/forge-kit): [scireason-forge](https://github.com/chenhz01/scireason-forge) · [forge-agentic](https://github.com/chenhz01/forge-agentic) · [forge-code](https://github.com/chenhz01/forge-code) · [forge-sql](https://github.com/chenhz01/forge-sql) · [forge-optimize](https://github.com/chenhz01/forge-optimize).

## Why this exists

Security is where a model's confident wrong answer costs real money. Yet most security QA datasets grade with... another model. Here every scenario is procedurally constructed with a *known* policy truth, and grading re-runs the policy engine — the same deterministic rules a gateway runs. No vibes, no judge-model bias.

## Five task types (W1: 250 problems)

| Type | What it drills | Oracle |
|---|---|---|
| `cors-check` | Origin/method policy decisions | Policy re-evaluation |
| `scope-check` | Token scopes vs required scopes (admin wildcard) | Set algebra |
| `rate-limit-replay` | Fixed-window replay: which request gets 429 | Deterministic replay |
| `auth-header` | Authorization header compliance | Rule engine |
| `quota-forecast` | Day of quota exhaustion from usage series | Cumulative-sum oracle |

## Quickstart

```bash
python cli.py generate --type all --per-type 50 --seed0 1000 --out data/w1.jsonl
python cli.py grade --file data/w1.jsonl        # SUMMARY: 250/250 passed
python self_test.py                             # SUMMARY: PASS 157/157
python -m bench.harness --file data/w1.jsonl --backend random   # chance: 0.0%
```

## When NOT to use

Penetration testing; adversarial red-teaming (these tasks teach policy *reading*, not offense); compliance certification.

## License & contact

MIT — © zhengming contributors. Developer tooling, not professional advice. Contact: hcac4735@agent.qq.com
