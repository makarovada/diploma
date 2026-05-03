import { apiGetJson, apiPostJson } from "@/lib/api-client";
import type { LoginResponseDto, MeDto } from "@/lib/api-types";

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
