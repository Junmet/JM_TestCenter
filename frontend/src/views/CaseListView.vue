<!--
  用例管理（按需求分组）· 设计说明（初稿）
  -------------------------------------
  1) 本页展示“需求列表”，不是直接展示全部用例
  2) 点击“查看用例”进入 /cases/:reqId，查看该需求下的用例清单
  3) 数据由后端接口提供
-->
<template>
  <div class="page-view req-page">
    <header class="page-header">
      <div class="header-left">
        <h1 class="title">用例管理</h1>
        <p class="subtitle">按需求维度管理测试用例，点击需求可查看该需求下的具体用例</p>
      </div>
      <div class="header-actions">
        <el-input v-model="keyword" class="search-input" placeholder="搜索需求标题/编号" clearable />
      </div>
    </header>

    <el-card class="table-panel" shadow="never">
      <div class="list-table-wrap">
        <div class="list-table-scroll">
          <el-table
            :data="requirements"
            stripe
            size="small"
            table-layout="fixed"
            height="100%"
            class="list-table list-table--first-left"
          >
          <el-table-column prop="code" label="需求编号" show-overflow-tooltip />
          <el-table-column prop="title" label="需求标题" show-overflow-tooltip />
          <el-table-column label="状态">
            <template #default="{ row }">
              <el-tag :type="progressTagType(row.status)" effect="light">{{ row.statusText }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="优先级">
            <template #default="{ row }">
              <el-tag
                :type="priorityTagType(row.priority)"
                effect="plain"
                class="priority-tag"
                @click.stop="cyclePriority(row)"
              >
                {{ row.priorityText }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="caseCount" label="用例数" />
          <el-table-column prop="owner" label="负责人" show-overflow-tooltip />
          <el-table-column prop="updatedAt" label="更新时间" show-overflow-tooltip />
          <el-table-column label="操作">
            <template #default="{ row }">
              <router-link :to="`/cases/${row.id}`" class="btn-link">查看用例</router-link>
              <button type="button" class="btn-link btn-link-edit" @click="openEdit(row)">编辑</button>
              <button type="button" class="btn-link btn-link-delete" @click="removeRequirement(row)">删除</button>
            </template>
          </el-table-column>
        </el-table>
        </div>
        <div class="table-pagination">
          <el-pagination
            background
            layout="total, sizes, prev, pager, next, jumper"
            :total="total"
            :page-size="pageSize"
            :current-page="page"
            :page-sizes="[5, 10, 20, 30, 50]"
            @current-change="onPageChange"
            @size-change="onPageSizeChange"
          />
        </div>
      </div>
      <footer class="table-footer">共 {{ total }} 条需求</footer>
    </el-card>

    <el-card v-if="editing" class="edit-panel" shadow="never">
      <h3 class="edit-title">编辑需求</h3>
      <div class="edit-row">
        <label>需求编号</label>
        <el-input v-model.trim="editForm.code" type="text" />
      </div>
      <div class="edit-row">
        <label>需求标题</label>
        <el-input v-model.trim="editForm.title" type="text" />
      </div>
      <div class="edit-row">
        <label>负责人</label>
        <span class="edit-owner">{{ currentUsername }}</span>
      </div>
      <p v-if="editError" class="edit-error">{{ editError }}</p>
      <div class="edit-actions">
        <el-button type="primary" @click="saveEdit">保存</el-button>
        <el-button @click="cancelEdit">取消</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  checkRequirementCodeExistsApi,
  deleteRequirementApi,
  listRequirementsApi,
  updateRequirementApi,
  updateRequirementPriorityApi,
  type RequirementItem
} from "../api/caseManagement";
import { useAuthStore } from "../stores/auth";

const authStore = useAuthStore();
const currentUsername = computed(() => authStore.user?.username || "-");

const keyword = ref("");
const page = ref(1);
const pageSize = ref(10);
const total = ref(0);

const requirements = ref<RequirementItem[]>([]);
const editing = ref<RequirementItem | null>(null);
const editError = ref("");
const editForm = reactive({ code: "", title: "" });

const PRI_ORDER = ["p0", "p1", "p2"];

function progressTagType(status: string) {
  if (status === "completed") return "success";
  if (status === "not_started") return "info";
  return "warning";
}

function priorityTagType(priority: string) {
  if (priority === "p0") return "danger";
  if (priority === "p1") return "warning";
  return "success";
}

async function cyclePriority(row: RequirementItem) {
  const idx = PRI_ORDER.indexOf(row.priority);
  const i = idx >= 0 ? idx : 0;
  const nextPriority = PRI_ORDER[(i + 1) % PRI_ORDER.length];
  try {
    await updateRequirementPriorityApi(row.code, nextPriority);
    await refreshRequirements();
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || "更新优先级失败");
  }
}

onMounted(async () => {
  await refreshRequirements();
});

async function refreshRequirements() {
  let data = await listRequirementsApi(page.value, pageSize.value, keyword.value);
  requirements.value = data.requirements || [];
  total.value = data.total || 0;
  page.value = data.page || page.value;
  pageSize.value = data.page_size || pageSize.value;
  const maxPage = Math.max(1, Math.ceil(total.value / pageSize.value) || 1);
  if (requirements.value.length === 0 && total.value > 0 && page.value > maxPage) {
    page.value = maxPage;
    data = await listRequirementsApi(page.value, pageSize.value, keyword.value);
    requirements.value = data.requirements || [];
    total.value = data.total || 0;
    page.value = data.page || page.value;
    pageSize.value = data.page_size || pageSize.value;
  }
}

let keywordDebounce: ReturnType<typeof setTimeout> | null = null;
watch(keyword, () => {
  if (keywordDebounce) clearTimeout(keywordDebounce);
  keywordDebounce = setTimeout(async () => {
    page.value = 1;
    await refreshRequirements();
  }, 300);
});

async function onPageChange(next: number) {
  page.value = next;
  await refreshRequirements();
}

async function onPageSizeChange(next: number) {
  pageSize.value = next;
  page.value = 1;
  await refreshRequirements();
}

function openEdit(row: RequirementItem) {
  editing.value = row;
  editError.value = "";
  editForm.code = row.code;
  editForm.title = row.title;
}

function cancelEdit() {
  editing.value = null;
  editError.value = "";
}

async function saveEdit() {
  if (!editing.value) return;
  const code = editForm.code.trim();
  const title = editForm.title.trim();
  if (!code || !title) {
    editError.value = "需求编号和标题不能为空";
    return;
  }
  const exists = await checkRequirementCodeExistsApi(code, editing.value.code);
  if (exists.exists) {
    editError.value = "需求编号已存在，请换一个";
    return;
  }
  try {
    await updateRequirementApi(editing.value.code, { code, title });
    await refreshRequirements();
    cancelEdit();
  } catch (err: any) {
    editError.value = err?.response?.data?.detail || "保存失败";
  }
}

async function removeRequirement(row: RequirementItem) {
  try {
    await ElMessageBox.confirm(
      `确认删除需求【${row.code} - ${row.title}】吗？删除后将无法恢复，并会同时删除该需求下所有用例。`,
      "删除确认",
      {
        confirmButtonText: "删除",
        cancelButtonText: "取消",
        type: "warning",
        confirmButtonClass: "el-button--danger"
      }
    );
    await deleteRequirementApi(row.code);
    if (editing.value?.code === row.code) {
      cancelEdit();
    }
    await refreshRequirements();
  } catch (err: any) {
    if (err === "cancel" || err === "close") return;
    editError.value = err?.response?.data?.detail || "删除失败";
  }
}
</script>

<style scoped>
.req-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
  flex: 1;
  min-height: 0;
  height: 100%;
}
.page-header {
  display: flex;
  flex-wrap: wrap;
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
.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}
.search-input {
  width: 260px;
}
.table-panel {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #fff;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
}
.table-panel :deep(.el-card__body) {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.priority-tag {
  cursor: pointer;
}
.btn-link {
  color: #6366f1;
  text-decoration: none;
  font-size: 13px;
  background: none;
  border: none;
  cursor: pointer;
}
.btn-link:hover {
  text-decoration: underline;
}
.btn-link-edit {
  margin-left: 8px;
}
.btn-link-delete {
  margin-left: 8px;
  color: #dc2626;
}
.table-footer {
  padding: 10px 16px;
  border-top: 1px solid #f1f5f9;
  color: #64748b;
  font-size: 13px;
}
.table-pagination {
  flex-shrink: 0;
  padding: 10px 16px 0;
  display: flex;
  justify-content: flex-end;
  flex-wrap: wrap;
  row-gap: 8px;
}
.edit-panel {
  padding: 14px;
}
.edit-title {
  margin: 0 0 10px;
  font-size: 15px;
}
.edit-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}
.edit-row label {
  width: 72px;
  color: #475569;
  font-size: 13px;
}
.edit-owner {
  font-size: 14px;
  color: #0f172a;
  font-weight: 600;
}
.edit-row :deep(.el-input) {
  width: 280px;
}
.edit-actions {
  display: flex;
  gap: 10px;
}
.edit-error {
  margin: 0 0 10px;
  color: #dc2626;
  font-size: 12px;
}
</style>
