<!--
  AI 对话（静态原型）：侧栏会话、主区消息流、输入区与常用弹窗；发送为本地模拟回复。
-->
<template>
  <div class="page-view ai-chat-page">
    <div class="ai-chat-shell">
      <!-- 侧栏 -->
      <aside class="ai-chat-aside">
        <div class="aside-top">
          <el-button type="primary" class="aside-new" @click="openNewDialog">
            <el-icon class="mr4"><Plus /></el-icon>
            新对话
          </el-button>
          <el-input
            v-model="convSearch"
            placeholder="搜索会话"
            clearable
            size="small"
            class="aside-search"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </div>
        <el-scrollbar class="aside-list-wrap">
          <div
            v-for="c in filteredConversations"
            :key="c.id"
            class="conv-item"
            :class="{ 'is-active': c.id === activeId }"
            @click="selectConv(c.id)"
          >
            <span class="conv-item__title">{{ c.title }}</span>
            <span class="conv-item__time">{{ c.updatedAt.slice(5, 16) }}</span>
            <el-dropdown trigger="click" @command="(cmd: string) => onConvMenu(cmd, c)">
              <span class="conv-item__more" @click.stop>
                <el-icon><MoreFilled /></el-icon>
              </span>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="rename">重命名</el-dropdown-item>
                  <el-dropdown-item command="export">导出</el-dropdown-item>
                  <el-dropdown-item command="delete" divided>删除</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
          <el-empty v-if="filteredConversations.length === 0" description="无匹配会话" />
        </el-scrollbar>
        <div class="aside-foot">
          <el-button text size="small" @click="dlgShortcuts = true">
            <el-icon><QuestionFilled /></el-icon>
            快捷键
          </el-button>
        </div>
      </aside>

      <!-- 主区 -->
      <div class="ai-chat-main">
        <header class="chat-toolbar">
          <div class="chat-toolbar__left">
            <span class="chat-title">{{ activeConv?.title ?? "对话" }}</span>
            <el-tag size="small" type="info" effect="plain">静态演示</el-tag>
          </div>
          <div class="chat-toolbar__right">
            <el-select v-model="currentModel" size="small" style="width: 200px" @change="onModelChange">
              <el-option v-for="m in MODEL_OPTIONS" :key="m.value" :label="m.label" :value="m.value" />
            </el-select>
            <el-button size="small" @click="dlgSettings = true">对话设置</el-button>
            <el-button size="small" :disabled="!activeConv || !activeConv.messages.length" @click="dlgClear = true">
              清空上下文
            </el-button>
            <el-button size="small" :disabled="!activeConv" @click="openExportDialog">导出</el-button>
          </div>
        </header>

        <el-scrollbar ref="msgScrollRef" class="chat-messages">
          <div v-if="!activeConv" class="chat-empty-main">
            <el-empty description="请选择或新建一个对话" />
          </div>
          <div v-else-if="!activeConv.messages.length" class="chat-empty-main">
            <div class="welcome-block">
              <h2>JMTEST AI 助手</h2>
              <p>类似 ChatGPT / 豆包 / DeepSeek 的对话体验（当前为前端静态，未请求大模型）。</p>
              <ul class="welcome-tips">
                <li>在下方输入问题，点击发送或 Ctrl+Enter</li>
                <li>侧栏可搜索、重命名、导出、删除会话</li>
                <li>「对话设置」可调整温度、系统提示等（本地保存）</li>
              </ul>
            </div>
          </div>
          <div v-else class="msg-list">
            <div
              v-for="msg in activeConv.messages"
              :key="msg.id"
              class="msg-row"
              :class="`msg-row--${msg.role}`"
            >
              <div class="msg-avatar">
                <el-icon v-if="msg.role === 'user'"><User /></el-icon>
                <el-icon v-else><Cpu /></el-icon>
              </div>
              <div class="msg-body">
                <div class="msg-meta">
                  <span class="msg-role">{{ msg.role === "user" ? "你" : "助手" }}</span>
                  <span v-if="prefs.showTimestamp" class="msg-time">{{ msg.createdAt }}</span>
                  <el-button
                    v-if="msg.role === 'assistant'"
                    link
                    type="primary"
                    size="small"
                    @click="copyMsg(msg.content)"
                  >
                    复制
                  </el-button>
                </div>
                <div class="msg-text">{{ msg.content }}</div>
              </div>
            </div>
          </div>
        </el-scrollbar>

        <footer class="chat-composer">
          <div class="composer-tools">
            <el-tooltip content="附件（静态占位）" placement="top">
              <el-button circle size="small" disabled>
                <el-icon><Paperclip /></el-icon>
              </el-button>
            </el-tooltip>
            <el-switch v-model="prefs.stream" active-text="流式" inactive-text="非流式" size="small" />
          </div>
          <div class="composer-input-row">
            <el-input
              v-model="draft"
              type="textarea"
              :rows="3"
              resize="none"
              placeholder="输入消息，Ctrl+Enter 发送…"
              class="composer-textarea"
              @keydown="onComposerKeydown"
            />
            <div class="composer-actions">
              <el-button v-if="sending" @click="stopFake">停止</el-button>
              <el-button type="primary" :loading="sending" :disabled="!draft.trim() || !activeConv" @click="send">
                发送
              </el-button>
            </div>
          </div>
          <p class="composer-hint">内容由静态逻辑模拟生成，不代表真实模型输出。</p>
        </footer>
      </div>
    </div>

    <!-- 新建对话 -->
    <el-dialog v-model="dlgNew" title="新建对话" width="440px" destroy-on-close @closed="newTitle = ''">
      <el-form label-width="88px">
        <el-form-item label="标题">
          <el-input v-model="newTitle" placeholder="可选，默认「新对话」" maxlength="80" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dlgNew = false">取消</el-button>
        <el-button type="primary" @click="confirmNew">创建</el-button>
      </template>
    </el-dialog>

    <!-- 重命名 -->
    <el-dialog v-model="dlgRename" title="重命名会话" width="440px" destroy-on-close>
      <el-input v-model="renameTitle" maxlength="80" show-word-limit />
      <template #footer>
        <el-button @click="dlgRename = false">取消</el-button>
        <el-button type="primary" @click="confirmRename">保存</el-button>
      </template>
    </el-dialog>

    <!-- 删除 -->
    <el-dialog v-model="dlgDelete" title="删除会话" width="400px">
      <p>确定删除「{{ deleteTarget?.title }}」？此操作在静态页中仅本地生效。</p>
      <template #footer>
        <el-button @click="dlgDelete = false">取消</el-button>
        <el-button type="danger" @click="confirmDelete">删除</el-button>
      </template>
    </el-dialog>

    <!-- 对话设置 -->
    <el-dialog v-model="dlgSettings" title="对话设置" width="520px" destroy-on-close>
      <el-form label-width="120px">
        <el-form-item label="温度">
          <el-slider v-model="prefs.temperature" :min="0" :max="2" :step="0.1" show-input />
        </el-form-item>
        <el-form-item label="最大长度">
          <el-input-number v-model="prefs.maxTokens" :min="256" :max="128000" :step="256" />
        </el-form-item>
        <el-form-item label="系统提示">
          <el-input v-model="prefs.systemPrompt" type="textarea" :rows="4" placeholder="可选，后续接 API 时注入" />
        </el-form-item>
        <el-form-item label="显示时间戳">
          <el-switch v-model="prefs.showTimestamp" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dlgSettings = false">关闭</el-button>
        <el-button type="primary" @click="savePrefs">保存到本地</el-button>
      </template>
    </el-dialog>

    <!-- 清空上下文 -->
    <el-dialog v-model="dlgClear" title="清空当前对话" width="420px">
      <p>将移除本会话中的所有消息，是否继续？</p>
      <template #footer>
        <el-button @click="dlgClear = false">取消</el-button>
        <el-button type="primary" @click="confirmClear">清空</el-button>
      </template>
    </el-dialog>

    <!-- 导出 -->
    <el-dialog v-model="dlgExport" title="导出对话" width="640px" destroy-on-close>
      <el-radio-group v-model="exportFormat" class="mb12">
        <el-radio value="md">Markdown</el-radio>
        <el-radio value="json">JSON</el-radio>
      </el-radio-group>
      <el-input v-model="exportText" type="textarea" :rows="14" readonly class="mono-area" />
      <template #footer>
        <el-button @click="copyExport">复制</el-button>
        <el-button type="primary" @click="dlgExport = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 快捷键 -->
    <el-dialog v-model="dlgShortcuts" title="快捷键" width="480px">
      <el-descriptions :column="1" border size="small">
        <el-descriptions-item label="发送">Ctrl + Enter</el-descriptions-item>
        <el-descriptions-item label="换行">Enter（在输入框内）</el-descriptions-item>
        <el-descriptions-item label="新对话">侧栏「新对话」按钮</el-descriptions-item>
      </el-descriptions>
      <template #footer>
        <el-button type="primary" @click="dlgShortcuts = false">知道了</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import {
  Cpu,
  MoreFilled,
  Paperclip,
  Plus,
  QuestionFilled,
  Search,
  User,
} from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { computed, nextTick, onMounted, ref, watch } from "vue";
import {
  genId,
  INITIAL_CONVERSATIONS,
  MODEL_OPTIONS,
  type Conversation,
} from "./ai-chat/mockData";

const STORAGE_KEY = "jmtest_ai_chat_prefs_v1";

const conversations = ref<Conversation[]>(JSON.parse(JSON.stringify(INITIAL_CONVERSATIONS)));
const activeId = ref<string | null>(conversations.value[0]?.id ?? null);
const convSearch = ref("");
const draft = ref("");
const sending = ref(false);
const msgScrollRef = ref<InstanceType<typeof import("element-plus")["ElScrollbar"]> | null>(null);

const currentModel = ref(conversations.value[0]?.model ?? MODEL_OPTIONS[0].value);

const prefs = ref({
  temperature: 0.7,
  maxTokens: 4096,
  systemPrompt: "你是一个有帮助的助手。",
  showTimestamp: true,
  stream: true,
});

const dlgNew = ref(false);
const newTitle = ref("");
const dlgRename = ref(false);
const renameTitle = ref("");
const renameConvId = ref<string | null>(null);
const dlgDelete = ref(false);
const deleteTarget = ref<Conversation | null>(null);
const dlgSettings = ref(false);
const dlgClear = ref(false);
const dlgExport = ref(false);
const exportFormat = ref<"md" | "json">("md");
const exportText = ref("");
const dlgShortcuts = ref(false);

let fakeTimer: ReturnType<typeof setTimeout> | null = null;

const filteredConversations = computed(() => {
  const q = convSearch.value.trim().toLowerCase();
  if (!q) return conversations.value;
  return conversations.value.filter((c) => c.title.toLowerCase().includes(q));
});

const activeConv = computed(() => conversations.value.find((c) => c.id === activeId.value) ?? null);

watch(activeConv, (c) => {
  if (c) currentModel.value = c.model;
});

onMounted(() => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const p = JSON.parse(raw) as Partial<typeof prefs.value>;
      prefs.value = { ...prefs.value, ...p };
    }
  } catch {
    /* ignore */
  }
});

function scrollToBottom() {
  nextTick(() => {
    const inst = msgScrollRef.value as unknown as { wrapRef?: HTMLElement; $el?: HTMLElement } | null;
    const wrap = inst?.wrapRef ?? inst?.$el?.querySelector?.(".el-scrollbar__wrap");
    if (wrap && "scrollHeight" in wrap) (wrap as HTMLElement).scrollTop = (wrap as HTMLElement).scrollHeight;
  });
}

function selectConv(id: string) {
  activeId.value = id;
  const c = conversations.value.find((x) => x.id === id);
  if (c) currentModel.value = c.model;
  scrollToBottom();
}

function onModelChange() {
  const c = activeConv.value;
  if (c) c.model = currentModel.value;
}

function openNewDialog() {
  newTitle.value = "";
  dlgNew.value = true;
}

function confirmNew() {
  const title = newTitle.value.trim() || "新对话";
  const nc: Conversation = {
    id: genId("c"),
    title,
    updatedAt: formatNow(),
    model: currentModel.value,
    messages: [],
  };
  conversations.value.unshift(nc);
  activeId.value = nc.id;
  dlgNew.value = false;
  ElMessage.success("已创建（本地）");
}

function onConvMenu(cmd: string, c: Conversation) {
  if (cmd === "rename") {
    renameConvId.value = c.id;
    renameTitle.value = c.title;
    dlgRename.value = true;
  } else if (cmd === "export") {
    activeId.value = c.id;
    openExportDialog();
  } else if (cmd === "delete") {
    deleteTarget.value = c;
    dlgDelete.value = true;
  }
}

function confirmRename() {
  const id = renameConvId.value;
  if (!id) return;
  const t = renameTitle.value.trim();
  if (!t) {
    ElMessage.warning("标题不能为空");
    return;
  }
  const c = conversations.value.find((x) => x.id === id);
  if (c) c.title = t;
  dlgRename.value = false;
  ElMessage.success("已重命名");
}

function confirmDelete() {
  const t = deleteTarget.value;
  if (!t) return;
  conversations.value = conversations.value.filter((x) => x.id !== t.id);
  if (activeId.value === t.id) {
    activeId.value = conversations.value[0]?.id ?? null;
  }
  dlgDelete.value = false;
  deleteTarget.value = null;
  ElMessage.success("已删除（本地）");
}

function savePrefs() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs.value));
  dlgSettings.value = false;
  ElMessage.success("已保存到浏览器本地");
}

function confirmClear() {
  const c = activeConv.value;
  if (c) {
    c.messages = [];
    c.updatedAt = formatNow();
  }
  dlgClear.value = false;
  ElMessage.success("已清空");
}

function buildExportBody(c: Conversation): string {
  if (exportFormat.value === "json") {
    return JSON.stringify(
      { title: c.title, model: c.model, updatedAt: c.updatedAt, messages: c.messages },
      null,
      2,
    );
  }
  const lines = [`# ${c.title}`, "", `模型: ${c.model}`, `更新: ${c.updatedAt}`, ""];
  for (const m of c.messages) {
    lines.push(`## ${m.role === "user" ? "用户" : "助手"} (${m.createdAt})`, "", m.content, "");
  }
  return lines.join("\n");
}

function openExportDialog() {
  const c = activeConv.value;
  if (!c) return;
  exportText.value = buildExportBody(c);
  dlgExport.value = true;
}

function copyExport() {
  navigator.clipboard.writeText(exportText.value);
  ElMessage.success("已复制");
}

function copyMsg(text: string) {
  navigator.clipboard.writeText(text);
  ElMessage.success("已复制");
}

function formatNow() {
  const d = new Date();
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
}

function send() {
  const c = activeConv.value;
  if (!c || !draft.value.trim()) return;
  const userMsg = {
    id: genId("m"),
    role: "user" as const,
    content: draft.value.trim(),
    createdAt: formatNow(),
  };
  c.messages.push(userMsg);
  c.updatedAt = userMsg.createdAt;
  draft.value = "";
  scrollToBottom();

  sending.value = true;
  fakeTimer = setTimeout(() => {
    const reply = {
      id: genId("m"),
      role: "assistant" as const,
      content:
        `（静态模拟回复）已收到你的消息。当前为前端演示：温度=${prefs.value.temperature}，流式=${prefs.value.stream ? "开" : "关"}，模型=${c.model}。\n\n真实接入时请替换为 SSE / WebSocket 或后端转发 API。`,
      createdAt: formatNow(),
    };
    c.messages.push(reply);
    c.updatedAt = reply.createdAt;
    sending.value = false;
    fakeTimer = null;
    scrollToBottom();
  }, 700);
}

function stopFake() {
  if (fakeTimer) {
    clearTimeout(fakeTimer);
    fakeTimer = null;
  }
  sending.value = false;
  ElMessage.info("已停止（本地）");
}

function onComposerKeydown(e: KeyboardEvent) {
  if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
    e.preventDefault();
    send();
  }
}
</script>

<style scoped>
.mr4 {
  margin-right: 4px;
}
.mb12 {
  margin-bottom: 12px;
}
.mono-area :deep(textarea) {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12px;
}

.ai-chat-page {
  padding: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background: #f0f2f5;
}
.ai-chat-shell {
  flex: 1;
  min-height: 0;
  display: flex;
  margin: 0;
  border-radius: 0;
  overflow: hidden;
  border: none;
  background: transparent;
}

.ai-chat-aside {
  width: 260px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  border-right: 1px solid #e5e7eb;
  background: #f9fafb;
}
.aside-top {
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.aside-new {
  width: 100%;
  justify-content: center;
}
.aside-list-wrap {
  flex: 1;
  min-height: 0;
  padding: 0 8px 8px;
}
.conv-item {
  position: relative;
  padding: 10px 36px 10px 10px;
  border-radius: 8px;
  cursor: pointer;
  margin-bottom: 4px;
  border: 1px solid transparent;
}
.conv-item:hover {
  background: #eef2ff;
}
.conv-item.is-active {
  background: #e0e7ff;
  border-color: #c7d2fe;
}
.conv-item__title {
  display: block;
  font-size: 13px;
  color: #111827;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.conv-item__time {
  display: block;
  font-size: 11px;
  color: #9ca3af;
  margin-top: 4px;
}
.conv-item__more {
  position: absolute;
  right: 6px;
  top: 50%;
  transform: translateY(-50%);
  padding: 4px;
  color: #6b7280;
  border-radius: 4px;
}
.conv-item__more:hover {
  background: rgba(255, 255, 255, 0.8);
}
.aside-foot {
  padding: 8px 12px;
  border-top: 1px solid #e5e7eb;
}

.ai-chat-main {
  flex: 1;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background: #fff;
}
.chat-toolbar {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 16px;
  border-bottom: 1px solid #e5e7eb;
  flex-wrap: wrap;
}
.chat-toolbar__left {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.chat-title {
  font-weight: 600;
  font-size: 15px;
  color: #111827;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: min(360px, 50vw);
}
.chat-toolbar__right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.chat-messages {
  flex: 1;
  min-height: 0;
  padding: 16px 20px;
  background: linear-gradient(180deg, #fafafa 0%, #fff 120px);
}
.chat-empty-main {
  min-height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.welcome-block {
  max-width: 480px;
  text-align: center;
  color: #4b5563;
}
.welcome-block h2 {
  margin: 0 0 12px;
  font-size: 20px;
  color: #111827;
}
.welcome-tips {
  text-align: left;
  margin: 16px 0 0;
  padding-left: 20px;
  font-size: 13px;
  line-height: 1.6;
}

.msg-list {
  max-width: 880px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-bottom: 24px;
}
.msg-row {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}
.msg-avatar {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-size: 16px;
}
.msg-row--user .msg-avatar {
  background: #dbeafe;
  color: #1d4ed8;
}
.msg-row--assistant .msg-avatar {
  background: #ecfdf5;
  color: #047857;
}
.msg-body {
  flex: 1;
  min-width: 0;
}
.msg-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
  flex-wrap: wrap;
}
.msg-role {
  font-size: 12px;
  font-weight: 600;
  color: #6b7280;
}
.msg-time {
  font-size: 11px;
  color: #9ca3af;
}
.msg-text {
  font-size: 14px;
  line-height: 1.65;
  color: #1f2937;
  white-space: pre-wrap;
  word-break: break-word;
}

.chat-composer {
  flex-shrink: 0;
  padding: 12px 16px 16px;
  border-top: 1px solid #e5e7eb;
  background: #fff;
}
.composer-tools {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}
.composer-input-row {
  display: flex;
  gap: 12px;
  align-items: flex-end;
}
.composer-textarea {
  flex: 1;
  min-width: 0;
}
.composer-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.composer-hint {
  margin: 8px 0 0;
  font-size: 11px;
  color: #9ca3af;
}

@media (max-width: 768px) {
  .ai-chat-shell {
    flex-direction: column;
  }
  .ai-chat-aside {
    width: 100%;
    max-height: 40vh;
    border-right: none;
    border-bottom: 1px solid #e5e7eb;
  }
}
</style>
