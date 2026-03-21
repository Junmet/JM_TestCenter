<template>
  <!-- 使用公共容器 page-view，内部用 hero-wrap 填满并居中，避免 min-height:100% 撑出滚动条 -->
  <div class="page-view">
    <div class="hero-wrap">
      <el-card class="hero" shadow="never">
        <p class="tagline">欢迎使用</p>
        <h1 class="welcome">JMTEST 测试平台</h1>
        <p class="desc">智能、高效、可扩展的测试管理平台</p>
        <el-tag class="user-badge" effect="light" round>
          <span class="user-label">当前用户</span>
          <span class="user-name">{{ authStore.user?.username ?? "-" }}</span>
        </el-tag>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useAuthStore } from "../stores/auth";

const authStore = useAuthStore();
</script>

<style scoped>
/* 填满 page-view 内容区并居中，不撑高，避免出现滚动条 */
.hero-wrap {
  height: 100%;
  min-height: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}
.hero {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 24px;
  border: none;
  background: transparent;
}
.tagline {
  margin: 0 0 8px;
  font-size: 15px;
  font-weight: 500;
  letter-spacing: 0.2em;
  color: #6366f1;
  text-transform: uppercase;
}
.welcome {
  margin: 0 0 16px;
  font-size: clamp(2rem, 5vw, 3.25rem);
  font-weight: 800;
  letter-spacing: 0.02em;
  color: #0f172a;
  line-height: 1.2;
}
.desc {
  margin: 0 0 40px;
  font-size: 1.0625rem;
  color: #64748b;
  font-weight: 400;
  max-width: 360px;
}
.user-badge {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 8px 16px;
}
.user-label {
  font-size: 13px;
  color: #94a3b8;
}
.user-name {
  font-size: 14px;
  font-weight: 600;
  color: #334155;
}
</style>
