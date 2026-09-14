-- One row per charge attempt, with refunds netted against the charge they reverse.
with charges as (
    select * from {{ ref('stg_stripe__charges') }}
),

refunds as (
    select charge_id, sum(amount_cents) as refunded_cents, max(created_at) as last_refunded_at
    from {{ ref('stg_stripe__refunds') }}
    group by charge_id
)

select
    charges.charge_id,
    charges.customer_id,
    charges.invoice_id,
    charges.charge_status,
    charges.failure_code,
    charges.amount_cents,
    coalesce(refunds.refunded_cents, 0) as refunded_cents,
    case
        when charges.charge_status = 'succeeded'
            then charges.amount_cents - coalesce(refunds.refunded_cents, 0)
        else 0
    end as net_collected_cents,
    refunds.last_refunded_at,
    charges.created_at,
    date_trunc('month', charges.created_at)::date as payment_month
from charges
left join refunds using (charge_id)
