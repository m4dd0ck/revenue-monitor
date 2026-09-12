with source as (
    {{ latest_raw('customers') }}
)

select
    payload ->> '$.id' as customer_id,
    payload ->> '$.name' as customer_name,
    payload ->> '$.email' as email,
    coalesce(payload ->> '$.metadata.country', payload ->> '$.address.country') as country,
    payload ->> '$.metadata.industry' as industry,
    payload ->> '$.metadata.employee_band' as employee_band,
    {{ epoch_to_ts("payload ->> '$.created'") }} as created_at
from source
