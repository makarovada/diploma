import { apiGetJson } from "@/lib/api-client";

export type GoogleOAuthCompleteDto = {
  oauth_access_token?: string | null;
  oauth_refresh_token: string;
  oauth_token_type?: string | null;
  oauth_expires_in?: number | null;
  oauth_scope?: string | null;
};

export function fetchGoogleOAuthStart(returnUrl?: string) {
  const q =
    returnUrl != null && returnUrl.startsWith("http")
      ? `?return_url=${encodeURIComponent(returnUrl)}`
      : "";
  return apiGetJson<{ authorization_url: string; state: string }>(
    `/api/v1/integrations/google/oauth/start${q}`,
  );
}

export function fetchGoogleOAuthComplete(state: string) {
  return apiGetJson<GoogleOAuthCompleteDto>(
    `/api/v1/integrations/google/oauth/complete?state=${encodeURIComponent(state)}`,
    { suppressGlobalAuthHandlers: true },
  );
}
