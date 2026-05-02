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
        person_full_name,
        person_family_name,
        person_given_name,
        person_patronymic,
        contact_phone_e164,
        contact_email,
        country_code,
        order_status_code,
        payment_status_code,
        shipment_status_code,
        {{ normalize_unit('line_unit_normalized') }} as line_unit_normalized,
        cbr_rate_date,
        _ingest_extracted_at,
        _ingest_meta,
        loaded_at,
        case
            when amount is not null and amount < 0 then true
            else false
        end as is_negative_amount
    from src
)
select * from typed
