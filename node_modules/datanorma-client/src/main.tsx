import ReactDOM from "react-dom/client";
import { Router } from "wouter";
import { useHashLocation } from "wouter/use-hash-location";
import { AppProviders } from "@/app/providers";
import { AppRoutes } from "@/app/routes";
import "@/index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <AppProviders>
    <Router hook={useHashLocation}>
      <AppRoutes />
    </Router>
  </AppProviders>,
);
