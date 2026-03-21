// 统一封装 localStorage：后续可以替换成 cookie 或其他存储介质

const KEY_ACCESS_TOKEN = "jmtestcenter_access_token";
const KEY_REFRESH_TOKEN = "jmtestcenter_refresh_token";
const KEY_USER = "jmtestcenter_user";

export function setAccessToken(token: string) {
  localStorage.setItem(KEY_ACCESS_TOKEN, token);
}

export function getAccessToken(): string | null {
  return localStorage.getItem(KEY_ACCESS_TOKEN);
}

export function setRefreshToken(token: string) {
  localStorage.setItem(KEY_REFRESH_TOKEN, token);
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(KEY_REFRESH_TOKEN);
}

export function clearAuth() {
  localStorage.removeItem(KEY_ACCESS_TOKEN);
  localStorage.removeItem(KEY_REFRESH_TOKEN);
  localStorage.removeItem(KEY_USER);
}

export type StoredUser = { id: number; username: string; is_admin: boolean };

export function setUser(user: StoredUser) {
  localStorage.setItem(KEY_USER, JSON.stringify(user));
}

export function getUser(): StoredUser | null {
  const raw = localStorage.getItem(KEY_USER);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as StoredUser;
  } catch {
    return null;
  }
}

