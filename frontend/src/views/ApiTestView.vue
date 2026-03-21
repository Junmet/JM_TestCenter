<!--
  接口测试（HTTP 客户端）— 前端静态原型：集合、历史、环境、鉴权、Params/Headers/Body、
  前置脚本/后置断言、请求设置、导入/导出 cURL、响应 Body/Headers/Cookies 等。
  发送结果为本地模拟，未发起真实网络请求。
-->
<template>
  <div class="page-view api-test-page">
    <el-container class="api-test-shell">
      <!-- 侧栏：集合 + 历史 -->
      <el-aside class="api-aside" width="280px">
        <div class="aside-head">
          <span class="aside-title">接口测试</span>
          <el-tag size="small" type="info">静态演示</el-tag>
        </div>
        <el-tabs v-model="sidebarTab" class="aside-tabs">
          <el-tab-pane label="集合" name="collections">
            <div class="aside-toolbar">
              <el-button size="small" type="primary" @click="openNewFolder">新建目录</el-button>
              <el-button size="small" @click="openSaveAs">保存当前</el-button>
            </div>
            <el-tree
              node-key="id"
              :data="collectionTree"
              :props="{ label: 'label', children: 'children' }"
              default-expand-all
              highlight-current
              class="col-tree"
              @node-click="onTreeNodeClick"
            />
          </el-tab-pane>
          <el-tab-pane label="历史" name="history">
            <el-scrollbar max-height="calc(100vh - 220px)">
              <div
                v-for="h in historyList"
                :key="h.id"
                class="hist-item"
                @click="loadSnapshot(h.id)"
              >
                <el-tag size="small" :type="methodTagType(h.method)">{{ h.method }}</el-tag>
                <span class="hist-title">{{ h.title }}</span>
                <span class="hist-at">{{ h.at }}</span>
              </div>
            </el-scrollbar>
          </el-tab-pane>
        </el-tabs>
      </el-aside>

      <el-container direction="vertical" class="api-main">
        <!-- 顶栏 -->
        <el-header class="api-toolbar" height="auto">
          <div class="toolbar-row">
            <el-select v-model="activeEnvId" placeholder="环境" style="width: 160px" @change="onEnvChange">
              <el-option v-for="e in environments" :key="e.id" :label="e.name" :value="e.id" />
            </el-select>
            <el-button @click="openEnvManage">环境管理</el-button>
            <el-button @click="resetWorkspace">新建请求</el-button>
            <el-button @click="openImport">导入</el-button>
            <el-button @click="openSaveAs">保存到集合</el-button>
            <el-button @click="openExportCurl">导出 cURL</el-button>
            <el-button @click="duplicateRequest">复制请求</el-button>
            <el-button @click="openSettings">请求设置</el-button>
            <el-button @click="openCookieManager">Cookie 管理</el-button>
            <div class="toolbar-spacer" />
            <el-text type="info" size="small">URL 预览：{{ resolvedUrlPreview }}</el-text>
          </div>
        </el-header>

        <el-main class="api-body">
          <!-- 请求行 -->
          <div class="request-line">
            <el-select v-model="method" class="method-select" style="width: 118px">
              <el-option v-for="m in METHODS" :key="m" :label="m" :value="m" />
            </el-select>
            <el-input v-model="url" placeholder="请输入 URL，支持 {{变量}}" clearable class="url-input" />
            <el-button type="primary" :loading="sending" @click="sendMock">发送</el-button>
            <el-button @click="cancelRequest" :disabled="!sending">取消</el-button>
          </div>

          <!-- 请求配置 -->
          <el-tabs v-model="requestTab" type="border-card" class="req-tabs">
            <el-tab-pane label="Params" name="params">
              <p class="tab-hint">Query 参数，将自动拼接到 URL（静态演示不拼接，仅展示）</p>
              <kv-editor v-model="params" />
            </el-tab-pane>
            <el-tab-pane label="Authorization" name="auth">
              <el-form label-width="120px" class="auth-form">
                <el-form-item label="类型">
                  <el-select v-model="authType" style="width: 220px">
                    <el-option label="No Auth" value="none" />
                    <el-option label="Bearer Token" value="bearer" />
                    <el-option label="Basic Auth" value="basic" />
                    <el-option label="API Key" value="apikey" />
                  </el-select>
                </el-form-item>
                <template v-if="authType === 'bearer'">
                  <el-form-item label="Token">
                    <el-input v-model="bearerToken" type="textarea" :rows="2" placeholder="Bearer Token" />
                  </el-form-item>
                </template>
                <template v-else-if="authType === 'basic'">
                  <el-form-item label="用户名">
                    <el-input v-model="basicUser" />
                  </el-form-item>
                  <el-form-item label="密码">
                    <el-input v-model="basicPass" type="password" show-password />
                  </el-form-item>
                </template>
                <template v-else-if="authType === 'apikey'">
                  <el-form-item label="Key 名">
                    <el-input v-model="apiKeyName" placeholder="如 X-API-Key" />
                  </el-form-item>
                  <el-form-item label="Key 值">
                    <el-input v-model="apiKeyValue" />
                  </el-form-item>
                  <el-form-item label="位置">
                    <el-radio-group v-model="apiKeyIn">
                      <el-radio value="header">Header</el-radio>
                      <el-radio value="query">Query</el-radio>
                    </el-radio-group>
                  </el-form-item>
                </template>
              </el-form>
            </el-tab-pane>
            <el-tab-pane label="Headers" name="headers">
              <kv-editor v-model="headers" />
            </el-tab-pane>
            <el-tab-pane label="Cookies" name="cookies_req">
              <p class="tab-hint">随请求发送的 Cookie（静态编辑；真实发送由后续后端代理）</p>
              <kv-editor v-model="requestCookies" />
            </el-tab-pane>
            <el-tab-pane label="Body" name="body">
              <el-radio-group v-model="bodyKind" class="body-kind">
                <el-radio-button value="none">none</el-radio-button>
                <el-radio-button value="form-data">form-data</el-radio-button>
                <el-radio-button value="urlencoded">x-www-form-urlencoded</el-radio-button>
                <el-radio-button value="raw">raw</el-radio-button>
                <el-radio-button value="binary">binary</el-radio-button>
                <el-radio-button value="graphql">GraphQL</el-radio-button>
              </el-radio-group>
              <div v-if="bodyKind === 'none'" class="tab-hint">当前请求无 Body</div>
              <div v-else-if="bodyKind === 'form-data'">
                <p class="tab-hint">multipart/form-data（文件选择为占位，后续接后端上传）</p>
                <el-table :data="formParts" border size="small" class="kv-table">
                  <el-table-column width="50">
                    <template #header>启用</template>
                    <template #default="{ row }">
                      <el-checkbox v-model="row.enabled" />
                    </template>
                  </el-table-column>
                  <el-table-column label="类型" width="100">
                    <template #default="{ row }">
                      <el-select v-model="row.partType" size="small">
                        <el-option label="text" value="text" />
                        <el-option label="file" value="file" />
                      </el-select>
                    </template>
                  </el-table-column>
                  <el-table-column label="Key" prop="key">
                    <template #default="{ row }">
                      <el-input v-model="row.key" size="small" />
                    </template>
                  </el-table-column>
                  <el-table-column label="Value" prop="value">
                    <template #default="{ row }">
                      <el-input v-if="row.partType === 'text'" v-model="row.value" size="small" />
                      <el-button v-else size="small" disabled>选择文件…</el-button>
                    </template>
                  </el-table-column>
                  <el-table-column width="70" align="center">
                    <template #default="{ $index }">
                      <el-button type="danger" link size="small" @click="removeRow(formParts, $index)">删</el-button>
                    </template>
                  </el-table-column>
                </el-table>
                <el-button class="mt8" size="small" @click="addFormRow">添加字段</el-button>
              </div>
              <div v-else-if="bodyKind === 'urlencoded'">
                <kv-editor v-model="urlEncodedParts" />
              </div>
              <div v-else-if="bodyKind === 'raw'">
                <el-select v-model="rawMime" style="width: 160px; margin-bottom: 8px">
                  <el-option label="JSON" value="json" />
                  <el-option label="XML" value="xml" />
                  <el-option label="Text" value="text" />
                  <el-option label="HTML" value="html" />
                </el-select>
                <el-input v-model="rawBody" type="textarea" :rows="14" class="raw-area" placeholder="请求体" />
              </div>
              <div v-else-if="bodyKind === 'binary'">
                <el-upload drag action="#" :auto-upload="false" disabled>
                  <el-icon class="el-icon--upload"><upload-filled /></el-icon>
                  <div class="el-upload__text">拖拽文件到此处（静态占位）</div>
                </el-upload>
              </div>
              <div v-else-if="bodyKind === 'graphql'">
                <el-form label-width="100px" class="gql-form">
                  <el-form-item label="Operation">
                    <el-input v-model="graphqlOperation" placeholder="可选 operation name" />
                  </el-form-item>
                  <el-form-item label="Query">
                    <el-input v-model="graphqlQuery" type="textarea" :rows="8" class="mono" />
                  </el-form-item>
                  <el-form-item label="Variables">
                    <el-input v-model="graphqlVariables" type="textarea" :rows="5" class="mono" placeholder="{}" />
                  </el-form-item>
                </el-form>
              </div>
            </el-tab-pane>
            <el-tab-pane label="前置脚本" name="pre">
              <p class="tab-hint">发送前执行（Postman 风格占位；后续可接沙箱执行）</p>
              <el-input v-model="preScript" type="textarea" :rows="12" class="mono" placeholder="// JavaScript" />
            </el-tab-pane>
            <el-tab-pane label="后置断言/测试" name="tests">
              <p class="tab-hint">响应后断言脚本（占位）</p>
              <el-input v-model="postTests" type="textarea" :rows="12" class="mono" placeholder="// JavaScript" />
            </el-tab-pane>
          </el-tabs>

          <!-- 响应 -->
          <div class="response-wrap">
            <div class="response-meta">
              <span>响应</span>
              <el-tag v-if="lastResponse" :type="lastResponse.status >= 400 ? 'danger' : 'success'">
                {{ lastResponse.status }} {{ lastResponse.statusText }}
              </el-tag>
              <el-text v-if="lastResponse" size="small">
                耗时 {{ lastResponse.timeMs }} ms · 约 {{ lastResponse.sizeBytes }} B
              </el-text>
              <el-button v-if="lastResponse" size="small" text type="primary" @click="copyResponseBody">
                复制 Body
              </el-button>
            </div>
            <el-tabs v-model="responseTab" type="card">
              <el-tab-pane label="Body" name="body">
                <div class="resp-toolbar">
                  <el-radio-group v-model="bodyViewMode" size="small">
                    <el-radio-button value="pretty">Pretty</el-radio-button>
                    <el-radio-button value="raw">Raw</el-radio-button>
                    <el-radio-button value="preview">Preview</el-radio-button>
                  </el-radio-group>
                </div>
                <div v-if="lastResponse && bodyViewMode === 'preview'" class="resp-preview-wrap">
                  <iframe class="resp-preview-iframe" title="preview" sandbox="" srcdoc="<!DOCTYPE html><html><body><p>静态预览：后续可根据 HTML 响应渲染；当前为占位。</p></body></html>" />
                </div>
                <pre
                  v-else-if="lastResponse"
                  class="resp-pre"
                ><code>{{ bodyViewMode === "pretty" ? prettyBody : lastResponse.body }}</code></pre>
                <el-empty v-else description="点击「发送」查看静态模拟响应" />
              </el-tab-pane>
              <el-tab-pane label="Headers" name="headers">
                <el-table v-if="lastResponse" :data="lastResponse.headers" size="small" border stripe>
                  <el-table-column prop="key" label="名称" width="180" />
                  <el-table-column prop="value" label="值" />
                </el-table>
                <el-empty v-else description="无数据" />
              </el-tab-pane>
              <el-tab-pane label="Cookies" name="cookies">
                <el-table v-if="lastResponse" :data="lastResponse.cookies" size="small" border stripe>
                  <el-table-column prop="key" label="名称" width="160" />
                  <el-table-column prop="value" label="值" />
                  <el-table-column prop="description" label="备注" width="120" />
                </el-table>
                <el-empty v-else description="无数据" />
              </el-tab-pane>
            </el-tabs>
          </div>
        </el-main>
      </el-container>
    </el-container>

    <!-- 保存到集合 -->
    <el-dialog v-model="dlgSave" title="保存到集合" width="520px" destroy-on-close>
      <el-form label-width="100px">
        <el-form-item label="名称" required>
          <el-input v-model="saveForm.name" placeholder="请求名称" />
        </el-form-item>
        <el-form-item label="目录">
          <el-tree-select
            v-model="saveForm.folderId"
            :data="folderTreeSelect"
            check-strictly
            :render-after-expand="false"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="saveForm.description" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dlgSave = false">取消</el-button>
        <el-button type="primary" @click="confirmSave">保存（静态）</el-button>
      </template>
    </el-dialog>

    <!-- 环境管理 -->
    <el-dialog v-model="dlgEnv" title="环境管理" width="720px" destroy-on-close>
      <el-table :data="environments" size="small" border>
        <el-table-column prop="name" label="环境名" />
        <el-table-column label="操作" width="200">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="editEnv(row)">变量</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-divider />
      <div v-if="editingEnv">
        <h4 class="sub-h4">{{ editingEnv.name }} — 变量</h4>
        <kv-editor v-model="editingEnv.variables" />
      </div>
      <template #footer>
        <el-button @click="dlgEnv = false">关闭</el-button>
        <el-button type="primary" @click="applyEnvEdit">应用（本地）</el-button>
      </template>
    </el-dialog>

    <!-- 导入 -->
    <el-dialog v-model="dlgImport" title="导入" width="640px" destroy-on-close>
      <el-tabs v-model="importTab">
        <el-tab-pane label="cURL" name="curl">
          <el-input v-model="importCurl" type="textarea" :rows="12" placeholder="粘贴 cURL" />
          <el-button class="mt8" type="primary" @click="parseCurlImport">解析并填充</el-button>
        </el-tab-pane>
        <el-tab-pane label="OpenAPI 3" name="openapi">
          <el-input v-model="importOpenapi" type="textarea" :rows="12" placeholder="粘贴 OpenAPI JSON/YAML（静态占位）" />
          <el-alert class="mt8" type="info" :closable="false" title="仅 UI 占位：后续可解析 paths 生成集合" />
        </el-tab-pane>
      </el-tabs>
      <template #footer>
        <el-button @click="dlgImport = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 请求设置 -->
    <el-dialog v-model="dlgSettings" title="请求设置" width="520px">
      <el-form label-width="140px">
        <el-form-item label="超时 (ms)">
          <el-input-number v-model="settings.timeoutMs" :min="1000" :max="120000" :step="1000" />
        </el-form-item>
        <el-form-item label="自动跟随重定向">
          <el-switch v-model="settings.followRedirects" />
        </el-form-item>
        <el-form-item label="校验 SSL 证书">
          <el-switch v-model="settings.verifySsl" />
        </el-form-item>
        <el-form-item label="客户端证书">
          <el-upload action="#" :auto-upload="false" disabled>
            <el-button disabled>选择 .p12/.pem（占位）</el-button>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dlgSettings = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 导出 cURL -->
    <el-dialog v-model="dlgExport" title="导出 cURL" width="640px">
      <el-input v-model="exportCurlText" type="textarea" :rows="14" readonly class="mono" />
      <template #footer>
        <el-button @click="copyExportCurl">复制</el-button>
        <el-button type="primary" @click="dlgExport = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 新建目录 -->
    <el-dialog v-model="dlgFolder" title="新建目录" width="420px">
      <el-form label-width="80px">
        <el-form-item label="名称">
          <el-input v-model="newFolderName" />
        </el-form-item>
        <el-form-item label="父级">
          <el-tree-select v-model="newFolderParent" :data="folderTreeSelect" check-strictly style="width: 100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dlgFolder = false">取消</el-button>
        <el-button type="primary" @click="confirmNewFolder">确定（静态）</el-button>
      </template>
    </el-dialog>

    <!-- Cookie 管理 -->
    <el-dialog v-model="dlgCookies" title="Cookie 管理（域名）" width="640px">
      <el-table :data="cookieJar" border size="small">
        <el-table-column prop="domain" label="域名" width="160" />
        <el-table-column prop="name" label="名称" width="120" />
        <el-table-column prop="value" label="值" />
      </el-table>
      <el-alert class="mt8" type="info" :closable="false" title="静态示例；后续可与真实请求 Cookie 同步" />
      <template #footer>
        <el-button @click="dlgCookies = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { UploadFilled } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { computed, ref } from "vue";
import type { AuthType, BodyKind, HttpMethod, KvRow, MockResponse, RawBodyMime, RequestSettings } from "./api-test/apiTestTypes";
import {
  buildCurlPreview,
  COLLECTION_TREE_UI,
  MOCK_ENVIRONMENTS,
  MOCK_HISTORY,
  MOCK_REQUEST_MAP,
  mockSendResponse,
} from "./api-test/apiTestMocks";
import KvEditor from "./api-test/KvEditor.vue";

const METHODS: HttpMethod[] = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"];

const collectionTree = ref(COLLECTION_TREE_UI);
const historyList = ref([...MOCK_HISTORY]);
const sidebarTab = ref("collections");

const activeEnvId = ref(MOCK_ENVIRONMENTS[0]?.id ?? "");
const environments = ref([...MOCK_ENVIRONMENTS]);

const method = ref<HttpMethod>("GET");
const url = ref("{{baseUrl}}/v1/health");
const params = ref<KvRow[]>([]);
const headers = ref<KvRow[]>([]);
const authType = ref<AuthType>("none");
const bearerToken = ref("");
const basicUser = ref("");
const basicPass = ref("");
const apiKeyName = ref("");
const apiKeyValue = ref("");
const apiKeyIn = ref<"header" | "query">("header");

const bodyKind = ref<BodyKind>("none");
const rawMime = ref<RawBodyMime>("json");
const rawBody = ref("");
const formParts = ref<KvRow[]>([]);
const urlEncodedParts = ref<KvRow[]>([]);
const requestCookies = ref<KvRow[]>([]);
const graphqlOperation = ref("");
const graphqlQuery = ref(`query Demo {\n  __typename\n}`);
const graphqlVariables = ref("{}");

const preScript = ref("");
const postTests = ref("");

const requestTab = ref("params");
const responseTab = ref("body");
const bodyViewMode = ref<"pretty" | "raw" | "preview">("pretty");

const sending = ref(false);
const lastResponse = ref<MockResponse | null>(null);

const settings = ref<RequestSettings>({
  timeoutMs: 30000,
  followRedirects: true,
  verifySsl: true,
});

/** 弹窗 */
const dlgSave = ref(false);
const dlgEnv = ref(false);
const dlgImport = ref(false);
const dlgSettings = ref(false);
const dlgExport = ref(false);
const dlgFolder = ref(false);
const dlgCookies = ref(false);

const saveForm = ref({ name: "", folderId: "root-demo", description: "" });
const importTab = ref("curl");
const importCurl = ref(
  `curl -X POST 'https://api.example.com/v1/demo' \\\n  -H 'Content-Type: application/json' \\\n  --data-raw '{\"a\":1}'`,
);
const importOpenapi = ref("");
const exportCurlText = ref("");
const newFolderName = ref("");
const newFolderParent = ref("root-demo");

const editingEnv = ref<(typeof environments.value)[0] | null>(null);

const cookieJar = ref([
  { domain: "api.example.com", name: "sid", value: "mock_session" },
  { domain: ".example.com", name: "track", value: "1" },
]);

const folderTreeSelect = computed(() => {
  const map = (nodes: typeof COLLECTION_TREE_UI): { label: string; value: string; children?: unknown[] }[] =>
    nodes.map((n) => ({
      label: n.label,
      value: n.id,
      children: n.children ? map(n.children) : undefined,
    }));
  return map(collectionTree.value);
});

const activeEnv = computed(() => environments.value.find((e) => e.id === activeEnvId.value));

const resolvedUrlPreview = computed(() => {
  let u = url.value;
  const vars = activeEnv.value?.variables.filter((v) => v.enabled) ?? [];
  for (const v of vars) {
    if (v.key) u = u.split(`{{${v.key}}}`).join(v.value);
  }
  return u || "—";
});

const prettyBody = computed(() => {
  if (!lastResponse.value) return "";
  if (lastResponse.value.bodyMime !== "json") return lastResponse.value.body;
  try {
    return JSON.stringify(JSON.parse(lastResponse.value.body), null, 2);
  } catch {
    return lastResponse.value.body;
  }
});

function methodTagType(m: HttpMethod): "success" | "warning" | "info" | "danger" {
  if (m === "GET" || m === "HEAD") return "success";
  if (m === "POST" || m === "PUT" || m === "PATCH") return "warning";
  if (m === "DELETE") return "danger";
  return "info";
}

function genUid() {
  return `row-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

function loadSnapshot(id: string) {
  const snap = MOCK_REQUEST_MAP[id];
  if (!snap) {
    ElMessage.warning("未找到该条目的静态快照");
    return;
  }
  method.value = snap.method;
  url.value = snap.url;
  params.value = snap.params.map((r) => ({ ...r }));
  headers.value = snap.headers.map((r) => ({ ...r }));
  authType.value = snap.authType;
  bearerToken.value = snap.bearerToken;
  basicUser.value = snap.basicUser;
  basicPass.value = snap.basicPass;
  apiKeyName.value = snap.apiKeyName;
  apiKeyValue.value = snap.apiKeyValue;
  apiKeyIn.value = snap.apiKeyIn;
  bodyKind.value = snap.bodyKind;
  rawMime.value = snap.rawMime;
  rawBody.value = snap.rawBody;
  formParts.value = snap.formParts.map((r) => ({ ...r }));
  urlEncodedParts.value = snap.urlEncodedParts.map((r) => ({ ...r }));
  requestCookies.value = [];
  graphqlOperation.value = "";
  graphqlQuery.value = `query Demo {\n  __typename\n}`;
  graphqlVariables.value = "{}";
  preScript.value = snap.preScript;
  postTests.value = snap.postTests;
  lastResponse.value = null;
  ElMessage.success("已载入静态请求");
}

function onTreeNodeClick(data: { id: string; isRequest?: boolean }) {
  if (data.isRequest) loadSnapshot(data.id);
}

function resetWorkspace() {
  method.value = "GET";
  url.value = "{{baseUrl}}/v1/health";
  params.value = [];
  headers.value = [];
  authType.value = "none";
  bearerToken.value = "";
  basicUser.value = "";
  basicPass.value = "";
  apiKeyName.value = "";
  apiKeyValue.value = "";
  bodyKind.value = "none";
  rawBody.value = "";
  formParts.value = [];
  urlEncodedParts.value = [];
  requestCookies.value = [];
  graphqlOperation.value = "";
  graphqlQuery.value = `query Demo {\n  __typename\n}`;
  graphqlVariables.value = "{}";
  preScript.value = "";
  postTests.value = "";
  lastResponse.value = null;
}

function onEnvChange() {
  ElMessage.info(`已切换环境：${activeEnv.value?.name ?? ""}`);
}

function openEnvManage() {
  editingEnv.value = environments.value.find((e) => e.id === activeEnvId.value) ?? environments.value[0] ?? null;
  if (editingEnv.value) {
    editingEnv.value = {
      ...editingEnv.value,
      variables: editingEnv.value.variables.map((v) => ({ ...v })),
    };
  }
  dlgEnv.value = true;
}

function applyEnvEdit() {
  if (!editingEnv.value) return;
  const idx = environments.value.findIndex((e) => e.id === editingEnv.value!.id);
  if (idx >= 0) environments.value[idx] = { ...editingEnv.value, variables: editingEnv.value.variables.map((v) => ({ ...v })) };
  dlgEnv.value = false;
  ElMessage.success("环境变量已更新（本地）");
}

function editEnv(row: (typeof environments.value)[0]) {
  editingEnv.value = {
    ...row,
    variables: row.variables.map((v) => ({ ...v })),
  };
}

function openSaveAs() {
  saveForm.value = { name: "未命名请求", folderId: "f-auth", description: "" };
  dlgSave.value = true;
}

function confirmSave() {
  dlgSave.value = false;
  ElMessage.success("已保存（静态演示，未写入服务端）");
}

function openImport() {
  dlgImport.value = true;
}

function parseCurlImport() {
  const text = importCurl.value.trim();
  const m = text.match(/curl\s+(?:-X\s+(\w+)\s+)?['"]([^'"]+)['"]/i);
  if (m) {
    method.value = (m[1]?.toUpperCase() as HttpMethod) || "GET";
    url.value = m[2];
  }
  if (/Content-Type:\s*application\/json/i.test(text)) {
    bodyKind.value = "raw";
    rawMime.value = "json";
  }
  const dataRaw = text.match(/--data-raw\s+['"]([\s\S]*?)['"]/);
  if (dataRaw) {
    rawBody.value = dataRaw[1].replace(/\\'/g, "'");
    bodyKind.value = "raw";
  }
  dlgImport.value = false;
  ElMessage.success("已从 cURL 解析并填充（简化规则）");
}

function openSettings() {
  dlgSettings.value = true;
}

function openExportCurl() {
  exportCurlText.value = buildCurlPreview({
    method: method.value,
    url: resolvedUrlPreview.value,
    headers: headers.value,
    bodyKind: bodyKind.value,
    rawBody: rawBody.value,
    rawMime: rawMime.value,
    authType: authType.value,
    bearerToken: bearerToken.value,
    basicUser: basicUser.value,
    basicPass: basicPass.value,
    apiKeyName: apiKeyName.value,
    apiKeyValue: apiKeyValue.value,
    apiKeyIn: apiKeyIn.value,
  });
  dlgExport.value = true;
}

function copyExportCurl() {
  navigator.clipboard.writeText(exportCurlText.value);
  ElMessage.success("已复制");
}

function duplicateRequest() {
  saveForm.value = { name: method.value + " 副本", folderId: "f-user", description: "由复制请求生成" };
  dlgSave.value = true;
}

function openNewFolder() {
  newFolderName.value = "";
  newFolderParent.value = "root-demo";
  dlgFolder.value = true;
}

function confirmNewFolder() {
  dlgFolder.value = false;
  ElMessage.success("目录已创建（静态演示，仅提示）");
}

function openCookieManager() {
  dlgCookies.value = true;
}

function removeRow(arr: KvRow[], index: number) {
  arr.splice(index, 1);
}

function addFormRow() {
  formParts.value.push({
    id: genUid(),
    enabled: true,
    key: "",
    value: "",
    partType: "text",
  });
}

let cancelTimer: ReturnType<typeof setTimeout> | null = null;

function sendMock() {
  sending.value = true;
  lastResponse.value = null;
  cancelTimer = setTimeout(() => {
    lastResponse.value = mockSendResponse();
    sending.value = false;
    cancelTimer = null;
    ElMessage.success("已返回静态模拟响应（未发起真实请求）");
  }, 600);
}

function cancelRequest() {
  if (cancelTimer) {
    clearTimeout(cancelTimer);
    cancelTimer = null;
  }
  sending.value = false;
  ElMessage.info("已取消（本地）");
}

function copyResponseBody() {
  if (!lastResponse.value) return;
  navigator.clipboard.writeText(lastResponse.value.body);
  ElMessage.success("已复制 Body");
}
</script>

<style scoped>
.api-test-page {
  padding: 0;
  overflow: hidden;
  background: #f5f7fb;
}
.api-test-shell {
  height: 100%;
  min-height: 0;
}
.api-aside {
  background: #fff;
  border-right: 1px solid #e5e7eb;
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.aside-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 12px 0;
}
.aside-title {
  font-weight: 700;
  font-size: 15px;
  color: #0f172a;
}
.aside-tabs {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  padding: 0 8px 8px;
}
.aside-tabs :deep(.el-tabs__content) {
  flex: 1;
  min-height: 0;
  overflow: auto;
}
.aside-toolbar {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
}
.col-tree {
  width: 100%;
}
.hist-item {
  padding: 8px 10px;
  border-radius: 8px;
  cursor: pointer;
  margin-bottom: 6px;
  border: 1px solid transparent;
}
.hist-item:hover {
  background: #f1f5f9;
  border-color: #e2e8f0;
}
.hist-title {
  display: block;
  font-size: 13px;
  color: #0f172a;
  margin-top: 4px;
}
.hist-at {
  font-size: 12px;
  color: #94a3b8;
}
.api-main {
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.api-toolbar {
  padding: 12px 16px 8px;
  background: #fff;
  border-bottom: 1px solid #e5e7eb;
}
.toolbar-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}
.toolbar-spacer {
  flex: 1;
  min-width: 8px;
}
.api-body {
  padding: 12px 16px 16px;
  min-height: 0;
  overflow: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.request-line {
  display: flex;
  gap: 8px;
  align-items: center;
  background: #fff;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
}
.url-input {
  flex: 1;
  min-width: 0;
}
.req-tabs {
  margin: 0;
  background: #fff;
  border-radius: 10px;
  overflow: hidden;
}
.req-tabs :deep(.el-tabs__content) {
  padding: 12px;
}
.tab-hint {
  margin: 0 0 10px;
  font-size: 12px;
  color: #94a3b8;
}
.body-kind {
  margin-bottom: 12px;
}
.auth-form {
  max-width: 520px;
}
.raw-area {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 13px;
}
.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 13px;
}
.mt8 {
  margin-top: 8px;
}
.kv-table {
  width: 100%;
}
.response-wrap {
  flex: 1;
  min-height: 200px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 10px 12px 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.response-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  font-weight: 600;
  color: #0f172a;
}
.resp-toolbar {
  margin-bottom: 8px;
}
.resp-pre {
  margin: 0;
  padding: 12px;
  background: #0f172a;
  color: #e2e8f0;
  border-radius: 8px;
  max-height: 320px;
  overflow: auto;
  font-size: 12px;
  line-height: 1.5;
}
.resp-preview-wrap {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  overflow: hidden;
  background: #fff;
  min-height: 200px;
}
.resp-preview-iframe {
  width: 100%;
  min-height: 200px;
  border: none;
}
.gql-form {
  max-width: 720px;
}
.sub-h4 {
  margin: 0 0 8px;
  font-size: 14px;
}
</style>
