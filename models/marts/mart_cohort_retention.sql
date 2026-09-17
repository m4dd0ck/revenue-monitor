-- Logo and revenue retention by the month a customer first paid.
-- Reactivated customers stay in their original cohort.
with customer_months as (
    select
        customer_id,
        cohort_month,
        month,
        date_diff('month', cohort_month, month) as months_since_start,
        is_active_end,
        ending_mrr_cents
    from {{ ref('fct_customer_mrr_monthly') }}
    where cohort_month is not null
      and month >= cohort_month
),

cohort_sizes as (
    select
        cohort_month,
        count(*) as cohort_customers,
        sum(ending_mrr_cents) as cohort_starting_mrr_cents
    from customer_months
    where months_since_start = 0
    group by cohort_month
),

retention as (
    select
        cohort_month,
        months_since_start,
        count(*) filter (where is_active_end) as retained_customers,
        sum(ending_mrr_cents) as cohort_mrr_cents
    from customer_months
    group by cohort_month, months_since_start
)

select
    retention.cohort_month,
    retention.months_since_start,
    cohort_sizes.cohort_customers,
    retention.retained_customers,
    round(100.0 * retention.retained_customers / cohort_sizes.cohort_customers, 2)
        as logo_retention_pct,
    round(cohort_sizes.cohort_starting_mrr_cents / 100.0, 2) as cohort_starting_mrr,
    round(retention.cohort_mrr_cents / 100.0, 2) as cohort_mrr,
    round(100.0 * retention.cohort_mrr_cents / cohort_sizes.cohort_starting_mrr_cents, 2)
        as net_revenue_retention_pct
from retention
inner join cohort_sizes using (cohort_month)
order by retention.cohort_month, retention.months_since_start
