with source as (
    {{ latest_raw('prices') }}
)

select
    payload ->> '$.id' as price_id,
    payload ->> '$.product' as product_id,
    payload ->> '$.nickname' as price_nickname,
    (payload ->> '$.unit_amount')::bigint as unit_amount_cents,
    payload ->> '$.currency' as currency,
    payload ->> '$.recurring.interval' as billing_interval,
    coalesce((payload ->> '$.recurring.interval_count')::integer, 1) as interval_count,
    {{ epoch_to_ts("payload ->> '$.created'") }} as created_at
from source
