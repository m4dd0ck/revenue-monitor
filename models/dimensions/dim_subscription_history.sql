-- SCD Type 2: one row per subscription version, valid_from inclusive, valid_to exclusive.
with versions as (
    select * from {{ ref('int_subscription_versions') }}
),

plans as (
    select price_id, plan_tier from {{ ref('dim_plan') }}
)

select
    md5(versions.subscription_id || versions.valid_from::varchar || coalesce(versions.event_id, ''))
        as subscription_version_id,
    versions.subscription_id,
    versions.customer_id,
    versions.event_id,
    versions.event_type,
    versions.valid_from,
    versions.valid_to,
    versions.valid_to is null as is_current,
    versions.status,
    versions.price_id,
    versions.product_id,
    plans.plan_tier,
    versions.billing_interval,
    versions.unit_amount_cents,
    versions.quantity,
    versions.item_count,
    versions.discount_percent_off,
    versions.discount_started_at,
    versions.discount_ended_at,
    versions.is_cancel_at_period_end,
    versions.cancellation_reason
from versions
left join plans using (price_id)
