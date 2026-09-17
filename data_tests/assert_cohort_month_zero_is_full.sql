-- Every cohort starts at 100% logo and revenue retention in its first month.
select *
from {{ ref('mart_cohort_retention') }}
where months_since_start = 0
  and (logo_retention_pct != 100 or net_revenue_retention_pct != 100)
