---
title: MRR Bridge
sidebar_position: 1
---

How MRR moved each month. Starting MRR plus new, expansion and reactivation, minus contraction
and churn, equals ending MRR; a dbt test checks that identity to the cent for every month.

```sql movements
select month, 'New' as movement, new_mrr as amount from warehouse.mart_mrr_bridge
union all
select month, 'Expansion', expansion_mrr from warehouse.mart_mrr_bridge
union all
select month, 'Reactivation', reactivation_mrr from warehouse.mart_mrr_bridge
union all
select month, 'Contraction', -contraction_mrr from warehouse.mart_mrr_bridge
union all
select month, 'Churn', -churned_mrr from warehouse.mart_mrr_bridge
order by month
```

<BarChart
    data={movements}
    x=month
    y=amount
    series=movement
    type=stacked
    yFmt="usd0k"
    title="MRR movements"
    seriesOrder={['New', 'Expansion', 'Reactivation', 'Contraction', 'Churn']}
    seriesColors={{
        New: '#236aa4',
        Expansion: '#45a1bf',
        Reactivation: '#a5cdee',
        Contraction: '#f4b548',
        Churn: '#c2410c',
    }}
/>

```sql rates
select
    month,
    logo_churn_pct / 100 as logo_churn,
    gross_mrr_churn_pct / 100 as gross_revenue_churn,
    net_revenue_retention_pct / 100 as net_revenue_retention
from warehouse.mart_mrr_bridge
order by month
```

<LineChart
    data={rates}
    x=month
    y=net_revenue_retention
    yFmt="pct1"
    yMin=0.9
    title="Net revenue retention, monthly"
/>

<LineChart
    data={rates}
    x=month
    y={['logo_churn', 'gross_revenue_churn']}
    yFmt="pct1"
    title="Churn, monthly"
    subtitle="Gross revenue churn = (churned + contraction MRR) / starting MRR"
/>

## Bridge table

```sql bridge
select * from warehouse.mart_mrr_bridge order by month desc
```

<DataTable data={bridge} rows=12>
    <Column id=month fmt="mmm yyyy" />
    <Column id=new_mrr title="New" fmt="usd0" />
    <Column id=expansion_mrr title="Expansion" fmt="usd0" />
    <Column id=reactivation_mrr title="Reactivation" fmt="usd0" />
    <Column id=contraction_mrr title="Contraction" fmt="usd0" />
    <Column id=churned_mrr title="Churn" fmt="usd0" />
    <Column id=ending_mrr title="Ending MRR" fmt="usd0" />
    <Column id=mrr_growth_pct title="Growth %" fmt="num1" />
</DataTable>
