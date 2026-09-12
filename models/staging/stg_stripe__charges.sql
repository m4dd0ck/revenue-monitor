with source as (
    {{ latest_raw('charges') }}
)

select
    payload ->> '$.id' as charge_id,
    payload ->> '$.customer' as customer_id,
    -- Newer API versions dropped charge.invoice; the generator records it in metadata.
    coalesce(payload ->> '$.invoice', payload ->> '$.metadata.invoice') as invoice_id,
    payload ->> '$.status' as charge_status,
    payload ->> '$.failure_code' as failure_code,
    (payload ->> '$.amount')::bigint as amount_cents,
    payload ->> '$.currency' as currency,
    {{ epoch_to_ts("payload ->> '$.created'") }} as created_at
from source
