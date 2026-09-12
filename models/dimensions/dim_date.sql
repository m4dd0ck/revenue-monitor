with days as (
    select unnest(range(
        date '{{ var("date_spine_start") }}',
        date '{{ var("date_spine_end") }}' + interval 1 day,
        interval 1 day
    ))::date as date_day
)

select
    date_day,
    date_trunc('month', date_day)::date as month_start,
    date_trunc('quarter', date_day)::date as quarter_start,
    year(date_day) as year_number,
    quarter(date_day) as quarter_number,
    month(date_day) as month_number,
    monthname(date_day) as month_name,
    dayofweek(date_day) as day_of_week,
    dayname(date_day) as day_name,
    date_day = last_day(date_day) as is_month_end,
    dayofweek(date_day) in (0, 6) as is_weekend
from days
