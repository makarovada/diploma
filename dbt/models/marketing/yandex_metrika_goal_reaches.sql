{{ config(materialized='table', schema='semantic') }}

SELECT
    g._raw_id AS record_id,
    g._workspace_id AS workspace_id,
    g._connection_id AS connection_id,
    (g._data->>'goalId')::text AS goal_id,
    (g._data->>'goalName')::text AS goal_name,
    (g._data->>'dateTime')::timestamptz AS reached_at,
    (g._data->>'revenue')::numeric AS revenue,
    (g._data->>'currency')::text AS currency
FROM {{ source('normalized', 'yandex_metrika__goals_reaches') }} AS g
