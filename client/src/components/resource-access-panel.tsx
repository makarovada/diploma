import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  deleteResourceGrant,
  fetchResourceGrants,
  postResourceGrant,
  type ResourceGrantDto,
} from "@/lib/api-workspaces";
import { formatApiErrorMessage } from "@/lib/api-client";

type ResourceKind = "sources" | "destinations" | "connections";

type Props = {
  resourceType: ResourceKind;
  resourceId: number;
  canManage: boolean;
};

export function ResourceAccessPanel({ resourceType, resourceId, canManage }: Props) {
  const qc = useQueryClient();
  const [username, setUsername] = useState("");
  const [level, setLevel] = useState<"view" | "edit" | "manage">("view");
  const [error, setError] = useState<string | null>(null);

  const grantsQuery = useQuery({
    queryKey: ["resource-grants", resourceType, resourceId],
    queryFn: async () => {
      const { items } = await fetchResourceGrants(resourceType, resourceId);
      return items;
    },
  });

  const addMut = useMutation({
    mutationFn: () => postResourceGrant(resourceType, resourceId, { username: username.trim(), level }),
    onSuccess: async () => {
      setUsername("");
      setError(null);
      await qc.invalidateQueries({ queryKey: ["resource-grants", resourceType, resourceId] });
    },
    onError: (e) => setError(formatApiErrorMessage(e)),
  });

  const delMut = useMutation({
    mutationFn: (granteeUserId: number) => deleteResourceGrant(resourceType, resourceId, granteeUserId),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["resource-grants", resourceType, resourceId] });
    },
  });

  if (!canManage && (grantsQuery.data ?? []).length === 0) {
    return null;
  }

  return (
    <Card className="p-4" data-testid="resource-access-panel">
      <h3 className="mb-2 text-sm font-semibold">Доступ к объекту</h3>
      {grantsQuery.isPending ? (
        <p className="text-sm text-muted-foreground">Загрузка…</p>
      ) : (
        <ul className="mb-3 space-y-1 text-sm">
          {(grantsQuery.data ?? []).map((g: ResourceGrantDto) => (
            <li key={g.id} className="flex items-center justify-between gap-2">
              <span>
                {g.grantee_username} — <span className="text-muted-foreground">{g.level}</span>
              </span>
              {canManage ? (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  disabled={delMut.isPending}
                  onClick={() => delMut.mutate(g.grantee_user_id)}
                >
                  Убрать
                </Button>
              ) : null}
            </li>
          ))}
          {(grantsQuery.data ?? []).length === 0 ? (
            <li className="text-muted-foreground">Нет делегированных прав</li>
          ) : null}
        </ul>
      )}
      {canManage ? (
        <div className="flex flex-wrap items-end gap-2">
          <label className="block text-xs">
            Пользователь
            <input
              className="mt-1 block rounded-md border bg-background px-2 py-1 text-sm"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="username"
            />
          </label>
          <label className="block text-xs">
            Уровень
            <select
              className="mt-1 block rounded-md border bg-background px-2 py-1 text-sm"
              value={level}
              onChange={(e) => setLevel(e.target.value as "view" | "edit" | "manage")}
            >
              <option value="view">Просмотр</option>
              <option value="edit">Изменение</option>
              <option value="manage">Полный</option>
            </select>
          </label>
          <Button type="button" size="sm" disabled={!username.trim() || addMut.isPending} onClick={() => addMut.mutate()}>
            Добавить
          </Button>
        </div>
      ) : null}
      {error ? <p className="mt-2 text-sm text-destructive">{error}</p> : null}
    </Card>
  );
}
