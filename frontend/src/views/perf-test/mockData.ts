/** 性能测试页静态数据（后续接压测引擎 / 后端时替换） */

export type PerfScenario = {
  id: string;
  name: string;
  method: string;
  url: string;
  headersText: string;
  bodyText: string;
  vus: number;
  durationSec: number;
  rampUpSec: number;
  thinkTimeMs: number;
  updatedAt: string;
};

export type PerfRunRecord = {
  id: string;
  scenarioId: string;
  scenarioName: string;
  startedAt: string;
  endedAt: string;
  status: "success" | "failed" | "stopped";
  durationSec: number;
  rps: number;
  p50: number;
  p95: number;
  p99: number;
  errorRate: number;
  totalRequests: number;
  failedRequests: number;
};

export type Point = { t: string; v: number };

export const INITIAL_SCENARIOS: PerfScenario[] = [
  {
    id: "s1",
    name: "登录接口冒烟",
    method: "POST",
    url: "https://api.example.com/v1/auth/login",
    headersText: '{\n  "Content-Type": "application/json"\n}',
    bodyText: '{\n  "username": "demo",\n  "password": "******"\n}',
    vus: 20,
    durationSec: 60,
    rampUpSec: 10,
    thinkTimeMs: 0,
    updatedAt: "2026-03-21 10:00",
  },
  {
    id: "s2",
    name: "商品列表查询",
    method: "GET",
    url: "https://api.example.com/v1/products?page=1",
    headersText: '{\n  "Authorization": "Bearer ***"\n}',
    bodyText: "",
    vus: 50,
    durationSec: 120,
    rampUpSec: 30,
    thinkTimeMs: 200,
    updatedAt: "2026-03-20 16:30",
  },
];

export const INITIAL_RUNS: PerfRunRecord[] = [
  {
    id: "r1",
    scenarioId: "s1",
    scenarioName: "登录接口冒烟",
    startedAt: "2026-03-21 09:58:00",
    endedAt: "2026-03-21 10:00:12",
    status: "success",
    durationSec: 62,
    rps: 842,
    p50: 28,
    p95: 156,
    p99: 312,
    errorRate: 0.12,
    totalRequests: 52180,
    failedRequests: 63,
  },
  {
    id: "r2",
    scenarioId: "s2",
    scenarioName: "商品列表查询",
    startedAt: "2026-03-20 16:25:00",
    endedAt: "2026-03-20 16:27:05",
    status: "stopped",
    durationSec: 125,
    rps: 1204,
    p50: 41,
    p95: 198,
    p99: 401,
    errorRate: 0.05,
    totalRequests: 150500,
    failedRequests: 75,
  },
];

/** 最近一次「报告」用折线图（静态） */
export function mockLatencySeries(): Point[] {
  const out: Point[] = [];
  for (let i = 0; i < 24; i++) {
    const sec = String(i).padStart(2, "0");
    out.push({ t: `${sec}s`, v: 20 + Math.sin(i / 2.2) * 15 + (i % 5) * 8 });
  }
  return out;
}

export function mockRpsSeries(): Point[] {
  const out: Point[] = [];
  for (let i = 0; i < 24; i++) {
    const sec = String(i).padStart(2, "0");
    out.push({ t: `${sec}s`, v: 700 + Math.cos(i / 3) * 120 + i * 6 });
  }
  return out;
}

let _seq = 1;
export function genId(p: string) {
  return `${p}-${Date.now()}-${_seq++}`;
}
