{#
    Raw tables can hold the same object from several Stripe pulls. Keep the copy from the
    newest file; file names are timestamped, so they sort by recency.
#}
{% macro latest_raw(table_name) -%}
    select *
    from {{ source('stripe', table_name) }}
    qualify row_number() over (
        partition by payload ->> '$.id'
        order by source_file desc
    ) = 1
{%- endmacro %}
