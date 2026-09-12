-- Current state of each subscription. History comes from stg_stripe__events.
with source as (
    {{ latest_raw('subscriptions') }}
)

select
    {{ subscription_fields('payload') }}
from source
