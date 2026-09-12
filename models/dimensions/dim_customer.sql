with customers as (
    select * from {{ ref('stg_stripe__customers') }}
),

subscriptions as (
    select
        customer_id,
        min(created_at) as first_subscription_at,
        count(*) as subscription_count
    from {{ ref('stg_stripe__subscriptions') }}
    group by customer_id
)

select
    customers.customer_id,
    customers.customer_name,
    customers.email,
    customers.country,
    customers.industry,
    customers.employee_band,
    customers.created_at as signed_up_at,
    date_trunc('month', customers.created_at)::date as signup_month,
    subscriptions.first_subscription_at,
    coalesce(subscriptions.subscription_count, 0) as subscription_count,
    coalesce(subscriptions.subscription_count, 0) > 1 as has_resubscribed
from customers
left join subscriptions using (customer_id)
