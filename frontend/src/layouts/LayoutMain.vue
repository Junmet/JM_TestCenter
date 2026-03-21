<template>
  <el-container class="layout-main">
    <el-header class="header">
      <div class="brand">JMTEST</div>
      <el-menu :default-active="activePath" mode="horizontal" :ellipsis="false" router class="nav">
        <el-menu-item v-for="item in menus" :key="item.id" :index="item.path">
          {{ item.title }}
        </el-menu-item>
      </el-menu>
      <div class="user">
        <span class="user-name">{{ authStore.user?.username }}</span>
        <el-button text @click="handleLogout">退出</el-button>
      </div>
    </el-header>
    <el-main class="main">
      <!-- 固定一层 flex 子节点，保证各页 page-view 能获得明确高度（避免部分页面内容区高度为 0 看起来像空白） -->
      <div class="main-route">
        <router-view />
      </div>
    </el-main>
  </el-container>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth";
import { getMenusApi, type MenuItem } from "../api/system";

const authStore = useAuthStore();
const router = useRouter();
const route = useRoute();
const menus = ref<MenuItem[]>([]);
const activePath = computed(() => route.path);

onMounted(async () => {
  try {
    const res = await getMenusApi();
    menus.value = res.menus ?? [];
  } catch {
    menus.value = [];
  }
});

function handleLogout() {
  authStore.logout();
  router.push({ name: "Login" });
}
</script>

<style scoped>
.layout-main {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #f5f7fb;
}
.header {
  height: 56px;
  padding: 0 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  background: #fff;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}
.brand {
  font-size: 18px;
  font-weight: 700;
  color: #1a1a2e;
  margin-right: 8px;
}
.nav {
  border-bottom: none;
  flex: 1;
  min-width: 0;
}
.user {
  display: flex;
  align-items: center;
  gap: 12px;
}
.user-name {
  font-size: 14px;
  color: #6b7280;
}
.main {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  padding: 20px;
  display: flex;
  flex-direction: column;
}
.main-route {
  flex: 1 1 0%;
  min-height: 0;
  min-width: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
/* 路由页面根节点：必须参与 flex 分配，否则在 el-main 内可能出现高度为 0 的「空白页」 */
.main-route > * {
  flex: 1 1 0%;
  min-height: 0;
  min-width: 0;
}
</style>
