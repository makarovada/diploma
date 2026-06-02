import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useRoute } from "wouter";
import { useAuth } from "@/app/auth-context";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { formatApiErrorMessage } from "@/lib/api-client";
import {
  deleteWorkspaceMember,
  fetchPermissionCatalog,
  fetchWorkspaceMembers,
  postWorkspaceMember,
  putMemberPermissions,
} from "@/lib/api-workspaces";
import { usePermission } from "@/hooks/use-permission";

export function WorkspaceSettingsPage() {
  const [, params] = useRoute("/workspaces/:workspaceId/settings");
  const workspaceId = Number(params?.workspaceId);
  const { user, refreshMe } = useAuth();
  const qc = useQueryClient();
  const canManageMembers = usePermission("workspace.members.manage");
  const canGrant = usePermission("workspace.permissions.grant");
  const [newUsername, setNewUsername] = useState("");
  const [error, setError] = useState<string | null>(null);

  const catalogQuery = useQuery({
    queryKey: ["permission-catalog"],
    queryFn: async () => {
      const { items } = await fetchPermissionCatalog();
      return items;
    },
    enabled: canGrant,
  });

  const membersQuery = useQuery({
    queryKey: ["workspace-members", workspaceId],
    queryFn: async () => {
      const { items } = await fetchWorkspaceMembers(workspaceId);
      return items;
    },
    enabled: Number.isFinite(workspaceId) && canManageMembers,
  });

  const [draftPerms, setDraftPerms] = useState<Record<number, string[]>>({});

  const addMemberMut = useMutation({
    mutationFn: () => postWorkspaceMember(workspaceId, newUsername.trim()),
    onSuccess: async () => {
      setNewUsername("");
      setError(null);
      await qc.invalidateQueries({ queryKey: ["workspace-members", workspaceId] });
      await refreshMe();
    },
    onError: (e) => setError(formatApiErrorMessage(e)),
  });

  const savePermsMut = useMutation({
    mutationFn: ({ userId, permissions }: { userId: number; permissions: string[] }) =>
      putMemberPermissions(workspaceId, userId, permissions),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["workspace-members", workspaceId] });
      await refreshMe();
    },
    onError: (e) => setError(formatApiErrorMessage(e)),
  });

  if (!Number.isFinite(workspaceId)) {
    return <div className="p-4">Некорректный идентификатор пространства.</div>;
  }

  if (!canManageMembers && !user?.is_workspace_admin) {
    return <div className="p-4">Недостаточно прав для настройки пространства.</div>;
  }

  const wsName = user?.workspaces?.find((w) => w.id === workspaceId)?.name ?? `ID ${workspaceId}`;

  return (
    <div className="p-4">
      <PageHeader
        title={`Участники: ${wsName}`}
        description="Приглашение пользователей и выдача прав в пространстве"
        breadcrumbs="Администрирование / Пространства / Настройки"
      />

      <Card className="mb-4 p-4">
        <h3 className="mb-2 text-sm font-semibold">Пригласить участника</h3>
        <div className="flex flex-wrap gap-2">
          <input
            className="rounded-md border bg-background px-2 py-1 text-sm"
            placeholder="Имя пользователя"
            value={newUsername}
            onChange={(e) => setNewUsername(e.target.value)}
          />
          <Button type="button" disabled={!newUsername.trim() || addMemberMut.isPending} onClick={() => addMemberMut.mutate()}>
            Добавить
          </Button>
        </div>
      </Card>

      {membersQuery.isPending ? (
        <p className="text-muted-foreground">Загрузка участников…</p>
      ) : (
        <div className="space-y-4">
          {(membersQuery.data ?? []).map((m) => {
            const selected = draftPerms[m.user_id] ?? m.permissions;
            return (
              <Card key={m.user_id} className="p-4">
                <div className="mb-2 flex items-center justify-between">
                  <div>
                    <p className="font-medium">{m.username}</p>
                    <p className="text-xs text-muted-foreground">
                      {m.is_admin ? "Администратор пространства" : "Участник"}
                    </p>
                  </div>
                  {!m.is_admin ? (
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={async () => {
                        await deleteWorkspaceMember(workspaceId, m.user_id);
                        await qc.invalidateQueries({ queryKey: ["workspace-members", workspaceId] });
                      }}
                    >
                      Удалить
                    </Button>
                  ) : null}
                </div>
                {canGrant && !m.is_admin && catalogQuery.data ? (
                  <div className="grid gap-1 sm:grid-cols-2">
                    {catalogQuery.data.map((p) => (
                      <label key={p.code} className="flex items-center gap-2 text-sm">
                        <input
                          type="checkbox"
                          checked={selected.includes(p.code)}
                          onChange={(e) => {
                            const next = e.target.checked
                              ? [...selected, p.code]
                              : selected.filter((c) => c !== p.code);
                            setDraftPerms((d) => ({ ...d, [m.user_id]: next }));
                          }}
                        />
                        {p.label_ru}
                      </label>
                    ))}
                    <Button
                      type="button"
                      size="sm"
                      className="mt-2 sm:col-span-2"
                      onClick={() => savePermsMut.mutate({ userId: m.user_id, permissions: selected })}
                    >
                      Сохранить права
                    </Button>
                  </div>
                ) : null}
              </Card>
            );
          })}
        </div>
      )}
      {error ? <p className="mt-2 text-sm text-destructive">{error}</p> : null}
    </div>
  );
}
