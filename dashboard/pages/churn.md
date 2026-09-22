---
title: Churn
sidebar_position: 4
---

Voluntary churn is a customer choosing to cancel. Involuntary churn is a subscription canceled
after failed payments ran out of retries, which better dunning can often recover.

```sql churn_by_type
select month, churn_type, sum(churned_mrr) as churned_mrr, sum(churned_customers) as churned_customers
from warehouse.mart_churn_analysis
group by month, churn_type
order by month
```

<BarChart
    data={churn_by_type}
    x=month
    y=churned_mrr
    series=churn_type
    type=stacked
    yFmt="usd0k"
    title="Churned MRR by type"
    seriesColors={{ voluntary: '#236aa4', involuntary: '#c2410c' }}
/>

```sql churn_by_tier
select
    plan_tier,
    churn_type,
    sum(churned_customers) as churned_customers,
    sum(churned_mrr) as churned_mrr
from warehouse.mart_churn_analysis
where month > (select max(month) from warehouse.mart_churn_analysis) - interval 12 month
group by plan_tier, churn_type
order by plan_tier
```

<BarChart
    data={churn_by_tier}
    x=plan_tier
    y=churned_customers
    series=churn_type
    type=stacked
    title="Churned customers by tier, last 12 months"
    seriesColors={{ voluntary: '#236aa4', involuntary: '#c2410c' }}
/>

## At-risk customers

Past due, two or more failed payments in the last 90 days, or a contraction in the last three
months.

```sql at_risk
select
    customer_name,
    plan_tier,
    billing_interval,
    current_mrr,
    tenure_months,
    failed_payments_90d,
    last_invoice_status,
    country
from warehouse.mart_customer_health
where health_status = 'at risk'
order by current_mrr desc
```

```sql at_risk_summary
select count(*) as customers, sum(current_mrr) as mrr from ${at_risk}
```

<BigValue data={at_risk_summary} value=customers title="At-risk customers" fmt="num0" />
<BigValue data={at_risk_summary} value=mrr title="MRR at risk" fmt="usd0" />

<DataTable data={at_risk} rows=15 search=true>
    <Column id=customer_name title="Customer" />
    <Column id=plan_tier title="Tier" />
    <Column id=billing_interval title="Billing" />
    <Column id=current_mrr title="MRR" fmt="usd0" />
    <Column id=tenure_months title="Tenure (months)" fmt="num0" />
    <Column id=failed_payments_90d title="Failed payments (90d)" fmt="num0" />
    <Column id=last_invoice_status title="Last invoice" />
</DataTable>
