-- Monthly MRR bridge in dollars: starting MRR + movements = ending MRR.
with monthly as (
    select
        month,
        sum(starting_mrr_cents) as starting_mrr_cents,
        sum(new_mrr_cents) as new_mrr_cents,
        sum(expansion_mrr_cents) as expansion_mrr_cents,
        sum(reactivation_mrr_cents) as reactivation_mrr_cents,
        sum(contraction_mrr_cents) as contraction_mrr_cents,
        sum(churned_mrr_cents) as churned_mrr_cents,
        sum(ending_mrr_cents) as ending_mrr_cents,
        sum(retained_mrr_cents) as retained_mrr_cents,
        count(*) filter (where is_active_start) as customers_start,
        count(*) filter (where is_active_end) as customers_end,
        count(*) filter (where movement_type = 'new') as new_customers,
        count(*) filter (where movement_type = 'reactivation') as reactivated_customers,
        count(*) filter (where movement_type = 'churn') as churned_customers
    from {{ ref('fct_customer_mrr_monthly') }}
    group by month
)

select
    month,
    round(starting_mrr_cents / 100.0, 2) as starting_mrr,
    round(new_mrr_cents / 100.0, 2) as new_mrr,
    round(expansion_mrr_cents / 100.0, 2) as expansion_mrr,
    round(reactivation_mrr_cents / 100.0, 2) as reactivation_mrr,
    round(contraction_mrr_cents / 100.0, 2) as contraction_mrr,
    round(churned_mrr_cents / 100.0, 2) as churned_mrr,
    round((ending_mrr_cents - starting_mrr_cents) / 100.0, 2) as net_new_mrr,
    round(ending_mrr_cents / 100.0, 2) as ending_mrr,
    round(ending_mrr_cents * 12 / 100.0, 2) as arr,
    customers_start,
    customers_end,
    new_customers,
    reactivated_customers,
    churned_customers,
    round(ending_mrr_cents / 100.0 / nullif(customers_end, 0), 2) as arpa,
    round(100.0 * (ending_mrr_cents - starting_mrr_cents) / nullif(starting_mrr_cents, 0), 2)
        as mrr_growth_pct,
    round(100.0 * churned_customers / nullif(customers_start, 0), 2) as logo_churn_pct,
    round(
        100.0 * (churned_mrr_cents + contraction_mrr_cents) / nullif(starting_mrr_cents, 0), 2
    ) as gross_mrr_churn_pct,
    round(100.0 * retained_mrr_cents / nullif(starting_mrr_cents, 0), 2)
        as net_revenue_retention_pct
from monthly
order by month
