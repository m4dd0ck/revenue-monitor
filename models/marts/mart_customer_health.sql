-- Current state of every customer who has paid, with simple risk flags for a CS team.
with mrr as (
    select * from {{ ref('fct_customer_mrr_monthly') }}
),

report as (
    select max(month) as report_month, max(month) + interval 1 month as report_end_at
    from mrr
),

latest as (
    select mrr.*
    from mrr
    inner join report on mrr.month = report.report_month
),

history as (
    select
        customer_id,
        count(*) filter (where is_active_end) as paid_months,
        bool_or(movement_type = 'contraction' and month > report.report_month - interval 3 month)
            as contracted_last_3_months
    from mrr
    cross join report
    group by customer_id
),

payments as (
    select
        customer_id,
        count(*) filter (
            where charge_status = 'failed' and created_at >= report.report_end_at - interval 90 day
        ) as failed_payments_90d,
        sum(net_collected_cents) as lifetime_collected_cents
    from {{ ref('fct_payments') }}
    cross join report
    group by customer_id
),

invoices as (
    select customer_id, arg_max(invoice_status, created_at) as last_invoice_status
    from {{ ref('fct_invoices') }}
    group by customer_id
)

select
    customers.customer_id,
    customers.customer_name,
    customers.country,
    customers.industry,
    customers.employee_band,
    latest.cohort_month,
    latest.plan_tier,
    latest.billing_interval,
    round(latest.ending_mrr_cents / 100.0, 2) as current_mrr,
    history.paid_months as tenure_months,
    coalesce(payments.failed_payments_90d, 0) as failed_payments_90d,
    invoices.last_invoice_status,
    round(coalesce(payments.lifetime_collected_cents, 0) / 100.0, 2) as lifetime_collected,
    case
        when latest.ending_mrr_cents = 0 then 'churned'
        when latest.has_past_due_subscription
            or coalesce(payments.failed_payments_90d, 0) >= 2
            or history.contracted_last_3_months then 'at risk'
        else 'healthy'
    end as health_status
from latest
inner join {{ ref('dim_customer') }} as customers using (customer_id)
inner join history using (customer_id)
left join payments using (customer_id)
left join invoices using (customer_id)
where latest.cohort_month is not null
