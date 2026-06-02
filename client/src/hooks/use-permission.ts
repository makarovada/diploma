import { useAuth } from "@/app/auth-context";

export function usePermission(code: string): boolean {
  const { user } = useAuth();
  if (!user) return false;
  if (user.is_workspace_admin) return true;
  return (user.permissions ?? []).includes(code);
}

export function useAnyPermission(codes: string[]): boolean {
  const { user } = useAuth();
  if (!user) return false;
  if (user.is_workspace_admin) return true;
  const set = new Set(user.permissions ?? []);
  return codes.some((c) => set.has(c));
}
