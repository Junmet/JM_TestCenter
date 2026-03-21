import { http } from "./http";

export type DashboardStats = {
  requirement_count: number;
  case_count: number;
  case_pass_rate_percent: number | null;
  ui_runs_today: number;
  ui_runs_total: number;
};

export type CaseExecutionBreakdown = {
  not_executed: number;
  success: number;
  failed: number;
  blocked: number;
};

export type DailyUiRunPoint = {
  date: string;
  count: number;
};

export type DashboardRecentRun = {
  id: string;
  title: string;
  status: string;
  status_text: string;
  run_at: string;
};

export type DashboardOverview = {
  stats: DashboardStats;
  case_execution: CaseExecutionBreakdown;
  ui_runs_last_7_days: DailyUiRunPoint[];
  recent_ui_runs: DashboardRecentRun[];
};

export async function getDashboardOverviewApi(): Promise<DashboardOverview> {
  const { data } = await http.get<DashboardOverview>("/api/v1/dashboard/overview");
  return data;
}
