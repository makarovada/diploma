"""Каталог разрешений workspace (замена глобальной RBAC-матрицы)."""

from __future__ import annotations

from typing import Final

# Workspace administration
PERM_WORKSPACE_MEMBERS_MANAGE: Final[str] = "workspace.members.manage"
PERM_WORKSPACE_PERMISSIONS_GRANT: Final[str] = "workspace.permissions.grant"

# Source
PERM_SOURCE_CREATE: Final[str] = "source.create"
PERM_SOURCE_READ: Final[str] = "source.read"
PERM_SOURCE_UPDATE: Final[str] = "source.update"
PERM_SOURCE_DELETE: Final[str] = "source.delete"

# Destination
PERM_DESTINATION_CREATE: Final[str] = "destination.create"
PERM_DESTINATION_READ: Final[str] = "destination.read"
PERM_DESTINATION_UPDATE: Final[str] = "destination.update"
PERM_DESTINATION_DELETE: Final[str] = "destination.delete"

# Connection
PERM_CONNECTION_CREATE: Final[str] = "connection.create"
PERM_CONNECTION_READ: Final[str] = "connection.read"
PERM_CONNECTION_UPDATE: Final[str] = "connection.update"
PERM_CONNECTION_DELETE: Final[str] = "connection.delete"
PERM_CONNECTION_SYNC_RUN: Final[str] = "connection.sync.run"

# Mapping & audit
PERM_MAPPING_READ: Final[str] = "mapping.read"
PERM_MAPPING_EDIT: Final[str] = "mapping.edit"
PERM_AUDIT_READ: Final[str] = "audit.read"

ALL_PERMISSION_CODES: Final[tuple[str, ...]] = (
    PERM_WORKSPACE_MEMBERS_MANAGE,
    PERM_WORKSPACE_PERMISSIONS_GRANT,
    PERM_SOURCE_CREATE,
    PERM_SOURCE_READ,
    PERM_SOURCE_UPDATE,
    PERM_SOURCE_DELETE,
    PERM_DESTINATION_CREATE,
    PERM_DESTINATION_READ,
    PERM_DESTINATION_UPDATE,
    PERM_DESTINATION_DELETE,
    PERM_CONNECTION_CREATE,
    PERM_CONNECTION_READ,
    PERM_CONNECTION_UPDATE,
    PERM_CONNECTION_DELETE,
    PERM_CONNECTION_SYNC_RUN,
    PERM_MAPPING_READ,
    PERM_MAPPING_EDIT,
    PERM_AUDIT_READ,
)

PERMISSION_LABELS_RU: dict[str, str] = {
    PERM_WORKSPACE_MEMBERS_MANAGE: "Управление участниками",
    PERM_WORKSPACE_PERMISSIONS_GRANT: "Выдача прав участникам",
    PERM_SOURCE_CREATE: "Создание источников",
    PERM_SOURCE_READ: "Просмотр источников",
    PERM_SOURCE_UPDATE: "Изменение источников",
    PERM_SOURCE_DELETE: "Удаление источников",
    PERM_DESTINATION_CREATE: "Создание приёмников",
    PERM_DESTINATION_READ: "Просмотр приёмников",
    PERM_DESTINATION_UPDATE: "Изменение приёмников",
    PERM_DESTINATION_DELETE: "Удаление приёмников",
    PERM_CONNECTION_CREATE: "Создание подключений",
    PERM_CONNECTION_READ: "Просмотр подключений",
    PERM_CONNECTION_UPDATE: "Изменение подключений",
    PERM_CONNECTION_DELETE: "Удаление подключений",
    PERM_CONNECTION_SYNC_RUN: "Запуск синхронизации",
    PERM_MAPPING_READ: "Просмотр маппинга",
    PERM_MAPPING_EDIT: "Изменение маппинга",
    PERM_AUDIT_READ: "Журнал аудита",
}

PERMISSION_CATEGORIES: dict[str, str] = {
    PERM_WORKSPACE_MEMBERS_MANAGE: "workspace",
    PERM_WORKSPACE_PERMISSIONS_GRANT: "workspace",
    PERM_SOURCE_CREATE: "source",
    PERM_SOURCE_READ: "source",
    PERM_SOURCE_UPDATE: "source",
    PERM_SOURCE_DELETE: "source",
    PERM_DESTINATION_CREATE: "destination",
    PERM_DESTINATION_READ: "destination",
    PERM_DESTINATION_UPDATE: "destination",
    PERM_DESTINATION_DELETE: "destination",
    PERM_CONNECTION_CREATE: "connection",
    PERM_CONNECTION_READ: "connection",
    PERM_CONNECTION_UPDATE: "connection",
    PERM_CONNECTION_DELETE: "connection",
    PERM_CONNECTION_SYNC_RUN: "connection",
    PERM_MAPPING_READ: "mapping",
    PERM_MAPPING_EDIT: "mapping",
    PERM_AUDIT_READ: "audit",
}

# Какое workspace-право нужно для уровня grant на ресурсе (кроме ownership/admin)
GRANT_LEVEL_TO_WORKSPACE_PERM: dict[str, dict[str, str]] = {
    "source": {
        "view": PERM_SOURCE_READ,
        "edit": PERM_SOURCE_UPDATE,
        "manage": PERM_SOURCE_DELETE,
    },
    "destination": {
        "view": PERM_DESTINATION_READ,
        "edit": PERM_DESTINATION_UPDATE,
        "manage": PERM_DESTINATION_DELETE,
    },
    "connection": {
        "view": PERM_CONNECTION_READ,
        "edit": PERM_CONNECTION_UPDATE,
        "manage": PERM_CONNECTION_DELETE,
    },
}

# permission -> минимальный уровень resource_grant
PERMISSION_TO_GRANT_LEVEL: dict[str, str] = {
    PERM_SOURCE_READ: "view",
    PERM_SOURCE_UPDATE: "edit",
    PERM_SOURCE_DELETE: "manage",
    PERM_DESTINATION_READ: "view",
    PERM_DESTINATION_UPDATE: "edit",
    PERM_DESTINATION_DELETE: "manage",
    PERM_CONNECTION_READ: "view",
    PERM_CONNECTION_UPDATE: "edit",
    PERM_CONNECTION_DELETE: "manage",
    PERM_CONNECTION_SYNC_RUN: "edit",
}

GRANT_LEVEL_ORDER: dict[str, int] = {"view": 1, "edit": 2, "manage": 3}


def grant_level_covers(grant_level: str, required_level: str) -> bool:
    return GRANT_LEVEL_ORDER.get(grant_level, 0) >= GRANT_LEVEL_ORDER.get(required_level, 0)


def catalog_payload() -> list[dict[str, str]]:
    return [
        {
            "code": code,
            "label_ru": PERMISSION_LABELS_RU.get(code, code),
            "category": PERMISSION_CATEGORIES.get(code, "other"),
        }
        for code in ALL_PERMISSION_CODES
    ]
