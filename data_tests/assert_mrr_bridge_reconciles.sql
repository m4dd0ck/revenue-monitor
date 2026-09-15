-- Starting MRR plus every movement must equal ending MRR, every month, to the cent.
select
    month,
    sum(starting_mrr_cents) as starting,
    sum(new_mrr_cents + expansion_mrr_cents + reactivation_mrr_cents
        - contraction_mrr_cents - churned_mrr_cents) as movements,
    sum(ending_mrr_cents) as ending
from {{ ref('fct_customer_mrr_monthly') }}
group by month
having sum(starting_mrr_cents)
    + sum(new_mrr_cents + expansion_mrr_cents + reactivation_mrr_cents
          - contraction_mrr_cents - churned_mrr_cents)
    != sum(ending_mrr_cents)
