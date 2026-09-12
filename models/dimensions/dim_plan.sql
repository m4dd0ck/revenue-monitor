-- One row per price. Plan tier comes from the product; MRR normalises annual prices to monthly.
with prices as (
    select * from {{ ref('stg_stripe__prices') }}
),

products as (
    select * from {{ ref('stg_stripe__products') }}
)

select
    prices.price_id,
    prices.product_id,
    products.product_name,
    products.plan_tier,
    prices.price_nickname,
    prices.billing_interval,
    prices.unit_amount_cents,
    case prices.billing_interval
        when 'year' then round(prices.unit_amount_cents / 12.0)
        else prices.unit_amount_cents
    end::bigint as monthly_seat_cents
from prices
left join products using (product_id)
