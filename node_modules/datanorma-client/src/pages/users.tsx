import { useQuery } from "@tanstack/react-query";
import { fetchAdminUsers } from "@/lib/api-datanorma";
import { queryKeys } from "@/lib/query-keys";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import type { AppUser } from "@/lib/types";

const roleRu: Record<string, string> = {
  platform_admin: "Администратор платформы",
  data_integrator: "Интегратор данных",
  analyst: "Аналитик",
  viewer: "Наблюдатель",
};

const statusRu: Record<string, string> = {
  active: "Активен",
  invited: "Приглашён",
  disabled: "Отключён",
};

function mapApiUser(u: { id: number; username: string; email: string | null; roles: string[] }): AppUser {
  const roleRaw = u.roles[0] ?? "viewer";
  const role =
    roleRaw === "platform_admin" || roleRaw === "data_integrator" || roleRaw === "analyst" || roleRaw === "viewer" ? roleRaw : "viewer";
  return {
    id: String(u.id),
    name: u.username,
    email: u.email ?? "",
    role,
    workspace: "—",
    status: "active",
    lastActive: "—",
  };
}

export function UsersPage() {
  const query = useQuery({
    queryKey: queryKeys.users.list(),
    queryFn: async () => {
      const { users } = await fetchAdminUsers();
      return users.map((u) => mapApiUser(u));
    },
  });

  if (query.isPending) return <div data-testid="state-loading-users" className="p-4">Загрузка пользователей…</div>;
  if (query.isError || !query.data) return <div data-testid="state-error-users" className="p-4">Ошибка загрузки.</div>;

  const rows = query.data;

  if (rows.length === 0) {
    return (
      <div className="p-4">
        <PageHeader title="Пользователи и роли" description="Доступ к интеграциям и администрированию" breadcrumbs="Администрирование / Пользователи" actions={<Button data-testid="button-invite-user">Пригласить пользователя</Button>} />
        <div data-testid="state-empty-users" className="rounded-lg border bg-card p-8 text-center text-sm text-muted-foreground">
          Пользователей не найдено.
        </div>
      </div>
    );
  }

  return (
    <div className="p-4">
      <PageHeader title="Пользователи и роли" description="Доступ к интеграциям и администрированию" breadcrumbs="Администрирование / Пользователи" actions={<Button data-testid="button-invite-user">Пригласить пользователя</Button>} />
      <div className="overflow-auto rounded-lg border" data-testid="table-users">
        <table className="w-full min-w-[900px] text-left text-sm" aria-label="Пользователи">
          <thead className="bg-muted">
            <tr>
              <th>Имя</th>
              <th>Email</th>
              <th>Роль</th>
              <th>Рабочее пространство</th>
              <th>Статус</th>
              <th>Последняя активность</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {rows.map((u) => (
              <tr key={u.id} className="border-t" data-testid={`row-user-${u.id}`}>
                <td>{u.name}</td>
                <td>{u.email}</td>
                <td>{roleRu[u.role]}</td>
                <td>{u.workspace}</td>
                <td>{statusRu[u.status]}</td>
                <td>{u.lastActive}</td>
                <td>
                  <Button variant="outline" className="px-2 py-1 text-xs" data-testid={`button-edit-user-${u.id}`}>
                    Изменить роль
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Card className="mt-6 p-4" data-testid="matrix-rbac-preview">
        <h2 className="mb-2 text-lg font-semibold">Матрица прав (фрагмент)</h2>
        <p className="mb-3 text-sm text-muted-foreground">Создание подключений, запуск sync, просмотр секретов — по ролям.</p>
        <div className="overflow-auto">
          <table className="w-full min-w-[640px] text-center text-xs" aria-label="Матрица ролей">
            <thead>
              <tr className="border-b bg-muted">
                <th className="p-2 text-left">Операция</th>
                <th className="p-2">Админ</th>
                <th className="p-2">Интегратор</th>
                <th className="p-2">Аналитик</th>
                <th className="p-2">Наблюдатель</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-t"><td className="p-2 text-left">Создавать подключение</td><td>✓</td><td>✓</td><td>—</td><td>—</td></tr>
              <tr className="border-t"><td className="p-2 text-left">Запускать синхронизацию</td><td>✓</td><td>✓</td><td>—</td><td>—</td></tr>
              <tr className="border-t"><td className="p-2 text-left">Редактировать маппинг</td><td>✓</td><td>✓</td><td>—</td><td>—</td></tr>
              <tr className="border-t"><td className="p-2 text-left">Смотреть логи</td><td>✓</td><td>✓</td><td>✓</td><td>✓</td></tr>
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
