<!--
  性能测试（静态原型）：场景配置、压测执行（模拟）、报告与图表、历史记录、各类弹窗。
-->
<template>
  <div class="page-view perf-page">
    <header class="perf-head">
      <div class="perf-head__title">
        <h1>性能测试</h1>
        <el-tag size="small" type="info">静态演示</el-tag>
      </div>
      <div class="perf-head__actions">
        <el-button type="primary" @click="openNewScenario">
          <el-icon class="mr4"><Plus /></el-icon>
          新建场景
        </el-button>
        <el-button @click="dlgImport = true">导入场景</el-button>
        <el-button :disabled="!activeScenario" @click="exportScenario">导出场景</el-button>
        <el-button @click="dlgGlobal = true">全局设置</el-button>
        <el-button @click="dlgSla = true">SLA / 阈值</el-button>
        <el-button @click="dlgHelp = true">说明</el-button>
      </div>
    </header>

    <div class="perf-body">
      <aside class="perf-aside">
        <div class="aside-title">压测场景</div>
        <el-scrollbar class="aside-scroll">
          <div
            v-for="s in scenarios"
            :key="s.id"
            class="scenario-item"
            :class="{ 'is-active': s.id === activeId }"
            @click="activeId = s.id"
          >
            <span class="scenario-item__name">{{ s.name }}</span>
            <span class="scenario-item__meta">{{ s.method }} · {{ s.vus }} VU</span>
            <el-dropdown trigger="click" @command="(c: string) => onScenarioMenu(c, s)">
              <span class="scenario-item__more" @click.stop><el-icon><MoreFilled /></el-icon></span>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="edit">编辑</el-dropdown-item>
                  <el-dropdown-item command="dup">复制</el-dropdown-item>
                  <el-dropdown-item command="del" divided>删除</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </el-scrollbar>
      </aside>

      <main class="perf-main">
        <el-tabs v-model="mainTab" type="border-card" class="perf-tabs">
          <el-tab-pane label="场景配置" name="config">
            <el-form v-if="activeScenario" label-width="120px" class="perf-form">
              <el-form-item label="场景名称">
                <el-input v-model="activeScenario.name" maxlength="80" show-word-limit />
              </el-form-item>
              <el-row :gutter="16">
                <el-col :xs="24" :md="8">
                  <el-form-item label="HTTP 方法">
                    <el-select v-model="activeScenario.method" style="width: 100%">
                      <el-option label="GET" value="GET" />
                      <el-option label="POST" value="POST" />
                      <el-option label="PUT" value="PUT" />
                      <el-option label="DELETE" value="DELETE" />
                    </el-select>
                  </el-form-item>
                </el-col>
                <el-col :xs="24" :md="16">
                  <el-form-item label="目标 URL">
                    <el-input v-model="activeScenario.url" placeholder="https://..." />
                  </el-form-item>
                </el-col>
              </el-row>
              <el-form-item label="Headers (JSON)">
                <el-input v-model="activeScenario.headersText" type="textarea" :rows="4" class="mono" />
              </el-form-item>
              <el-form-item label="Body">
                <el-input v-model="activeScenario.bodyText" type="textarea" :rows="5" placeholder="GET 可为空" class="mono" />
              </el-form-item>
              <el-row :gutter="16">
                <el-col :xs="24" :sm="12" :md="6">
                  <el-form-item label="虚拟用户数">
                    <el-input-number v-model="activeScenario.vus" :min="1" :max="100000" :step="1" style="width: 100%" />
                  </el-form-item>
                </el-col>
                <el-col :xs="24" :sm="12" :md="6">
                  <el-form-item label="持续时间(s)">
                    <el-input-number v-model="activeScenario.durationSec" :min="1" :max="86400" :step="1" style="width: 100%" />
                  </el-form-item>
                </el-col>
                <el-col :xs="24" :sm="12" :md="6">
                  <el-form-item label="爬坡时间(s)">
                    <el-input-number v-model="activeScenario.rampUpSec" :min="0" :max="3600" :step="1" style="width: 100%" />
                  </el-form-item>
                </el-col>
                <el-col :xs="24" :sm="12" :md="6">
                  <el-form-item label="思考时间(ms)">
                    <el-input-number v-model="activeScenario.thinkTimeMs" :min="0" :max="60000" :step="50" style="width: 100%" />
                  </el-form-item>
                </el-col>
              </el-row>
              <el-form-item>
                <el-button type="primary" @click="saveScenarioLocal">保存配置（本地）</el-button>
              </el-form-item>
            </el-form>
            <el-empty v-else description="请先新建或选择场景" />
          </el-tab-pane>

          <el-tab-pane label="执行" name="run">
            <div v-if="activeScenario" class="run-panel">
              <el-alert type="info" :closable="false" show-icon title="以下为前端模拟执行，不向真实地址发压。" class="mb12" />
              <div class="run-actions">
                <el-button type="primary" :loading="running" :disabled="running" @click="startRun">开始压测</el-button>
                <el-button :disabled="!running" @click="stopRun">停止</el-button>
                <el-button @click="dlgRunAdv = true">高级选项</el-button>
              </div>
              <el-progress v-if="running || runProgress > 0" :percentage="runProgress" :status="running ? undefined : 'success'" class="run-progress" />
              <p v-if="lastRunMessage" class="run-msg">{{ lastRunMessage }}</p>
            </div>
            <el-empty v-else description="无可用场景" />
          </el-tab-pane>

          <el-tab-pane label="报告" name="report">
            <div v-if="reportRun" class="report-panel">
              <el-row :gutter="12" class="stat-row">
                <el-col :xs="12" :sm="8" :md="4" v-for="card in reportCards" :key="card.key">
                  <el-card shadow="hover" class="stat-card">
                    <div class="stat-label">{{ card.label }}</div>
                    <div class="stat-value">{{ card.value }}</div>
                  </el-card>
                </el-col>
              </el-row>
              <el-row :gutter="16" class="chart-row">
                <el-col :xs="24" :lg="12">
                  <el-card shadow="never" class="chart-card">
                    <template #header>响应时间趋势 (ms)</template>
                    <v-chart class="perf-chart" :option="latencyChartOption" autoresize />
                  </el-card>
                </el-col>
                <el-col :xs="24" :lg="12">
                  <el-card shadow="never" class="chart-card">
                    <template #header>吞吐 RPS</template>
                    <v-chart class="perf-chart" :option="rpsChartOption" autoresize />
                  </el-card>
                </el-col>
              </el-row>
              <el-card shadow="never" class="table-card">
                <template #header>采样摘要（静态）</template>
                <el-table :data="sampleTable" border size="small" stripe>
                  <el-table-column prop="label" label="指标" width="160" />
                  <el-table-column prop="value" label="值" />
                </el-table>
              </el-card>
            </div>
            <el-empty v-else description="暂无报告，请先执行一次压测（模拟）" />
          </el-tab-pane>

          <el-tab-pane label="历史记录" name="history">
            <el-table :data="runs" stripe border size="small" class="hist-table">
              <el-table-column prop="scenarioName" label="场景" min-width="140" show-overflow-tooltip />
              <el-table-column prop="startedAt" label="开始时间" width="160" />
              <el-table-column prop="status" label="状态" width="90">
                <template #default="{ row }">
                  <el-tag :type="statusTag(row.status)" size="small">{{ formatStatus(row.status) }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="rps" label="RPS" width="90" />
              <el-table-column prop="p95" label="P95(ms)" width="90" />
              <el-table-column prop="errorRate" label="错误率%" width="100">
                <template #default="{ row }">{{ row.errorRate.toFixed(2) }}</template>
              </el-table-column>
              <el-table-column label="操作" width="120" fixed="right">
                <template #default="{ row }">
                  <el-button link type="primary" size="small" @click="openRunDetail(row)">详情</el-button>
                  <el-button link size="small" @click="compareWith(row)">对比</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>
        </el-tabs>
      </main>
    </div>

    <!-- 新建 / 编辑场景 -->
    <el-dialog v-model="dlgForm" :title="formMode === 'new' ? '新建场景' : '编辑场景'" width="640px" destroy-on-close>
      <el-form label-width="110px">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" maxlength="80" show-word-limit />
        </el-form-item>
        <el-form-item label="方法">
          <el-select v-model="form.method" style="width: 120px">
            <el-option label="GET" value="GET" />
            <el-option label="POST" value="POST" />
            <el-option label="PUT" value="PUT" />
            <el-option label="DELETE" value="DELETE" />
          </el-select>
        </el-form-item>
        <el-form-item label="URL">
          <el-input v-model="form.url" />
        </el-form-item>
        <el-form-item label="Headers">
          <el-input v-model="form.headersText" type="textarea" :rows="3" class="mono" />
        </el-form-item>
        <el-form-item label="Body">
          <el-input v-model="form.bodyText" type="textarea" :rows="4" class="mono" />
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="12"><el-form-item label="VU"><el-input-number v-model="form.vus" :min="1" style="width: 100%" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="时长(s)"><el-input-number v-model="form.durationSec" :min="1" style="width: 100%" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="爬坡(s)"><el-input-number v-model="form.rampUpSec" :min="0" style="width: 100%" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="思考(ms)"><el-input-number v-model="form.thinkTimeMs" :min="0" style="width: 100%" /></el-form-item></el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="dlgForm = false">取消</el-button>
        <el-button type="primary" @click="confirmForm">确定</el-button>
      </template>
    </el-dialog>

    <!-- 删除 -->
    <el-dialog v-model="dlgDelete" title="删除场景" width="400px">
      <p>确定删除「{{ deleteTarget?.name }}」？</p>
      <template #footer>
        <el-button @click="dlgDelete = false">取消</el-button>
        <el-button type="danger" @click="confirmDelete">删除</el-button>
      </template>
    </el-dialog>

    <!-- 导入 -->
    <el-dialog v-model="dlgImport" title="导入场景 (JSON)" width="640px" destroy-on-close>
      <el-input v-model="importText" type="textarea" :rows="14" class="mono" placeholder="粘贴 JSON" />
      <template #footer>
        <el-button @click="dlgImport = false">取消</el-button>
        <el-button type="primary" @click="doImport">解析并创建</el-button>
      </template>
    </el-dialog>

    <!-- 全局设置 -->
    <el-dialog v-model="dlgGlobal" title="全局设置" width="480px">
      <el-form label-width="120px">
        <el-form-item label="请求超时(ms)">
          <el-input-number v-model="globalSettings.timeoutMs" :min="1000" :max="120000" :step="1000" />
        </el-form-item>
        <el-form-item label="连接超时(ms)">
          <el-input-number v-model="globalSettings.connectTimeoutMs" :min="500" :max="60000" :step="500" />
        </el-form-item>
        <el-form-item label="忽略 TLS 校验">
          <el-switch v-model="globalSettings.insecureTls" />
        </el-form-item>
        <el-form-item label="代理 URL">
          <el-input v-model="globalSettings.proxyUrl" placeholder="可选 http://proxy:8080" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dlgGlobal = false">关闭</el-button>
        <el-button type="primary" @click="saveGlobal">保存（本地）</el-button>
      </template>
    </el-dialog>

    <!-- SLA -->
    <el-dialog v-model="dlgSla" title="SLA / 阈值" width="520px">
      <el-form label-width="140px">
        <el-form-item label="P95 上限 (ms)">
          <el-input-number v-model="sla.p95Max" :min="1" :max="60000" />
        </el-form-item>
        <el-form-item label="错误率上限 (%)">
          <el-input-number v-model="sla.errorRateMax" :min="0" :max="100" :step="0.01" />
        </el-form-item>
        <el-form-item label="最低 RPS">
          <el-input-number v-model="sla.rpsMin" :min="0" :max="1000000" />
        </el-form-item>
      </el-form>
      <el-alert type="info" :closable="false" title="真实判定时由后端任务比对；此处仅保存偏好。" />
      <template #footer>
        <el-button @click="dlgSla = false">关闭</el-button>
        <el-button type="primary" @click="saveSla">保存</el-button>
      </template>
    </el-dialog>

    <!-- 高级运行选项 -->
    <el-dialog v-model="dlgRunAdv" title="高级运行选项" width="480px">
      <el-form label-width="140px">
        <el-form-item label="预热次数">
          <el-input-number v-model="runAdv.warmup" :min="0" :max="1000" />
        </el-form-item>
        <el-form-item label="最大迭代/ VU">
          <el-input-number v-model="runAdv.maxIter" :min="0" :max="10000000" />
        </el-form-item>
        <el-form-item label="DNS 缓存">
          <el-switch v-model="runAdv.dnsCache" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button type="primary" @click="dlgRunAdv = false">确定</el-button>
      </template>
    </el-dialog>

    <!-- 单次运行详情 -->
    <el-dialog v-model="dlgRunDetail" title="运行详情" width="560px">
      <el-descriptions v-if="detailRun" :column="1" border size="small">
        <el-descriptions-item label="场景">{{ detailRun.scenarioName }}</el-descriptions-item>
        <el-descriptions-item label="开始">{{ detailRun.startedAt }}</el-descriptions-item>
        <el-descriptions-item label="结束">{{ detailRun.endedAt }}</el-descriptions-item>
        <el-descriptions-item label="RPS">{{ detailRun.rps }}</el-descriptions-item>
        <el-descriptions-item label="P50/P95/P99">{{ detailRun.p50 }} / {{ detailRun.p95 }} / {{ detailRun.p99 }} ms</el-descriptions-item>
        <el-descriptions-item label="请求总数">{{ detailRun.totalRequests }}（失败 {{ detailRun.failedRequests }}）</el-descriptions-item>
        <el-descriptions-item label="错误率">{{ detailRun.errorRate.toFixed(3) }}%</el-descriptions-item>
      </el-descriptions>
      <template #footer>
        <el-button type="primary" @click="dlgRunDetail = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 对比 -->
    <el-dialog v-model="dlgCompare" title="运行对比（静态）" width="640px">
      <el-descriptions v-if="compareA && compareB" :column="1" border size="small">
        <el-descriptions-item label="A">{{ compareA.scenarioName }} @ {{ compareA.startedAt }} — RPS {{ compareA.rps }}, P95 {{ compareA.p95 }}</el-descriptions-item>
        <el-descriptions-item label="B">{{ compareB.scenarioName }} @ {{ compareB.startedAt }} — RPS {{ compareB.rps }}, P95 {{ compareB.p95 }}</el-descriptions-item>
      </el-descriptions>
      <template #footer>
        <el-button @click="dlgCompare = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 说明 -->
    <el-dialog v-model="dlgHelp" title="性能测试说明" width="520px">
      <ul class="help-list">
        <li>场景配置、执行与报告均为<strong>前端静态演示</strong>，不发起真实压测流量。</li>
        <li>「开始压测」会模拟进度条并在结束后写入一条历史记录。</li>
        <li>图表与表格数据为示例，接入后端后替换为真实时序与聚合指标。</li>
      </ul>
      <template #footer>
        <el-button type="primary" @click="dlgHelp = false">知道了</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { use } from "echarts/core";
import { LineChart } from "echarts/charts";
import { GridComponent, LegendComponent, TooltipComponent } from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import type { ComposeOption } from "echarts/core";
import type { LineSeriesOption } from "echarts/charts";
import VChart from "vue-echarts";
import { MoreFilled, Plus } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { computed, ref } from "vue";
import {
  genId,
  INITIAL_RUNS,
  INITIAL_SCENARIOS,
  mockLatencySeries,
  mockRpsSeries,
  type PerfRunRecord,
  type PerfScenario,
} from "./perf-test/mockData";

use([CanvasRenderer, LineChart, GridComponent, LegendComponent, TooltipComponent]);

const scenarios = ref<PerfScenario[]>(JSON.parse(JSON.stringify(INITIAL_SCENARIOS)));
const runs = ref<PerfRunRecord[]>(JSON.parse(JSON.stringify(INITIAL_RUNS)));
const activeId = ref<string | null>(scenarios.value[0]?.id ?? null);
const mainTab = ref("config");

const activeScenario = computed(() => scenarios.value.find((s) => s.id === activeId.value) ?? null);

const reportRun = ref<PerfRunRecord | null>(runs.value[0] ?? null);
const latencyPts = mockLatencySeries();
const rpsPts = mockRpsSeries();

type LineOpt = ComposeOption<LineSeriesOption>;
const latencyChartOption = computed<LineOpt>(() => ({
  tooltip: { trigger: "axis" },
  grid: { left: 48, right: 16, top: 24, bottom: 32 },
  xAxis: { type: "category", data: latencyPts.map((p) => p.t) },
  yAxis: { type: "value", name: "ms" },
  series: [{ type: "line", smooth: true, data: latencyPts.map((p) => p.v), areaStyle: { opacity: 0.08 } }],
}));

const rpsChartOption = computed<LineOpt>(() => ({
  tooltip: { trigger: "axis" },
  grid: { left: 48, right: 16, top: 24, bottom: 32 },
  xAxis: { type: "category", data: rpsPts.map((p) => p.t) },
  yAxis: { type: "value", name: "RPS" },
  series: [{ type: "line", smooth: true, data: rpsPts.map((p) => p.v), color: "#10b981" }],
}));

const reportCards = computed(() => {
  const r = reportRun.value;
  if (!r) return [];
  return [
    { key: "rps", label: "RPS", value: String(r.rps) },
    { key: "p50", label: "P50 (ms)", value: String(r.p50) },
    { key: "p95", label: "P95 (ms)", value: String(r.p95) },
    { key: "p99", label: "P99 (ms)", value: String(r.p99) },
    { key: "err", label: "错误率", value: `${r.errorRate.toFixed(2)}%` },
    { key: "tot", label: "总请求", value: String(r.totalRequests) },
  ];
});

const sampleTable = computed(() => {
  const r = reportRun.value;
  if (!r) return [];
  return [
    { label: "迭代次数（示意）", value: "12,480" },
    { label: "网络吞吐（示意）", value: "38.2 MB/s" },
    { label: "平均体大小", value: "412 B" },
    { label: "TCP 连接复用", value: "是（静态）" },
  ];
});

const running = ref(false);
const runProgress = ref(0);
const lastRunMessage = ref("");

const dlgForm = ref(false);
const formMode = ref<"new" | "edit">("new");
const form = ref({
  name: "",
  method: "GET",
  url: "",
  headersText: "{}",
  bodyText: "",
  vus: 10,
  durationSec: 60,
  rampUpSec: 0,
  thinkTimeMs: 0,
});
const editId = ref<string | null>(null);

const dlgDelete = ref(false);
const deleteTarget = ref<PerfScenario | null>(null);

const dlgImport = ref(false);
const importText = ref("");

const dlgGlobal = ref(false);
const globalSettings = ref({
  timeoutMs: 30000,
  connectTimeoutMs: 10000,
  insecureTls: false,
  proxyUrl: "",
});

const dlgSla = ref(false);
const sla = ref({ p95Max: 300, errorRateMax: 1, rpsMin: 500 });

const dlgRunAdv = ref(false);
const runAdv = ref({ warmup: 2, maxIter: 0, dnsCache: true });

const dlgRunDetail = ref(false);
const detailRun = ref<PerfRunRecord | null>(null);

const dlgCompare = ref(false);
const compareA = ref<PerfRunRecord | null>(null);
const compareB = ref<PerfRunRecord | null>(null);

const dlgHelp = ref(false);

let progressTimer: ReturnType<typeof setInterval> | null = null;

function formatNow() {
  const d = new Date();
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
}

function statusTag(s: string): "success" | "warning" | "danger" | "info" {
  if (s === "success") return "success";
  if (s === "failed") return "danger";
  if (s === "stopped") return "warning";
  return "info";
}

function formatStatus(s: string) {
  const m: Record<string, string> = { success: "成功", failed: "失败", stopped: "已停止" };
  return m[s] ?? s;
}

function openNewScenario() {
  formMode.value = "new";
  editId.value = null;
  form.value = {
    name: "新场景",
    method: "GET",
    url: "https://api.example.com/",
    headersText: "{}",
    bodyText: "",
    vus: 10,
    durationSec: 60,
    rampUpSec: 5,
    thinkTimeMs: 0,
  };
  dlgForm.value = true;
}

function onScenarioMenu(cmd: string, s: PerfScenario) {
  if (cmd === "edit") {
    formMode.value = "edit";
    editId.value = s.id;
    form.value = {
      name: s.name,
      method: s.method,
      url: s.url,
      headersText: s.headersText,
      bodyText: s.bodyText,
      vus: s.vus,
      durationSec: s.durationSec,
      rampUpSec: s.rampUpSec,
      thinkTimeMs: s.thinkTimeMs,
    };
    dlgForm.value = true;
  } else if (cmd === "dup") {
    const ns: PerfScenario = {
      ...s,
      id: genId("s"),
      name: `${s.name} 副本`,
      updatedAt: formatNow().slice(0, 16),
    };
    scenarios.value.unshift(ns);
    activeId.value = ns.id;
    ElMessage.success("已复制");
  } else if (cmd === "del") {
    deleteTarget.value = s;
    dlgDelete.value = true;
  }
}

function confirmForm() {
  const f = form.value;
  if (!f.name.trim() || !f.url.trim()) {
    ElMessage.warning("请填写名称与 URL");
    return;
  }
  if (formMode.value === "new") {
    const ns: PerfScenario = {
      id: genId("s"),
      name: f.name.trim(),
      method: f.method,
      url: f.url.trim(),
      headersText: f.headersText,
      bodyText: f.bodyText,
      vus: f.vus,
      durationSec: f.durationSec,
      rampUpSec: f.rampUpSec,
      thinkTimeMs: f.thinkTimeMs,
      updatedAt: formatNow().slice(0, 16),
    };
    scenarios.value.unshift(ns);
    activeId.value = ns.id;
  } else if (editId.value) {
    const t = scenarios.value.find((x) => x.id === editId.value);
    if (t) {
      Object.assign(t, {
        name: f.name.trim(),
        method: f.method,
        url: f.url.trim(),
        headersText: f.headersText,
        bodyText: f.bodyText,
        vus: f.vus,
        durationSec: f.durationSec,
        rampUpSec: f.rampUpSec,
        thinkTimeMs: f.thinkTimeMs,
        updatedAt: formatNow().slice(0, 16),
      });
    }
  }
  dlgForm.value = false;
  ElMessage.success("已保存");
}

function confirmDelete() {
  const t = deleteTarget.value;
  if (!t) return;
  scenarios.value = scenarios.value.filter((x) => x.id !== t.id);
  if (activeId.value === t.id) activeId.value = scenarios.value[0]?.id ?? null;
  dlgDelete.value = false;
  deleteTarget.value = null;
  ElMessage.success("已删除");
}

function saveScenarioLocal() {
  const s = activeScenario.value;
  if (!s) return;
  s.updatedAt = formatNow().slice(0, 16);
  ElMessage.success("配置已更新（本地）");
}

function doImport() {
  try {
    const o = JSON.parse(importText.value) as Partial<PerfScenario>;
    if (!o.name || !o.url) throw new Error("需包含 name、url");
    const ns: PerfScenario = {
      id: genId("s"),
      name: String(o.name),
      method: (o.method as string) || "GET",
      url: String(o.url),
      headersText: typeof o.headersText === "string" ? o.headersText : "{}",
      bodyText: typeof o.bodyText === "string" ? o.bodyText : "",
      vus: Number(o.vus) || 10,
      durationSec: Number(o.durationSec) || 60,
      rampUpSec: Number(o.rampUpSec) || 0,
      thinkTimeMs: Number(o.thinkTimeMs) || 0,
      updatedAt: formatNow().slice(0, 16),
    };
    scenarios.value.unshift(ns);
    activeId.value = ns.id;
    dlgImport.value = false;
    importText.value = "";
    ElMessage.success("导入成功");
  } catch {
    ElMessage.error("JSON 解析失败或字段不全");
  }
}

function exportScenario() {
  const s = activeScenario.value;
  if (!s) return;
  const text = JSON.stringify(s, null, 2);
  navigator.clipboard.writeText(text);
  ElMessage.success("已复制场景 JSON 到剪贴板");
}

function saveGlobal() {
  dlgGlobal.value = false;
  ElMessage.success("全局设置已记录（前端）");
}

function saveSla() {
  dlgSla.value = false;
  ElMessage.success("SLA 已保存（前端）");
}

function startRun() {
  if (!activeScenario.value) return;
  running.value = true;
  runProgress.value = 0;
  lastRunMessage.value = "压测进行中（模拟）…";
  progressTimer = setInterval(() => {
    runProgress.value = Math.min(100, runProgress.value + 10);
    if (runProgress.value >= 100 && progressTimer) {
      clearInterval(progressTimer);
      progressTimer = null;
      running.value = false;
      const sc = activeScenario.value!;
      const rec: PerfRunRecord = {
        id: genId("r"),
        scenarioId: sc.id,
        scenarioName: sc.name,
        startedAt: formatNow(),
        endedAt: formatNow(),
        status: "success",
        durationSec: sc.durationSec,
        rps: 600 + Math.floor(Math.random() * 200),
        p50: 25 + Math.floor(Math.random() * 20),
        p95: 120 + Math.floor(Math.random() * 80),
        p99: 280 + Math.floor(Math.random() * 100),
        errorRate: Math.random() * 0.5,
        totalRequests: sc.vus * sc.durationSec * 12,
        failedRequests: Math.floor(Math.random() * 50),
      };
      runs.value.unshift(rec);
      reportRun.value = rec;
      lastRunMessage.value = `完成：${rec.scenarioName}，RPS≈${rec.rps}（模拟）`;
      mainTab.value = "report";
      ElMessage.success("模拟压测完成，已生成报告与历史");
    }
  }, 200);
}

function stopRun() {
  if (progressTimer) {
    clearInterval(progressTimer);
    progressTimer = null;
  }
  running.value = false;
  lastRunMessage.value = "已停止（本地）";
  ElMessage.info("已停止");
}

function openRunDetail(row: PerfRunRecord) {
  detailRun.value = row;
  dlgRunDetail.value = true;
}

function compareWith(row: PerfRunRecord) {
  compareA.value = runs.value.find((r) => r.id !== row.id) ?? null;
  compareB.value = row;
  dlgCompare.value = true;
}
</script>

<style scoped>
.mr4 {
  margin-right: 4px;
}
.mb12 {
  margin-bottom: 12px;
}
.mono :deep(textarea) {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12px;
}

.perf-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 0;
  overflow: auto;
  padding: 20px;
  background: #f5f7fb;
}
.perf-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}
.perf-head__title {
  display: flex;
  align-items: center;
  gap: 10px;
}
.perf-head__title h1 {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  color: #0f172a;
}
.perf-head__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.perf-body {
  flex: 1;
  min-height: 480px;
  display: flex;
  gap: 16px;
  min-width: 0;
}
.perf-aside {
  width: 260px;
  flex-shrink: 0;
  background: #fff;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.aside-title {
  padding: 12px 14px;
  font-weight: 600;
  font-size: 14px;
  border-bottom: 1px solid #e5e7eb;
}
.aside-scroll {
  flex: 1;
  min-height: 0;
  padding: 8px;
}
.scenario-item {
  position: relative;
  padding: 10px 32px 10px 10px;
  border-radius: 8px;
  cursor: pointer;
  margin-bottom: 6px;
  border: 1px solid transparent;
}
.scenario-item:hover {
  background: #f1f5f9;
}
.scenario-item.is-active {
  background: #eff6ff;
  border-color: #bfdbfe;
}
.scenario-item__name {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: #0f172a;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.scenario-item__meta {
  display: block;
  font-size: 11px;
  color: #94a3b8;
  margin-top: 4px;
}
.scenario-item__more {
  position: absolute;
  right: 6px;
  top: 50%;
  transform: translateY(-50%);
  color: #64748b;
  padding: 4px;
}

.perf-main {
  flex: 1;
  min-width: 0;
  background: #fff;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.perf-tabs {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  border: none;
  box-shadow: none;
}
.perf-tabs :deep(.el-tabs__content) {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 16px;
}
.perf-form {
  max-width: 960px;
}

.run-panel {
  max-width: 720px;
}
.run-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}
.run-progress {
  margin: 12px 0;
}
.run-msg {
  font-size: 13px;
  color: #64748b;
}

.stat-row {
  margin-bottom: 16px;
}
.stat-card {
  border-radius: 10px;
}
.stat-label {
  font-size: 12px;
  color: #64748b;
}
.stat-value {
  font-size: 22px;
  font-weight: 700;
  color: #0f172a;
  margin-top: 4px;
}
.chart-row {
  margin-bottom: 16px;
}
.chart-card :deep(.el-card__header) {
  padding: 10px 14px;
  font-size: 14px;
  font-weight: 600;
}
.perf-chart {
  height: 260px;
  width: 100%;
}
.table-card :deep(.el-card__header) {
  font-size: 14px;
  font-weight: 600;
}

.hist-table {
  width: 100%;
}

.help-list {
  margin: 0;
  padding-left: 20px;
  line-height: 1.7;
  font-size: 14px;
  color: #475569;
}

@media (max-width: 900px) {
  .perf-body {
    flex-direction: column;
  }
  .perf-aside {
    width: 100%;
    max-height: 220px;
  }
}
</style>
