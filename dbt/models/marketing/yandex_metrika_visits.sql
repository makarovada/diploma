{{ config(materialized='table', schema='semantic') }}

SELECT
    v._raw_id AS record_id,
    v._workspace_id AS workspace_id,
    v._connection_id AS connection_id,
    (v._data->>'visitId')::text AS visit_id,
    (v._data->>'dateTime')::timestamptz AS visit_datetime,
    (v._data->>'clientId')::text AS client_id,
    (v._data->>'trafficSource')::text AS traffic_source,
    (v._data->>'utmSource')::text AS utm_source,
    (v._data->>'utmMedium')::text AS utm_medium,
    (v._data->>'utmCampaign')::text AS utm_campaign,
    (v._data->>'deviceCategory')::text AS device,
    (v._data->>'regionName')::text AS region,
    (v._data->>'goalReachesCount')::int AS goal_count
FROM {{ source('normalized', 'yandex_metrika__visits') }} AS v
