{#
    Stripe timestamps are Unix seconds. make_timestamp() gives a naive UTC timestamp;
    to_timestamp() would return TIMESTAMPTZ and shift month boundaries on non-UTC machines.
#}
{% macro epoch_to_ts(column) -%}
    make_timestamp(({{ column }})::bigint * 1000000)
{%- endmacro %}
