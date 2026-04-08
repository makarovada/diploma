"""Матрица «операция → допустимые роли» (единый источник для API и UI)."""

from __future__ import annotations

# Имена ролей совпадают с таблицей role (сиды / миграция).
ROLE_PLATFORM_ADMIN = "platform_admin"
ROLE_DATA_INTEGRATOR = "data_integrator"
ROLE_ANALYST = "analyst"

ALL_ROLES = (ROLE_PLATFORM_ADMIN, ROLE_DATA_INTEGRATOR, ROLE_ANALYST)

# Ключ операции → кортеж ролей, которым разрешено.
OPERATION_ROLES: dict[str, tuple[str, ...]] = {
    # Витрина и отчёты
    "view_sales_summary": (ROLE_PLATFORM_ADMIN, ROLE_DATA_INTEGRATOR, ROLE_ANALYST),
    "view_sales_rows": (ROLE_PLATFORM_ADMIN, ROLE_DATA_INTEGRATOR, ROLE_ANALYST),
    "export_sales_csv": (ROLE_PLATFORM_ADMIN, ROLE_DATA_INTEGRATOR, ROLE_ANALYST),
    # Staging / сырой слой
    "view_staging_counts": (ROLE_PLATFORM_ADMIN, ROLE_DATA_INTEGRATOR),
    "view_staging_ozon_sample": (ROLE_PLATFORM_ADMIN, ROLE_DATA_INTEGRATOR),
    "view_staging_1c_sample": (ROLE_PLATFORM_ADMIN, ROLE_DATA_INTEGRATOR),
    "view_staging_sheet_sample": (ROLE_PLATFORM_ADMIN, ROLE_DATA_INTEGRATOR),
    # Операции и состояние интеграций
    "view_sync_state": (ROLE_PLATFORM_ADMIN, ROLE_DATA_INTEGRATOR),
    "view_normalization_issues": (ROLE_PLATFORM_ADMIN, ROLE_DATA_INTEGRATOR),
    "view_mapping_profiles": (ROLE_PLATFORM_ADMIN, ROLE_DATA_INTEGRATOR),
    "edit_mapping_profiles": (ROLE_PLATFORM_ADMIN, ROLE_DATA_INTEGRATOR),
    # Справочники (чтение для аналитика)
    "view_dim_sources": (ROLE_PLATFORM_ADMIN, ROLE_DATA_INTEGRATOR, ROLE_ANALYST),
    "configure_new_source": (ROLE_PLATFORM_ADMIN, ROLE_DATA_INTEGRATOR),
    "view_dim_currencies": (ROLE_PLATFORM_ADMIN, ROLE_DATA_INTEGRATOR, ROLE_ANALYST),
    # Администрирование
    "view_admin_users": (ROLE_PLATFORM_ADMIN,),
    "view_admin_roles": (ROLE_PLATFORM_ADMIN,),
    "view_integration_config": (ROLE_PLATFORM_ADMIN,),
    "edit_integration_config": (ROLE_PLATFORM_ADMIN,),
    "view_pipeline_runs": (ROLE_PLATFORM_ADMIN, ROLE_DATA_INTEGRATOR),
    "view_rbac_matrix": ALL_ROLES,
    "view_ops_console_hint": (ROLE_PLATFORM_ADMIN, ROLE_DATA_INTEGRATOR),
    # Веб-клиент (фаза C): страницы Jinja2
    "web_basic": ALL_ROLES,
    "view_samples_preview": ALL_ROLES,
    "view_pipeline_graph_static": ALL_ROLES,
    "assign_user_roles": (ROLE_PLATFORM_ADMIN,),
    "edit_schedule_cron": (ROLE_PLATFORM_ADMIN, ROLE_DATA_INTEGRATOR),
    # Веб-консоль (ориентир Airbyte: Connections / Destinations)
    "view_connections_overview": ALL_ROLES,
    "edit_connections_builder": (ROLE_PLATFORM_ADMIN, ROLE_DATA_INTEGRATOR),
    "view_destinations_page": ALL_ROLES,
    # API v1: orchestration and sync management
    "manage_connections_api": (ROLE_PLATFORM_ADMIN, ROLE_DATA_INTEGRATOR),
    "manage_syncs_api": (ROLE_PLATFORM_ADMIN, ROLE_DATA_INTEGRATOR),
    "view_workspaces": ALL_ROLES,
    "manage_workspaces": (ROLE_PLATFORM_ADMIN, ROLE_DATA_INTEGRATOR),
    "view_analyst_cabinet": (ROLE_PLATFORM_ADMIN, ROLE_DATA_INTEGRATOR, ROLE_ANALYST),
}

# Человекочитаемые подписи для таблицы в UI / ВКР.
OPERATION_LABELS_RU: dict[str, str] = {
    "view_sales_summary": "Сводка по витрине canonical_sales",
    "view_sales_rows": "Выборка строк витрины",
    "export_sales_csv": "Выгрузка витрины (CSV)",
    "view_staging_counts": "Счётчики записей в raw_*_staging",
    "view_staging_ozon_sample": "Просмотр образца raw Ozon",
    "view_staging_1c_sample": "Просмотр образца raw 1С",
    "view_staging_sheet_sample": "Просмотр образца raw Sheets",
    "view_sync_state": "Состояние sync_state (курсоры)",
    "view_normalization_issues": "События normalization_issue",
    "view_mapping_profiles": "Профили mapping_profile",
    "edit_mapping_profiles": "Изменение профилей маппинга (заглушка API)",
    "view_dim_sources": "Справочник источников (dim_source_system)",
    "configure_new_source": "Мастер New Source (check / discover коннектора)",
    "view_dim_currencies": "Справочник валют (dim_currency)",
    "view_admin_users": "Список пользователей и ролей",
    "view_admin_roles": "Список ролей",
    "view_integration_config": "Просмотр integration_config",
    "edit_integration_config": "Изменение integration_config",
    "view_pipeline_runs": "Журнал pipeline_run_summary",
    "view_rbac_matrix": "Матрица доступа (роль × операция)",
    "view_ops_console_hint": "Доступ к описанию операционной консоли (Dagster)",
    "web_basic": "Базовые страницы (смена пароля, о системе, справка)",
    "view_samples_preview": "Предпросмотр sample-данных",
    "view_pipeline_graph_static": "Статическая схема пайплайна",
    "assign_user_roles": "Назначение ролей пользователю",
    "edit_schedule_cron": "Настройка cron расписания (текстом)",
    "view_connections_overview": "Обзор подключений (как Connections в Airbyte)",
    "edit_connections_builder": "No-code редактор Connections (stream/sync/cursor)",
    "view_destinations_page": "Назначения данных / warehouse (как Destinations)",
    "manage_connections_api": "API v1: управление connections",
    "manage_syncs_api": "API v1: управление/просмотр sync jobs",
    "view_workspaces": "Просмотр organizations/workspaces",
    "manage_workspaces": "Управление organizations/workspaces",
    "view_analyst_cabinet": "Личный кабинет аналитика",
}


def role_labels_ru() -> dict[str, str]:
    return {
        ROLE_PLATFORM_ADMIN: "Администратор платформы",
        ROLE_DATA_INTEGRATOR: "Интегратор данных",
        ROLE_ANALYST: "Аналитик (только чтение)",
    }


def matrix_payload() -> dict:
    """Структура для GET /api/rbac/matrix и отрисовки таблицы."""
    rl = role_labels_ru()
    rows = []
    for op, roles in sorted(OPERATION_ROLES.items()):
        rows.append(
            {
                "operation": op,
                "label_ru": OPERATION_LABELS_RU.get(op, op),
                "allowed_roles": list(roles),
                "cells": {r: (r in roles) for r in ALL_ROLES},
            }
        )
    return {
        "roles": [{"name": r, "label_ru": rl[r]} for r in ALL_ROLES],
        "operations": rows,
    }
