with source as (
    {{ latest_raw('refunds') }}
)

select
    payload ->> '$.id' as refund_id,
    payload ->> '$.charge' as charge_id,
    payload ->> '$.reason' as refund_reason,
    (payload ->> '$.amount')::bigint as amount_cents,
    {{ epoch_to_ts("payload ->> '$.created'") }} as created_at
from source
