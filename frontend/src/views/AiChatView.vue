<!--
  AI 对话：会话与消息存数据库，换设备登录同一账号可同步历史。
  UI：Element Plus + 自定义主题色与气泡布局。
-->
<template>
  <div class="page-view ai-chat-page">
    <div class="ai-chat-shell">
      <!-- 侧栏 -->
      <el-card class="aside-card" shadow="never" :body-style="{ padding: '0', height: '100%', display: 'flex', flexDirection: 'column' }">
        <div class="aside-brand">
          <div class="aside-brand__icon">
            <el-icon :size="22"><ChatDotRound /></el-icon>
          </div>
          <div class="aside-brand__text">
            <span class="aside-brand__title">JMTEST AI</span>
            <span class="aside-brand__sub">智能对话</span>
          </div>
        </div>

        <div class="aside-actions">
          <el-button type="primary" class="aside-new" round @click="openNewDialog">
            <el-icon class="mr4"><Plus /></el-icon>
            新对话
          </el-button>
          <el-input
            v-model="convSearch"
            placeholder="搜索历史会话"
            clearable
            class="aside-search"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </div>

        <el-scrollbar v-loading="listLoading" class="aside-list-wrap">
          <div class="conv-list">
            <div
              v-for="c in filteredConversations"
              :key="c.id"
              class="conv-item"
              :class="{ 'is-active': c.id === activeId }"
              @click="selectConv(c.id)"
            >
              <div class="conv-item__body">
                <span class="conv-item__title">{{ c.title }}</span>
                <span class="conv-item__time">{{ c.updatedAt.slice(5, 16) }}</span>
              </div>
              <el-dropdown trigger="click" @command="(cmd: string) => onConvMenu(cmd, c)">
                <el-button class="conv-item__more" text circle size="small" @click.stop>
                  <el-icon><MoreFilled /></el-icon>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="rename">
                      <el-icon class="dd-ico"><EditPen /></el-icon>重命名
                    </el-dropdown-item>
                    <el-dropdown-item command="export">
                      <el-icon class="dd-ico"><Download /></el-icon>导出
                    </el-dropdown-item>
                    <el-dropdown-item command="delete" divided>
                      <el-icon class="dd-ico"><Delete /></el-icon>删除
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </div>
          <el-empty v-if="filteredConversations.length === 0" description="无匹配会话" :image-size="72" />
        </el-scrollbar>

        <div class="aside-foot">
          <el-button text type="primary" @click="dlgShortcuts = true">
            <el-icon><QuestionFilled /></el-icon>
            快捷键说明
          </el-button>
        </div>
      </el-card>

      <!-- 主区 -->
      <div class="ai-chat-main">
        <header class="chat-toolbar">
          <div class="chat-toolbar__left">
            <el-text truncated class="chat-title">{{ activeConv?.title ?? "选择或新建对话" }}</el-text>
            <el-tag size="small" type="success" effect="light" round>DeepSeek</el-tag>
          </div>
          <el-space wrap :size="8" class="chat-toolbar__right">
            <el-select v-model="currentModel" placeholder="模型" style="width: 200px" @change="onModelChange">
              <template #prefix>
                <el-icon class="sel-ico"><Cpu /></el-icon>
              </template>
              <el-option v-for="m in MODEL_OPTIONS" :key="m.value" :label="m.label" :value="m.value" />
            </el-select>
            <el-button @click="dlgSettings = true">
              <el-icon class="mr4"><Setting /></el-icon>
              设置
            </el-button>
            <el-button :disabled="!activeConv || !activeConv.messages.length" @click="dlgClear = true">清空</el-button>
            <el-button type="primary" plain :disabled="!activeConv" @click="openExportDialog">导出</el-button>
          </el-space>
        </header>

        <el-scrollbar ref="msgScrollRef" v-loading="messagesLoading" class="chat-messages">
          <div v-if="!activeConv" class="chat-empty-main">
            <el-empty description="从左侧选择会话，或点击「新对话」开始">
              <el-button type="primary" round @click="openNewDialog">新建对话</el-button>
            </el-empty>
          </div>
          <div v-else-if="!activeConv.messages.length" class="chat-empty-main">
            <el-card class="welcome-card" shadow="hover">
              <div class="welcome-inner">
                <el-icon class="welcome-logo" :size="48"><ChatDotRound /></el-icon>
                <h2 class="welcome-h2">开始与 AI 对话</h2>
                <p class="welcome-desc">
                  消息经后端转发至 DeepSeek（与「用例生成」共用服务端 API Key 配置）。
                </p>
                <el-divider />
                <ul class="welcome-tips">
                  <li>在底部输入问题，<kbd>Ctrl</kbd> + <kbd>Enter</kbd> 发送</li>
                  <li>侧栏支持搜索、重命名、导出与删除会话</li>
                  <li>聊天记录在服务器；温度等可在「设置」调整（偏好存本机浏览器）</li>
                </ul>
              </div>
            </el-card>
          </div>
          <div v-else class="msg-list">
            <div
              v-for="msg in activeConv.messages"
              :key="msg.id"
              class="msg-row"
              :class="`msg-row--${msg.role}`"
            >
              <el-avatar
                v-if="msg.role === 'user'"
                :size="40"
                class="msg-avatar msg-avatar--user"
              >
                <el-icon><User /></el-icon>
              </el-avatar>
              <el-avatar
                v-else
                :size="40"
                class="msg-avatar msg-avatar--bot"
              >
                <el-icon><Cpu /></el-icon>
              </el-avatar>
              <div class="msg-stack">
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
                <div
                  v-if="msg.role === 'user'"
                  class="msg-bubble msg-bubble--user"
                >
                  {{ msg.content }}
                </div>
                <div
                  v-else
                  class="msg-bubble msg-bubble--assistant markdown-body chat-md"
                  v-html="renderChatMarkdown(msg.content)"
                ></div>
              </div>
            </div>
            <div v-if="streamingReply" class="msg-row msg-row--assistant">
              <el-avatar :size="40" class="msg-avatar msg-avatar--bot">
                <el-icon><Cpu /></el-icon>
              </el-avatar>
              <div class="msg-stack">
                <div class="msg-meta">
                  <span class="msg-role">助手</span>
                  <span class="msg-time">生成中…</span>
                </div>
                <div
                  class="msg-bubble msg-bubble--assistant markdown-body chat-md"
                  v-html="renderChatMarkdown(streamingReply)"
                ></div>
              </div>
            </div>
          </div>
        </el-scrollbar>

        <footer class="chat-composer">
          <el-card class="composer-card" shadow="hover" :body-style="{ padding: '12px 14px 14px' }">
            <div class="composer-tools">
              <el-tooltip content="附件（占位）" placement="top">
                <el-button circle disabled>
                  <el-icon><Paperclip /></el-icon>
                </el-button>
              </el-tooltip>
              <el-divider direction="vertical" />
              <span class="composer-label">输出</span>
              <el-switch v-model="prefs.stream" inline-prompt active-text="流式" inactive-text="整段" />
            </div>
            <div class="composer-input-row">
              <el-input
                v-model="draft"
                type="textarea"
                :autosize="{ minRows: 3, maxRows: 8 }"
                resize="none"
                placeholder="输入消息…  Ctrl + Enter 发送"
                class="composer-textarea"
                @keydown="onComposerKeydown"
              />
              <div class="composer-actions">
                <el-button v-if="sending" @click="stopRequest">停止</el-button>
                <el-button
                  type="primary"
                  size="large"
                  round
                  :loading="sending"
                  :disabled="!draft.trim() || !activeConv"
                  @click="send"
                >
                  <el-icon class="mr4"><Promotion /></el-icon>
                  发送
                </el-button>
              </div>
            </div>
            <p class="composer-hint">
              <el-icon><InfoFilled /></el-icon>
              消息经后端写入数据库并调用 DeepSeek；「流式」打开时逐段显示回复。
            </p>
          </el-card>
        </footer>
      </div>
    </div>

    <!-- 弹窗 -->
    <el-dialog v-model="dlgNew" title="新建对话" width="440px" destroy-on-close align-center @closed="newTitle = ''">
      <el-form label-width="72px">
        <el-form-item label="标题">
          <el-input v-model="newTitle" placeholder="可选，默认「新对话」" maxlength="80" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dlgNew = false">取消</el-button>
        <el-button type="primary" @click="confirmNew">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="dlgRename" title="重命名会话" width="440px" destroy-on-close align-center>
      <el-input v-model="renameTitle" maxlength="80" show-word-limit />
      <template #footer>
        <el-button @click="dlgRename = false">取消</el-button>
        <el-button type="primary" @click="confirmRename">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="dlgDelete" title="删除会话" width="400px" align-center>
      <p>确定删除「{{ deleteTarget?.title }}」？将同时删除服务器上该会话及全部消息，不可恢复。</p>
      <template #footer>
        <el-button @click="dlgDelete = false">取消</el-button>
        <el-button type="danger" @click="confirmDelete">删除</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="dlgSettings" title="对话设置" width="520px" destroy-on-close align-center>
      <el-form label-width="112px">
        <el-form-item label="温度">
          <el-slider v-model="prefs.temperature" :min="0" :max="2" :step="0.1" show-input />
        </el-form-item>
        <el-form-item label="最大长度">
          <el-input-number v-model="prefs.maxTokens" :min="256" :max="128000" :step="256" style="width: 100%" />
        </el-form-item>
        <el-form-item label="系统提示">
          <el-input v-model="prefs.systemPrompt" type="textarea" :rows="4" placeholder="将作为 system 消息发给模型（可选）" />
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

    <el-dialog v-model="dlgClear" title="清空当前对话" width="420px" align-center>
      <p>将移除本会话中的所有消息，是否继续？</p>
      <template #footer>
        <el-button @click="dlgClear = false">取消</el-button>
        <el-button type="primary" @click="confirmClear">清空</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="dlgExport" title="导出对话" width="640px" destroy-on-close align-center>
      <el-radio-group v-model="exportFormat" class="mb12">
        <el-radio-button value="md">Markdown</el-radio-button>
        <el-radio-button value="json">JSON</el-radio-button>
      </el-radio-group>
      <el-input v-model="exportText" type="textarea" :rows="14" readonly class="mono-area" />
      <template #footer>
        <el-button @click="copyExport">复制</el-button>
        <el-button type="primary" @click="dlgExport = false">关闭</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="dlgShortcuts" title="快捷键" width="480px" align-center>
      <el-descriptions :column="1" border size="small">
        <el-descriptions-item label="发送">Ctrl + Enter</el-descriptions-item>
        <el-descriptions-item label="换行">Enter</el-descriptions-item>
        <el-descriptions-item label="新对话">侧栏「新对话」</el-descriptions-item>
      </el-descriptions>
      <template #footer>
        <el-button type="primary" @click="dlgShortcuts = false">知道了</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import {
  ChatDotRound,
  Cpu,
  Delete,
  Download,
  EditPen,
  InfoFilled,
  MoreFilled,
  Paperclip,
  Plus,
  Promotion,
  QuestionFilled,
  Search,
  Setting,
  User,
} from "@element-plus/icons-vue";
import axios from "axios";
import { ElMessage } from "element-plus";
import { computed, nextTick, onMounted, ref, watch } from "vue";
import {
  chatTurnApi,
  chatTurnStreamApi,
  clearConversationMessagesApi,
  createConversationApi,
  deleteConversationApi,
  fetchConversationMessagesApi,
  fetchConversationsApi,
  updateConversationApi,
  type ChatConversationOut,
  type ChatMessageOut,
} from "../api/aiChat";
import { renderChatMarkdown } from "../utils/markdown";
import { MODEL_OPTIONS, type ChatMessage, type Conversation } from "./ai-chat/mockData";

const STORAGE_KEY = "jmtest_ai_chat_prefs_v1";

const conversations = ref<Conversation[]>([]);
const activeId = ref<number | null>(null);
const convSearch = ref("");
const draft = ref("");
const sending = ref(false);
const listLoading = ref(false);
const messagesLoading = ref(false);
const msgScrollRef = ref<InstanceType<typeof import("element-plus")["ElScrollbar"]> | null>(null);

const currentModel = ref(MODEL_OPTIONS[0].value);

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
const renameConvId = ref<number | null>(null);
const dlgDelete = ref(false);
const deleteTarget = ref<Conversation | null>(null);
const dlgSettings = ref(false);
const dlgClear = ref(false);
const dlgExport = ref(false);
const exportFormat = ref<"md" | "json">("md");
const exportText = ref("");
const dlgShortcuts = ref(false);

const abortRef = ref<AbortController | null>(null);
/** 流式输出中的助手片段（完成后清空，消息写入 messages） */
const streamingReply = ref("");

const filteredConversations = computed(() => {
  const q = convSearch.value.trim().toLowerCase();
  if (!q) return conversations.value;
  return conversations.value.filter((c) => c.title.toLowerCase().includes(q));
});

const activeConv = computed(() => conversations.value.find((c) => c.id === activeId.value) ?? null);

watch(
  activeConv,
  (c) => {
    if (c) currentModel.value = c.model;
  },
  { immediate: true }
);

watch(streamingReply, () => {
  nextTick(() => scrollToBottom());
});

function formatMsgTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
}

function mapConvFromApi(r: ChatConversationOut): Conversation {
  return {
    id: r.id,
    title: r.title,
    model: r.model,
    updatedAt: formatMsgTime(r.updated_at),
    messages: [],
    messagesLoaded: false,
  };
}

function mapMsgFromApi(m: ChatMessageOut): ChatMessage {
  return {
    id: m.id,
    role: m.role,
    content: m.content,
    createdAt: formatMsgTime(m.created_at),
  };
}

function syncConvMeta(c: Conversation, title: string, updatedIso: string) {
  c.title = title;
  const updated = conversations.value.find((x) => x.id === c.id);
  if (updated) {
    updated.title = title;
    updated.updatedAt = formatMsgTime(updatedIso);
  }
  const idx = conversations.value.findIndex((x) => x.id === c.id);
  if (idx > 0) {
    const [item] = conversations.value.splice(idx, 1);
    conversations.value.unshift(item);
  }
}

function errDetail(e: unknown): string {
  const detail = axios.isAxiosError(e) ? e.response?.data?.detail : undefined;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)
    && detail.length
    && typeof detail[0] === "object"
    && detail[0] !== null
    && "msg" in detail[0]) {
    return (detail as { msg?: string }[]).map((x) => x.msg).filter(Boolean).join("；");
  }
  return "请求失败，请检查登录态与网络";
}

async function loadConversationList() {
  listLoading.value = true;
  try {
    const rows = await fetchConversationsApi();
    conversations.value = rows.map(mapConvFromApi);
  } catch (e) {
    ElMessage.error(errDetail(e));
  } finally {
    listLoading.value = false;
  }
}

onMounted(async () => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const p = JSON.parse(raw) as Partial<typeof prefs.value>;
      prefs.value = { ...prefs.value, ...p };
    }
  } catch {
    /* ignore */
  }
  await loadConversationList();
  if (conversations.value.length > 0) {
    await selectConv(conversations.value[0].id);
  }
});

function scrollToBottom() {
  nextTick(() => {
    const inst = msgScrollRef.value as unknown as { wrapRef?: HTMLElement; $el?: HTMLElement } | null;
    const wrap = inst?.wrapRef ?? inst?.$el?.querySelector?.(".el-scrollbar__wrap");
    if (wrap && "scrollHeight" in wrap) (wrap as HTMLElement).scrollTop = (wrap as HTMLElement).scrollHeight;
  });
}

async function selectConv(id: number) {
  activeId.value = id;
  const c = conversations.value.find((x) => x.id === id);
  if (c) currentModel.value = c.model;
  if (!c) return;
  if (c.messagesLoaded) {
    scrollToBottom();
    return;
  }
  messagesLoading.value = true;
  try {
    const msgs = await fetchConversationMessagesApi(id);
    c.messages = msgs.map(mapMsgFromApi);
    c.messagesLoaded = true;
  } catch (e) {
    ElMessage.error(errDetail(e));
  } finally {
    messagesLoading.value = false;
    scrollToBottom();
  }
}

async function onModelChange() {
  const c = activeConv.value;
  if (!c) return;
  c.model = currentModel.value;
  try {
    const out = await updateConversationApi(c.id, { model: currentModel.value });
    c.updatedAt = formatMsgTime(out.updated_at);
  } catch (e) {
    ElMessage.error(errDetail(e));
  }
}

function openNewDialog() {
  newTitle.value = "";
  dlgNew.value = true;
}

async function confirmNew() {
  try {
    const title = newTitle.value.trim() || "新对话";
    const out = await createConversationApi({ title, model: currentModel.value });
    const nc = mapConvFromApi(out);
    nc.messagesLoaded = true;
    nc.messages = [];
    conversations.value.unshift(nc);
    activeId.value = nc.id;
    dlgNew.value = false;
    ElMessage.success("已创建");
  } catch (e) {
    ElMessage.error(errDetail(e));
  }
}

async function onConvMenu(cmd: string, c: Conversation) {
  if (cmd === "rename") {
    renameConvId.value = c.id;
    renameTitle.value = c.title;
    dlgRename.value = true;
  } else if (cmd === "export") {
    activeId.value = c.id;
    if (!c.messagesLoaded) {
      await selectConv(c.id);
    }
    openExportDialog();
  } else if (cmd === "delete") {
    deleteTarget.value = c;
    dlgDelete.value = true;
  }
}

async function confirmRename() {
  const id = renameConvId.value;
  if (id == null) return;
  const t = renameTitle.value.trim();
  if (!t) {
    ElMessage.warning("标题不能为空");
    return;
  }
  try {
    const out = await updateConversationApi(id, { title: t });
    const c = conversations.value.find((x) => x.id === id);
    if (c) {
      c.title = out.title;
      c.updatedAt = formatMsgTime(out.updated_at);
    }
    dlgRename.value = false;
    ElMessage.success("已重命名");
  } catch (e) {
    ElMessage.error(errDetail(e));
  }
}

async function confirmDelete() {
  const t = deleteTarget.value;
  if (!t) return;
  try {
    await deleteConversationApi(t.id);
    conversations.value = conversations.value.filter((x) => x.id !== t.id);
    if (activeId.value === t.id) {
      activeId.value = conversations.value[0]?.id ?? null;
      if (activeId.value != null) {
        await selectConv(activeId.value);
      }
    }
    dlgDelete.value = false;
    deleteTarget.value = null;
    ElMessage.success("已删除");
  } catch (e) {
    ElMessage.error(errDetail(e));
  }
}

function savePrefs() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs.value));
  dlgSettings.value = false;
  ElMessage.success("已保存到浏览器本地");
}

async function confirmClear() {
  const c = activeConv.value;
  if (!c) return;
  try {
    await clearConversationMessagesApi(c.id);
    c.messages = [];
    c.updatedAt = formatMsgTime(new Date().toISOString());
    dlgClear.value = false;
    ElMessage.success("已清空");
  } catch (e) {
    ElMessage.error(errDetail(e));
  }
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

async function send() {
  if (prefs.value.stream) {
    await sendStream();
  } else {
    await sendBlock();
  }
}

async function sendBlock() {
  const c = activeConv.value;
  if (!c || !draft.value.trim()) return;
  const text = draft.value.trim();
  draft.value = "";
  scrollToBottom();

  sending.value = true;
  abortRef.value = new AbortController();
  try {
    const res = await chatTurnApi(
      c.id,
      {
        content: text,
        system_prompt: prefs.value.systemPrompt.trim() || undefined,
        temperature: prefs.value.temperature,
        max_tokens: prefs.value.maxTokens,
        model: c.model || undefined,
      },
      { signal: abortRef.value.signal }
    );
    c.messages.push(mapMsgFromApi(res.user_message));
    c.messages.push(mapMsgFromApi(res.assistant_message));
    c.messagesLoaded = true;
    syncConvMeta(c, res.title, res.updated_at);
  } catch (e: unknown) {
    if (axios.isAxiosError(e) && e.code === "ERR_CANCELED") {
      ElMessage.info("已停止");
    } else {
      ElMessage.error(errDetail(e));
    }
  } finally {
    sending.value = false;
    abortRef.value = null;
    scrollToBottom();
  }
}

async function sendStream() {
  const c = activeConv.value;
  if (!c || !draft.value.trim()) return;
  const text = draft.value.trim();
  draft.value = "";
  streamingReply.value = "";
  scrollToBottom();

  sending.value = true;
  abortRef.value = new AbortController();
  try {
    await chatTurnStreamApi(
      c.id,
      {
        content: text,
        system_prompt: prefs.value.systemPrompt.trim() || undefined,
        temperature: prefs.value.temperature,
        max_tokens: prefs.value.maxTokens,
        model: c.model || undefined,
      },
      {
        signal: abortRef.value.signal,
        onChunk: (t) => {
          streamingReply.value += t;
        },
        onDone: (d) => {
          c.messages.push(mapMsgFromApi(d.user_message));
          c.messages.push(mapMsgFromApi(d.assistant_message));
          c.messagesLoaded = true;
          syncConvMeta(c, d.title, d.updated_at);
        },
        onError: (m) => ElMessage.error(m),
      }
    );
  } catch (e: unknown) {
    if (e instanceof Error && e.name === "AbortError") {
      ElMessage.info("已停止");
    } else if (axios.isAxiosError(e) && e.code === "ERR_CANCELED") {
      ElMessage.info("已停止");
    } else {
      ElMessage.error(e instanceof Error ? e.message : errDetail(e));
    }
  } finally {
    streamingReply.value = "";
    sending.value = false;
    abortRef.value = null;
    scrollToBottom();
  }
}

function stopRequest() {
  abortRef.value?.abort();
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
  --ai-accent: var(--el-color-primary);
  --ai-accent-soft: var(--el-color-primary-light-9);
  --ai-sidebar-bg: var(--el-bg-color);
  --ai-msg-user: linear-gradient(
    135deg,
    var(--el-color-primary) 0%,
    var(--el-color-primary-light-3) 100%
  );
  --ai-msg-bot-bg: #ffffff;
  --ai-msg-bot-border: #e2e8f0;

  padding: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background: #f5f7fb;
}

.ai-chat-shell {
  flex: 1;
  min-height: 0;
  display: flex;
  gap: 0;
  overflow: hidden;
}

/* ========== 侧栏 ========== */
.aside-card {
  width: 280px;
  flex-shrink: 0;
  border-radius: 0 !important;
  border: none !important;
  border-right: 1px solid var(--el-border-color-lighter) !important;
  background: var(--ai-sidebar-bg) !important;
}

.aside-card :deep(.el-card__body) {
  color: var(--el-text-color-primary);
}

.aside-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px 16px 16px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}
.aside-brand__icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: var(--el-color-primary-light-9);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--el-color-primary);
}
.aside-brand__text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.aside-brand__title {
  font-size: 17px;
  font-weight: 700;
  letter-spacing: 0.02em;
  color: #1a1a2e;
}
.aside-brand__sub {
  font-size: 12px;
  color: #6b7280;
}

.aside-actions {
  padding: 12px 14px 10px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.aside-new {
  width: 100%;
  font-weight: 600;
}
.aside-search :deep(.el-input__wrapper) {
  border-radius: 10px;
}
.aside-search :deep(.el-input__inner) {
  color: var(--el-text-color-primary);
}
.aside-search :deep(.el-input__inner::placeholder) {
  color: var(--el-text-color-placeholder);
}
.aside-search :deep(.el-input__prefix) {
  color: var(--el-text-color-secondary);
}

.aside-list-wrap {
  flex: 1;
  min-height: 0;
  padding: 4px 10px 8px;
}
.conv-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.conv-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 10px 6px 10px 12px;
  border-radius: 10px;
  cursor: pointer;
  transition: background 0.15s ease;
  border: 1px solid transparent;
}
.conv-item:hover {
  background: var(--el-fill-color-light);
}
.conv-item.is-active {
  background: var(--el-color-primary-light-9);
  border-color: var(--el-color-primary-light-5);
}
.conv-item__body {
  flex: 1;
  min-width: 0;
}
.conv-item__title {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: var(--el-text-color-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.conv-item__time {
  display: block;
  font-size: 11px;
  color: var(--el-text-color-secondary);
  margin-top: 4px;
}
.conv-item__more {
  color: var(--el-text-color-secondary) !important;
  flex-shrink: 0;
}
.conv-item__more:hover {
  color: var(--el-color-primary) !important;
  background: var(--el-fill-color-light) !important;
}
.dd-ico {
  margin-right: 6px;
  vertical-align: middle;
}

.aside-foot {
  padding: 10px 14px 14px;
  border-top: 1px solid var(--el-border-color-lighter);
}

/* ========== 主区 ========== */
.ai-chat-main {
  flex: 1;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background: #f5f7fb;
  /* 消息区与输入框统一最大宽度，大屏少留白 */
  --chat-content-max: min(1280px, 100%);
}

.chat-toolbar {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 12px;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(8px);
  border-bottom: 1px solid var(--el-border-color-lighter);
  flex-wrap: wrap;
}
.chat-toolbar__left {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.chat-title {
  font-size: 16px;
  font-weight: 600;
  color: #0f172a;
  max-width: min(560px, 55vw);
}
.sel-ico {
  color: var(--el-text-color-secondary);
}

.chat-messages {
  flex: 1;
  min-height: 0;
  padding: 20px 12px;
}
.chat-empty-main {
  min-height: 280px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.welcome-card {
  width: 100%;
  max-width: var(--chat-content-max);
  border-radius: 16px !important;
  border: 1px solid var(--el-border-color-lighter) !important;
}
.welcome-inner {
  text-align: center;
  padding: 8px 8px 4px;
}
.welcome-logo {
  color: var(--ai-accent);
  margin-bottom: 8px;
}
.welcome-h2 {
  margin: 0 0 8px;
  font-size: 20px;
  font-weight: 700;
  color: #0f172a;
}
.welcome-desc {
  margin: 0;
  font-size: 14px;
  color: #64748b;
  line-height: 1.6;
}
.welcome-tips {
  text-align: left;
  margin: 0;
  padding-left: 20px;
  font-size: 13px;
  color: #475569;
  line-height: 1.75;
}
.welcome-tips kbd {
  display: inline-block;
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 11px;
  font-family: inherit;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
}

.msg-list {
  width: 100%;
  max-width: var(--chat-content-max);
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding-bottom: 28px;
}
.msg-row {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}
.msg-row--user {
  flex-direction: row-reverse;
}
.msg-row--user .msg-stack {
  align-items: flex-end;
}
.msg-row--user .msg-meta {
  justify-content: flex-end;
}
.msg-avatar {
  flex-shrink: 0;
}
.msg-avatar--user {
  background: var(--ai-msg-user) !important;
  color: #fff !important;
}
.msg-avatar--bot {
  background: #ecfdf5 !important;
  color: #047857 !important;
  border: 1px solid #d1fae5;
}
.msg-stack {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
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
  color: #64748b;
}
.msg-time {
  font-size: 11px;
  color: #94a3b8;
}
.msg-bubble {
  max-width: 100%;
  padding: 12px 16px;
  border-radius: 14px;
  font-size: 14px;
  line-height: 1.65;
  white-space: pre-wrap;
  word-break: break-word;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.06);
}
.msg-bubble--user {
  background: var(--ai-msg-user);
  color: #fff;
  border-bottom-right-radius: 4px;
}
.msg-bubble--assistant {
  background: var(--ai-msg-bot-bg);
  color: #1e293b;
  border: 1px solid var(--ai-msg-bot-border);
  border-bottom-left-radius: 4px;
}
.msg-bubble--assistant.chat-md {
  white-space: normal;
}
.msg-bubble--assistant.chat-md :deep(.markdown-body) {
  font-size: 14px;
}
.msg-bubble--assistant.chat-md :deep(h1),
.msg-bubble--assistant.chat-md :deep(h2),
.msg-bubble--assistant.chat-md :deep(h3),
.msg-bubble--assistant.chat-md :deep(h4) {
  margin: 0.6em 0 0.35em;
  font-weight: 700;
  line-height: 1.35;
  color: #0f172a;
}
.msg-bubble--assistant.chat-md :deep(h1) {
  font-size: 1.35em;
  border-bottom: 1px solid #e2e8f0;
  padding-bottom: 0.25em;
}
.msg-bubble--assistant.chat-md :deep(h2) {
  font-size: 1.2em;
}
.msg-bubble--assistant.chat-md :deep(p) {
  margin: 0.4em 0;
}
.msg-bubble--assistant.chat-md :deep(p:first-child) {
  margin-top: 0;
}
.msg-bubble--assistant.chat-md :deep(p:last-child) {
  margin-bottom: 0;
}
.msg-bubble--assistant.chat-md :deep(ul),
.msg-bubble--assistant.chat-md :deep(ol) {
  margin: 0.4em 0;
  padding-left: 1.35em;
}
.msg-bubble--assistant.chat-md :deep(blockquote) {
  margin: 0.5em 0;
  padding: 0.25em 0 0.25em 0.75em;
  border-left: 3px solid #cbd5e1;
  color: #475569;
}
.msg-bubble--assistant.chat-md :deep(pre) {
  margin: 0.65em 0;
  padding: 12px 14px;
  border-radius: 10px;
  overflow-x: auto;
  background: #f1f5f9 !important;
  border: 1px solid #e2e8f0;
}
.msg-bubble--assistant.chat-md :deep(pre code) {
  display: block;
  background: transparent !important;
  padding: 0;
  font-size: 13px;
  line-height: 1.5;
}
.msg-bubble--assistant.chat-md :deep(code:not(pre code)) {
  padding: 0.15em 0.4em;
  border-radius: 6px;
  background: #f1f5f9;
  font-size: 0.9em;
}
.msg-bubble--assistant.chat-md :deep(a) {
  color: var(--el-color-primary);
}

/* ========== 输入区 ========== */
.chat-composer {
  flex-shrink: 0;
  padding: 12px 12px 18px;
  background: linear-gradient(180deg, transparent 0%, rgba(245, 247, 251, 0.95) 35%);
}
.composer-card {
  width: 100%;
  max-width: var(--chat-content-max);
  margin: 0 auto;
  border-radius: 16px !important;
  border: 1px solid var(--el-border-color-lighter) !important;
}
.composer-tools {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
  flex-wrap: wrap;
}
.composer-label {
  font-size: 12px;
  color: #64748b;
}
.composer-input-row {
  display: flex;
  gap: 12px;
  align-items: flex-end;
}
.composer-textarea :deep(textarea) {
  font-size: 14px;
  line-height: 1.55;
}
.composer-textarea {
  flex: 1;
  min-width: 0;
}
.composer-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex-shrink: 0;
}
.composer-hint {
  margin: 10px 0 0;
  font-size: 12px;
  color: #94a3b8;
  display: flex;
  align-items: center;
  gap: 6px;
}

@media (max-width: 900px) {
  .ai-chat-shell {
    flex-direction: column;
  }
  .aside-card {
    width: 100%;
    max-height: 38vh;
    border-right: none !important;
    border-bottom: 1px solid var(--el-border-color-lighter) !important;
  }
}
</style>

<style>
@import "github-markdown-css/github-markdown-light.css";
@import "highlight.js/styles/github.css";
</style>
