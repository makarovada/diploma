import { PageHeader } from "@/components/page-header";
import { PageFooter } from "@/components/page-footer";
import { Card } from "@/components/ui/card";

export function ApiDocsPage() {
  return (
    <div className="p-4">
      <PageHeader title="Документация API" description="DataNorma MVP · REST API v1 (мок)" breadcrumbs="Сервис / API" />
      <Card className="p-4 font-mono text-xs" data-testid="api-docs-content">
        <pre className="whitespace-pre-wrap">
{`GET  /api/v1/connections
POST /api/v1/connections
GET  /api/v1/runs/{id}
GET  /api/v1/issues

Заголовок: Authorization: Bearer <token>
Базовый URL задаётся в настройках.`}
        </pre>
      </Card>
      <PageFooter />
    </div>
  );
}
