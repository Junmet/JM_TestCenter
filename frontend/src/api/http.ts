import axios from "axios";

import { getAccessToken } from "../utils/storage";

// 创建 axios 实例：所有 API 都从这里发出，方便统一拦截器管理
export const http = axios.create({
  timeout: 15000
});

// 请求拦截：自动把 access_token 塞进 Authorization
http.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 响应拦截：401 视为 token 失效，清理登录态并跳转登录页（动态 import 避免与 router/store 循环依赖）
http.interceptors.response.use(
  (resp) => resp,
  async (err) => {
    const status = err?.response?.status;
    if (status === 401) {
      const { useAuthStore } = await import("../stores/auth");
      useAuthStore().logout();
      const router = (await import("../router")).default;
      if (router.currentRoute.value.name !== "Login") {
        await router.replace({ name: "Login" });
      }
    }
    return Promise.reject(err);
  }
);

