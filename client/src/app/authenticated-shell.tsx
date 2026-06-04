import { useEffect } from "react";
import { Route, Switch, useLocation } from "wouter";
import { useAuth } from "@/app/auth-context";
import { hasGoogleOAuthCallback } from "@/lib/oauth-return";
import { currentHashRoutePath } from "@/lib/route-utils";
import { MainShell } from "@/components/main-shell";
import { ActivityPage } from "@/pages/activity";
import { AuditPage } from "@/pages/audit";
import { ConnectionDetailPage } from "@/pages/connection-detail";
import { ConnectionEditPage } from "@/pages/connection-edit";
import { ConnectionIssuesPage } from "@/pages/connection-issues";
import { ConnectionLogsPage } from "@/pages/connection-logs";
import { ConnectionRunsPage } from "@/pages/connection-runs";
import { ConnectionSettingsPage } from "@/pages/connection-settings";
import { ConnectionStreamsPage } from "@/pages/connection-streams";
import { ConnectionStreamsEditPage } from "@/pages/connection-streams-edit";
import { ConnectionWizardPage } from "@/pages/connection-wizard";
import { ConnectionsPage } from "@/pages/connections";
import { ConnectorDetailPage } from "@/pages/connector-detail";
import { ConnectorsPage } from "@/pages/connectors";
import { DashboardPage } from "@/pages/dashboard";
import { DestinationDetailPage } from "@/pages/destination-detail";
import { DestinationEditPage } from "@/pages/destination-edit";
import { DestinationNewPage } from "@/pages/destination-new";
import { DestinationsPage } from "@/pages/destinations";
import { DictionariesPage } from "@/pages/dictionaries";
import { ForbiddenPage } from "@/pages/forbidden";
import { IssueDetailPage } from "@/pages/issue-detail";
import { IssuesPage } from "@/pages/issues";
import { NotFoundPage } from "@/pages/not-found";
import { QueuePage } from "@/pages/queue";
import { RunDetailPage } from "@/pages/run-detail";
import { RunLogsPage } from "@/pages/run-logs";
import { RunsPage } from "@/pages/runs";
import { SchedulesPage } from "@/pages/schedules";
import { SourceDetailPage } from "@/pages/source-detail";
import { SourceEditPage } from "@/pages/source-edit";
import { SourceNewPage } from "@/pages/source-new";
import { SourcesPage } from "@/pages/sources";
import { UsersPage } from "@/pages/users";
import { WorkspaceSettingsPage } from "@/pages/workspace-settings";
import { WorkspacesPage } from "@/pages/workspaces";

function MainRoutes() {
  return (
    <MainShell>
      <Switch>
        <Route path="/" component={DashboardPage} />
        <Route path="/activity" component={ActivityPage} />

        <Route path="/connections/new" component={ConnectionWizardPage} />
        <Route path="/connections/:id/edit" component={ConnectionEditPage} />
        <Route path="/connections/:id/streams/edit" component={ConnectionStreamsEditPage} />
        <Route path="/connections/:id/streams" component={ConnectionStreamsPage} />
        <Route path="/connections/:id/runs" component={ConnectionRunsPage} />
        <Route path="/connections/:id/logs" component={ConnectionLogsPage} />
        <Route path="/connections/:id/issues" component={ConnectionIssuesPage} />
        <Route path="/connections/:id/settings" component={ConnectionSettingsPage} />
        <Route path="/connections/:id" component={ConnectionDetailPage} />
        <Route path="/connections" component={ConnectionsPage} />

        <Route path="/sources/new" component={SourceNewPage} />
        <Route path="/sources/:sourceId/edit" component={SourceEditPage} />
        <Route path="/sources/:sourceId" component={SourceDetailPage} />
        <Route path="/sources" component={SourcesPage} />

        <Route path="/destinations/new" component={DestinationNewPage} />
        <Route path="/destinations/:destinationId/edit" component={DestinationEditPage} />
        <Route path="/destinations/:destinationId" component={DestinationDetailPage} />
        <Route path="/destinations" component={DestinationsPage} />

        <Route path="/connectors/:connectorId" component={ConnectorDetailPage} />
        <Route path="/connectors" component={ConnectorsPage} />

        <Route path="/runs/:runId/logs" component={RunLogsPage} />
        <Route path="/runs/:id" component={RunDetailPage} />
        <Route path="/runs" component={RunsPage} />

        <Route path="/schedules" component={SchedulesPage} />
        <Route path="/queue" component={QueuePage} />

        <Route path="/issues/:issueId" component={IssueDetailPage} />
        <Route path="/issues" component={IssuesPage} />

        <Route path="/users" component={UsersPage} />
        <Route path="/workspaces/:workspaceId/settings" component={WorkspaceSettingsPage} />
        <Route path="/workspaces" component={WorkspacesPage} />
        <Route path="/dictionaries" component={DictionariesPage} />
        <Route path="/audit" component={AuditPage} />

        <Route component={NotFoundPage} />
      </Switch>
    </MainShell>
  );
}

export function AuthenticatedShell() {
  const { status, user } = useAuth();
  const [, setLocation] = useLocation();

  useEffect(() => {
    if (status !== "unauthenticated") return;
    const path = currentHashRoutePath();
    const next = encodeURIComponent(path === "/login" ? "/" : path);
    setLocation(`/login?next=${next}`);
  }, [status, setLocation]);

  if (status === "initializing") {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-background text-muted-foreground" data-testid="auth-loading">
        Загрузка сессии…
      </div>
    );
  }

  if ((status === "unauthenticated" || !user) && !hasGoogleOAuthCallback()) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-background text-muted-foreground" data-testid="auth-redirect">
        Перенаправление на страницу входа…
      </div>
    );
  }


  return (
    <Switch>
      <Route path="/forbidden" component={ForbiddenPage} />
      <Route component={MainRoutes} />
    </Switch>
  );
}
