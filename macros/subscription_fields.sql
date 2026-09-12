{#
    Subscription payloads look the same in raw.subscriptions and inside event snapshots, so
    both are parsed here. Assumes one item per subscription (asserted by a data test).
    Discount paths cover the older `discount` field and newer `discounts` list shapes.
#}
{% macro subscription_fields(obj) -%}
    {{ obj }} ->> '$.id' as subscription_id,
    {{ obj }} ->> '$.customer' as customer_id,
    {{ obj }} ->> '$.status' as status,
    {{ epoch_to_ts(obj ~ " ->> '$.created'") }} as created_at,
    {{ epoch_to_ts(obj ~ " ->> '$.start_date'") }} as started_at,
    {{ epoch_to_ts(obj ~ " ->> '$.trial_start'") }} as trial_started_at,
    {{ epoch_to_ts(obj ~ " ->> '$.trial_end'") }} as trial_ended_at,
    {{ epoch_to_ts(obj ~ " ->> '$.canceled_at'") }} as canceled_at,
    {{ epoch_to_ts(obj ~ " ->> '$.ended_at'") }} as ended_at,
    coalesce(({{ obj }} ->> '$.cancel_at_period_end')::boolean, false) as is_cancel_at_period_end,
    {{ obj }} ->> '$.cancellation_details.reason' as cancellation_reason,
    json_array_length({{ obj }} -> '$.items.data') as item_count,
    {{ obj }} ->> '$.items.data[0].price.id' as price_id,
    {{ obj }} ->> '$.items.data[0].price.product' as product_id,
    ({{ obj }} ->> '$.items.data[0].price.unit_amount')::bigint as unit_amount_cents,
    {{ obj }} ->> '$.items.data[0].price.recurring.interval' as billing_interval,
    ({{ obj }} ->> '$.items.data[0].quantity')::integer as quantity,
    coalesce(
        {{ obj }} ->> '$.discounts[0].coupon.percent_off',
        {{ obj }} ->> '$.discounts[0].source.coupon.percent_off',
        {{ obj }} ->> '$.discount.coupon.percent_off'
    )::double as discount_percent_off,
    {{ epoch_to_ts("coalesce(" ~ obj ~ " ->> '$.discounts[0].start', " ~ obj ~ " ->> '$.discount.start')") }}
        as discount_started_at,
    {{ epoch_to_ts("coalesce(" ~ obj ~ " ->> '$.discounts[0].end', " ~ obj ~ " ->> '$.discount.end')") }}
        as discount_ended_at
{%- endmacro %}
