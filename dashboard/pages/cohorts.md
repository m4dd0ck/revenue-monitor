---
title: Cohorts
sidebar_position: 2
---

Customers grouped by the month they first paid. Logo retention counts customers still paying;
net revenue retention compares the cohort's MRR today with its MRR in the first month, so
expansion can push it above 100%.

```sql cohorts
select
    strftime(cohort_month, '%Y-%m') as cohort,
    months_since_start,
    cohort_customers,
    logo_retention_pct / 100 as logo_retention,
    net_revenue_retention_pct / 100 as net_revenue_retention
from warehouse.mart_cohort_retention
where cohort_month >= (select max(cohort_month) from warehouse.mart_cohort_retention) - interval 23 month
  and months_since_start <= 12
order by cohort_month, months_since_start
```

<Heatmap
    data={cohorts}
    x=months_since_start
    xSort=months_since_start
    y=cohort
    value=logo_retention
    valueFmt="pct0"
    title="Logo retention by cohort (last 24 cohorts, first 12 months)"
    nullsZero=false
/>

<Heatmap
    data={cohorts}
    x=months_since_start
    xSort=months_since_start
    y=cohort
    value=net_revenue_retention
    valueFmt="pct0"
    title="Net revenue retention by cohort"
    nullsZero=false
/>

```sql curve
-- Weighted across every cohort old enough to have reached each month.
select
    months_since_start,
    sum(retained_customers) / sum(cohort_customers) as logo_retention,
    sum(cohort_mrr) / sum(cohort_starting_mrr) as net_revenue_retention
from warehouse.mart_cohort_retention
where months_since_start <= 24
group by months_since_start
order by months_since_start
```

<LineChart
    data={curve}
    x=months_since_start
    y={['logo_retention', 'net_revenue_retention']}
    yFmt="pct0"
    xAxisTitle="Months since first payment"
    title="Average retention curve"
/>
