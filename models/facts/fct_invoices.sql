with invoices as (
    select * from {{ ref('stg_stripe__invoices') }}
)

select
    invoice_id,
    customer_id,
    subscription_id,
    invoice_status,
    billing_reason,
    amount_due_cents,
    amount_paid_cents,
    attempt_count,
    attempt_count > 1 or invoice_status = 'uncollectible' as had_failed_payment,
    created_at,
    date_trunc('month', created_at)::date as invoice_month,
    period_started_at,
    period_ended_at
from invoices
