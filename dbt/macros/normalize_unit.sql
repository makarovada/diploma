{% macro normalize_unit(value) -%}
    case
        when {{ value }} is null then null
        when lower(trim({{ value }})) in ('шт', 'штука', 'pieces', 'pcs') then 'pcs'
        when lower(trim({{ value }})) in ('кг', 'kg', 'килограмм') then 'kg'
        when lower(trim({{ value }})) in ('л', 'l', 'литр') then 'l'
        else lower(trim({{ value }}))
    end
{%- endmacro %}
