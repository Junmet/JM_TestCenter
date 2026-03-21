import { http } from "./http";

export type MidsceneModelConfig = {
  base_url: string;
  api_key: string;
  name: string;
  family: string;
};

export type MidsceneRunCreate = {
  /** midscene：视觉模型；playwright：纯 Playwright，须步骤编排且无 aiAction */
  runner?: "midscene" | "playwright";
  model: MidsceneModelConfig;
  start_url: string;
  /** 与 execution_steps 二选一；步骤编排时可为空字符串 */
  instructions: string;
  instruction_mode: "multi_line" | "single_block";
  headless: boolean;
  record_video: boolean;
  /** 每步之后的额外睡眠(ms)；与 stable_wait_after_step（domcontentloaded）叠加。默认 400 */
  step_gap_ms: number;
  /** 每步后先 domcontentloaded 再 sleep step_gap_ms；默认 false。慢页可开；networkidle 见服务端 */
  stable_wait_after_step: boolean;
  /** 仅 Playwright：操作间隔延迟(ms)，便于录屏观察；不传或 0 为关闭 */
  slow_mo_ms?: number | null;
  /** 非空时优先按步骤编排执行（混合 aiAction 与白名单 Playwright 操作） */
  execution_steps?: Array<Record<string, unknown>> | null;
};

export type MidsceneRun = {
  id: string;
  status: string;
  error_message: string | null;
  model_name: string;
  model_family: string;
  model_base_url: string;
  start_url: string;
  instructions: string;
  instruction_mode: string;
  headless: boolean;
  record_video: boolean;
  report_file: string | null;
  video_file: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
};

export type MidsceneRunListResponse = {
  items: MidsceneRun[];
  total: number;
  page: number;
  page_size: number;
};

export type MidsceneRunnerHealth = {
  ok: boolean;
  node_found: boolean;
  runner_dir_exists: boolean;
  tsx_exists: boolean;
  runner_script_exists: boolean;
  message: string;
  playwright_runner_dir_exists?: boolean;
  playwright_script_exists?: boolean;
  playwright_ok?: boolean;
  playwright_message?: string;
};

export async function getMidsceneHealthApi(): Promise<MidsceneRunnerHealth> {
  const resp = await http.get<MidsceneRunnerHealth>("/api/v1/ui-automation/health");
  return resp.data;
}

export async function createMidsceneRunApi(body: MidsceneRunCreate): Promise<MidsceneRun> {
  const resp = await http.post<MidsceneRun>("/api/v1/ui-automation/runs", body, { timeout: 0 });
  return resp.data;
}

export async function listMidsceneRunsApi(
  page = 1,
  pageSize = 10
): Promise<MidsceneRunListResponse> {
  const resp = await http.get<MidsceneRunListResponse>("/api/v1/ui-automation/runs", {
    params: { page, page_size: pageSize }
  });
  return resp.data;
}

export async function getMidsceneRunApi(runId: string): Promise<MidsceneRun> {
  const resp = await http.get<MidsceneRun>(`/api/v1/ui-automation/runs/${runId}`);
  return resp.data;
}

export function reportUrl(runId: string): string {
  return `/api/v1/ui-automation/runs/${runId}/report`;
}

export function videoUrl(runId: string): string {
  return `/api/v1/ui-automation/runs/${runId}/video`;
}
