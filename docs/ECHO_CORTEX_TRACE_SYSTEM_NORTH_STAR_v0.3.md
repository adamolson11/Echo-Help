# ECHO CORTEX / TRACE SYSTEM — NORTH STAR PSEUDO-CODE (v0.3)

## Goal
Funnel disparate support signals (Echo tickets + Jira + Slack) → produce ONE recommended next step → collect Y/N outcome + short dictation → improve ranking + grow clusters → promote stable patterns into KB (`candidate` → `reviewed` → `published`).

## Constraints
- Minimal end-user friction (1 freeform input + max 1 follow-up question)
- One recommendation at a time (no option dumps)
- Always traceable (refs to evidence)
- CPU/disk-friendly: TF-IDF/BM25 + explainable scoring first

## Entities

### Ticket
- `id`
- `source` (`echo` | `jira` | `slack` | `manual`)
- `title`
- `description`
- `comments[]`
- `text_blob` (derived: `title + description + comments`)
- `status` (`open` | `closed`)
- `what_worked_text?` (required when closing as confirmed)
- `resolution_ref?` (`kb_id` OR `ref_ticket_id` OR external link)
- `outcome` (`confirmed` | `failed` | `unknown`)
- `created_at`
- `updated_at`

### Evidence
- `id`
- `type` (`jira_ticket` | `slack_thread` | `kb_article` | `internal_ticket`)
- `link`
- `excerpt`
- `metadata`

### Cluster
- `id`
- `label_auto`
- `keywords[]`
- `representative_ticket_ids[]`
- `size`
- `confirmed_count`
- `failed_count`
- `top_fix_signature_rate`
- `recurs_over_time_weeks`
- `promoted_kb_id?` (optional)
- `candidate_kb_id?` (optional)

### KBArticle (Markdown source of truth)
- `kb_id`
- `title`
- `status` (`candidate` | `reviewed` | `published`)
- `cluster_id?`
- `tags[]`
- `evidence_links[]` (jira/slack/tickets)
- `content_md`
- `created_at`
- `updated_at`

## Pipeline

### A) Intake (minimal friction)
```text
function intake(issue_text_or_transcript):
  query = parse(issue_text_or_transcript)      # extract: error codes, env hints, entities, keywords
  candidates = retrieve(query)                 # hybrid: metadata filter + BM25/TF-IDF
  confidence = compute_confidence(candidates, query)

  if confidence == LOW:
    # choose fastest path to increase confidence
    q1 = choose_best_question_or_diagnostic(query, candidates)
    if q1.type == "question":
      answer = ask_user(q1.text)               # max 1 question (rarely 2)
      query = update_query(query, answer)
    else:
      # diagnostic yields signal, not a risky fix
      show_single_recommendation(q1.diagnostic_step, refs=q1.refs, confidence=LOW)
      return goto_outcome_loop(q1)

    # rerun once after the clarification
    candidates = retrieve(query)
    confidence = compute_confidence(candidates, query)

  # B) Recommend (ONE step only)
  best = rank(candidates, query).top1
  plan = build_single_step_plan(best, query, confidence)

  # show minimal text, always refs
  show_single_recommendation(
    do_this_next = plan.step,
    why_one_line = plan.why,
    refs = plan.refs,                 # always include source references (KB/Jira/Slack/tickets)
    confidence = confidence
  )

  # C) Outcome (the learning fuel)
  result = ask_user_yes_no("Did it work?")
  if result == YES:
    record_outcome(query, best, outcome="confirmed")
    maybe_create_or_update_cluster(best, query, outcome="confirmed")
    maybe_generate_kb_candidate(best, query)   # gated by rubric below
  else:
    what_happened = ask_user_text("What happened / why not? (dictate is fine)")
    record_outcome(query, best, outcome="failed", note=what_happened)
    maybe_create_or_update_cluster(best, query, outcome="failed", note=what_happened)

  return
```

### Retrieval (CPU-first)
```text
function retrieve(query):
  meta_filtered = filter_by_metadata(query.product_area?, query.env?, query.error_codes?)
  text_hits = bm25_or_tfidf_search(query.text)
  return union(meta_filtered, text_hits).topN(200)
```

### Ranking (rules → learned weights later)
```text
function score(item, query):
  s = 0
  s += w_text * similarity(item.text_blob, query.text)
  s += w_area if match(item.product_area, query.product_area)
  s += w_env  if match(item.env, query.env)
  s += w_err  if overlap(item.error_codes, query.error_codes)
  s += w_confirmed * item.confirmed_fix_count
  s -= w_bad * item.bad_fix_count
  return s

function rank(candidates, query):
  return sort_by(score(c, query))
```

### Confidence + gating
```text
function compute_confidence(candidates, query):
  top1, top2 = candidates[0], candidates[1]
  gap = score(top1)-score(top2)
  evidence_strength = confirmed_strength(top1)
  structured_match = structured_match_ratio(top1, query)

  conf = sigmoid(a*gap + b*evidence_strength + c*structured_match)

  if conf >= HIGH_T: return HIGH
  if conf >= MID_T:  return MID
  return LOW
```

### Choose fastest confidence booster
```text
function choose_best_question_or_diagnostic(query, candidates):
  # pick the option with highest expected confidence gain per user effort
  options = [
    question("What environment/version?", if missing(query.env) and env_conflicts(candidates)),
    question("What’s the exact error text?", if missing(query.error_text) and low_signal(query)),
    question("What have you tried so far?", if missing(query.tried_steps)),
    question("Is it one user or everyone?", if unclear_scope(query)),
    diagnostic("Collect a quick log/screenshot and paste the key error line", always_safe=True)
  ]
  return argmax_expected_gain(options)
```

### Clustering (not every ticket becomes KB)
```text
function maybe_create_or_update_cluster(best_item, query, outcome, note=None):
  vec = tfidf_vectorize(query.text + best_item.text_blob)
  cluster = assign_incremental_cluster(vec)
  update_cluster_stats(cluster, best_item, outcome)
  update_fix_signature_stats(cluster, best_item.what_worked_text?)
```

### Fix signature (CPU-friendly normalization)
```text
function fix_signature(what_worked_text):
  s = normalize_text(what_worked_text)          # lowercase, strip punctuation, stopwords
  s = apply_synonym_map(s)                      # "reindex" ≈ "rebuild index"
  return hash(s)
```

### Promotion rubric (truth-first)

#### Candidate KB (start early, but clearly labeled)
```text
function maybe_generate_kb_candidate(best_item, query):
  cluster = get_cluster_for(best_item)

  # Candidate threshold (your decision B)
  if cluster.confirmed_count >= 5 and cluster.top_fix_signature_rate >= 0.65:
    create_kb_article(status="candidate", cluster_id=cluster.id, evidence=top_refs(cluster))

  # Reviewed/Publish threshold (your decision C)
  if cluster.confirmed_count >= 6
     and cluster.top_fix_signature_rate >= 0.70
     and cluster.recurs_over_time_weeks >= 2:
    suggest_promote_candidate_to_reviewed(cluster)
```

Reviewer adds screenshots/videos + verifies steps.

Flow: `candidate` → `reviewed` → `published`.
