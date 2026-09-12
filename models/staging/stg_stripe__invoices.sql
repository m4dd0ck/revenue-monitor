with source as (
    {{ latest_raw('invoices') }}
)

select
    payload ->> '$.id' as invoice_id,
    payload ->> '$.customer' as customer_id,
    payload ->> '$.subscription' as subscription_id,
    payload ->> '$.status' as invoice_status,
    payload ->> '$.billing_reason' as billing_reason,
    (payload ->> '$.amount_due')::bigint as amount_due_cents,
    (payload ->> '$.amount_paid')::bigint as amount_paid_cents,
    (payload ->> '$.attempt_count')::integer as attempt_count,
    {{ epoch_to_ts("payload ->> '$.created'") }} as created_at,
    {{ epoch_to_ts("payload ->> '$.period_start'") }} as period_started_at,
    {{ epoch_to_ts("payload ->> '$.period_end'") }} as period_ended_at
from source
