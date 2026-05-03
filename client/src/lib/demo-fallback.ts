import { ApiError } from "@/lib/api-client";

/**
 * При сетевой/серверной ошибке подставляет демо-данные. 401/403 пробрасываются (auth/RBAC).
 */
export async function withApiOrDemo<T>(fn: () => Promise<T>, demo: T): Promise<{ value: T; isDemoFallback: boolean }> {
  try {
    const value = await fn();
    return { value, isDemoFallback: false };
  } catch (e) {
    if (e instanceof ApiError && (e.status === 401 || e.status === 403)) {
      throw e;
    }
    return { value: demo, isDemoFallback: true };
  }
}
