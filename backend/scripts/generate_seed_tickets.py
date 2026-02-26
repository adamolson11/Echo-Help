from __future__ import annotations

import argparse
import json
import random
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path


PRODUCT_AREAS = [
	"auth",
	"billing",
	"search",
	"embeddings",
	"frontend",
	"integrations",
]

ENVIRONMENTS = ["local", "stage", "prod"]
SEVERITIES = ["S1", "S2", "S3", "S4"]
PRIORITIES = ["P0", "P1", "P2", "P3"]

GOOD_RC = {
	"auth": "Session cookie scope and callback nonce validation diverged across regions.",
	"billing": "Webhook idempotency key was dropped in retry worker.",
	"search": "Ranking index used stale feature snapshot after deploy.",
	"embeddings": "Fallback embedding path saturated CPU cache under burst load.",
	"frontend": "Proxy/base path mismatch caused API calls to bypass expected route.",
	"integrations": "Source payload mapping omitted stable source_id field on transform.",
}

GOOD_RES = {
	"auth": [
		"Aligned cookie domain/path with callback host and enforced SameSite policy.",
		"Added JWT clock-skew tolerance and synchronized auth service NTP drift checks.",
		"Verified Okta callback redirect URI per environment and rotated stale client secret.",
	],
	"billing": [
		"Added webhook idempotency lock keyed by event id and invoice id.",
		"Reconciled plan state transition with invoice finalization workflow.",
		"Replayed dead-letter events and validated invoice totals against source-of-truth ledger.",
	],
	"search": [
		"Guarded empty/special-character query handling before scoring pipeline.",
		"Rebuilt ranking feature cache and invalidated stale evidence snapshots.",
		"Added deterministic tie-break ordering for equivalent similarity scores.",
	],
	"embeddings": [
		"Enabled batched embedding cache with TTL and warmed hot query set.",
		"Forced re-index after model version drift and removed stale vectors.",
		"Moved fallback path to bounded worker pool to prevent saturation.",
	],
	"frontend": [
		"Corrected Vite base path and API proxy target for non-root deploy.",
		"Normalized import casing to avoid Linux-only module resolution failures.",
		"Tightened CORS origin list and aligned credentials mode with backend headers.",
	],
	"integrations": [
		"Added strict schema mapping with explicit optional/required field guards.",
		"Persisted upstream source_id and source_url for traceability.",
		"Introduced retry contract that preserves original event envelope.",
	],
}

BAD_ATTEMPTS = [
	(
		"Restarted service repeatedly until issue looked resolved.",
		"Correlation not causation: restart masked timing issue without fixing root cause.",
	),
	(
		"Copied production config into stage and assumed parity.",
		"Ignored environment-specific secrets/URLs; fix does not generalize safely.",
	),
	(
		"Increased timeout everywhere to hide failures.",
		"Treats symptom not cause; latency budget regression remains unresolved.",
	),
	(
		"Applied cargo-cult cache clear from unrelated incident doc.",
		"Cargo-cult fix: no evidence it targets this subsystem failure mode.",
	),
]

AREA_TEMPLATES = {
	"auth": [
		"SSO callback returns 302 loop after Okta login",
		"JWT clock skew causes intermittent token rejection",
		"Session TTL expires immediately for long-running dashboard session",
		"Cookie SameSite setting breaks redirect-based auth",
	],
	"billing": [
		"Stripe webhook replay creates duplicate credit adjustments",
		"Plan state mismatch after annual-to-monthly downgrade",
		"Invoice finalized but subscription remains pending",
		"Billing portal update not reflected in entitlement state",
	],
	"search": [
		"Ask Echo returns low-quality evidence for special-character query",
		"Empty query path bypasses guard and emits generic answer",
		"Ranking tie yields inconsistent ticket order across runs",
		"Missing evidence snippets for known resolved issue",
	],
	"embeddings": [
		"Fallback embeddings path slows under burst traffic",
		"Stale index after re-embed produces irrelevant nearest neighbors",
		"Embedding cache misses spike during deploy window",
		"Vector dimension mismatch silently drops candidate rows",
	],
	"frontend": [
		"Vite proxy routes /api to wrong backend target",
		"Import casing mismatch fails only in Linux container",
		"CORS preflight blocked for credentialed request",
		"Base path misconfiguration breaks hash route deep links",
	],
	"integrations": [
		"Connector mapping drops required source_id field",
		"External payload schema change breaks transform",
		"Retry worker mutates source envelope unexpectedly",
		"Upstream issue key not preserved in internal ticket",
	],
}


def _rand_description(area: str, env: str) -> str:
	examples = {
		"auth": "User authenticates successfully, but callback processing replays stale nonce and redirects back to login.",
		"billing": "Webhook delivery retries arrive out of order and idempotency key collision handling is inconsistent.",
		"search": "Query parser accepts input but evidence retrieval omits high-confidence historical resolutions.",
		"embeddings": "Model fallback path executes but cache churn causes repeated recomputation on hot queries.",
		"frontend": "Client app loads, yet API calls fail due to proxy/basepath mismatch under non-root deployments.",
		"integrations": "Inbound payload is accepted; downstream mapper drops a required identity field before persistence.",
	}
	return f"[{env}] {examples[area]}"


def _pick_priority_for_severity(sev: str) -> str:
	mapping = {"S1": "P0", "S2": "P1", "S3": "P2", "S4": "P3"}
	return mapping.get(sev, "P2")


def generate_rows(*, count: int, seed: int = 42) -> list[dict]:
	rng = random.Random(seed)
	now = datetime.now(timezone.utc)
	rows: list[dict] = []

	for idx in range(count):
		area = PRODUCT_AREAS[idx % len(PRODUCT_AREAS)]
		env_weights = [0.18, 0.27, 0.55] if area in {"auth", "billing", "search"} else [0.35, 0.35, 0.30]
		env = rng.choices(ENVIRONMENTS, weights=env_weights, k=1)[0]

		sev = rng.choices(SEVERITIES, weights=[0.12, 0.28, 0.40, 0.20], k=1)[0]
		prio = _pick_priority_for_severity(sev)

		title = rng.choice(AREA_TEMPLATES[area])
		desc = _rand_description(area, env)

		age_days = int(rng.triangular(low=0, high=365, mode=35))
		created_at = now - timedelta(days=age_days, hours=rng.randint(0, 22), minutes=rng.randint(0, 59))
		resolution_minutes = rng.randint(20, 60 * 72)
		resolved_at = created_at + timedelta(minutes=resolution_minutes)

		include_bad = rng.random() < 0.30
		bad_attempts: list[str] = []
		root_cause_bad: str | None = None
		bad_reason: str | None = None
		quality_label = "good"
		if include_bad:
			bad_attempt, bad_why = rng.choice(BAD_ATTEMPTS)
			bad_attempts = [bad_attempt]
			root_cause_bad = "Operator assumed nearest visible symptom was causal."
			bad_reason = bad_why
			quality_label = "mixed"

		if rng.random() < 0.08:
			quality_label = "bad"
			if not bad_attempts:
				bad_attempt, bad_why = rng.choice(BAD_ATTEMPTS)
				bad_attempts = [bad_attempt]
				bad_reason = bad_why
				root_cause_bad = "Resolution path was never validated against root cause."

		fix_confirmed_good = quality_label in {"good", "mixed"} and rng.random() < 0.85

		key_num = 1000 + idx
		key = f"ECHO-{key_num}"
		source_id = f"seed-{key_num}"

		row = {
			"key": key,
			"title": title,
			"description": desc,
			"product_area": area,
			"environment": env,
			"severity": sev,
			"priority": prio,
			"created_at": created_at.isoformat(),
			"resolved_at": resolved_at.isoformat(),
			"repro_steps": [
				"Open affected flow and capture request/response ids.",
				"Repeat in target environment with fresh session.",
				"Compare observed behavior against expected entitlement/auth state.",
			],
			"expected": "System should return successful result with stable state transition and no redirect loop.",
			"actual": "Request completes with incorrect state and requires manual retry or produces incorrect evidence.",
			"resolution_good": rng.sample(GOOD_RES[area], k=2),
			"root_cause_good": GOOD_RC[area],
			"fix_confirmed_good": bool(fix_confirmed_good),
			"resolution_bad": bad_attempts,
			"root_cause_bad": root_cause_bad,
			"bad_reason": bad_reason,
			"answer_quality_label": quality_label,
			"tags": [
				f"area:{area}",
				f"env:{env}",
				f"severity:{sev.lower()}",
				f"priority:{prio.lower()}",
				f"fix_confirmed:{str(bool(fix_confirmed_good)).lower()}",
			],
			"source_system": "seed",
			"source_id": source_id,
			"source_url": f"https://jira.example.local/browse/{key}",
		}
		rows.append(row)

	return rows


def _print_hist(rows: list[dict]) -> None:
	area = Counter(str(r.get("product_area") or "unknown") for r in rows)
	env = Counter(str(r.get("environment") or "unknown") for r in rows)
	sev = Counter(str(r.get("severity") or "unknown") for r in rows)
	q = Counter(str(r.get("answer_quality_label") or "unknown") for r in rows)
	print("histogram.product_area", dict(sorted(area.items())))
	print("histogram.environment", dict(sorted(env.items())))
	print("histogram.severity", dict(sorted(sev.items())))
	print("histogram.answer_quality_label", dict(sorted(q.items())))


def main() -> None:
	parser = argparse.ArgumentParser(description="Generate realistic Jira-like seed tickets as JSONL")
	parser.add_argument("--out", type=Path, required=True)
	parser.add_argument("--count", type=int, default=600)
	parser.add_argument("--seed", type=int, default=42)
	args = parser.parse_args()

	if args.count < 1:
		raise ValueError("--count must be >= 1")

	rows = generate_rows(count=args.count, seed=args.seed)
	args.out.parent.mkdir(parents=True, exist_ok=True)
	with args.out.open("w", encoding="utf-8") as f:
		for row in rows:
			f.write(json.dumps(row, ensure_ascii=False) + "\n")

	print(f"generated {len(rows)} tickets -> {args.out}")
	_print_hist(rows)


if __name__ == "__main__":
	main()
