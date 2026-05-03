import { Route, Switch } from "wouter";
import { AuthenticatedShell } from "@/app/authenticated-shell";
import { LoginPage } from "@/pages/login";

export function AppRoutes() {
  return (
    <Switch>
      <Route path="/login" component={LoginPage} />
      <Route component={AuthenticatedShell} />
    </Switch>
  );
}
