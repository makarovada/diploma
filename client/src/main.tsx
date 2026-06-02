import ReactDOM from "react-dom/client";
import { Router } from "wouter";
import { useHashLocation } from "wouter/use-hash-location";
import { AuthProvider } from "@/app/auth-context";
import { AppProviders } from "@/app/providers";
import { AppRoutes } from "@/app/routes";
import {
  hasGoogleOAuthCallback,
  migrateOAuthCallbackToHashRouter,
  repairOAuthLandingHash,
  stashGoogleOAuthParamsFromUrl,
} from "@/lib/oauth-return";
import "@/index.css";

migrateOAuthCallbackToHashRouter();
repairOAuthLandingHash();
if (hasGoogleOAuthCallback()) {
  stashGoogleOAuthParamsFromUrl();
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <Router hook={useHashLocation}>
    <AppProviders>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </AppProviders>
  </Router>,
);
