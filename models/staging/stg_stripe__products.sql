with source as (
    {{ latest_raw('products') }}
)

select
    payload ->> '$.id' as product_id,
    payload ->> '$.name' as product_name,
    coalesce(payload ->> '$.metadata.tier', lower(payload ->> '$.name')) as plan_tier,
    {{ epoch_to_ts("payload ->> '$.created'") }} as created_at
from source
