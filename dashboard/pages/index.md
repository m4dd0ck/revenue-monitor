---
title: Overview
---

Subscription revenue for a fictional B2B SaaS selling per-seat plans in three tiers. Data comes
from `revmon generate` (or a Stripe test account); MRR is measured per customer at month end.

```sql kpis
select
    month,
    ending_mrr,
    arr,
    customers_end,
    arpa,
    logo_churn_pct / 100 as logo_churn,
    net_revenue_retention_pct / 100 as nrr,
    ending_mrr / lag(ending_mrr) over (order by month) - 1 as mrr_change,
    customers_end - lag(customers_end) over (order by month) as customer_change,
    arpa / lag(arpa) over (order by month) - 1 as arpa_change,
    (logo_churn_pct - lag(logo_churn_pct) over (order by month)) / 100 as churn_change,
    (net_revenue_retention_pct - lag(net_revenue_retention_pct) over (order by month)) / 100
        as nrr_change
from warehouse.mart_mrr_bridge
order by month desc
```

<BigValue data={kpis} value=ending_mrr title="MRR" fmt="usd0k" sparkline=month
    comparison=mrr_change comparisonFmt="pct1" comparisonTitle="vs last month" />
<BigValue data={kpis} value=arr title="ARR" fmt="usd1m" sparkline=month
    comparison=mrr_change comparisonFmt="pct1" comparisonTitle="vs last month" />
<BigValue data={kpis} value=customers_end title="Paying customers" fmt="num0" sparkline=month
    comparison=customer_change comparisonFmt="num0" comparisonTitle="vs last month" />
<BigValue data={kpis} value=arpa title="ARPA" fmt="usd0" sparkline=month
    comparison=arpa_change comparisonFmt="pct1" comparisonTitle="vs last month" />
<BigValue data={kpis} value=logo_churn title="Logo churn (month)" fmt="pct1" sparkline=month
    comparison=churn_change comparisonFmt="pct1" comparisonTitle="vs last month" downIsGood=true />
<BigValue data={kpis} value=nrr title="Net revenue retention (month)" fmt="pct1" sparkline=month
    comparison=nrr_change comparisonFmt="pct1" comparisonTitle="vs last month" />

## MRR

```sql bridge
select * from warehouse.mart_mrr_bridge order by month
```

<LineChart data={bridge} x=month y=ending_mrr yFmt="usd0k" title="MRR at month end" />

<BarChart data={bridge} x=month y=net_new_mrr yFmt="usd0k" title="Net new MRR" />

## Customers

<LineChart data={bridge} x=month y=customers_end yFmt="num0" title="Paying customers" />

<BarChart
    data={bridge}
    x=month
    y={['new_customers', 'reactivated_customers']}
    type=stacked
    title="Customers won per month"
/>
