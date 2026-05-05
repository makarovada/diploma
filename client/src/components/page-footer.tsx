/** Служебный футер для настроек, справки, аудита и документации API (по ТЗ). */
export function PageFooter() {
  return (
    <footer
      className="mt-8 border-t px-4 py-6 text-xs text-muted-foreground"
      data-testid="page-footer-meta"
    >
      <p>DataNorma · API v1 · Europe/Moscow</p>
      <p className="mt-1">Последнее обновление интерфейса: 2026-05-02</p>
      <p className="mt-1">Данные обрабатываются в рамках выбранного рабочего пространства.</p>
    </footer>
  );
}
