# Return Prevention System (RPS) — Meesho
### A PM × Data Science Portfolio Project by Borshan Haque

> *"Most teams ask: how do we process returns better? I asked: how do we prevent them before they happen?"*

![Python](https://img.shields.io/badge/Python-3.10-3776AB?logo=python&logoColor=white)
![SQL](https://img.shields.io/badge/SQL-PostgreSQL-336791?logo=postgresql&logoColor=white)
![ML](https://img.shields.io/badge/Model-Logistic%20Regression-FF6B35)
![AUC](https://img.shields.io/badge/AUC--ROC-0.683-2ECC71)
![Dataset](https://img.shields.io/badge/Dataset-5%2C000%20orders-9B59B6)

---

## TL;DR

Meesho loses ₹80–120 on every returned order. COD returns = ₹0 revenue recovery. At scale, this is a crore-level problem hiding in plain sight.

I built a **Return Prevention System (RPS)** — a data-driven product that scores every order for return risk at checkout, then automatically triggers the right intervention.

| What | Result |
|---|---|
| Dataset | 5,000 orders · 18 features · 18 months |
| Key finding | Fashion + COD = **70%+ return rate** (compounding risk) |
| Risk engine | Very High tier: **82.8% return rate** vs Low tier: **29.4%** |
| Model | Logistic Regression · AUC **0.683** · interpretable by design |
| Business impact | **₹1.0 Cr/month** saved (base case · 1M orders/month scale) |

---

Key Insight

Returns are not independent — they compound.

👉 A small set of high-risk orders drives majority of losses.

Example:

Base: 12%
Fashion → 34%
COD → 49%
Low seller → 67%


Late delivery → 81% return probability

## The Problem

Meesho operates on thin margins in a high-volume, COD-heavy environment. Returns don't just hurt unit economics — they compound.

```
Reverse logistics cost:        ₹80–120 per return
COD return revenue recovery:   ₹0
Fashion return rate:           60.7%
Overall platform return rate:  48.0%
```

The business question I asked: **which orders are most likely to be returned, and what can we do before checkout to stop it?**

---

## System Architecture

How the Return Prevention System works end-to-end:

```
User adds item to cart
        │
        ▼
┌─────────────────────────────────────────────────────┐
│              AI Risk Engine (RRS)                   │
│  Inputs: payment type · category · seller rating    │
│          delivery ETA · user return history         │
│  Computed: real-time, <50ms, at cart-checkout entry │
└────────────────────┬────────────────────────────────┘
                     │
        ┌────────────┼─────────────────────┐
        ▼            ▼                     ▼
   RRS 0–25      RRS 26–75          RRS 76–100
  Standard     Size guide +       Prepaid cashback
  checkout     trust signals      nudge (₹30–50)
```

No user sees their score. They see a relevant offer or helpful information — never a punishment.

---

## The Compounding Risk Effect (Most Important Finding)

Risk factors don't add linearly — **they stack**:

```
Base return rate:        12%
+ Fashion category:     +22pp → 34%
+ COD payment:          +15pp → 49%
+ Low seller rating:    +18pp → 67%
+ 7+ day delivery:      +14pp → 81%

Final return probability:  81%
```

A single bad factor is manageable. All four together = near-certain return. This is why aggregate return rates (48%) hide the real problem — there's a bimodal reality underneath.

---

## Key Findings

### Finding 1 — Fashion is the Return Capital
**60.7% return rate** — nearly 2× the platform average. This is not a product quality problem. It's an *information problem*. Users can't feel fabric or try sizing, so they order multiple options and return what doesn't fit.

**Implication:** Smart size recommendation ("buyers like you order M, but this seller runs large — try L") is the highest-ROI single investment.

### Finding 2 — COD is a 38% Risk Multiplier
| Payment Type | Return Rate | Orders |
|---|---|---|
| COD | 54.7% | 2,750 |
| Prepaid | 39.5% | 2,250 |

15.2pp gap. Structural, not random. COD removes the psychological sunk cost of payment — the buyer decides *after* receiving, not before.

**The nuance:** Meesho's Tier 2/3 growth was built on COD trust. Hard-blocking COD for any segment risks acquisition more than it saves in returns. Answer: *nudge with incentive*, not *restrict with friction*.

### Finding 3 — Seller Quality Directly Predicts Returns
| Seller Rating | Return Rate |
|---|---|
| < 2 stars | ~68% |
| 2–3 stars | ~57% |
| 3–4 stars | ~47% |
| 4–5 stars | 42.0% |

Low-rated sellers have a **43% higher return rate** than high-rated sellers. The marketplace absorbs the cost of bad supply-side quality in reverse logistics bills.

### Finding 4 — The 7-Day Cliff
Orders delivered in 7+ days: **60.4% return rate** vs ~38% for 1–2 days.
A 22pp gap driven by emotional detachment. The purchase excitement evaporates. By the time the parcel arrives, the buyer has moved on.

---

## Return Risk Score (RRS) — The Engine

Deliberately rules-based for v1:

```python
def compute_rrs(order):
    score = 0

    # Payment type — highest single weight
    if order.payment_type == 'COD':            score += 25

    # Seller quality
    if order.seller_rating < 3:                score += 30
    elif order.seller_rating < 4:              score += 15

    # Delivery speed
    if order.delivery_days > 7:                score += 20
    elif order.delivery_days > 5:              score += 10

    # User return history
    if order.user_past_returns >= 3:           score += 20
    elif order.user_past_returns >= 1:         score += 10

    # Category risk
    if order.product_category == 'Fashion':    score += 15

    return min(score, 100)
```

> A score a PM can whiteboard in 5 minutes will get shipped. A black-box model only the data scientist understands will die in a Jira ticket.

**Results:**

| Tier | RRS Range | Actual Return Rate | Action |
|---|---|---|---|
| Low | 0–25 | 29.4% | Standard checkout |
| Medium | 26–50 | ~42% | Size guide + customer photos |
| High | 51–75 | ~65% | Prepaid cashback offer |
| **Very High** | **76–100** | **82.8%** | COD soft-block or review |

**2.8× risk gap between Very High and Low tier.** That's the intervention zone.

---

## ML Model — Logistic Regression

**AUC-ROC: 0.683** on 80/20 train-test split.

Top features by coefficient magnitude:
1. `payment_type_Prepaid` — strong negative predictor
2. `seller_rating` — negative predictor
3. `product_category_Fashion` — strongest positive predictor
4. `user_past_returns` — strong positive predictor
5. `delivery_days` — moderate positive predictor

### Why 0.683 is the right call for v1

This model doesn't need to be perfect — it needs to rank-order risk well enough to assign tiers. AUC 0.683 does that. Interpretability matters more than marginal accuracy for a system that restricts checkout options.

### What v2 looks like

| Limitation | Root Cause | v2 Fix |
|---|---|---|
| No product image data | Synthetic dataset | Image quality score (blur, resolution) |
| No user embeddings | No session data | User return propensity vector |
| No seller historical rate | Missing feature | `seller_30d_return_rate` as feature |
| No review NLP | No text data | Sentiment score on review text |
| No temporal features | Limited dates | Recency of last return, seasonal patterns |

Expected AUC with v2 features: **~0.76–0.80**

---

## Trade-off Analysis

### Trade-off 1: COD Restriction vs Conversion

| | Hard Block COD | Nudge with Incentive |
|---|---|---|
| Return reduction | High (~20pp) | Moderate (~8–10pp) |
| Conversion impact | −15 to −25% | −2 to −5% |
| User trust impact | Negative — alienates Tier 2/3 | Neutral to positive |
| **Recommendation** | Only blacklisted users | Default for RRS > 75 |

Losing a Tier 2/3 customer costs more in CAC than one bad return. The nudge approach protects both.

### Trade-off 2: Seller Penalties vs Supply Diversity

Penalising high-return sellers improves quality but risks supply-side churn. Answer: graduated penalties — visibility reduction first (>45% return rate), listing suspension only above 60% sustained. Seller improvement dashboard so they can self-correct before penalties hit.

### Trade-off 3: Model Complexity vs Explainability

XGBoost would likely push AUC to ~0.78. But it becomes a black box that trust & safety, legal, and product teams can't audit. For a system that restricts checkout options, explainability is non-negotiable. Rules-based RRS first. ML layer second — to tune weights, not replace logic.

---

## Product Interventions — Prioritised

| Priority | Intervention | Expected Impact | How |
|---|---|---|---|
| **P0** | Smart size recommendation | −12 to −18pp for Fashion | User order history + seller size complaint tags |
| **P0** | Prepaid cashback nudge (RRS > 75) | −8 to −10pp on high-risk segment | "Save ₹40 with UPI" framing at checkout |
| **P1** | Seller Intelligence System | Upstream quality improvement | Visibility penalty >45% RR · suspension >60% |
| **P1** | Delivery Confidence Indicator | Reduces emotional detachment | Show ETA · proactive coupon if >7 days likely |
| **P2** | Trust Layer | Reduces speculative ordering | Real customer photos · Quality Confidence Score |

---

## A/B Test Design

| | Test Group | Control Group |
|---|---|---|
| Segment | RRS > 75 orders | All other orders |
| Intervention | ₹30–50 prepaid cashback nudge | Standard flow |
| Primary metric | Return rate | Return rate |
| Secondary metric | Prepaid conversion rate | Prepaid conversion rate |
| Guardrail | Overall GMV must not drop > 3% | |
| Duration | 3 weeks minimum | |
| Min sample | 5,000 test orders | 5,000 control orders |
| **Success** | **Return rate ↓ ≥ 4pp** | **Baseline holds** |

**Failure signal:** Return rate drops but GMV guardrail is breached → pause, redesign nudge framing.

---

## Business Impact — Three Scenarios

*Assumptions: 1M orders/month · ₹100 avg reverse logistics cost · 48% baseline return rate*

| Scenario | Assumption | Return Rate | Monthly Savings |
|---|---|---|---|
| Conservative | P0 only · 40% effectiveness | 44% | **₹0.4 Cr** |
| **Base Case** | P0 + P1 · 65% effectiveness | **38%** | **₹1.0 Cr** |
| Optimistic | All 5 interventions · 80% effective | 35% | **₹1.3 Cr** |

**Annual base case: ₹12 Cr+** — from product and data changes, zero infrastructure cost.

The conservative scenario alone justifies the engineering investment.

---

## What I Would Build Next

1. **Real-time RRS API** — sub-50ms scoring endpoint integrated with checkout service
2. **Cohort analysis** — track return behaviour for RRS-intervention users over 90 days to measure long-term change, not just first-order return rate
3. **Seller improvement dashboard** — full visibility into their own return drivers so they self-correct before penalties
4. **Personalised size model** — user × seller × category size mapping, updated per order
5. **Return reason classifier** — NLP on return reason text to separate *preventable* returns (size, quality) from *unavoidable* ones (gift returns, wrong address)

---

## Learnings

**1. Frame before you model.** Day 1 was the hypothesis tree, not Python. This stopped me building answers to the wrong questions.

**2. Transparency beats accuracy in product ML.** The rules-based RRS gets shipped. An XGBoost black-box gets stuck in review. For v1, explainability is the feature.

**3. COD is not the villain — it's the trust mechanism.** Meesho's Tier 2/3 growth was built on COD. Any solution that ignores why COD exists will fail.

**4. SQL is still the fastest way to test a hypothesis.** Every insight here was validated with a 5-line query before writing a single line of Python.

**5. One number without scenarios is not credible.** "₹1.2 Cr/month" sounds good but means nothing without a conservative case. The ₹0.4 Cr conservative scenario is what you'd actually commit to in a business review.

---

## Repo Structure

```
meesho-rris/
├── README.md                           ← this file
├── case_study.md                       ← full write-up 
├── data/
│   └── meesho_orders_enriched.csv      ← 5,000 orders · 18 features · RRS + tier
├── analysis/
│   └── rris_analysis.py                ← EDA · RRS engine · ML model · all charts
├── sql/
│   └── meesho_sql_queries.sql          ← 10 production-grade SQL queries
└── charts/
|   ├── chart1_eda_dashboard.png        ← 4-panel EDA with captions
|   ├── chart2_compounding_risk.png     ← waterfall + heatmap (key insight)
|  ├── chart3_risk_model.png           ← RRS distribution · tiers · features
|  ├── chart4_impact_abtest.png        ← scenarios · monthly trend · A/B design
|  └── chart5_user_behaviour.png       ← repeat returners · reasons · geography
|  └── chart6_reaso_prediction.png 
|  ── chart7_conversion_impact.png 
└── assets/ 
	└── architecture.png
```

---

## Run It

```bash
pip install pandas numpy matplotlib scikit-learn
python analysis/rris_analysis.py
```

---

*Dataset is synthetic, modeled on real Meesho product dynamics. All projections based on publicly available e-commerce benchmarks and industry cost data.*

---

**Built by Borshan Haque** · 
Aspiring Product Manager / Data Scientist
[LinkedIn](https://www.linkedin.com/in/borshan-haque-4133b9328/)

> If you're working on e-commerce trust, return prevention, or marketplace quality — I'd genuinely like to compare notes.
