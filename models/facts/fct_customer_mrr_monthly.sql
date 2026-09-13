-- One row per customer per month with the MRR movement that got them there.
with customer_months as (
    select * from {{ ref('int_customer_months') }}
),

with_prior as (
    select
        *,
        coalesce(lag(mrr_cents) over by_customer, 0) as starting_mrr_cents,
        lag(plan_tier) over by_customer as prior_plan_tier,
        lag(billing_interval) over by_customer as prior_billing_interval,
        coalesce(
            max(mrr_cents) over (
                partition by customer_id
                order by month
                rows between unbounded preceding and 1 preceding
            ),
            0
        ) > 0 as has_paid_before
    from customer_months
    window by_customer as (partition by customer_id order by month)
),

classified as (
    select
        *,
        mrr_cents as ending_mrr_cents,
        case
            when starting_mrr_cents = 0 and mrr_cents > 0 and not has_paid_before then 'new'
            when starting_mrr_cents = 0 and mrr_cents > 0 then 'reactivation'
            when starting_mrr_cents > 0 and mrr_cents = 0 then 'churn'
            when mrr_cents > starting_mrr_cents then 'expansion'
            when mrr_cents < starting_mrr_cents then 'contraction'
            else 'none'
        end as movement_type
    from with_prior
)

select
    md5(customer_id || month::varchar) as customer_month_id,
    customer_id,
    month,
    movement_type,
    -- churned customers keep the tier they left from, so churn can be sliced by tier
    case when ending_mrr_cents > 0 then plan_tier else prior_plan_tier end as plan_tier,
    case when ending_mrr_cents > 0 then billing_interval else prior_billing_interval end
        as billing_interval,
    case
        when movement_type != 'churn' then null
        when cancellation_reason = 'payment_failed' then 'involuntary'
        else 'voluntary'
    end as churn_type,
    starting_mrr_cents,
    ending_mrr_cents,
    case when movement_type = 'new' then ending_mrr_cents else 0 end as new_mrr_cents,
    case when movement_type = 'expansion' then ending_mrr_cents - starting_mrr_cents else 0 end
        as expansion_mrr_cents,
    case when movement_type = 'contraction' then starting_mrr_cents - ending_mrr_cents else 0 end
        as contraction_mrr_cents,
    case when movement_type = 'churn' then starting_mrr_cents else 0 end as churned_mrr_cents,
    case when movement_type = 'reactivation' then ending_mrr_cents else 0 end
        as reactivation_mrr_cents,
    ending_mrr_cents - starting_mrr_cents as net_new_mrr_cents,
    case when starting_mrr_cents > 0 then ending_mrr_cents else 0 end as retained_mrr_cents,
    starting_mrr_cents > 0 as is_active_start,
    ending_mrr_cents > 0 as is_active_end,
    has_past_due_subscription,
    min(month) filter (where ending_mrr_cents > 0) over (partition by customer_id) as cohort_month
from classified
