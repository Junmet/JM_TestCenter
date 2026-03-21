import { createRouter, createWebHistory, RouteRecordRaw } from "vue-router";
import LoginView from "../views/LoginView.vue";
import LayoutMain from "../layouts/LayoutMain.vue";
import HomeView from "../views/HomeView.vue";
import DashboardView from "../views/DashboardView.vue";
import CaseListView from "../views/CaseListView.vue";
import CaseRequirementDetailView from "../views/CaseRequirementDetailView.vue";
import CaseGenView from "../views/CaseGenView.vue";
import UiAutomationView from "../views/UiAutomationView.vue";
import ApiTestView from "../views/ApiTestView.vue";
import PerformanceTestView from "../views/PerformanceTestView.vue";
import AiChatView from "../views/AiChatView.vue";

const routes: RouteRecordRaw[] = [
  { path: "/", redirect: "/home" },
  {
    path: "/login",
    name: "Login",
    component: LoginView
  },
  {
    path: "/",
    component: LayoutMain,
    meta: { requiresAuth: true },
    children: [
      { path: "home", name: "Home", component: HomeView },
      { path: "dashboard", name: "Dashboard", component: DashboardView },
      { path: "cases", name: "Cases", component: CaseListView },
      { path: "cases/:reqId", name: "CaseRequirementDetail", component: CaseRequirementDetailView },
      { path: "case-gen", name: "CaseGen", component: CaseGenView },
      { path: "ui-automation", name: "UiAutomation", component: UiAutomationView },
      { path: "api-test", name: "ApiTest", component: ApiTestView },
      { path: "perf-test", name: "PerfTest", component: PerformanceTestView },
      { path: "ai-chat", name: "AiChat", component: AiChatView }
    ]
  }
];

const router = createRouter({
  history: createWebHistory(),
  routes
});

// 简单的鉴权守卫：没有 access_token 时禁止访问受保护页面
router.beforeEach((to, _from, next) => {
  if (!to.meta.requiresAuth) {
    next();
    return;
  }

  // 动态 import，减少初始加载
  import("../stores/auth").then(({ useAuthStore }) => {
    const authStore = useAuthStore();
    if (authStore.accessToken) {
      next();
    } else {
      next({ name: "Login" });
    }
  });
});

export default router;

