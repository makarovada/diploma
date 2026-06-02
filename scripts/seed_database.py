"""Сиды для фазы А: справочники, демо-пользователи, ≥500 строк в витрине и смежных таблицах.

Запуск после `alembic upgrade head` и `docker compose up -d`.
Переменная окружения: DATABASE_URL (как в приложении).
Повторный запуск удаляет данные с префиксами seed_* / seed. и пересоздаёт их.
"""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine

from datanorma.config import get_settings
from datanorma.web.passwords import hash_password

_BATCH = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-000000000001")


def _url() -> str:
    return get_settings().database_url


def _clear_seed_rows(conn: Connection) -> None:
    conn.execute(text("DELETE FROM normalized.seed_demo__orders WHERE source_system LIKE 'seed_%'"))
    conn.execute(text("DELETE FROM user_role WHERE user_id IN (SELECT id FROM app_user WHERE username LIKE 'seed_%')"))
    conn.execute(text("DELETE FROM app_user WHERE username LIKE 'seed_%'"))
    conn.execute(text("DELETE FROM normalization_issue WHERE issue_type = 'seed_demo'"))
    conn.execute(text("DELETE FROM pipeline_run_summary WHERE job_name = 'seed_daily_refresh'"))
    conn.execute(text("DELETE FROM sync_state WHERE integration_code LIKE 'seed_%'"))
    # Нельзя глотать ошибку в той же транзакции: в PostgreSQL после сбоя нужен ROLLBACK TO SAVEPOINT.
    try:
        with conn.begin_nested():
            conn.execute(text("DELETE FROM mapping_profile_legacy WHERE name LIKE 'Seed %'"))
    except Exception:
        pass  # таблица может отсутствовать в старых схемах
    conn.execute(text("DELETE FROM integration_config WHERE config_key LIKE 'seed.%'"))
    conn.execute(
        text("DELETE FROM raw_google_sheet_orders_staging WHERE ingest_batch_id = :bid"), {"bid": _BATCH}
    )
    conn.execute(text("DELETE FROM raw_1c_orders_staging WHERE ingest_batch_id = :bid"), {"bid": _BATCH})
    conn.execute(text("DELETE FROM raw_ozon_postings_staging WHERE ingest_batch_id = :bid"), {"bid": _BATCH})


def seed_reference(conn: Connection) -> None:
    sources = [
        ("ozon", "Ozon Seller API", "Постинги FBS"),
        ("1c", "1С:УТ / выгрузка", "Заказы из ERP"),
        ("google_sheet", "Google Sheets", "Ручной ввод"),
        ("seed_1c", "Демо 1С (сиды)", "Синтетика для отчёта"),
        ("seed_ozon", "Демо Ozon (сиды)", "Синтетика для отчёта"),
        ("seed_sheet", "Демо Sheets (сиды)", "Синтетика для отчёта"),
    ]
    for code, name, desc in sources:
        conn.execute(
            text(
                "INSERT INTO dim_source_system (code, name, description) "
                "VALUES (:c, :n, :d) ON CONFLICT (code) DO NOTHING"
            ),
            {"c": code, "n": name, "d": desc},
        )
    currencies = [
        ("RUB", "Российский рубль"),
        ("USD", "Доллар США"),
        ("EUR", "Евро"),
        ("CNY", "Юань"),
        ("KZT", "Тенге"),
        ("BYN", "Белорусский рубль"),
        ("GBP", "Фунт стерлингов"),
        ("CHF", "Швейцарский франк"),
    ]
    for code, name in currencies:
        conn.execute(
            text(
                "INSERT INTO dim_currency (code, name) VALUES (:c, :n) ON CONFLICT (code) DO NOTHING"
            ),
            {"c": code, "n": name},
        )
    countries = [
        ("RU", "Россия"),
        ("KZ", "Казахстан"),
        ("BY", "Беларусь"),
    ]
    for code, name in countries:
        conn.execute(
            text("INSERT INTO dim_country (code, name) VALUES (:c, :n) ON CONFLICT (code) DO NOTHING"),
            {"c": code, "n": name},
        )
    units = [
        ("pcs", "Штуки"),
        ("kg", "Килограмм"),
        ("m", "Метр"),
    ]
    for code, name in units:
        conn.execute(
            text("INSERT INTO dim_unit (code, name) VALUES (:c, :n) ON CONFLICT (code) DO NOTHING"),
            {"c": code, "n": name},
        )
    status_rows = [
        ("order", "ozon", "delivered", "order_completed"),
        ("order", "ozon", "cancelled", "order_cancelled"),
        ("order", "1c", "Оплачен", "order_paid"),
        ("order", "google_sheet", "paid", "order_paid"),
    ]
    for dim, src, raw, canon in status_rows:
        conn.execute(
            text(
                "INSERT INTO dim_status_map (dimension, source_system, raw_status, canonical_code) "
                "VALUES (:d, :s, :r, :c) ON CONFLICT (dimension, source_system, raw_status) DO NOTHING"
            ),
            {"d": dim, "s": src, "r": raw, "c": canon},
        )


def seed_roles_and_users(conn: Connection) -> None:
    roles = [
        ("platform_admin", "Администратор платформы"),
        ("data_integrator", "Интегратор данных"),
        ("analyst", "Аналитик (read-only в продукте)"),
    ]
    for name, desc in roles:
        conn.execute(
            text(
                "INSERT INTO role (name, description) VALUES (:n, :d) ON CONFLICT (name) DO NOTHING"
            ),
            {"n": name, "d": desc},
        )
    id_by_name: dict[str, int] = {}
    for rid, rname in conn.execute(text("SELECT id, name FROM role")):
        id_by_name[str(rname)] = int(rid)

    # Пароли для скриншотов ВКР (в дипломе указать смену в проде; хеш = bcrypt).
    users = [
        ("seed_admin", "seed-admin@example.local", ("platform_admin",), hash_password("AdminDemo2026")),
        ("seed_integrator", "seed-integrator@example.local", ("data_integrator",), hash_password("IntegratorDemo2026")),
        ("seed_analyst", "seed-analyst@example.local", ("analyst",), hash_password("AnalystDemo2026")),
        ("seed_analyst2", "seed-analyst2@example.local", ("analyst",), hash_password("AnalystDemo2026")),
        ("seed_ops", "seed-ops@example.local", ("data_integrator", "analyst"), hash_password("IntegratorDemo2026")),
    ]
    for uname, email, rnames, pw_hash in users:
        res = conn.execute(
            text(
                "INSERT INTO app_user (username, password_hash, email) "
                "VALUES (:u, :p, :e) ON CONFLICT (username) DO UPDATE SET "
                "email = EXCLUDED.email, password_hash = EXCLUDED.password_hash "
                "RETURNING id"
            ),
            {"u": uname, "p": pw_hash, "e": email},
        )
        uid = int(res.scalar_one())
        for rn in rnames:
            rid = id_by_name[rn]
            conn.execute(
                text(
                    "INSERT INTO user_role (user_id, role_id) VALUES (:uid, :rid) "
                    "ON CONFLICT DO NOTHING"
                ),
                {"uid": uid, "rid": rid},
            )


def seed_workspace_acl_demo(conn: Connection) -> None:
    """Демо: второе пространство и права участников (после миграции 014)."""
    admin = conn.execute(
        text("SELECT id FROM app_user WHERE username = 'seed_admin'")
    ).scalar()
    integrator = conn.execute(
        text("SELECT id FROM app_user WHERE username = 'seed_integrator'")
    ).scalar()
    analyst = conn.execute(
        text("SELECT id FROM app_user WHERE username = 'seed_analyst'")
    ).scalar()
    if admin is None:
        return
    conn.execute(
        text(
            "INSERT INTO organization(code, name) VALUES ('ws-demo', 'Demo Org') "
            "ON CONFLICT (code) DO NOTHING"
        )
    )
    conn.execute(
        text(
            """
            INSERT INTO workspace(organization_id, code, name, created_by_user_id)
            SELECT o.id, 'demo', 'Демо-песочница', :uid
            FROM organization o WHERE o.code = 'ws-demo'
            ON CONFLICT ON CONSTRAINT uq_workspace_org_code DO UPDATE SET name = EXCLUDED.name
            """
        ),
        {"uid": int(admin)},
    )
    demo_wid = conn.execute(
        text("SELECT w.id FROM workspace w WHERE w.code = 'demo'")
    ).scalar()
    if demo_wid is None:
        return
    for uid, adm in ((admin, True), (integrator, False), (analyst, False)):
        if uid is None:
            continue
        conn.execute(
            text(
                "INSERT INTO user_workspace(user_id, workspace_id, is_admin) "
                "VALUES (:u, :w, :a) ON CONFLICT (user_id, workspace_id) "
                "DO UPDATE SET is_admin = EXCLUDED.is_admin"
            ),
            {"u": int(uid), "w": int(demo_wid), "a": adm},
        )
    integrator_perms = [
        "source.create",
        "source.read",
        "source.update",
        "destination.read",
        "connection.read",
        "connection.sync.run",
    ]
    analyst_perms = ["source.read", "destination.read", "connection.read"]
    if integrator:
        for p in integrator_perms:
            conn.execute(
                text(
                    "INSERT INTO workspace_member_permission(workspace_id, user_id, permission_code) "
                    "VALUES (:w, :u, :p) ON CONFLICT DO NOTHING"
                ),
                {"w": int(demo_wid), "u": int(integrator), "p": p},
            )
    if analyst:
        for p in analyst_perms:
            conn.execute(
                text(
                    "INSERT INTO workspace_member_permission(workspace_id, user_id, permission_code) "
                    "VALUES (:w, :u, :p) ON CONFLICT DO NOTHING"
                ),
                {"w": int(demo_wid), "u": int(analyst), "p": p},
            )


def seed_workspace_acl_for_all_existing_workspaces(conn: Connection) -> None:
    """Выдать membership всем пользователям на ВСЕ существующие workspaces.

    Цель: чтобы при выборе "текущего" workspace в UI не было 403 `Нет доступа к workspace`.

    Правила:
    - `seed_admin` получает `user_workspace.is_admin = true` (права создателя пространства)
    - остальные пользователи получают membership (is_admin=false)
    - для non-admin пользователей заполняем `workspace_member_permission` по глобальным ролям
      (`data_integrator` и `analyst`), чтобы дальше не упираться в "недостаточно прав".
    """

    seed_admin_uid = conn.execute(
        text("SELECT id FROM app_user WHERE username = 'seed_admin'")
    ).scalar()
    if seed_admin_uid is None:
        return

    # Вdev-режиме нам важно гарантировать отсутствие "workspace_forbidden" для любых текущих workspace.
    workspace_ids = conn.execute(text("SELECT id FROM workspace")).scalars().all()
    if not workspace_ids:
        return

    # 1) Membership: добавить строки user_workspace для всех пользователей на каждый workspace.
    # Для seed_admin выставляем is_admin=true. Для остальных не "затираем" возможный is_admin
    # (если вдруг ранее выставлялся) — OR сохраняет true.
    conn.execute(
        text(
            """
            INSERT INTO user_workspace (user_id, workspace_id, is_admin)
            SELECT u.id,
                   w.id,
                   (u.id = :seed_uid) AS is_admin
            FROM app_user u
            CROSS JOIN workspace w
            ON CONFLICT (user_id, workspace_id)
            DO UPDATE SET is_admin = user_workspace.is_admin OR EXCLUDED.is_admin
            """
        ),
        {"seed_uid": int(seed_admin_uid)},
    )

    # 2) Permissions для non-admin (seed_admin пропускаем, т.к. is_admin=true даёт доступ на всё).
    # Карта ролей из миграции 014 (минимум, чтобы уйти от 403 "Недостаточно прав").
    integrator_perms = [
        "source.create",
        "source.read",
        "source.update",
        "source.delete",
        "destination.create",
        "destination.read",
        "destination.update",
        "destination.delete",
        "connection.create",
        "connection.read",
        "connection.update",
        "connection.delete",
        "connection.sync.run",
        "mapping.read",
        "mapping.edit",
    ]
    analyst_perms = [
        "source.read",
        "destination.read",
        "connection.read",
        "mapping.read",
    ]

    user_role_rows = conn.execute(
        text(
            """
            SELECT ur.user_id, r.name
            FROM user_role ur
            JOIN role r ON r.id = ur.role_id
            """
        )
    ).all()
    roles_by_user: dict[int, set[str]] = {}
    for user_id, role_name in user_role_rows:
        roles_by_user.setdefault(int(user_id), set()).add(str(role_name))

    for wid in workspace_ids:
        for user_id, roles in roles_by_user.items():
            if user_id == int(seed_admin_uid):
                continue
            perm_codes: set[str] = set()
            if "data_integrator" in roles:
                perm_codes.update(integrator_perms)
            if "analyst" in roles:
                perm_codes.update(analyst_perms)
            if not perm_codes:
                continue
            for p in perm_codes:
                conn.execute(
                    text(
                        "INSERT INTO workspace_member_permission (workspace_id, user_id, permission_code) "
                        "VALUES (:w, :u, :p) ON CONFLICT DO NOTHING"
                    ),
                    {"w": int(wid), "u": int(user_id), "p": p},
                )


def seed_config_and_meta(conn: Connection) -> None:
    cfg = [
        ("seed.pipeline.batch_size", "500", False),
        ("seed.pipeline.retry_max", "3", False),
        ("seed.feature.flags", '{"staging_writes": true}', False),
    ]
    for k, v, sec in cfg:
        conn.execute(
            text(
                "INSERT INTO integration_config (config_key, config_value, is_secret) "
                "VALUES (:k, :v, :s)"
            ),
            {"k": k, "v": v, "s": sec},
        )
    for i in range(4):
        try:
            conn.execute(
                text(
                    "INSERT INTO mapping_profile_legacy (name, version, notes) VALUES (:n, :ver, :notes)"
                ),
                {
                    "n": f"Seed profile {i + 1}",
                    "ver": 1,
                    "notes": f"Демо-профиль маппинга #{i + 1}",
                },
            )
        except Exception:
            pass
    syncs = [
        ("seed_ozon", '{"page": 12}'),
        ("seed_1c", "2024-12-31T23:59:59"),
        ("seed_sheet", "row:840"),
    ]
    ajs = '{"cursor": null, "rows_emitted": 0, "edited_via": "seed"}'
    for code, cursor in syncs:
        cv = json.dumps({"cursor": cursor, "seed": True}, ensure_ascii=False)
        conn.execute(
            text(
                "INSERT INTO sync_state (integration_code, stream_name, sync_mode, cursor_field, cursor_value, ingest_state, last_success_at, updated_at) "
                "VALUES (:c, 'orders', 'full_refresh', NULL, :cv, CAST(:ajs AS jsonb), NOW(), NOW()) "
                "ON CONFLICT (integration_code, stream_name) DO UPDATE SET cursor_value = EXCLUDED.cursor_value, updated_at = NOW()"
            ),
            {"c": code, "cv": cv, "ajs": ajs},
        )


def seed_staging_and_issues(conn: Connection) -> None:
    oz = {"posting_number": "SEED-OZ-1", "status": "delivered", "items": [{"sku": "X", "qty": 1}]}
    conn.execute(
        text(
            "INSERT INTO raw_ozon_postings_staging (ingest_batch_id, payload_json, _ingest_extracted_at, _ingest_meta) "
            "VALUES (:b, CAST(:j AS jsonb), NOW(), CAST(:m AS jsonb))"
        ),
        {"b": _BATCH, "j": json.dumps(oz), "m": json.dumps({"seed": True})},
    )
    for i in range(5):
        row = {"order_id": f"S1C-{i}", "sum": 100 + i}
        conn.execute(
            text(
                "INSERT INTO raw_1c_orders_staging (ingest_batch_id, row_json, _ingest_extracted_at, _ingest_meta) "
                "VALUES (:b, CAST(:j AS jsonb), NOW(), CAST(:m AS jsonb))"
            ),
            {"b": _BATCH, "j": json.dumps(row), "m": json.dumps({"seed": True})},
        )
    for i in range(5):
        row = {"sheet_row": i, "client": f"Client {i}"}
        conn.execute(
            text(
                "INSERT INTO raw_google_sheet_orders_staging (ingest_batch_id, row_json, _ingest_extracted_at, _ingest_meta) "
                "VALUES (:b, CAST(:j AS jsonb), NOW(), CAST(:m AS jsonb))"
            ),
            {"b": _BATCH, "j": json.dumps(row), "m": json.dumps({"seed": True})},
        )
    for i in range(20):
        conn.execute(
            text(
                "INSERT INTO normalization_issue (batch_id, source_system, source_record_id, "
                "field_name, issue_type, message) VALUES (:b, :ss, :sid, :fn, 'seed_demo', :msg)"
            ),
            {
                "b": _BATCH,
                "ss": "1c",
                "sid": f"demo-{i}",
                "fn": "amount",
                "msg": f"Демо-предупреждение #{i}",
            },
        )
    for i in range(8):
        conn.execute(
            text(
                "INSERT INTO pipeline_run_summary (dagster_run_id, job_name, status, started_at, finished_at, meta) "
                "VALUES (:rid, 'seed_daily_refresh', :st, NOW() - INTERVAL '1 hour', NOW(), CAST(:m AS jsonb))"
            ),
            {
                "rid": f"seed-run-{i:04d}",
                "st": "success" if i % 2 == 0 else "failed",
                "m": json.dumps({"rows": 100 + i}),
            },
        )


def seed_normalized_bulk(conn: Connection) -> None:
    loaded_at = datetime.now(timezone.utc)
    systems = ["seed_1c", "seed_ozon", "seed_sheet"]
    conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS normalized.seed_demo__orders (
                id bigserial PRIMARY KEY,
                source_system text,
                source_record_id text,
                event_datetime timestamptz,
                amount numeric,
                currency_code text,
                status text,
                channel text,
                loaded_at timestamptz
            )
            """
        )
    )
    stmt = text(
        "INSERT INTO normalized.seed_demo__orders ("
        "source_system, source_record_id, event_datetime, amount, currency_code, status, channel, loaded_at"
        ") VALUES ("
        ":ss, :sid, :ed, :am, :cc, :st, :ch, :la)"
    )
    base_date = date(2024, 6, 1)
    for i in range(520):
        ss = systems[i % 3]
        sid = f"{ss.upper()}-{i:05d}"
        d = base_date + timedelta(days=i % 120)
        conn.execute(
            stmt,
            {
                "ss": ss,
                "sid": sid,
                "ed": datetime(d.year, d.month, d.day, 12, 0, tzinfo=timezone.utc),
                "am": Decimal("100.00") + Decimal(i % 50),
                "cc": "RUB",
                "ch": "retail" if i % 2 == 0 else "online",
                "st": "paid",
                "la": loaded_at,
            },
        )


def run(engine: Engine | None = None) -> dict[str, int]:
    eng = engine or create_engine(_url(), pool_pre_ping=True)
    counts: dict[str, int] = {}
    with eng.begin() as conn:
        _clear_seed_rows(conn)
        seed_reference(conn)
        seed_roles_and_users(conn)
        seed_workspace_acl_demo(conn)
        seed_workspace_acl_for_all_existing_workspaces(conn)
        seed_config_and_meta(conn)
        seed_staging_and_issues(conn)
        seed_normalized_bulk(conn)
        counts["normalized_orders_seed"] = conn.execute(
            text("SELECT COUNT(*) FROM normalized.seed_demo__orders WHERE source_system LIKE 'seed_%'")
        ).scalar_one()
        counts["normalization_issue_seed"] = conn.execute(
            text("SELECT COUNT(*) FROM normalization_issue WHERE issue_type = 'seed_demo'")
        ).scalar_one()
    return counts


def main() -> None:
    c = run()
    print("Seed OK:", c)


if __name__ == "__main__":
    main()
