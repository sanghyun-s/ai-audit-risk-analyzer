# Fraud Detection Model Comparison — Unsupervised vs. Supervised

**Context:** App 3 (AI Audit Risk Analyzer) currently uses unsupervised Isolation Forest. This study simulates both approaches on identical audit-style GL data to determine which is optimal for the real audit field.

## Method

A synthetic 2,000-transaction GL was generated with a hidden `is_fraud` ground-truth label (3% fraud rate). Fraud was planted in three archetypes that mirror real audit scenarios:

- **Obvious** — large anomalous amounts (statistically loud)
- **Structured** — amounts just under approval thresholds, with multiple fraud fingerprints (weekend, new vendor, missing description)
- **Subtle** — small amounts that look almost normal, with a couple of quiet red flags

Both models used the same 6 interpretable audit features. The unsupervised model trained on all data with no labels (the true audit scenario). The supervised model trained on a 60% labeled split and was tested on a 40% held-out split (the standard supervised protocol).

## Headline results

| Metric | Unsupervised (Isolation Forest) | Supervised (Random Forest) |
|---|---|---|
| PR-AUC | 0.932 | 1.000 |
| Recall | 0.850 | 1.000 |
| Precision | 0.850 | 1.000 |
| Requires fraud labels to train | No | Yes |
| Works on a raw QuickBooks GL upload | Yes | No |

On metrics alone, supervised wins decisively. But two findings reframe what that means.

## Finding 1 — The supervised "perfect score" is partly a synthetic-data artifact

The classifier hit 1.000 because the planted fraud followed clean, learnable rules. Its feature importance leaned 52% on `is_new_vendor` alone. On real data — where new vendors are usually legitimate — that reliance would produce heavy false positives. Real fraud is messier and less separable, so the perfect score should be read as "supervised learns clean patterns well," not "supervised is perfect in production."

## Finding 2 — The binding constraint: supervised needs labels that real GL uploads don't have

This is the decisive point for the audit field. A supervised classifier learns from a `Class`/`is_fraud` column. A real QuickBooks GL export has no such column — identifying fraud is the very job the app exists to do. So a pure supervised model **cannot be trained on a new client's data**. The options in the field are:

1. Reuse a model trained on a different client's labeled data — only works if fraud patterns transfer, which they often don't
2. Derive weak labels from rules — the hybrid approach
3. Fall back to unsupervised — no labels needed

The unsupervised model achieved 0.85 recall **with no labels at all** — the only condition that actually exists at upload time.

## Finding 3 — Where unsupervised actually struggles (the real case for supervised)

Detection rate by fraud archetype (unsupervised):

| Archetype | Caught |
|---|---|
| Obvious (loud amounts) | 100% |
| Structured (threshold-evading) | 100% |
| Subtle (small, quiet) | 67% |

The gap is **subtle fraud** — small transactions that aren't statistical outliers, so anomaly detection misses a third of them. This is the genuine, evidence-based argument for *adding* a supervised layer: to catch quiet fraud that doesn't look anomalous.

## Recommendation

The evidence does not support replacing Isolation Forest with pure supervised learning, because the latter can't run on label-free real uploads. It does support a **hybrid**:

- Keep unsupervised Isolation Forest for label-free anomaly detection (catches obvious + structured fraud at 100%)
- Add a supervised layer trained on weak labels (derived from the existing rule-based `fraud_risk_flag`) to improve subtle-fraud recall above 67%
- Keep the 12 interpretable audit features throughout, so findings remain explainable in PCAOB terms

This is also a stronger portfolio narrative than either pure approach: it demonstrates understanding of *why* the audit domain constrains the model choice, not just how to train a classifier.

## A note for the mentor conversation

The supervised files are an excellent learning scaffold and the supervised technique clearly outperforms on labeled data. The question is purely about the deployment constraint: where do training labels come from for a client whose fraud is unknown? The hybrid answers that by bootstrapping labels from domain rules. If labeled audit data is available from another source, pure supervised becomes viable and this conclusion would change.
