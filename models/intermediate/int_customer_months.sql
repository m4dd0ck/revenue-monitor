-- MRR per customer as of the end of every month, from their first subscription to the last
-- month with data. The state that counts is the subscription version in force just before the
-- next month starts; see README "Metric definitions" for the rules applied here.
with history as (
    select * from {{ ref('dim_subscription_history') }}
),

report_end as (
    select date_trunc('month', max(valid_from))::date as report_end_month
    from history
),

customer_starts as (
    select customer_id, date_trunc('month', min(valid_from))::date as first_month
    from history
    group by customer_id
),

spine as (
    select
        customer_starts.customer_id,
        unnest(range(
            customer_starts.first_month,
            report_end.report_end_month + interval 1 month,
            interval 1 month
        ))::date as month
    from customer_starts
    cross join report_end
),

state_at_month_end as (
    select
        spine.customer_id,
        spine.month,
        history.subscription_id,
        history.status,
        history.plan_tier,
        history.billing_interval,
        history.cancellation_reason,
        -- canceled during this month, as opposed to a subscription that ended earlier
        history.status = 'canceled' and history.valid_from >= spine.month as is_canceled_this_month,
        case
            when history.status in ('active', 'past_due') then
                history.unit_amount_cents * history.quantity
                / case history.billing_interval when 'year' then 12.0 else 1.0 end
                * (1 - case
                    when history.discount_started_at < spine.month + interval 1 month
                        and (
                            history.discount_ended_at is null
                            or history.discount_ended_at >= spine.month + interval 1 month
                        )
                        then coalesce(history.discount_percent_off, 0)
                    else 0
                end / 100.0)
            else 0
        end as subscription_mrr_cents
    from spine
    left join history
        on history.customer_id = spine.customer_id
        and history.valid_from < spine.month + interval 1 month
        and (history.valid_to is null or history.valid_to >= spine.month + interval 1 month)
)

select
    customer_id,
    month,
    round(coalesce(sum(subscription_mrr_cents), 0))::bigint as mrr_cents,
    arg_max(plan_tier, subscription_mrr_cents) filter (where subscription_mrr_cents > 0)
        as plan_tier,
    arg_max(billing_interval, subscription_mrr_cents) filter (where subscription_mrr_cents > 0)
        as billing_interval,
    bool_or(status = 'past_due') as has_past_due_subscription,
    -- 'payment_failed' sorts after 'cancellation_requested', so max() prefers involuntary
    max(cancellation_reason) filter (where is_canceled_this_month) as cancellation_reason
from state_at_month_end
group by customer_id, month
