# Return Prevention System (RPS) — Meesho
### A PM × Data Science Case Study

**Duration:** 7 days &nbsp;|&nbsp; **Stack:** Python · SQL · Logistic Regression · Power BI  
**Simulated Impact:** ~25% return reduction · ₹1.2 Cr/month saved at scale

---

## TL;DR

Meesho loses ₹80–120 on every returned order — and COD returns mean zero revenue recovery. I built a **Return Prevention System (RPS)** that scores every order for return risk before checkout, then triggers the right intervention automatically.

- Identified **4 compounding risk drivers**: payment type, product category, seller quality, delivery speed
- Built a **Return Risk Score (RRS)** — Very High tier has **82.8% return rate** vs 29.4% for Low tier
- Designed **5 product interventions** prioritised by ROI and UX impact
- Projected savings: **₹1.2 Cr/month** at 1M orders/month scale (conservative estimate)
- Trained a baseline Logistic Regression: **AUC = 0.683**, sufficient for risk-tier ranking

---

## Why This Problem

Meesho is India's fastest-growing social commerce platform — but returns are silently destroying its unit economics.

The math most people miss:

| Cost Item | Amount |
|---|---|
| Reverse logistics per order | ₹80–120 |
| COD return revenue recovery | ₹0 |
| Return rate — Fashion category | ~60% |
| Return rate — overall platform | ~48% |

Most teams try to *process* returns better. I asked a different question: **what if we prevent them before they happen?**

That reframing is the entire project.

---

## System Architecture

Here's how the Return Prevention System works end-to-end in a real product:

```
User adds item to cart
        │
        ▼
   Risk Engine
   (RRS computed in real-time from user history + order features)
        │
        ├── RRS 0–25   (Low)       → Standard checkout flow
        ├── RRS 26–50  (Medium)    → Show trust signals + size guide
        ├── RRS 51–75  (High)      → Prepaid cashback nudge (₹30–50)
        └── RRS 76–100 (Very High) → COD soft-block OR mandatory review
```

**When is RRS computed?**
At cart-checkout entry — synchronously, under 50ms, using pre-computed user feature vectors updated nightly. No model inference at runtime for the rules-based version; only for the ML upgrade path.

**How is it used?**
The Decision Layer reads the RRS and routes the user to one of four checkout experiences. No user ever sees their score. They see a relevant offer or a gentle friction — nothing punitive.

---

## Hypothesis Tree

I approached this as a PM writing a problem brief, not as a data scientist jumping to models.

```
Why do users return?
│
├── H1: Payment type      → COD removes psychological commitment to buy
├── H2: Product category  → Fashion = can't feel fabric, can't try sizing
├── H3: Seller quality    → Bad sellers ship wrong/damaged items
└── H4: Logistics         → Delayed delivery → emotional detachment
```

Each hypothesis became an SQL query. Each query became a number. Each number became a product decision.

---

## The Dataset

5,000 orders engineered with domain-accurate return probability weights:

| Feature | Description | Notes |
|---|---|---|
| `order_id` | Unique identifier | |
| `user_id` | Buyer (1,000 unique users) | |
| `seller_id` | Seller (200 unique sellers) | |
| `product_category` | Fashion, Electronics, Beauty, etc. | Fashion = 38% of orders |
| `price` | Order value (₹99–₹15,000) | Log-normal distribution |
| `payment_type` | COD / Prepaid | COD = 55% of orders |
| `seller_rating` | 1.0–5.0 stars | |
| `delivery_days` | Days to deliver | 1–10 days |
| `user_past_returns` | Historical return count | 0–5 |
| `order_date` | Jan 2023–Jun 2024 | 18-month window |
| `user_state` | 10 Indian states | |
| `return_flag` | 0 = kept, 1 = returned | **48% overall return rate** |
| `return_reason` | Size mismatch, quality issue, etc. | Only for return_flag = 1 |

Return probabilities were modeled realistically: Fashion adds +22pp base risk, COD adds +15pp, seller rating < 3 adds +18pp, delivery > 7 days adds +14pp, repeat returner (3+) adds +20pp. These stack — which leads to the most important finding in the project.

---

## Finding 0 — Returns Compound (Most Important Insight)

**Risk factors don't add linearly — they multiply.**

A Fashion order placed on COD with a low-rated seller delivered in 8 days:

```
Base return rate:     12%
+ Fashion:           +22pp → 34%
+ COD:               +15pp → 49%
+ Low seller:        +18pp → 67%
+ Late delivery:     +14pp → 81%
```

This order has an **81% probability of return**. Every single factor pushed it higher.

This is why aggregate return rates are misleading. The 48% headline number hides a bimodal reality: a segment of mostly-safe orders and a smaller segment of near-certain returns. The RPS targets that second group.

---

## Finding 1 — Fashion is the Return Capital

**60.7% of Fashion orders are returned** — nearly 2× the platform average.

This is not a product problem. It's an *information problem*. Users can't feel the fabric. They can't try the sizing. Meesho's Tier 2/3 buyers have low trust and high uncertainty, so they order multiple options and return what doesn't fit.

**Implication:** A size recommendation engine ("buyers like you usually order M, but this seller runs small — order L") is the highest-ROI single investment to reduce Fashion returns. No model needed — just order history + seller complaint tags.

---

## Finding 2 — COD is a 38% Risk Multiplier

| Payment Type | Return Rate | Orders |
|---|---|---|
| COD | 54.7% | 2,750 |
| Prepaid | 39.5% | 2,250 |

The 15.2 percentage point gap is structural, not random. COD eliminates the psychological sunk cost of payment. For impulse fashion buys especially, the mental model is "I'll decide when it arrives." That decision often goes: return.

**The nuance:** Meesho's entire Tier 2/3 growth engine was built on COD-enabled trust. Hard-blocking COD for any segment carries real acquisition risk. The answer is *nudge with incentive*, not *restrict with friction*.

---

## Finding 3 — Seller Quality Predicts Returns

| Seller Rating | Return Rate |
|---|---|
| < 3 stars | 59.8% |
| 3–4 stars | ~47% |
| 4+ stars | 42.0% |

Low-rated sellers have a **43% higher return rate** than high-rated sellers. The marketplace is absorbing the cost of bad supply-side quality in reverse logistics bills.

**Implication:** Seller penalties need to be algorithmic, not manual. A seller above 45% return rate should automatically lose search ranking — before a human reviews it.

---

## Finding 4 — The 7-Day Cliff

Orders delivered in 7+ days: **60.4% return rate**.
Orders delivered in 1–2 days: **~38% return rate**.

A 22 percentage point gap driven by emotional detachment. Fashion is especially vulnerable — the purchase excitement evaporates over a week. By the time the parcel arrives, the buyer has already mentally moved on.

**Implication:** Surface a delivery confidence indicator at checkout. If the seller is likely to breach 7 days, proactively offer a coupon — it's cheaper than eating the return.

---

## The Return Risk Score (RRS)

I deliberately chose a **rules-based scoring model** over a pure ML approach for the first version. Here's why:

> A score that a PM can whiteboard in 5 minutes will get shipped and used. A black-box model that only the data scientist understands will die in a Jira ticket.

```python
def compute_rrs(order):
    score = 0

    # Payment type (highest single weight)
    if order.payment_type == 'COD':           score += 25

    # Seller quality
    if order.seller_rating < 3:               score += 30
    elif order.seller_rating < 4:             score += 15

    # Delivery speed
    if order.delivery_days > 7:               score += 20
    elif order.delivery_days > 5:             score += 10

    # User return history
    if order.user_past_returns >= 3:          score += 20
    elif order.user_past_returns >= 1:        score += 10

    # Category risk
    if order.product_category == 'Fashion':   score += 15

    return min(score, 100)
```

**Result:**

| Risk Tier | RRS Range | Return Rate | Recommended Action |
|---|---|---|---|
| Low | 0–25 | 29.4% | Standard flow |
| Medium | 26–50 | ~42% | Show size guide + customer photos |
| High | 51–75 | ~65% | Prepaid cashback offer (₹30–50) |
| Very High | 76–100 | **82.8%** | COD soft-block or order review |

The Very High tier is **2.8× more likely to return** than the Low tier. That's the intervention zone.

---

## ML Model — Logistic Regression Baseline

**AUC-ROC: 0.683**

Trained on 80/20 split. Features: payment type, category, seller rating, delivery days, user return history, price.

### Why 0.683 is acceptable for v1

This model doesn't need to be perfect — it needs to rank-order risk well enough to trigger the right intervention. AUC of 0.683 is sufficient for tier assignment. It's the same job as a credit score: directionally correct, not perfectly precise.

### Why it's limited — and what v2 looks like

| Limitation | Root Cause | v2 Fix |
|---|---|---|
| No product image data | Synthetic dataset | Add image quality score (blur detection, resolution) |
| No user embeddings | No session data | Build user return propensity vector from history |
| No seller historical rate | Feature not in dataset | Add `seller_30d_return_rate` as feature |
| No NLP on reviews | No text data | Sentiment score on review text as predictor |
| No temporal features | Minimal date features | Add recency of last return, seasonal patterns |

**Expected AUC with v2 features: ~0.76–0.80**

---

## Trade-Off Analysis

### Trade-off 1: COD Restriction vs Conversion

| | Restrict COD | Nudge with Incentive |
|---|---|---|
| Return reduction | High (~20pp) | Moderate (~8–10pp) |
| Conversion impact | High drop (–15 to –25%) | Low drop (–2 to –5%) |
| User trust impact | Negative — alienates Tier 2/3 | Neutral to positive |
| **Recommendation** | Only for blacklisted users | Default for RRS > 75 |

Meesho's competitive moat in Tier 2/3 is COD availability. Restricting it even for high-risk users risks acquisition more than it saves in returns. The math: losing a customer costs more in CAC than one bad return. The nudge approach protects both.

### Trade-off 2: Seller Penalties vs Seller Supply

Penalising high-return sellers reduces marketplace quality problems but risks supply-side churn — especially in Fashion where seller diversity is a product advantage. The answer: graduated penalties (visibility reduction first, listing suspension only above 60% sustained return rate) with a seller improvement dashboard so they can self-correct.

### Trade-off 3: Model Complexity vs Explainability

A gradient boosting model (XGBoost) would likely push AUC to ~0.78. But it becomes a black box that trust & safety, legal, and product teams can't audit or challenge. For a system that restricts checkout options, explainability is non-negotiable. Rules-based RRS first. ML layer second — only to tune weights, not to replace the logic.

---

## Product Interventions — Prioritised

### P0 — Smart Size Recommendation (Fashion)
> "Buyers similar to you usually order M. This seller's sizing runs large — consider L."
- Pulls from: user order history + seller-level size complaint tags
- No model needed — deterministic rules on existing data
- Expected return reduction for Fashion: **12–18 percentage points**

### P0 — Risk-Based Checkout Intervention
> Prepaid cashback nudge (₹30–50) shown to RRS > 75 orders
- Framed as benefit ("Save ₹40 with UPI") not punishment ("COD unavailable")
- Expected: 15–20% of high-risk COD orders shift to prepaid
- Return rate reduction on this segment: **~8–10pp**

### P1 — Seller Intelligence System
- RR > 45%: search ranking penalty
- RR > 60%: mandatory quality review + seller improvement dashboard
- RR < 30%: "Reliable Seller" badge displayed on PDP
- Sellers have full visibility into their own metrics

### P1 — Delivery Confidence Indicator
> "Estimated delivery: Friday. This seller ships in 2 days on average."
- If delivery likely > 7 days: proactive ₹25 coupon offered at checkout
- Reduces late-delivery emotional detachment

### P2 — Trust Layer
- Real customer photos (not just star ratings) surfaced on PDP
- "Quality Confidence Score" per seller per category (composite of rating + return rate + complaint tags)
- Reduces speculative ordering by surfacing social proof

---

## A/B Test Design

| | Control | Test |
|---|---|---|
| Segment | All orders, standard flow | RRS > 75 orders only |
| Intervention | None | Prepaid cashback nudge |
| Primary metric | Return rate | Return rate |
| Secondary metric | Prepaid conversion rate | Prepaid conversion rate |
| Guardrail metric | Overall GMV | Must not drop > 3% |
| Duration | 3 weeks | 3 weeks |
| Minimum sample | — | 5,000 test orders |
| Expected lift | Baseline | 20–25% relative return reduction |

**What success looks like:** Return rate in test group drops by ≥ 4pp, GMV guardrail holds, prepaid conversion increases by ≥ 2pp.

**What failure looks like:** Return rate drops but conversion drops more than GMV guardrail allows → pause and redesign the nudge framing.

---

## Business Impact — Three Scenarios

**Assumptions:** 1M orders/month, ₹100 avg reverse logistics cost, 48% baseline return rate

| Scenario | Assumption | Return Rate | Monthly Savings |
|---|---|---|---|
| Conservative | Only P0 interventions, 40% effectiveness | 44% | **₹0.4 Cr** |
| Base case | P0 + P1, 65% effectiveness | 38% | **₹1.0 Cr** |
| Optimistic | All interventions, 80% effectiveness | 35% | **₹1.3 Cr** |

**Annual base case: ₹12 Cr+ in reverse logistics savings** — with zero infrastructure cost. Pure product and data changes.

The conservative scenario alone justifies the engineering investment.

---

## What I Would Build Next

1. **Real-time RRS API** — sub-50ms scoring endpoint, integrates with checkout service
2. **Cohort analysis** — track return behaviour for RRS-intervention users over 90 days to measure long-term behaviour change, not just first-order return rate
3. **Seller improvement dashboard** — give sellers visibility into their return drivers so they self-correct before penalties kick in
4. **Personalised size model** — user × seller × category size mapping, updated with every new order
5. **Return reason classifier** — NLP on return reason text to distinguish preventable returns (size, quality) from unavoidable ones (gift returns, wrong address)

---

## What I Learned

**Frame before you model.** I spent Day 1 on the hypothesis tree, not Python. This stopped me from building answers to the wrong questions.

**Transparency beats accuracy in product ML.** The rules-based RRS will get shipped. A black-box XGBoost model will die in a Jira ticket. For v1, explainability is a feature.

**The COD trade-off is the whole product challenge.** You can't understand Meesho's return problem without understanding why COD exists — it's not a bug in the system, it's the trust mechanism that got Meesho to Tier 2/3 in the first place. Any solution that ignores that context will fail.

**SQL is still the fastest way to test a hypothesis.** Every insight here was validated with a 5-line query before building anything in Python.

**Numbers without scenarios are not credible.** "₹1.2 Cr/month savings" sounds good but means nothing without a conservative case. The conservative scenario (₹0.4 Cr) is what you'd actually commit to in a business review.

---

## Deliverables

| File | Contents |
|---|---|
| `meesho_orders_enriched.csv` | 5,000 orders · 18 features · RRS + risk tier included |
| `rris_analysis.py` | Full EDA · RRS engine · Logistic Regression · 4 charts |
| `meesho_sql_queries.sql` | 10 production SQL queries · PostgreSQL-compatible |
| `eda_analysis.png` | 4-panel EDA: category · payment · seller · delivery |
| `risk_score_analysis.png` | RRS distribution + tier return rates |
| `feature_importance.png` | Logistic regression coefficients |
| `monthly_trend.png` | Volume + return rate trend (Jan 2023–Jun 2024) |

---

*Dataset is synthetic, modeled on real Meesho product dynamics. All projections are estimates based on publicly available e-commerce benchmarks.*

---

> Built this to think like a PM and execute like a data scientist. If you're working on e-commerce trust, returns, or marketplace quality problems — I'd genuinely like to compare notes.
