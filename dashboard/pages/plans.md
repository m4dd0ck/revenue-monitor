---
title: Plans
sidebar_position: 3
---

MRR by plan tier and billing interval. Annual plans are billed at ten times the monthly price and
counted as one twelfth of that per month.

```sql plans
select
    month,
    plan_tier,
    sum(mrr) as mrr,
    sum(customers) as customers,
    sum(mrr) / sum(customers) as arpa
from warehouse.mart_plan_summary
group by month, plan_tier
order by month, plan_tier
```

<AreaChart
    data={plans}
    x=month
    y=mrr
    series=plan_tier
    type=stacked
    yFmt="usd0k"
    title="MRR by tier"
    seriesOrder={['starter', 'growth', 'scale']}
/>

<LineChart
    data={plans}
    x=month
    y=arpa
    series=plan_tier
    yFmt="usd0"
    title="Average revenue per account by tier"
    seriesOrder={['starter', 'growth', 'scale']}
/>

```sql interval_mix
select
    month,
    sum(mrr) filter (where billing_interval = 'year') / sum(mrr) as annual_share_of_revenue,
    sum(customers) filter (where billing_interval = 'year') / sum(customers)
        as annual_share_of_customers
from warehouse.mart_plan_summary
group by month
order by month
```

<LineChart
    data={interval_mix}
    x=month
    y={['annual_share_of_revenue', 'annual_share_of_customers']}
    yFmt="pct0"
    yMin=0
    title="Annual billing mix"
/>

## Latest month

```sql latest
select plan_tier, billing_interval, customers, mrr, arpa, share_of_mrr_pct / 100 as share_of_mrr
from warehouse.mart_plan_summary
where month = (select max(month) from warehouse.mart_plan_summary)
order by mrr desc
```

<DataTable data={latest}>
    <Column id=plan_tier title="Tier" />
    <Column id=billing_interval title="Billing" />
    <Column id=customers fmt="num0" />
    <Column id=mrr title="MRR" fmt="usd0" />
    <Column id=arpa title="ARPA" fmt="usd0" />
    <Column id=share_of_mrr title="Share of MRR" fmt="pct1" />
</DataTable>
