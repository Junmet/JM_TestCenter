import { defineStore } from "pinia";

import { getAccessToken, getRefreshToken, getUser, setAccessToken, setRefreshToken, setUser, clearAuth } from "../utils/storage";
import type { StoredUser } from "../utils/storage";
import { loginApi, type LoginRequest } from "../api/auth";

type AuthState = {
  accessToken: string | null;
  refreshToken: string | null;
  user: StoredUser | null;
};

export const useAuthStore = defineStore("auth", {
  state: (): AuthState => ({
    accessToken: getAccessToken(),
    refreshToken: getRefreshToken(),
    user: getUser()
  }),
  actions: {
    // 登录：调用后端登录接口并保存 token
    async login(payload: LoginRequest) {
      const res = await loginApi(payload);
      setAccessToken(res.access_token);
      setRefreshToken(res.refresh_token);
      setUser(res.user);

      this.accessToken = res.access_token;
      this.refreshToken = res.refresh_token;
      this.user = res.user;
    },

    // 退出登录：清理本地鉴权信息
    logout() {
      clearAuth();
      this.accessToken = null;
      this.refreshToken = null;
      this.user = null;
    }
  }
});

