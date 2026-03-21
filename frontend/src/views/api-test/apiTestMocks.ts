/**
 * 接口测试页：静态示例数据与模拟「发送」结果（后续接后端时替换）
 */
import type {
  ApiEnvironment,
  AuthType,
  BodyKind,
  CollectionFolder,
  HistoryItem,
  HttpMethod,
  KvRow,
  MockResponse,
  RawBodyMime,
} from "./apiTestTypes";

export const MOCK_ENVIRONMENTS: ApiEnvironment[] = [
  {
    id: "env-dev",
    name: "开发环境",
    variables: [
      { id: "v1", enabled: true, key: "baseUrl", value: "https://api.example.com", description: "API 根地址" },
      { id: "v2", enabled: true, key: "token", value: "dev_static_token", description: "Bearer" },
    ],
  },
  {
    id: "env-stg",
    name: "预发环境",
    variables: [
      { id: "v3", enabled: true, key: "baseUrl", value: "https://stg-api.example.com", description: "" },
      { id: "v4", enabled: false, key: "token", value: "", description: "未启用" },
    ],
  },
];

export const MOCK_COLLECTION_TREE: CollectionFolder[] = [
  {
    id: "root-demo",
    label: "示例集合",
    children: [
      {
        id: "f-auth",
        label: "认证模块",
        requestIds: ["req-login", "req-refresh"],
      },
      {
        id: "f-user",
        label: "用户模块",
        requestIds: ["req-user-profile"],
      },
    ],
  },
];

/** el-tree 用：带子节点请求条目的静态树 */
export type CollectionTreeNode = {
  id: string;
  label: string;
  isRequest?: boolean;
  children?: CollectionTreeNode[];
};

export const COLLECTION_TREE_UI: CollectionTreeNode[] = [
  {
    id: "root-demo",
    label: "示例集合",
    children: [
      {
        id: "f-auth",
        label: "认证模块",
        children: [
          { id: "req-login", label: "POST 登录", isRequest: true },
          { id: "req-refresh", label: "POST 刷新令牌", isRequest: true },
        ],
      },
      {
        id: "f-user",
        label: "用户模块",
        children: [{ id: "req-user-profile", label: "GET 当前用户", isRequest: true }],
      },
    ],
  },
];

export const MOCK_HISTORY: HistoryItem[] = [
  {
    id: "h1",
    method: "GET",
    url: "{{baseUrl}}/v1/health",
    title: "健康检查",
    at: "2026-03-21 10:12:33",
  },
  {
    id: "h2",
    method: "POST",
    url: "{{baseUrl}}/v1/auth/login",
    title: "登录",
    at: "2026-03-21 10:11:02",
  },
];

/** 预设请求快照（点击集合/历史时载入） */
export type RequestSnapshot = {
  method: HttpMethod;
  url: string;
  params: KvRow[];
  headers: KvRow[];
  authType: AuthType;
  bearerToken: string;
  basicUser: string;
  basicPass: string;
  apiKeyName: string;
  apiKeyValue: string;
  apiKeyIn: "header" | "query";
  bodyKind: BodyKind;
  rawMime: RawBodyMime;
  rawBody: string;
  formParts: KvRow[];
  urlEncodedParts: KvRow[];
  preScript: string;
  postTests: string;
};

const row = (id: string, enabled: boolean, key: string, value: string, description = ""): KvRow => ({
  id,
  enabled,
  key,
  value,
  description,
});

export const MOCK_REQUEST_MAP: Record<string, RequestSnapshot> = {
  "req-login": {
    method: "POST",
    url: "{{baseUrl}}/v1/auth/login",
    params: [],
    headers: [row("h1", true, "Content-Type", "application/json", "")],
    authType: "none",
    bearerToken: "",
    basicUser: "",
    basicPass: "",
    apiKeyName: "",
    apiKeyValue: "",
    apiKeyIn: "header",
    bodyKind: "raw",
    rawMime: "json",
    rawBody: '{\n  "username": "demo",\n  "password": "******"\n}',
    formParts: [],
    urlEncodedParts: [],
    preScript: "// 示例：设置动态时间戳\n// pm.environment.set('ts', Date.now());",
    postTests:
      '// 示例：断言状态码\n// pm.test("Status 200", () => pm.response.code === 200);\n// pm.test("Has token", () => JSON.parse(pm.response.body).token);',
  },
  "req-refresh": {
    method: "POST",
    url: "{{baseUrl}}/v1/auth/refresh",
    params: [],
    headers: [row("h1", true, "Content-Type", "application/json", "")],
    authType: "bearer",
    bearerToken: "{{token}}",
    basicUser: "",
    basicPass: "",
    apiKeyName: "",
    apiKeyValue: "",
    apiKeyIn: "header",
    bodyKind: "raw",
    rawMime: "json",
    rawBody: "{}",
    formParts: [],
    urlEncodedParts: [],
    preScript: "",
    postTests: "",
  },
  "req-user-profile": {
    method: "GET",
    url: "{{baseUrl}}/v1/users/me",
    params: [row("p1", true, "expand", "roles", "附加字段")],
    headers: [],
    authType: "bearer",
    bearerToken: "{{token}}",
    basicUser: "",
    basicPass: "",
    apiKeyName: "",
    apiKeyValue: "",
    apiKeyIn: "header",
    bodyKind: "none",
    rawMime: "json",
    rawBody: "",
    formParts: [],
    urlEncodedParts: [],
    preScript: "",
    postTests: "",
  },
  h1: {
    method: "GET",
    url: "{{baseUrl}}/v1/health",
    params: [],
    headers: [row("h1", true, "Accept", "application/json", "")],
    authType: "none",
    bearerToken: "",
    basicUser: "",
    basicPass: "",
    apiKeyName: "",
    apiKeyValue: "",
    apiKeyIn: "header",
    bodyKind: "none",
    rawMime: "json",
    rawBody: "",
    formParts: [],
    urlEncodedParts: [],
    preScript: "",
    postTests: "",
  },
  h2: {
    method: "POST",
    url: "{{baseUrl}}/v1/auth/login",
    params: [],
    headers: [],
    authType: "none",
    bearerToken: "",
    basicUser: "",
    basicPass: "",
    apiKeyName: "",
    apiKeyValue: "",
    apiKeyIn: "header",
    bodyKind: "raw",
    rawMime: "json",
    rawBody: "{}",
    formParts: [],
    urlEncodedParts: [],
    preScript: "",
    postTests: "",
  },
};

export function mockSendResponse(): MockResponse {
  return {
    status: 200,
    statusText: "OK",
    timeMs: 238,
    sizeBytes: 428,
    bodyMime: "json",
    body: JSON.stringify(
      {
        code: 0,
        message: "success（静态模拟响应，未真实发起网络请求）",
        data: {
          id: "550e8400-e29b-41d4-a716-446655440000",
          name: "演示数据",
          items: [{ sku: "A-1", qty: 2 }],
        },
        requestId: "req-mock-" + Date.now(),
      },
      null,
      2,
    ),
    headers: [
      row("rh1", true, "content-type", "application/json; charset=utf-8", ""),
      row("rh2", true, "x-request-id", "trace-mock-001", ""),
      row("rh3", true, "server", "jmtestcenter-api-test/0.1", ""),
    ],
    cookies: [
      row("ck1", true, "session_id", "sess_mock_abc123", "HttpOnly"),
      row("ck2", true, "locale", "zh-CN", ""),
    ],
  };
}

export function buildCurlPreview(input: {
  method: HttpMethod;
  url: string;
  headers: KvRow[];
  bodyKind: BodyKind;
  rawBody: string;
  rawMime: string;
  authType: AuthType;
  bearerToken: string;
  basicUser: string;
  basicPass: string;
  apiKeyName: string;
  apiKeyValue: string;
  apiKeyIn: "header" | "query";
}): string {
  const lines: string[] = [`curl -X ${input.method} '${input.url}'`];
  const enabledHeaders = input.headers.filter((h) => h.enabled && h.key.trim());
  for (const h of enabledHeaders) {
    lines.push(`  -H '${h.key}: ${h.value.replace(/'/g, "'\\''")}'`);
  }
  if (input.authType === "bearer" && input.bearerToken.trim()) {
    lines.push(`  -H 'Authorization: Bearer ${input.bearerToken.replace(/'/g, "'\\''")}'`);
  }
  if (input.authType === "basic" && input.basicUser) {
    const raw = btoa(`${input.basicUser}:${input.basicPass}`);
    lines.push(`  -H 'Authorization: Basic ${raw}'`);
  }
  if (input.authType === "apikey" && input.apiKeyName.trim() && input.apiKeyValue.trim()) {
    if (input.apiKeyIn === "header") {
      lines.push(
        `  -H '${input.apiKeyName}: ${input.apiKeyValue.replace(/'/g, "'\\''")}'`,
      );
    }
  }
  if (input.bodyKind === "raw" && input.rawBody.trim()) {
    const mime =
      input.rawMime === "json"
        ? "application/json"
        : input.rawMime === "xml"
          ? "application/xml"
          : input.rawMime === "html"
            ? "text/html"
            : "text/plain";
    lines.push(`  -H 'Content-Type: ${mime}'`);
    lines.push(`  --data-raw '${input.rawBody.replace(/'/g, "'\\''")}'`);
  }
  return lines.join(" \\\n");
}
