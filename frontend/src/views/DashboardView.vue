<!--
  控制台：对接 GET /api/v1/dashboard/overview（用例管理 + UI 自动化统计与趋势）
-->
<template>
  <div class="page-view dashboard" v-loading="loading">
    <header class="dashboard-header">
      <h1 class="title">控制台</h1>
      <p class="subtitle">
        测试需求、用例与 UI 自动化执行概览；数据来自当前登录账号的后台记录
      </p>
    </header>

    <el-alert
      v-if="loadError"
      type="warning"
      :closable="false"
      show-icon
      class="dash-alert"
      :title="loadError"
    />

    <!-- 统计卡片 -->
    <section class="stats-row">
      <el-card v-for="card in statCards" :key="card.key" class="stat-card" shadow="hover">
        <span class="stat-label">{{ card.label }}</span>
        <span class="stat-value">{{ card.value }}</span>
        <span v-if="card.extra" class="stat-extra">{{ card.extra }}</span>
      </el-card>
    </section>

    <!-- 图表区 -->
    <section class="charts-row">
      <el-card class="chart-panel" shadow="never">
        <h2 class="panel-title">用例执行状态分布</h2>
        <p class="chart-hint">基于「用例管理」中各用例的执行状态汇总</p>
        <v-chart class="dash-chart" :option="pieOption" autoresize />
      </el-card>
      <el-card class="chart-panel" shadow="never">
        <h2 class="panel-title">近 7 日 UI 自动化执行</h2>
        <p class="chart-hint">按自然日统计（Asia/Shanghai）</p>
        <v-chart class="dash-chart" :option="barOption" autoresize />
      </el-card>
    </section>

    <!-- 最近执行 + 快捷入口 -->
    <section class="dashboard-main">
      <el-card class="panel panel-recent" shadow="never">
        <h2 class="panel-title">最近 UI 自动化任务</h2>
        <div class="list-table-wrap list-table-wrap--dashboard">
          <div class="list-table-scroll">
            <el-table
              :data="recentRuns"
              stripe
              size="small"
              table-layout="fixed"
              height="100%"
              class="list-table list-table--first-left"
              empty-text="暂无执行记录，可在「UI 自动化」发起任务"
            >
              <el-table-column prop="title" label="任务名称" show-overflow-tooltip />
              <el-table-column label="状态" width="100" show-overflow-tooltip>
                <template #default="{ row }">
                  <el-tag :type="tagTypeForRun(row.status)" effect="light">
                    {{ row.status_text }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="run_at" label="创建时间" width="160" show-overflow-tooltip />
            </el-table>
          </div>
        </div>
      </el-card>
      <el-card class="panel panel-side" shadow="never">
        <h2 class="panel-title">快捷入口</h2>
        <div class="quick-links">
          <router-link
            v-for="link in quickLinks"
            :key="link.path"
            :to="link.path"
            class="quick-link"
          >
            {{ link.title }}
          </router-link>
        </div>
        <h2 class="panel-title panel-title--small">说明</h2>
        <p class="panel-desc">
          通过率按已执行用例中「成功 / (成功+失败)」计算；未执行或阻塞不计入分母。UI
          任务为 Midscene / Playwright 运行记录。
        </p>
      </el-card>
    </section>
  </div>
</template>

<script setup lang="ts">
import { use } from "echarts/core";
import { BarChart, PieChart } from "echarts/charts";
import {
  GridComponent,
  LegendComponent,
  TitleComponent,
  TooltipComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import type { ComposeOption } from "echarts/core";
import type { BarSeriesOption, PieSeriesOption } from "echarts/charts";
import VChart from "vue-echarts";
import { computed, onMounted, ref } from "vue";
import { isAxiosError } from "axios";
import { getDashboardOverviewApi, type DashboardOverview } from "../api/dashboard";

use([CanvasRenderer, BarChart, PieChart, GridComponent, LegendComponent, TitleComponent, TooltipComponent]);

const loading = ref(false);
const loadError = ref("");
const overview = ref<DashboardOverview | null>(null);

const statCards = computed(() => {
  const s = overview.value?.stats;
  if (!s) {
    return [
      { key: "req", label: "测试需求", value: "—", extra: "" },
      { key: "cases", label: "用例总数", value: "—", extra: "" },
      { key: "pass", label: "用例通过率", value: "—", extra: "" },
      { key: "today", label: "今日 UI 执行", value: "—", extra: "" },
    ];
  }
  const pass =
    s.case_pass_rate_percent === null || s.case_pass_rate_percent === undefined
      ? "—"
      : String(s.case_pass_rate_percent);
  const passExtra = pass === "—" ? "" : "%";
  return [
    { key: "req", label: "测试需求", value: String(s.requirement_count), extra: "个" },
    { key: "cases", label: "用例总数", value: String(s.case_count), extra: "条" },
    { key: "pass", label: "用例通过率", value: pass, extra: passExtra },
    {
      key: "today",
      label: "今日 UI 执行",
      value: String(s.ui_runs_today),
      extra: `次 · 累计 ${s.ui_runs_total}`,
    },
  ];
});

const recentRuns = computed(() => overview.value?.recent_ui_runs ?? []);

type EChartsOption = ComposeOption<PieSeriesOption | BarSeriesOption>;

const pieOption = computed<EChartsOption>(() => {
  const c = overview.value?.case_execution;
  if (!c) {
    return {
      tooltip: { trigger: "item" },
      series: [{ type: "pie", radius: ["42%", "68%"], data: [] }],
    };
  }
  const data = [
    { value: c.not_executed, name: "未执行" },
    { value: c.success, name: "成功" },
    { value: c.failed, name: "失败" },
    { value: c.blocked, name: "阻塞" },
  ].filter((x) => x.value > 0);
  const empty = data.length === 0;
  return {
    color: ["#94a3b8", "#22c55e", "#ef4444", "#f59e0b"],
    tooltip: { trigger: "item", formatter: "{b}: {c} ({d}%)" },
    legend: { bottom: 0, left: "center" },
    series: [
      {
        type: "pie",
        radius: ["42%", "68%"],
        avoidLabelOverlap: true,
        itemStyle: { borderRadius: 6, borderColor: "#fff", borderWidth: 2 },
        label: { formatter: "{b}\n{c}" },
        data: empty ? [{ value: 1, name: "暂无数据", itemStyle: { color: "#e2e8f0" } }] : data,
      },
    ],
  };
});

const barOption = computed<EChartsOption>(() => {
  const pts = overview.value?.ui_runs_last_7_days ?? [];
  const labels = pts.map((p) => p.date.slice(5));
  const counts = pts.map((p) => p.count);
  return {
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
    grid: { left: 48, right: 16, top: 24, bottom: 40 },
    xAxis: {
      type: "category",
      data: labels,
      axisLabel: { color: "#64748b" },
    },
    yAxis: {
      type: "value",
      minInterval: 1,
      axisLabel: { color: "#64748b" },
      splitLine: { lineStyle: { type: "dashed", color: "#e2e8f0" } },
    },
    series: [
      {
        type: "bar",
        name: "执行次数",
        data: counts,
        barMaxWidth: 36,
        itemStyle: {
          color: "#3b82f6",
          borderRadius: [4, 4, 0, 0],
        },
      },
    ],
  };
});

const quickLinks = [
  { title: "用例管理", path: "/cases" },
  { title: "UI 自动化", path: "/ui-automation" },
  { title: "用例生成", path: "/case-gen" },
];

function tagTypeForRun(status: string): "success" | "danger" | "warning" | "info" | "primary" {
  if (status === "success") return "success";
  if (status === "failed") return "danger";
  if (status === "running") return "primary";
  if (status === "pending") return "info";
  return "info";
}

onMounted(async () => {
  loading.value = true;
  loadError.value = "";
  try {
    overview.value = await getDashboardOverviewApi();
  } catch (e: unknown) {
    let detail = "";
    if (isAxiosError(e)) {
      const d = e.response?.data;
      if (typeof d === "string") detail = d;
      else if (d && typeof d === "object" && "detail" in d) detail = String((d as { detail: unknown }).detail);
    } else if (e instanceof Error) {
      detail = e.message;
    }
    loadError.value = detail ? `加载控制台数据失败：${detail}` : "加载控制台数据失败，请稍后重试";
  } finally {
    loading.value = false;
  }
});
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
.dash-alert {
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
  font-size: 13px;
  color: #64748b;
}

.charts-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
  min-height: 0;
}
.chart-panel {
  display: flex;
  flex-direction: column;
  min-height: 0;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
}
.chart-hint {
  margin: 0 0 8px;
  font-size: 12px;
  color: #94a3b8;
}
.dash-chart {
  height: 280px;
  width: 100%;
  min-height: 240px;
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
  color: #2563eb;
  font-size: 14px;
  text-decoration: none;
}
.quick-link:hover {
  text-decoration: underline;
}

@media (max-width: 1200px) {
  .stats-row {
    grid-template-columns: repeat(2, 1fr);
  }
  .charts-row {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 900px) {
  .dashboard-main {
    grid-template-columns: 1fr;
  }
}
</style>
