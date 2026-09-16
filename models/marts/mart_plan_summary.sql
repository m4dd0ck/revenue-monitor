-- Paying customers and MRR by plan tier and billing interval, per month.
select
    month,
    plan_tier,
    billing_interval,
    count(*) as customers,
    round(sum(ending_mrr_cents) / 100.0, 2) as mrr,
    round(sum(ending_mrr_cents) / 100.0 / count(*), 2) as arpa,
    round(
        100.0 * sum(ending_mrr_cents) / sum(sum(ending_mrr_cents)) over (partition by month), 2
    ) as share_of_mrr_pct
from {{ ref('fct_customer_mrr_monthly') }}
where is_active_end
group by month, plan_tier, billing_interval
order by month, plan_tier, billing_interval
