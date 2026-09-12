-- One row per subscription state, rebuilt from event snapshots.
-- Subscriptions with no events (Stripe keeps events for 30 days) fall back to their current
-- snapshot: one version from start, plus a canceled version at ended_at when it has ended.
with events as (
    select * from {{ ref('stg_stripe__events') }}
),

subscriptions as (
    select * from {{ ref('stg_stripe__subscriptions') }}
),

event_versions as (
    select
        event_id,
        event_type,
        created_at as valid_from,
        {{ subscription_fields('subscription_snapshot') }}
    from events
),

without_events as (
    select subscriptions.*
    from subscriptions
    anti join event_versions using (subscription_id)
),

fallback_start as (
    select
        null::varchar as event_id,
        'snapshot.start' as event_type,
        started_at as valid_from,
        * replace (
            case
                when status != 'canceled' then status
                when ended_at = trial_ended_at then 'trialing'
                else 'active'
            end as status
        )
    from without_events
),

fallback_end as (
    select
        null::varchar as event_id,
        'snapshot.end' as event_type,
        ended_at as valid_from,
        *
    from without_events
    where status = 'canceled' and ended_at is not null
),

versions as (
    select * from event_versions
    union all by name
    select * from fallback_start
    union all by name
    select * from fallback_end
)

select
    *,
    lead(valid_from) over (
        partition by subscription_id
        order by valid_from, event_id
    ) as valid_to
from versions
