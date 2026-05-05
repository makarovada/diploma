{{ config(materialized='table') }}

with src as (
    select *
    from {{ source('normalized', 'seed_demo__orders') }}
),
typed as (
    select
        source_system,
        source_record_id,
        event_datetime,
        amount,
        currency_code,
        status,
        channel,
        loaded_at
    from src
)
select * from typed

