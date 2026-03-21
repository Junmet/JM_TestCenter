<!--
  用例生成页 · 设计说明
  ---------------------
  1. 上传需求文件（支持 txt / md 等）
  2. AI 生成用例（当前为前端模拟数据展示）
  3. 勾选确定用例后，支持导出：MD / TXT / XLSX
-->
<template>
  <div class="page-view case-gen case-gen--fill">
    <header class="page-header">
      <h1 class="title">用例生成</h1>
      <p class="subtitle">上传需求文件，由 AI 生成测试用例；确定后可导出为 MD、TXT、XLSX</p>
    </header>

    <!-- 上传需求文件 -->
    <section class="panel upload-panel">
      <h2 class="panel-title">上传需求文件</h2>
      <div
        class="upload-zone"
        :class="{ 'upload-zone--active': isDragging, 'upload-zone--has-file': uploadedFile }"
        @click="openFilePicker"
        @dragover.prevent="isDragging = true"
        @dragleave.prevent="isDragging = false"
        @drop.prevent="onDrop"
      >
        <input
          ref="fileInputRef"
          type="file"
          accept=".txt,.md,.markdown,.docx,.pdf"
          class="upload-input"
          @change="onFileSelect"
        />
        <template v-if="!uploadedFile">
          <p class="upload-hint">拖拽文件到此处，或点击选择</p>
          <p class="upload-types">支持 .txt、.md、.markdown、.docx、.pdf</p>
        </template>
        <template v-else>
          <p class="upload-name">{{ uploadedFile.name }}</p>
          <button type="button" class="btn-link" @click.stop="clearFile">移除</button>
        </template>
      </div>
      <div class="upload-actions">
        <div class="case-count-config">
          <label class="count-label" for="caseCountInput">目标用例数</label>
          <el-input-number
            id="caseCountInput"
            v-model="targetCaseCount"
            :min="10"
            :max="200"
            class="count-input"
            @change="onTargetCaseCountChange"
          />
          <span class="count-tip">建议 30-200；若需求不足会自动少于目标值（最多 200）</span>
          <el-button type="primary" :disabled="!uploadedFile || generating" :loading="generating" @click="generateByApi">
            {{ generating ? "生成中..." : generated.length ? "重新生成" : "生成用例" }}
          </el-button>
        </div>
      </div>
      <div v-if="generating" class="loading-box">
        <span class="loading-dot" />
        <div class="loading-text">
          <div>AI 正在分析需求并生成用例，请耐心等待...</div>
          <div class="loading-sub">已耗时：{{ formatDuration(loadingElapsedSec * 1000) }}</div>
        </div>
      </div>
      <div v-else-if="lastGenerateCostMs !== null" class="success-box">
        生成完成，用时 {{ formatMinutes(lastGenerateCostMs) }} 分钟（{{ formatDuration(lastGenerateCostMs) }}）
      </div>
      <p v-if="errorText" class="error-text">{{ errorText }}</p>
    </section>

    <!-- 生成历史 -->
    <section class="panel history-panel">
      <div class="history-header">
        <h2 class="panel-title">生成历史</h2>
        <el-button @click="loadHistories(historyPage)">刷新历史</el-button>
      </div>
      <div v-if="histories.length === 0" class="history-empty">暂无历史记录</div>
      <div v-else class="list-table-wrap">
        <div class="list-table-scroll">
          <el-table
            :data="histories"
            stripe
            size="small"
            class="list-table list-table--first-left history-list"
            table-layout="fixed"
            height="100%"
            :row-class-name="historyRowClassName"
          >
          <el-table-column label="文件名" show-overflow-tooltip>
            <template #default="{ row }">
              <el-link
                type="primary"
                underline="never"
                :disabled="loadingHistory"
                :class="{ 'history-link--active': selectedHistoryId === row.requirement_id }"
                @click="loadHistoryCases(row.requirement_id)"
              >
                {{ row.source_name }}
              </el-link>
            </template>
          </el-table-column>
          <el-table-column label="状态">
            <template #default="{ row }">
              <el-tag :type="historyStatusTagType(row.status)" effect="light">
                {{ formatHistoryStatus(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="case_count" label="总用例" />
          <el-table-column prop="confirmed_count" label="已确定" />
          <el-table-column label="生成时间" show-overflow-tooltip>
            <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
          </el-table-column>
          <el-table-column label="操作">
            <template #default="{ row }">
              <el-button type="danger" text @click="deleteHistory(row.requirement_id)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
        </div>
        <div class="history-pagination">
          <el-pagination
            background
            layout="total, sizes, prev, pager, next, jumper"
            :total="historyTotal"
            :page-size="historyPageSize"
            :current-page="historyPage"
            :page-sizes="[5, 8, 10, 20, 30, 50]"
            @current-change="onHistoryPageChange"
            @size-change="onHistoryPageSizeChange"
          />
        </div>
      </div>
    </section>

    <el-drawer
      v-model="resultDrawerVisible"
      :title="resultDrawerTitle"
      size="82%"
      :destroy-on-close="false"
      class="result-drawer"
    >
      <div v-if="generated.length > 0" class="result-panel">
        <div class="result-header">
          <h2 class="panel-title">测试用例</h2>
          <div class="result-actions">
            <el-checkbox :model-value="allSelected" @change="toggleAll">全选</el-checkbox>
            <el-button @click="confirmSelected">确定用例</el-button>
            <div ref="exportWrapRef" class="export-wrap">
              <el-button type="primary" plain :disabled="confirmed.length === 0" @click.stop="showExport = !showExport">
                导出用例
              </el-button>
              <div v-if="showExport" class="export-menu" @click.stop>
                <el-button text @click="exportAs('md')">导出为文档（.md）</el-button>
                <el-button text @click="exportAs('txt')">导出为纯文本（.txt）</el-button>
                <el-button text @click="exportAs('xlsx')">导出为表格（.xlsx）</el-button>
              </div>
            </div>
            <el-button :disabled="generated.length === 0" @click="openAddToCasesPanel">
              添加到用例管理
            </el-button>
          </div>
        </div>
        <div class="list-table-wrap">
          <div class="list-table-scroll">
            <el-table
              :data="pagedGenerated"
              stripe
              size="small"
              class="list-table list-table--check-left"
              table-layout="fixed"
              height="100%"
            >
              <el-table-column label="" width="56">
                <template #header>
                  <el-checkbox :model-value="allSelected" @change="toggleAll" />
                </template>
                <template #default="{ row }">
                  <el-checkbox :model-value="selectedIds.has(row.id)" :disabled="row.confirmed" @change="toggleRow(row.id)" />
                </template>
              </el-table-column>
              <el-table-column prop="case_code" label="用例编号" show-overflow-tooltip />
              <el-table-column prop="priority" label="优先级" show-overflow-tooltip />
              <el-table-column prop="module" label="模块" show-overflow-tooltip />
              <el-table-column prop="name" label="用例名称" show-overflow-tooltip />
              <el-table-column prop="precondition" label="前置条件" show-overflow-tooltip />
              <el-table-column prop="steps_text" label="步骤" show-overflow-tooltip />
              <el-table-column prop="expected_text" label="预期结果" show-overflow-tooltip />
            </el-table>
          </div>
          <div class="drawer-pagination">
            <el-pagination
              background
              layout="total, sizes, prev, pager, next, jumper"
              :total="generated.length"
              :page-size="drawerPageSize"
              :current-page="drawerPage"
              :page-sizes="[5, 10, 20, 30, 50, 100]"
              @current-change="onDrawerPageChange"
              @size-change="onDrawerPageSizeChange"
            />
          </div>
        </div>
        <footer class="table-footer">
          已确定 {{ confirmed.length }} 条，当前展示 {{ generated.length }} 条
        </footer>
        <div class="download-bar">
          <span class="download-title">下载导出：</span>
          <el-button size="small" :disabled="generated.length === 0" @click="exportAs('md')">
            文档（.md）
          </el-button>
          <el-button size="small" :disabled="generated.length === 0" @click="exportAs('txt')">
            纯文本
          </el-button>
          <el-button size="small" :disabled="generated.length === 0" @click="exportAs('xlsx')">
            表格（.xlsx）
          </el-button>
        </div>
        <section v-if="showAddPanel" class="add-panel">
          <h3 class="add-title">添加到用例管理</h3>
          <div class="add-row">
            <label class="add-label">需求编号模式</label>
            <el-radio-group v-model="reqCodeMode">
              <el-radio label="auto">自动生成</el-radio>
              <el-radio label="manual">手动输入</el-radio>
            </el-radio-group>
            <el-input
              v-model.trim="manualReqCode"
              :disabled="reqCodeMode !== 'manual'"
              class="add-input"
              placeholder="例如 REQ-1208"
            />
          </div>
          <div class="add-row">
            <label class="add-label">需求标题</label>
            <el-input v-model.trim="editableReqTitle" class="add-input add-input--wide" placeholder="请输入需求标题" />
          </div>
          <div class="add-row">
            <label class="add-label">说明</label>
            <span class="add-tip">标题默认取需求文档名，可直接修改</span>
          </div>
          <div class="add-row">
            <label class="add-label">添加后跳转</label>
            <el-checkbox v-model="addToCasesJump">跳转到用例管理页</el-checkbox>
          </div>
          <div class="add-actions">
            <el-button @click="showAddPanel = false">取消</el-button>
            <el-button type="primary" @click="addToCaseManagement">确认添加</el-button>
          </div>
          <p v-if="addSuccessText" class="success-box">{{ addSuccessText }}</p>
        </section>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from "vue";
import {
  type CaseGenerationResponse,
  confirmCasesApi,
  deleteGenerationHistoryApi,
  getCasesByRequirementApi,
  getGenerationHistoriesApi,
  type CaseGenerationHistoryItem,
  type GeneratedCase
} from "../api/caseGen";
import { checkRequirementCodeExistsApi, createRequirementApi } from "../api/caseManagement";
import { useCaseGenStore } from "../stores/caseGen";
import { useRouter } from "vue-router";
import { ElMessageBox } from "element-plus";

const fileInputRef = ref<HTMLInputElement | null>(null);
const uploadedFile = ref<File | null>(null);
const isDragging = ref(false);
const showExport = ref(false);
const exportWrapRef = ref<HTMLElement | null>(null);
const caseGenStore = useCaseGenStore();
const generating = computed(() => caseGenStore.generating);
const loadingHistory = ref(false);
const errorText = ref("");
const requirementId = ref<number | null>(null);
const histories = ref<CaseGenerationHistoryItem[]>([]);
const historyTotal = ref(0);
const historyPage = ref(1);
const historyPageSize = ref(8);
const lastGenerateCostMs = ref<number | null>(null);
const loadingElapsedSec = ref(0);
const targetCaseCount = ref<number | undefined>(80);
let loadingTimer: ReturnType<typeof setInterval> | null = null;
const showAddPanel = ref(false);
const reqCodeMode = ref<"auto" | "manual">("auto");
const manualReqCode = ref("");
const editableReqTitle = ref("");
const addSuccessText = ref("");
const addToCasesJump = ref(true);
const selectedHistoryId = ref<number | null>(null);
/** 最近一次成功生成的需求 ID，用于历史列表行高亮 */
const highlightRequirementId = ref<number | null>(null);
const resultDrawerVisible = ref(false);
const resultDrawerTitle = ref("生成结果");
const drawerPage = ref(1);
const drawerPageSize = ref(10);
const router = useRouter();

function onDocClick(e: MouseEvent) {
  if (showExport.value && exportWrapRef.value && !exportWrapRef.value.contains(e.target as Node)) {
    showExport.value = false;
  }
}
onMounted(() => document.addEventListener("click", onDocClick));
onUnmounted(() => document.removeEventListener("click", onDocClick));
onMounted(async () => {
  await loadHistories(1);
  if (caseGenStore.generating && caseGenStore.startedAt) {
    startLoadingCounter(caseGenStore.startedAt);
  }
  if (!generated.value.length && caseGenStore.latestResult) {
    applyGenerateResult(caseGenStore.latestResult, false);
    lastGenerateCostMs.value = caseGenStore.lastDurationMs;
    highlightRequirementId.value = caseGenStore.latestResult.requirement_id;
  }
  if (caseGenStore.latestError) {
    errorText.value = caseGenStore.latestError;
  }
});
onUnmounted(() => {
  if (loadingTimer) {
    clearInterval(loadingTimer);
    loadingTimer = null;
  }
});

type UICase = GeneratedCase & {
  name: string;
  precondition: string;
  steps_text: string;
  expected_text: string;
};

const generated = ref<UICase[]>([]);
const selectedIds = ref<Set<number>>(new Set());

const allSelected = computed(() => {
  const selectable = generated.value.filter((r) => !r.confirmed);
  if (selectable.length === 0) return false;
  return selectable.every((r) => selectedIds.value.has(r.id));
});

const confirmed = computed(() => generated.value.filter((r) => r.confirmed));
const pagedGenerated = computed(() => {
  const start = (drawerPage.value - 1) * drawerPageSize.value;
  return generated.value.slice(start, start + drawerPageSize.value);
});

function onFileSelect(e: Event) {
  const input = e.target as HTMLInputElement;
  const file = input.files?.[0];
  if (file) {
    uploadedFile.value = file;
    errorText.value = "";
  }
}

function onDrop(e: DragEvent) {
  isDragging.value = false;
  const file = e.dataTransfer?.files?.[0];
  if (file) {
    uploadedFile.value = file;
    errorText.value = "";
  }
}

function clearFile() {
  uploadedFile.value = null;
  if (fileInputRef.value) fileInputRef.value.value = "";
}

function openFilePicker() {
  fileInputRef.value?.click();
}

function toUIRows(rows: GeneratedCase[]): UICase[] {
  return rows.map((r) => ({
    ...r,
    name: r.title,
    precondition: r.preconditions,
    steps_text: (r.steps || []).join("；"),
    expected_text: (r.expected || []).join("；")
  }));
}

function defaultReqTitleFromFileName() {
  const name = uploadedFile.value?.name || "新需求";
  const idx = name.lastIndexOf(".");
  return idx > 0 ? name.slice(0, idx) : name;
}

/** 超过 200 时按需求清空输入 */
function onTargetCaseCountChange(val: number | undefined) {
  if (val !== undefined && val !== null && val > 200) {
    targetCaseCount.value = undefined;
  }
}

watch(targetCaseCount, (v) => {
  if (typeof v === "number" && v > 200) {
    targetCaseCount.value = undefined;
  }
});

function resetDrawerPagination() {
  drawerPage.value = 1;
}

function historyRowClassName({ row }: { row: CaseGenerationHistoryItem }) {
  if (highlightRequirementId.value !== null && row.requirement_id === highlightRequirementId.value) {
    return "history-row-highlight";
  }
  return "";
}

function applyGenerateResult(data: CaseGenerationResponse, openDrawer = true) {
  requirementId.value = data.requirement_id;
  generated.value = toUIRows(data.cases);
  resetDrawerPagination();
  selectedIds.value = new Set(generated.value.filter((r) => !r.confirmed).map((r) => r.id));
  editableReqTitle.value = defaultReqTitleFromFileName();
  showAddPanel.value = false;
  addSuccessText.value = "";
  resultDrawerTitle.value = `生成结果 - ${data.source_name || "当前文件"}`;
  if (openDrawer) {
    resultDrawerVisible.value = true;
  }
}

async function generateByApi() {
  if (!uploadedFile.value || caseGenStore.generating) return;
  caseGenStore.clearLatestResult();
  errorText.value = "";
  const normalizedTarget = Math.max(10, Math.min(Number(targetCaseCount.value) || 30, 200));
  targetCaseCount.value = normalizedTarget;
  const adaptiveBatchSize = normalizedTarget >= 120 ? 20 : normalizedTarget >= 60 ? 15 : 10;
  await caseGenStore.startGenerate(uploadedFile.value, {
    maxCases: normalizedTarget,
    batchSize: adaptiveBatchSize
  });
}

function openAddToCasesPanel() {
  if (generated.value.length === 0) return;
  showAddPanel.value = true;
  addSuccessText.value = "";
  manualReqCode.value = "";
  reqCodeMode.value = "auto";
  if (!editableReqTitle.value) {
    editableReqTitle.value = defaultReqTitleFromFileName();
  }
}

function makeAutoReqCode() {
  const d = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  return `REQ-${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}${pad(d.getHours())}${pad(d.getMinutes())}${pad(
    d.getSeconds()
  )}`;
}

async function addToCaseManagement() {
  if (generated.value.length === 0) return;
  const code = reqCodeMode.value === "manual" ? manualReqCode.value.trim() : makeAutoReqCode();
  if (!code) {
    addSuccessText.value = "需求编号不能为空";
    return;
  }
  const title = editableReqTitle.value.trim() || defaultReqTitleFromFileName();
  try {
    const exists = await checkRequirementCodeExistsApi(code);
    if (exists.exists) {
      addSuccessText.value = "需求编号已存在，请修改后重试";
      return;
    }
    await createRequirementApi({
      code,
      title,
      owner: "当前用户",
      priority: "p1",
      cases: generated.value.map((r) => ({
        code: r.case_code,
        name: r.name,
        priorityText: r.priority || "P1",
        stepsText: r.steps_text || ""
      }))
    });
    addSuccessText.value = `已添加到用例管理：${code}`;
    showAddPanel.value = false;
    if (addToCasesJump.value) {
      await router.push("/cases");
    }
  } catch (err: any) {
    addSuccessText.value = err?.response?.data?.detail || "添加失败，请稍后重试";
  }
}

async function loadHistories(page = historyPage.value) {
  try {
    const safePage = Math.max(1, page);
    const data = await getGenerationHistoriesApi(safePage, historyPageSize.value);
    histories.value = data.items || [];
    historyTotal.value = data.total || 0;
    historyPage.value = data.page || safePage;
  } catch {
    // ignore history loading error for page usability
  }
}

async function onHistoryPageChange(page: number) {
  await loadHistories(page);
}

async function onHistoryPageSizeChange(size: number) {
  historyPageSize.value = size;
  historyPage.value = 1;
  await loadHistories(1);
}

async function deleteHistory(id: number) {
  try {
    await ElMessageBox.confirm(
      "确认删除这条生成历史吗？删除后会同时删除对应生成用例，且不可恢复。",
      "删除确认",
      {
        confirmButtonText: "删除",
        cancelButtonText: "取消",
        type: "warning",
        confirmButtonClass: "el-button--danger"
      }
    );
    await deleteGenerationHistoryApi(id);
    if (highlightRequirementId.value === id) {
      highlightRequirementId.value = null;
    }
    if (selectedHistoryId.value === id) {
      selectedHistoryId.value = null;
      requirementId.value = null;
      generated.value = [];
      selectedIds.value = new Set();
    }
    const totalAfterDelete = Math.max(0, historyTotal.value - 1);
    const maxPage = Math.max(1, Math.ceil(totalAfterDelete / historyPageSize.value));
    const targetPage = Math.min(historyPage.value, maxPage);
    await loadHistories(targetPage);
  } catch (err: any) {
    if (err === "cancel" || err === "close") return;
    errorText.value = err?.response?.data?.detail || "删除历史失败";
  }
}

async function loadHistoryCases(id: number, forceReload = false) {
  if (loadingHistory.value) return;
  if (!forceReload && selectedHistoryId.value === id && generated.value.length > 0) {
    resultDrawerVisible.value = true;
    return;
  }
  loadingHistory.value = true;
  errorText.value = "";
  try {
    const data = await getCasesByRequirementApi(id);
    const historyItem = histories.value.find((h) => h.requirement_id === id);
    selectedHistoryId.value = id;
    requirementId.value = data.requirement_id;
    generated.value = toUIRows(data.cases);
    resetDrawerPagination();
    selectedIds.value = new Set(generated.value.filter((r) => !r.confirmed).map((r) => r.id));
    resultDrawerTitle.value = `历史详情 - ${historyItem?.source_name || data.source_name || id}`;
    resultDrawerVisible.value = true;
  } catch (err: any) {
    errorText.value = err?.response?.data?.detail || "加载历史详情失败";
  } finally {
    loadingHistory.value = false;
  }
}

function toggleAll() {
  const selectable = generated.value.filter((r) => !r.confirmed);
  if (allSelected.value) {
    selectable.forEach((r) => selectedIds.value.delete(r.id));
  } else {
    selectable.forEach((r) => selectedIds.value.add(r.id));
  }
  selectedIds.value = new Set(selectedIds.value);
}

function onDrawerPageChange(page: number) {
  drawerPage.value = page;
}

function onDrawerPageSizeChange(size: number) {
  drawerPageSize.value = size;
  drawerPage.value = 1;
}

function toggleRow(id: number) {
  const row = generated.value.find((r) => r.id === id);
  if (row?.confirmed) return;
  if (selectedIds.value.has(id)) selectedIds.value.delete(id);
  else selectedIds.value.add(id);
  selectedIds.value = new Set(selectedIds.value);
}

async function confirmSelected() {
  if (!requirementId.value) return;
  const ids = [...selectedIds.value];
  if (ids.length === 0) return;
  try {
    await confirmCasesApi(requirementId.value, ids);
    generated.value.forEach((r) => {
      if (selectedIds.value.has(r.id)) r.confirmed = true;
    });
    selectedIds.value = new Set();
  } catch (err: any) {
    errorText.value = err?.response?.data?.detail || "确定用例失败";
  }
}

function getExportList(): UICase[] {
  return confirmed.value.length > 0 ? confirmed.value : generated.value;
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
  showExport.value = false;
}

function formatTime(v: string) {
  if (!v) return "-";
  const d = new Date(v);
  if (Number.isNaN(d.getTime())) return v;
  return d.toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false
  });
}

/** 生成历史状态（接口为英文枚举，界面展示中文） */
function formatHistoryStatus(status: string): string {
  const map: Record<string, string> = {
    generated: "已生成",
    failed: "失败"
  };
  return map[status] ?? "未知";
}

function historyStatusTagType(status: string): "success" | "danger" | "info" | "warning" {
  if (status === "generated") return "success";
  if (status === "failed") return "danger";
  return "info";
}

function startLoadingCounter(startAtMs?: number) {
  loadingElapsedSec.value = startAtMs ? Math.max(0, Math.floor((Date.now() - startAtMs) / 1000)) : 0;
  if (loadingTimer) {
    clearInterval(loadingTimer);
  }
  loadingTimer = setInterval(() => {
    loadingElapsedSec.value += 1;
  }, 1000);
}

function stopLoadingCounter() {
  if (loadingTimer) {
    clearInterval(loadingTimer);
    loadingTimer = null;
  }
}

watch(
  () => caseGenStore.generating,
  (isGenerating) => {
    if (isGenerating) {
      startLoadingCounter(caseGenStore.startedAt || Date.now());
      return;
    }
    stopLoadingCounter();
    if (caseGenStore.latestResult) {
      lastGenerateCostMs.value = caseGenStore.lastDurationMs;
      applyGenerateResult(caseGenStore.latestResult, false);
      highlightRequirementId.value = caseGenStore.latestResult.requirement_id;
      void loadHistories(1);
      return;
    }
    if (caseGenStore.latestError) {
      errorText.value = caseGenStore.latestError;
      lastGenerateCostMs.value = null;
    }
  }
);

function formatDuration(ms: number) {
  const totalSec = Math.max(0, Math.floor(ms / 1000));
  const m = Math.floor(totalSec / 60);
  const s = totalSec % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

function formatMinutes(ms: number) {
  return (ms / 60000).toFixed(2);
}

function exportAs(format: "md" | "txt" | "xlsx") {
  const list = getExportList();
  const baseName = "用例导出";

  if (format === "md") {
    const lines = list.map(
      (r, i) =>
        `## ${i + 1}. ${r.name}\n- **编号**: ${r.case_code}\n- **优先级**: ${r.priority}\n- **模块**: ${r.module}\n- **前置**: ${r.precondition}\n- **步骤**: ${r.steps_text}\n- **预期**: ${r.expected_text}\n`
    );
    const md = "# 测试用例\n\n" + lines.join("\n");
    downloadBlob(new Blob([md], { type: "text/markdown;charset=utf-8" }), `${baseName}.md`);
    return;
  }
  if (format === "txt") {
    const lines = list.map(
      (r, i) =>
        `${i + 1}. ${r.name}\n编号: ${r.case_code}\n优先级: ${r.priority}\n模块: ${r.module}\n前置: ${r.precondition}\n步骤: ${r.steps_text}\n预期: ${r.expected_text}\n`
    );
    const txt = "测试用例\n\n" + lines.join("\n");
    downloadBlob(new Blob([txt], { type: "text/plain;charset=utf-8" }), `${baseName}.txt`);
    return;
  }
  if (format === "xlsx") {
    import("xlsx").then((XLSX) => {
      const ws = XLSX.utils.json_to_sheet(
        list.map((r) => ({
          用例编号: r.case_code,
          优先级: r.priority,
          模块: r.module,
          用例名称: r.name,
          前置条件: r.precondition,
          步骤: r.steps_text,
          预期结果: r.expected_text
        }))
      );
      const wb = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(wb, ws, "用例");
      XLSX.writeFile(wb, `${baseName}.xlsx`);
    });
    showExport.value = false;
    return;
  }
}
</script>

<style scoped>
/* 顶栏 56 + main 上下 padding 40 + page-view 上下 padding 48 */
.case-gen.case-gen--fill {
  height: calc(100vh - 144px);
  max-height: calc(100vh - 144px);
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  gap: 16px;
}
.case-gen .upload-panel {
  flex-shrink: 0;
}
.page-header {
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

.panel {
  background: #fff;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  padding: 20px;
}
.panel-title {
  margin: 0 0 16px;
  font-size: 15px;
  font-weight: 600;
  color: #0f172a;
}
.history-header {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}
.history-header .panel-title {
  margin: 0;
}
.history-panel {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.history-empty {
  flex: 1;
  min-height: 120px;
  display: flex;
  align-items: center;
  color: #64748b;
  font-size: 13px;
}
.history-list :deep(tr.history-row-highlight) {
  background: #eef2ff !important;
}
.history-list :deep(tr.history-row-highlight:hover > td) {
  background: #e0e7ff !important;
}
.history-link--active {
  font-weight: 700;
}
.history-pagination {
  flex-shrink: 0;
  display: flex;
  justify-content: flex-end;
  flex-wrap: wrap;
  row-gap: 8px;
}
@media (max-width: 1024px) {
  .history-header {
    flex-wrap: wrap;
    gap: 8px;
  }
}

.upload-zone {
  border: 2px dashed #cbd5e1;
  border-radius: 10px;
  padding: 32px;
  text-align: center;
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s;
}
.upload-zone:hover,
.upload-zone--active {
  border-color: #6366f1;
  background: #f5f3ff;
}
.upload-zone--has-file {
  border-style: solid;
  border-color: #a5b4fc;
  background: #eef2ff;
}
.upload-input {
  position: absolute;
  width: 0;
  height: 0;
  opacity: 0;
}
.upload-hint {
  margin: 0 0 8px;
  font-size: 15px;
  color: #475569;
}
.upload-types {
  margin: 0;
  font-size: 13px;
  color: #94a3b8;
}
.upload-name {
  margin: 0 0 8px;
  font-weight: 600;
  color: #334155;
}
.upload-actions {
  margin-top: 16px;
}
.case-count-config {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
  flex-wrap: wrap;
}
.count-label {
  color: #334155;
  font-size: 13px;
}
.count-input {
  width: 110px;
  height: 32px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 0 10px;
  font-size: 13px;
  color: #0f172a;
}
.count-tip {
  color: #64748b;
  font-size: 12px;
  margin-right: 15px;
}
.error-text {
  margin: 10px 0 0;
  color: #dc2626;
  font-size: 13px;
  line-height: 1.55;
  white-space: pre-line;
  max-width: 720px;
}
.loading-box {
  margin-top: 12px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid #c7d2fe;
  background: #eef2ff;
}
.loading-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #4f46e5;
  animation: pulse 1s ease-in-out infinite;
}
.loading-text {
  color: #3730a3;
  font-size: 13px;
}
.loading-sub {
  margin-top: 2px;
  font-size: 12px;
  color: #6366f1;
}
.success-box {
  margin-top: 12px;
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid #bbf7d0;
  background: #f0fdf4;
  color: #166534;
  font-size: 13px;
}
@keyframes pulse {
  0% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.35);
    opacity: 0.5;
  }
  100% {
    transform: scale(1);
    opacity: 1;
  }
}
.btn-primary {
  height: 36px;
  padding: 0 20px;
  border: none;
  border-radius: 8px;
  background: #6366f1;
  color: #fff;
  font-size: 14px;
  cursor: pointer;
}
.btn-primary:hover:not(:disabled) {
  background: #4f46e5;
}
.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.result-panel {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.result-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 12px;
}
.result-header .panel-title {
  margin: 0;
}
.result-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}
.check-all {
  font-size: 13px;
  color: #64748b;
  cursor: pointer;
}
.btn-secondary {
  height: 32px;
  padding: 0 14px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #fff;
  font-size: 13px;
  color: #475569;
  cursor: pointer;
}
.btn-secondary:hover {
  background: #f8fafc;
}
.export-wrap {
  position: relative;
}
.btn-export {
  height: 32px;
  padding: 0 14px;
  border: 1px solid #6366f1;
  border-radius: 8px;
  background: #eef2ff;
  color: #6366f1;
  font-size: 13px;
  cursor: pointer;
}
.btn-export:hover:not(:disabled) {
  background: #e0e7ff;
}
.btn-export:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.export-menu {
  position: absolute;
  right: 0;
  top: 100%;
  margin-top: 4px;
  min-width: 200px;
  padding: 8px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  z-index: 10;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.export-menu button {
  padding: 8px 12px;
  border: none;
  background: none;
  text-align: left;
  font-size: 13px;
  color: #334155;
  cursor: pointer;
  border-radius: 6px;
}
.export-menu button:hover {
  background: #f1f5f9;
}

.result-panel > .list-table-wrap {
  flex: 1;
  min-height: 0;
}
.drawer-pagination {
  flex-shrink: 0;
  display: flex;
  justify-content: flex-end;
  flex-wrap: wrap;
  row-gap: 8px;
}
.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}
.data-table th,
.data-table td {
  padding: 10px 12px;
  text-align: left;
  border-bottom: 1px solid #f1f5f9;
}
.data-table th {
  background: #f8fafc;
  color: #475569;
  font-weight: 600;
}
.data-table td {
  color: #334155;
}
.table-footer {
  padding: 10px 0 0;
  font-size: 13px;
  color: #64748b;
}
.download-bar {
  margin-top: 10px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}
.download-title {
  color: #475569;
  font-size: 13px;
}
.btn-download {
  height: 30px;
  padding: 0 12px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  background: #fff;
  color: #334155;
  font-size: 12px;
  cursor: pointer;
}
.btn-download:hover:not(:disabled) {
  background: #f8fafc;
}
.btn-download:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.add-panel {
  margin-top: 12px;
  padding: 12px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: #f8fafc;
}
.add-title {
  margin: 0 0 10px;
  font-size: 14px;
  color: #0f172a;
}
.add-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
  flex-wrap: wrap;
}
.add-label {
  min-width: 88px;
  font-size: 13px;
  color: #334155;
}
.add-input {
  height: 32px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 0 10px;
  font-size: 13px;
  min-width: 180px;
}
.add-input--wide {
  min-width: 320px;
}
.add-tip {
  color: #64748b;
  font-size: 12px;
}
.add-actions {
  display: flex;
  gap: 10px;
}
.btn-link {
  border: none;
  background: none;
  color: #6366f1;
  font-size: 13px;
  cursor: pointer;
}
.btn-link:hover {
  text-decoration: underline;
}
</style>
