import { http } from "./http";

export type RequirementProgressStatus = "not_started" | "in_progress" | "completed";

export type RequirementItem = {
  id: string;
  code: string;
  title: string;
  status: RequirementProgressStatus;
  statusText: string;
  priority: string;
  priorityText: string;
  caseCount: number;
  owner: string;
  updatedAt: string;
};

export type CaseExecutionStatus = "not_executed" | "success" | "failed" | "blocked";

export type RequirementDetail = {
  code: string;
  title: string;
  status: RequirementProgressStatus;
  statusText: string;
  priorityText: string;
  owner: string;
  cases: Array<{
    id: number;
    code: string;
    name: string;
    typeText: string;
    priorityText: string;
    executionStatus: CaseExecutionStatus;
    executionStatusText: string;
    lastRunAt: string;
    stepsText: string;
  }>;
};

export type RequirementListResponse = {
  total: number;
  page: number;
  page_size: number;
  requirements: RequirementItem[];
};

export async function listRequirementsApi(
  page = 1,
  pageSize = 10,
  keyword?: string
): Promise<RequirementListResponse> {
  const resp = await http.get<RequirementListResponse>("/api/v1/case-management/requirements", {
    params: { page, page_size: pageSize, q: keyword?.trim() || undefined }
  });
  return resp.data;
}

export async function getRequirementDetailApi(reqCode: string): Promise<RequirementDetail> {
  const resp = await http.get<RequirementDetail>(`/api/v1/case-management/requirements/${reqCode}`);
  return resp.data;
}

export async function checkRequirementCodeExistsApi(
  code: string,
  excludeCode?: string
): Promise<{ exists: boolean }> {
  const resp = await http.get<{ exists: boolean }>("/api/v1/case-management/requirements/code-exists", {
    params: { code, exclude_code: excludeCode }
  });
  return resp.data;
}

export async function createRequirementApi(payload: {
  code: string;
  title: string;
  owner?: string;
  priority: string;
  cases: Array<{ code: string; name: string; priorityText: string; stepsText: string }>;
}): Promise<{ ok: boolean }> {
  const resp = await http.post<{ ok: boolean }>("/api/v1/case-management/requirements", payload);
  return resp.data;
}

export async function updateRequirementApi(
  reqCode: string,
  payload: { code: string; title: string }
): Promise<{ ok: boolean }> {
  const resp = await http.put<{ ok: boolean }>(`/api/v1/case-management/requirements/${reqCode}`, payload);
  return resp.data;
}

export async function updateRequirementPriorityApi(reqCode: string, priority: string): Promise<{ ok: boolean }> {
  const resp = await http.patch<{ ok: boolean }>(`/api/v1/case-management/requirements/${reqCode}/priority`, {
    priority
  });
  return resp.data;
}

export async function updateCaseExecutionApi(
  reqCode: string,
  caseId: number,
  executionStatus: CaseExecutionStatus
): Promise<{ ok: boolean }> {
  const code = encodeURIComponent(reqCode);
  const resp = await http.patch<{ ok: boolean }>(
    `/api/v1/case-management/requirements/${code}/cases/${caseId}/execution`,
    { execution_status: executionStatus }
  );
  return resp.data;
}

export async function deleteRequirementApi(reqCode: string): Promise<{ ok: boolean }> {
  const resp = await http.delete<{ ok: boolean }>(`/api/v1/case-management/requirements/${reqCode}`);
  return resp.data;
}
