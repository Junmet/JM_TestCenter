<!--
  需求下用例列表页
  路由：/cases/:reqId
-->
<template>
  <div class="page-view detail-page detail-page--fill">
    <header class="header">
      <div>
        <h1 class="title">{{ requirementInfo.code }} · {{ requirementInfo.title }}</h1>
        <p class="subtitle">需求下用例清单；执行状态变更后会自动更新上方需求状态</p>
      </div>
      <el-button type="primary" plain @click="$router.push('/cases')">返回需求列表</el-button>
    </header>

    <section class="meta-grid">
      <el-card class="meta-item" shadow="never">
        <span class="meta-label">需求状态</span>
        <span class="meta-value">{{ requirementInfo.statusText }}</span>
      </el-card>
      <el-card class="meta-item" shadow="never">
        <span class="meta-label">优先级</span>
        <span class="meta-value">{{ requirementInfo.priorityText }}</span>
      </el-card>
      <el-card class="meta-item" shadow="never">
        <span class="meta-label">负责人</span>
        <span class="meta-value">{{ requirementInfo.owner }}</span>
      </el-card>
      <el-card class="meta-item" shadow="never">
        <span class="meta-label">用例数</span>
        <span class="meta-value">{{ caseList.length }}</span>
      </el-card>
    </section>

    <el-card class="table-panel" shadow="never">
      <div class="list-table-wrap">
        <div class="list-table-scroll">
          <el-table
            :data="caseList"
            stripe
            size="small"
            table-layout="fixed"
            height="100%"
            class="list-table list-table--first-left"
          >
            <el-table-column prop="code" label="用例编号" show-overflow-tooltip />
            <el-table-column prop="name" label="用例名称" show-overflow-tooltip />
            <el-table-column label="步骤" show-overflow-tooltip>
              <template #default="{ row }">
                <span class="steps-cell" :title="row.stepsText">{{ row.stepsText || "-" }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="typeText" label="类型" show-overflow-tooltip />
            <el-table-column prop="priorityText" label="优先级" show-overflow-tooltip />
            <el-table-column label="执行状态" width="120" align="center">
              <template #default="{ row }">
                <el-dropdown trigger="click" @command="onExecDropdownCommand">
                  <span class="exec-dropdown-trigger" @click.stop>
                    <el-tag :type="execTagType(row.executionStatus)" effect="plain" class="exec-tag">
                      {{ row.executionStatusText }}
                    </el-tag>
                  </span>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <!-- command 用对象携带 caseId，避免 @command 与高阶函数绑定异常；菜单内勿再嵌套 el-tag，以免拦截点击 -->
                      <el-dropdown-item
                        v-for="opt in execOptions"
                        :key="opt.value"
                        :command="{ caseId: row.id, value: opt.value }"
                      >
                        <span class="exec-menu-opt" :data-exec="opt.value">{{ opt.label }}</span>
                      </el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
              </template>
            </el-table-column>
            <el-table-column prop="lastRunAt" label="最后执行" show-overflow-tooltip />
          </el-table>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { ElMessage } from "element-plus";
import {
  getRequirementDetailApi,
  updateCaseExecutionApi,
  type CaseExecutionStatus,
  type RequirementDetail
} from "../api/caseManagement";
import { useAuthStore } from "../stores/auth";

const route = useRoute();
const authStore = useAuthStore();
const reqId = computed(() => String(route.params.reqId || ""));
const detail = ref<RequirementDetail | null>(null);

async function loadDetail() {
  if (!reqId.value) return;
  try {
    detail.value = await getRequirementDetailApi(reqId.value);
  } catch {
    detail.value = null;
  }
}

onMounted(loadDetail);
watch(reqId, loadDetail);

const requirementInfo = computed(() => {
  const owner = detail.value?.owner || authStore.user?.username || "-";
  return {
    code: detail.value?.code || reqId.value,
    title: detail.value?.title || "需求详情",
    statusText: detail.value?.statusText || "未开始",
    priorityText: detail.value?.priorityText || "P1",
    owner
  };
});

const caseList = computed(() => detail.value?.cases || []);

/** 与优先级列类似：彩色标签；下拉项同步配色 */
const execOptions = [
  { value: "not_executed", label: "未执行", tagType: "info" as const },
  { value: "success", label: "成功", tagType: "success" as const },
  { value: "failed", label: "失败", tagType: "danger" as const },
  { value: "blocked", label: "阻塞", tagType: "warning" as const }
];

function execTagType(status: string): "success" | "info" | "warning" | "danger" {
  switch (status) {
    case "success":
      return "success";
    case "failed":
      return "danger";
    case "blocked":
      return "warning";
    default:
      return "info";
  }
}

function onExecDropdownCommand(cmd: unknown) {
  if (!cmd || typeof cmd !== "object") return;
  const o = cmd as { caseId?: number | string; value?: string };
  const caseId = Number(o.caseId);
  if (!Number.isFinite(caseId) || typeof o.value !== "string") return;
  void onExecutionChange(caseId, o.value);
}

async function onExecutionChange(caseId: number, executionStatus: unknown) {
  if (!reqId.value) return;
  const status = String(executionStatus) as CaseExecutionStatus;
  try {
    await updateCaseExecutionApi(reqId.value, caseId, status);
    await loadDetail();
  } catch (err: any) {
    const detail = err?.response?.data?.detail;
    const msg = Array.isArray(detail)
      ? detail.map((d: { msg?: string }) => d.msg || "").join("; ")
      : detail || "更新执行状态失败";
    ElMessage.error(msg);
    await loadDetail();
  }
}
</script>

<style scoped>
.detail-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
/* 与用例生成页一致的可视高度，便于列表区域 flex 撑满 */
.page-view.detail-page--fill {
  height: calc(100vh - 144px);
  max-height: calc(100vh - 144px);
  min-height: 0;
  overflow: hidden;
}
.detail-page--fill {
  flex: 1;
  min-height: 0;
}
.header {
  flex-shrink: 0;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
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
.meta-grid {
  flex-shrink: 0;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}
.meta-item {
  padding: 0;
}
.meta-label {
  display: block;
  font-size: 12px;
  color: #64748b;
  margin-bottom: 4px;
}
.meta-value {
  font-size: 14px;
  color: #0f172a;
  font-weight: 600;
}
.table-panel {
  flex: 1;
  min-height: 0;
  width: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.table-panel :deep(.el-card__body) {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.steps-cell {
  display: block;
  width: 100%;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.exec-dropdown-trigger {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  vertical-align: middle;
}
.exec-tag {
  cursor: pointer;
  user-select: none;
}
.exec-menu-opt {
  display: inline-block;
  min-width: 3em;
}
.exec-menu-opt[data-exec="not_executed"] {
  color: var(--el-color-info);
}
.exec-menu-opt[data-exec="success"] {
  color: var(--el-color-success);
}
.exec-menu-opt[data-exec="failed"] {
  color: var(--el-color-danger);
}
.exec-menu-opt[data-exec="blocked"] {
  color: var(--el-color-warning);
}
</style>
