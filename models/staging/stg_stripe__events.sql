-- Subscription change events. data.object is a full snapshot of the subscription after the
-- change, which int_subscription_versions turns into SCD2 history.
with source as (
    {{ latest_raw('events') }}
)

select
    payload ->> '$.id' as event_id,
    payload ->> '$.type' as event_type,
    {{ epoch_to_ts("payload ->> '$.created'") }} as created_at,
    payload -> '$.data.object' as subscription_snapshot
from source
where payload ->> '$.type' like 'customer.subscription.%'
