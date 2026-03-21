/** 接口测试页：类型定义（与后端对接时可复用） */

export type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE" | "HEAD" | "OPTIONS";

export type AuthType = "none" | "bearer" | "basic" | "apikey";

export type BodyKind = "none" | "form-data" | "urlencoded" | "raw" | "binary" | "graphql";

export type RawBodyMime = "json" | "xml" | "text" | "html";

export type KvRow = {
  id: string;
  enabled: boolean;
  key: string;
  value: string;
  description?: string;
  /** form-data 专用：text | file */
  partType?: "text" | "file";
  fileName?: string;
};

export type ApiEnvironment = {
  id: string;
  name: string;
  variables: KvRow[];
};

export type SavedRequestMeta = {
  id: string;
  name: string;
  folderId: string;
  description?: string;
};

export type CollectionFolder = {
  id: string;
  label: string;
  children?: CollectionFolder[];
  requestIds?: string[];
};

export type HistoryItem = {
  id: string;
  method: HttpMethod;
  url: string;
  title: string;
  at: string;
};

export type MockResponse = {
  status: number;
  statusText: string;
  timeMs: number;
  sizeBytes: number;
  body: string;
  bodyMime: "json" | "text" | "html" | "xml";
  headers: KvRow[];
  cookies: KvRow[];
};

export type RequestSettings = {
  timeoutMs: number;
  followRedirects: boolean;
  verifySsl: boolean;
};
