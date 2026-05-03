import ReactDOM from "react-dom/client";
import { Router } from "wouter";
import { useHashLocation } from "wouter/use-hash-location";
import { AuthProvider } from "@/app/auth-context";
import { AppProviders } from "@/app/providers";
import { AppRoutes } from "@/app/routes";
import "@/index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <Router hook={useHashLocation}>
    <AppProviders>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </AppProviders>
  </Router>,
);
