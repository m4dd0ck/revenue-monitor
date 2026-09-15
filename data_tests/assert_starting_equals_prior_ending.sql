-- A customer's starting MRR is last month's ending MRR; no gaps in the monthly spine.
with ordered as (
    select
        customer_id,
        month,
        starting_mrr_cents,
        lag(ending_mrr_cents) over (partition by customer_id order by month) as prior_ending,
        lag(month) over (partition by customer_id order by month) as prior_month
    from {{ ref('fct_customer_mrr_monthly') }}
)

select *
from ordered
where prior_month is not null
  and (starting_mrr_cents != prior_ending or prior_month != month - interval 1 month)
