import type { LucideIcon } from "lucide-react";
import {
  Activity,
  BookOpen,
  Cable,
  CalendarClock,
  CircleAlert,
  Database,
  HardDriveDownload,
  LayoutDashboard,
  Plug,
  PlayCircle,
  Users,
  Warehouse,
} from "lucide-react";

export type NavItem = {
  href: string;
  label: string;
  icon: LucideIcon;
  badge?: string;
  match?: "exact" | "prefix";
  /** Скрыть пункт, если нет workspace-права. */
  requiredPermission?: string;
};

export const navSections: { title: string; items: NavItem[] }[] = [
  {
    title: "Обзор",
    items: [
      { href: "/", label: "Дашборд", icon: LayoutDashboard, match: "exact" },
      { href: "/activity", label: "Активность", icon: Activity, match: "exact" },
    ],
  },
  {
    title: "Интеграции",
    items: [
      { href: "/connections", label: "Подключения", icon: Cable, match: "prefix" },
      { href: "/sources", label: "Источники", icon: Database, match: "prefix" },
      { href: "/destinations", label: "Приёмники", icon: HardDriveDownload, match: "prefix" },
      { href: "/connectors", label: "Каталог коннекторов", icon: Plug, match: "prefix" },
    ],
  },
  {
    title: "Синхронизация",
    items: [
      { href: "/runs", label: "Запуски", icon: PlayCircle, badge: "1", match: "prefix" },
      { href: "/schedules", label: "Расписания", icon: CalendarClock, match: "exact" },
      { href: "/queue", label: "Очередь", icon: Warehouse, match: "exact" },
    ],
  },
  {
    title: "Данные",
    items: [
      { href: "/issues", label: "Проблемные записи", icon: CircleAlert, badge: "73", match: "prefix" },
    ],
  },
  {
    title: "Администрирование",
    items: [
      { href: "/users", label: "Пользователи и роли", icon: Users, match: "prefix" },
      { href: "/workspaces", label: "Рабочие пространства", icon: Warehouse, match: "prefix" },
      { href: "/dictionaries", label: "Справочники", icon: BookOpen, match: "prefix" },
      { href: "/audit", label: "Аудит", icon: Activity, match: "prefix", requiredPermission: "audit.read" },
    ],
  },
];

export function navActive(location: string, item: NavItem): boolean {
  if (item.match === "exact" || item.href === "/") {
    return location === item.href;
  }
  return location === item.href || location.startsWith(`${item.href}/`);
}
