import { http } from "./http";

/** 导航项，与 Backend 接口一致 */
export type MenuItem = {
  id: string;
  title: string;
  path: string;
  icon: string | null;
};

export type MenuListResponse = {
  menus: MenuItem[];
};

/** 获取导航菜单数据，由 Backend 提供，需登录后调用 */
export async function getMenusApi(): Promise<MenuListResponse> {
  const resp = await http.get<MenuListResponse>("/api/v1/system/menus");
  return resp.data;
}
