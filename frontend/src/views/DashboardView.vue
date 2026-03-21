<!--
  控制台页面 · 设计说明（初稿）
  --------------------------
  布局：
  1. 顶部：标题「控制台」+ 副标题说明
  2. 统计区：一行 4 张卡片（测试项目 / 用例总数 / 通过率 / 今日执行），后续可接 GET /api/v1/dashboard/stats
  3. 主内容：左右两栏
     - 左：最近执行（表格，任务名、状态、执行时间），后续可接 GET /api/v1/dashboard/recent-runs
     - 右：快捷入口列表 + 平台说明
  数据：当前全部写死，等后端接口后再替换为请求结果。
-->
<template>
  <div class="page-view dashboard">
    <header class="dashboard-header">
      <h1 class="title">控制台</h1>
      <p class="subtitle">测试平台运行概览，数据为前端写死，后续由后端接口提供</p>
    </header>

    <!-- 统计卡片：一行 4 个，后续可接 /api/v1/dashboard/stats -->
    <section class="stats-row">
      <el-card v-for="card in statCards" :key="card.key" class="stat-card" shadow="hover">
        <span class="stat-label">{{ card.label }}</span>
        <span class="stat-value">{{ card.value }}</span>
        <span v-if="card.extra" class="stat-extra">{{ card.extra }}</span>
      </el-card>
    </section>

    <!-- 主内容区：左侧最近执行，右侧快捷信息 -->
    <section class="dashboard-main">
      <el-card class="panel panel-recent" shadow="never">
        <h2 class="panel-title">最近执行</h2>
        <div class="list-table-wrap list-table-wrap--dashboard">
          <div class="list-table-scroll">
            <el-table
              :data="recentRuns"
              stripe
              size="small"
              table-layout="fixed"
              height="100%"
              class="list-table list-table--first-left"
            >
              <el-table-column prop="name" label="任务名称" show-overflow-tooltip />
              <el-table-column label="状态" show-overflow-tooltip>
                <template #default="{ row }">
                  <el-tag :type="row.status === 'success' ? 'success' : row.status === 'fail' ? 'danger' : 'primary'" effect="light">
                    {{ row.statusText }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="runAt" label="执行时间" show-overflow-tooltip />
            </el-table>
          </div>
        </div>
      </el-card>
      <el-card class="panel panel-side" shadow="never">
        <h2 class="panel-title">快捷入口</h2>
        <div class="quick-links">
          <el-link v-for="link in quickLinks" :key="link.path" :href="link.path" class="quick-link" type="primary">
            {{ link.title }}
          </el-link>
        </div>
        <h2 class="panel-title panel-title--small">平台说明</h2>
        <p class="panel-desc">JMTEST 为测试管理平台，后续将接入：用例管理、执行计划、报告与权限等。当前控制台为静态示意。</p>
      </el-card>
    </section>
  </div>
</template>

<script setup lang="ts">
import { useAuthStore } from "../stores/auth";

const authStore = useAuthStore();

// ========== 以下为写死数据，后续由后端接口替换 ==========

const statCards = [
  { key: "projects", label: "测试项目", value: "6", extra: "" },
  { key: "cases", label: "用例总数", value: "128", extra: "" },
  { key: "passRate", label: "通过率", value: "96.2", extra: "%" },
  { key: "today", label: "今日执行", value: "24", extra: "次" }
];

const recentRuns = [
  { id: 1, name: "回归用例集-A", status: "success", statusText: "通过", runAt: "2025-03-19 10:32" },
  { id: 2, name: "接口冒烟测试", status: "success", statusText: "通过", runAt: "2025-03-19 09:15" },
  { id: 3, name: "登录流程用例", status: "fail", statusText: "失败", runAt: "2025-03-18 16:20" },
  { id: 4, name: "支付流程回归", status: "success", statusText: "通过", runAt: "2025-03-18 14:00" },
  { id: 5, name: "性能压测-P0", status: "running", statusText: "执行中", runAt: "2025-03-19 11:00" }
];

const quickLinks = [
  { title: "用例管理", path: "#" },
  { title: "执行计划", path: "#" },
  { title: "测试报告", path: "#" }
];
</script>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: 24px;
  min-width: 0;
}
.dashboard-header {
  flex-shrink: 0;
}
.title {
  margin: 0 0 4px;
  font-size: 20px;
  font-weight: 700;
  color: #0f172a;
}
.subtitle {
  margin: 0;
  font-size: 13px;
  color: #64748b;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  flex-shrink: 0;
}
.stat-card {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  border: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.stat-label {
  font-size: 13px;
  color: #64748b;
}
.stat-value {
  font-size: 26px;
  font-weight: 700;
  color: #0f172a;
}
.stat-extra {
  font-size: 14px;
  color: #64748b;
}

.dashboard-main {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 1fr 280px;
  gap: 24px;
}
.panel {
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.panel-recent {
  overflow: hidden;
}
.panel-side {
  overflow: auto;
}
.panel-title {
  margin: 0 0 16px;
  font-size: 15px;
  font-weight: 600;
  color: #0f172a;
}
.panel-title--small {
  margin-top: 20px;
  margin-bottom: 8px;
  font-size: 14px;
}
.panel-desc {
  margin: 0;
  font-size: 13px;
  color: #64748b;
  line-height: 1.5;
}

.list-table-wrap--dashboard {
  flex: 1;
  min-height: 280px;
}
.panel-recent :deep(.el-card__body) {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.quick-links {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.quick-link {
  justify-content: flex-start;
}
</style>
