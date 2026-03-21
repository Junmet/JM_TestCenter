import { defineStore } from "pinia";

import { generateCasesApi, type CaseGenerationResponse } from "../api/caseGen";

/** FastAPI detail 可能是 string 或校验错误数组 */
function extractApiDetail(err: unknown): string {
  const d = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) {
    return d
      .map((x) => (typeof x === "object" && x !== null && "msg" in x ? String((x as { msg: string }).msg) : String(x)))
      .join("；");
  }
  return "";
}

type CaseGenState = {
  generating: boolean;
  startedAt: number | null;
  latestResult: CaseGenerationResponse | null;
  latestError: string;
  /** 最近一次成功生成耗时（毫秒），用于切页返回后展示） */
  lastDurationMs: number | null;
};

export const useCaseGenStore = defineStore("caseGen", {
  state: (): CaseGenState => ({
    generating: false,
    startedAt: null,
    latestResult: null,
    latestError: "",
    lastDurationMs: null
  }),
  actions: {
    async startGenerate(
      file: File,
      options?: {
        maxCases?: number;
        batchSize?: number;
      }
    ) {
      if (this.generating) return;
      this.generating = true;
      this.startedAt = Date.now();
      this.latestError = "";
      this.latestResult = null;
      this.lastDurationMs = null;
      try {
        const data = await generateCasesApi(file, options);
        this.latestResult = data;
        const start = this.startedAt ?? Date.now();
        this.lastDurationMs = Math.max(0, Date.now() - start);
      } catch (err: any) {
        this.latestError = extractApiDetail(err) || "生成失败，请稍后重试（可尝试降低目标用例数）";
        this.lastDurationMs = null;
      } finally {
        this.generating = false;
      }
    },
    clearLatestResult() {
      this.latestResult = null;
      this.latestError = "";
      this.lastDurationMs = null;
    }
  }
});
