/** Показывается, когда список загружен из mock-data из-за ошибки API. */
export function DemoFallbackBanner() {
  return (
    <div
      className="mb-3 rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs text-amber-950 dark:text-amber-100"
      data-testid="banner-demo-fallback"
    >
      Показаны демо-данные: не удалось загрузить ответ API (сеть или сервер). После восстановления backend данные обновятся сами.
    </div>
  );
}
