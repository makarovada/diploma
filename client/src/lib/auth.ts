import { apiGetJson, apiPostJson } from "@/lib/api-client";
import type { LoginResponseDto, MeDto, RegisterResponseDto } from "@/lib/api-types";

export async function fetchAuthMe(): Promise<MeDto> {
  return apiGetJson<MeDto>("/api/auth/me");
}

export async function postAuthLogin(username: string, password: string): Promise<LoginResponseDto> {
  return apiPostJson<LoginResponseDto, { username: string; password: string }>(
    "/api/auth/login",
    { username, password },
    { skipAuth: true },
  );
}

export type RegisterPayload = {
  username: string;
  email?: string | null;
  password: string;
  registration_mode: "create_workspace" | "wait_for_invite";
  workspace_name?: string;
  workspace_code?: string;
};

export async function postAuthRegister(payload: RegisterPayload): Promise<RegisterResponseDto> {
  return apiPostJson<RegisterResponseDto, RegisterPayload>("/api/auth/register", payload, { skipAuth: true });
}
