select *
from {{ ref('fct_customer_mrr_monthly') }}
where new_mrr_cents < 0
   or expansion_mrr_cents < 0
   or contraction_mrr_cents < 0
   or churned_mrr_cents < 0
   or reactivation_mrr_cents < 0
