-- Churned customers and MRR by month, voluntary vs involuntary, and the tier they left from.
select
    month,
    churn_type,
    plan_tier,
    billing_interval,
    count(*) as churned_customers,
    round(sum(churned_mrr_cents) / 100.0, 2) as churned_mrr
from {{ ref('fct_customer_mrr_monthly') }}
where movement_type = 'churn'
group by month, churn_type, plan_tier, billing_interval
order by month, churn_type, plan_tier, billing_interval
