import { http } from "./http";
import type { StoredUser } from "../utils/storage";

export type LoginRequest = {
  username: string;
  password: string;
};

export type LoginResponse = {
  token_type: string;
  access_token: string;
  refresh_token: string;
  expires_in: number;
  user: StoredUser;
};

// 调用后端登录接口：POST /api/v1/auth/login
export async function loginApi(payload: LoginRequest): Promise<LoginResponse> {
  const resp = await http.post<LoginResponse>("/api/v1/auth/login", payload);
  return resp.data;
}

