-- ═══════════════════════════════════════════════════════════════════════════
-- MEESHO RRIS — SQL ANALYSIS QUERIES
-- Database: PostgreSQL | Table: meesho_orders
-- Author: RRIS Analytics | 2024
-- ═══════════════════════════════════════════════════════════════════════════

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. OVERALL RETURN RATE SNAPSHOT
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    COUNT(*)                                         AS total_orders,
    SUM(return_flag)                                 AS total_returns,
    ROUND(AVG(return_flag) * 100, 2)                 AS return_rate_pct,
    ROUND(AVG(price), 2)                             AS avg_order_value,
    ROUND(SUM(return_flag) * 100.0, 2)               AS estimated_reverse_logistics_cost_inr  -- ~₹100 per return
FROM meesho_orders;


-- ─────────────────────────────────────────────────────────────────────────────
-- 2. RETURN RATE BY CATEGORY (with GMV impact)
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    product_category,
    COUNT(*)                                         AS total_orders,
    SUM(return_flag)                                 AS returned_orders,
    ROUND(AVG(return_flag) * 100, 2)                 AS return_rate_pct,
    ROUND(SUM(price), 2)                             AS total_gmv,
    ROUND(SUM(CASE WHEN return_flag = 1 THEN price ELSE 0 END), 2)  AS returned_gmv,
    ROUND(SUM(CASE WHEN return_flag = 1 THEN price ELSE 0 END) /
          NULLIF(SUM(price), 0) * 100, 2)            AS returned_gmv_pct
FROM meesho_orders
GROUP BY product_category
ORDER BY return_rate_pct DESC;


-- ─────────────────────────────────────────────────────────────────────────────
-- 3. COD vs PREPAID ANALYSIS
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    payment_type,
    COUNT(*)                                         AS total_orders,
    SUM(return_flag)                                 AS returns,
    ROUND(AVG(return_flag) * 100, 2)                 AS return_rate_pct,
    ROUND(AVG(price), 2)                             AS avg_order_value,
    ROUND(SUM(return_flag) * 100.0 / COUNT(*), 2)    AS cost_per_100_orders  -- ₹100 reverse logistics
FROM meesho_orders
GROUP BY payment_type;


-- ─────────────────────────────────────────────────────────────────────────────
-- 4. SELLER PERFORMANCE INTELLIGENCE
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    seller_id,
    COUNT(*)                                         AS total_orders,
    ROUND(AVG(seller_rating), 2)                     AS avg_rating,
    SUM(return_flag)                                 AS total_returns,
    ROUND(AVG(return_flag) * 100, 2)                 AS return_rate_pct,
    ROUND(SUM(CASE WHEN return_flag = 1 THEN price ELSE 0 END), 2) AS returned_gmv,
    CASE
        WHEN AVG(return_flag) > 0.55 THEN 'High Risk — Review'
        WHEN AVG(return_flag) > 0.40 THEN 'Medium Risk — Monitor'
        ELSE 'Low Risk — Reliable'
    END                                              AS seller_risk_label
FROM meesho_orders
GROUP BY seller_id
HAVING COUNT(*) >= 10                                -- minimum order threshold
ORDER BY return_rate_pct DESC
LIMIT 20;


-- ─────────────────────────────────────────────────────────────────────────────
-- 5. DELIVERY DELAY IMPACT
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    CASE
        WHEN delivery_days <= 2 THEN '1-2 days (Fast)'
        WHEN delivery_days <= 4 THEN '3-4 days (Standard)'
        WHEN delivery_days <= 6 THEN '5-6 days (Slow)'
        ELSE '7+ days (Very Slow)'
    END                                              AS delivery_bucket,
    COUNT(*)                                         AS orders,
    ROUND(AVG(return_flag) * 100, 2)                 AS return_rate_pct,
    ROUND(AVG(price), 2)                             AS avg_order_value
FROM meesho_orders
GROUP BY
    CASE
        WHEN delivery_days <= 2 THEN '1-2 days (Fast)'
        WHEN delivery_days <= 4 THEN '3-4 days (Standard)'
        WHEN delivery_days <= 6 THEN '5-6 days (Slow)'
        ELSE '7+ days (Very Slow)'
    END
ORDER BY return_rate_pct;


-- ─────────────────────────────────────────────────────────────────────────────
-- 6. RETURN RISK SCORE (RRS) — COMPUTED IN SQL
-- ─────────────────────────────────────────────────────────────────────────────
WITH risk_scores AS (
    SELECT
        order_id,
        user_id,
        product_category,
        payment_type,
        seller_rating,
        delivery_days,
        user_past_returns,
        return_flag,
        price,
        (
            CASE WHEN payment_type = 'COD'         THEN 25 ELSE 0 END +
            CASE WHEN seller_rating < 3             THEN 30
                 WHEN seller_rating < 4             THEN 15 ELSE 0 END +
            CASE WHEN delivery_days > 7             THEN 20
                 WHEN delivery_days > 5             THEN 10 ELSE 0 END +
            CASE WHEN user_past_returns >= 3        THEN 20
                 WHEN user_past_returns >= 1        THEN 10 ELSE 0 END +
            CASE WHEN product_category = 'Fashion' THEN 15 ELSE 0 END
        )                                          AS rrs
    FROM meesho_orders
),
tiered AS (
    SELECT *,
        CASE
            WHEN rrs <= 25  THEN 'Low'
            WHEN rrs <= 50  THEN 'Medium'
            WHEN rrs <= 75  THEN 'High'
            ELSE                 'Very High'
        END                                        AS risk_tier
    FROM risk_scores
)
SELECT
    risk_tier,
    COUNT(*)                                       AS orders,
    ROUND(AVG(return_flag) * 100, 2)               AS actual_return_rate_pct,
    ROUND(AVG(rrs), 1)                             AS avg_rrs,
    SUM(return_flag)                               AS actual_returns,
    ROUND(SUM(return_flag) * 100.0, 2)             AS potential_cost_inr
FROM tiered
GROUP BY risk_tier
ORDER BY
    CASE risk_tier
        WHEN 'Low' THEN 1 WHEN 'Medium' THEN 2
        WHEN 'High' THEN 3 WHEN 'Very High' THEN 4
    END;


-- ─────────────────────────────────────────────────────────────────────────────
-- 7. HIGH-RISK USER IDENTIFICATION (Intervention candidates)
-- ─────────────────────────────────────────────────────────────────────────────
WITH user_stats AS (
    SELECT
        user_id,
        COUNT(*)                                   AS total_orders,
        SUM(return_flag)                           AS total_returns,
        ROUND(AVG(return_flag) * 100, 2)           AS return_rate_pct,
        ROUND(SUM(price), 2)                       AS lifetime_gmv,
        MAX(order_date::DATE)                      AS last_order_date,
        SUM(CASE WHEN payment_type = 'COD' THEN 1 ELSE 0 END) AS cod_orders,
        MODE() WITHIN GROUP (ORDER BY product_category)       AS favourite_category
    FROM meesho_orders
    GROUP BY user_id
    HAVING COUNT(*) >= 3                           -- minimum order threshold
)
SELECT
    user_id,
    total_orders,
    total_returns,
    return_rate_pct,
    lifetime_gmv,
    cod_orders,
    favourite_category,
    CASE
        WHEN return_rate_pct >= 70 THEN 'Blacklist candidate'
        WHEN return_rate_pct >= 50 THEN 'COD restriction candidate'
        WHEN return_rate_pct >= 35 THEN 'Show trust nudge'
        ELSE 'Standard flow'
    END                                            AS recommended_intervention
FROM user_stats
WHERE return_rate_pct >= 35
ORDER BY return_rate_pct DESC, total_returns DESC
LIMIT 30;


-- ─────────────────────────────────────────────────────────────────────────────
-- 8. MONTHLY TREND WITH MoM CHANGE
-- ─────────────────────────────────────────────────────────────────────────────
WITH monthly AS (
    SELECT
        DATE_TRUNC('month', order_date::DATE)      AS month,
        COUNT(*)                                   AS total_orders,
        SUM(return_flag)                           AS returns,
        ROUND(AVG(return_flag) * 100, 2)           AS return_rate_pct
    FROM meesho_orders
    GROUP BY DATE_TRUNC('month', order_date::DATE)
)
SELECT
    TO_CHAR(month, 'Mon YYYY')                     AS month_label,
    total_orders,
    returns,
    return_rate_pct,
    ROUND(return_rate_pct - LAG(return_rate_pct) OVER (ORDER BY month), 2) AS mom_change_ppt
FROM monthly
ORDER BY month;


-- ─────────────────────────────────────────────────────────────────────────────
-- 9. CROSS-SEGMENT: FASHION × COD — HIGHEST RISK COMBO
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    product_category,
    payment_type,
    CASE
        WHEN delivery_days <= 4 THEN 'Fast (<= 4 days)'
        ELSE 'Slow (> 4 days)'
    END                                            AS delivery_speed,
    COUNT(*)                                       AS orders,
    ROUND(AVG(return_flag) * 100, 2)               AS return_rate_pct
FROM meesho_orders
GROUP BY product_category, payment_type,
    CASE WHEN delivery_days <= 4 THEN 'Fast (<= 4 days)' ELSE 'Slow (> 4 days)' END
ORDER BY return_rate_pct DESC
LIMIT 15;


-- ─────────────────────────────────────────────────────────────────────────────
-- 10. A/B TEST SIMULATION — IMPACT OF COD RESTRICTION
-- ─────────────────────────────────────────────────────────────────────────────
-- Simulate: restrict COD for Very High RRS users (rrs > 75)
-- Assumption: 30% of these users convert to prepaid, 70% abandon
-- Prepaid return rate for this segment based on actual data

WITH rrs_calc AS (
    SELECT *,
        (
            CASE WHEN payment_type = 'COD'         THEN 25 ELSE 0 END +
            CASE WHEN seller_rating < 3             THEN 30
                 WHEN seller_rating < 4             THEN 15 ELSE 0 END +
            CASE WHEN delivery_days > 7             THEN 20
                 WHEN delivery_days > 5             THEN 10 ELSE 0 END +
            CASE WHEN user_past_returns >= 3        THEN 20
                 WHEN user_past_returns >= 1        THEN 10 ELSE 0 END +
            CASE WHEN product_category = 'Fashion' THEN 15 ELSE 0 END
        ) AS rrs
    FROM meesho_orders
)
SELECT
    'Baseline (No Intervention)'                   AS scenario,
    COUNT(*)                                       AS orders,
    SUM(return_flag)                               AS returns,
    ROUND(AVG(return_flag) * 100, 2)               AS return_rate_pct,
    ROUND(SUM(return_flag) * 100.0, 2)             AS logistics_cost_inr
FROM rrs_calc

UNION ALL

SELECT
    'Test (COD restricted for RRS > 75)'           AS scenario,
    COUNT(*) - ROUND(COUNT(*) * 0.7 * (rrs > 75)::INT * 0.1)  AS estimated_orders,
    -- Very High RRS COD orders: 30% stay (become prepaid, lower return) + 70% abandon
    SUM(CASE
        WHEN rrs > 75 AND payment_type = 'COD' THEN return_flag * 0.35  -- prepaid rate
        ELSE return_flag
    END)                                           AS estimated_returns,
    ROUND(SUM(CASE
        WHEN rrs > 75 AND payment_type = 'COD' THEN return_flag * 0.35
        ELSE return_flag
    END) / COUNT(*) * 100, 2)                      AS estimated_return_rate_pct,
    ROUND(SUM(CASE
        WHEN rrs > 75 AND payment_type = 'COD' THEN return_flag * 35
        ELSE return_flag * 100
    END), 2)                                       AS estimated_logistics_cost_inr
FROM rrs_calc;

