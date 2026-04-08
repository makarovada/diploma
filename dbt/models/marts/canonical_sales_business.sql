{{ config(materialized='table') }}

with src as (
    select *
    from {{ source('public', 'typed_canonical_sales') }}
),
typed as (
    select
        source_system,
        source_record_id,
        event_datetime,
        amount,
        amount_rub,
        currency_code,
        counterparty_name,
        channel,
        line_description,
        status,
        {{ normalize_unit('line_unit_normalized') }} as line_unit_normalized,
        cbr_rate_date,
        _airbyte_extracted_at,
        _airbyte_meta,
        loaded_at,
        case
            when amount is not null and amount < 0 then true
            else false
        end as is_negative_amount
    from src
)
select * from typed
