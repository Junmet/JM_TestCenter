import { http } from "./http";

export type GeneratedCase = {
  id: number;
  case_code: string;
  priority: string;
  module: string;
  title: string;
  summary: string;
  preconditions: string;
  steps: string[];
  expected: string[];
  actual_result: string;
  test_type: string;
  data: string;
  remarks: string;
  confirmed: boolean;
};

export type CaseGenerationResponse = {
  requirement_id: number;
  source_name: string;
  created_at: string;
  cases: GeneratedCase[];
};

export type CaseGenerationHistoryItem = {
  requirement_id: number;
  source_name: string;
  status: string;
  case_count: number;
  confirmed_count: number;
  created_at: string;
};

export type CaseGenerationHistoryResponse = {
  total: number;
  page: number;
  page_size: number;
  items: CaseGenerationHistoryItem[];
};

export async function generateCasesApi(
  file: File,
  options?: {
    maxCases?: number;
    batchSize?: number;
  }
): Promise<CaseGenerationResponse> {
  const formData = new FormData();
  formData.append("file", file);
  if (options?.maxCases) formData.append("max_cases", String(options.maxCases));
  if (options?.batchSize) formData.append("batch_size", String(options.batchSize));
  const resp = await http.post<CaseGenerationResponse>("/api/v1/case-gen/generate", formData, {
    headers: {
      "Content-Type": "multipart/form-data"
    },
    timeout: 0
  });
  return resp.data;
}

export async function confirmCasesApi(requirementId: number, caseIds: number[]): Promise<{ updated: number }> {
  const resp = await http.post<{ updated: number }>(`/api/v1/case-gen/requirements/${requirementId}/confirm`, {
    case_ids: caseIds
  });
  return resp.data;
}

export async function getGenerationHistoriesApi(page = 1, pageSize = 10): Promise<CaseGenerationHistoryResponse> {
  const resp = await http.get<CaseGenerationHistoryResponse>("/api/v1/case-gen/histories", {
    params: { page, page_size: pageSize }
  });
  return resp.data;
}

export async function deleteGenerationHistoryApi(requirementId: number): Promise<{ ok: boolean }> {
  const resp = await http.delete<{ ok: boolean }>(`/api/v1/case-gen/histories/${requirementId}`);
  return resp.data;
}

export async function getCasesByRequirementApi(requirementId: number): Promise<CaseGenerationResponse> {
  const resp = await http.get<CaseGenerationResponse>(`/api/v1/case-gen/requirements/${requirementId}/cases`);
  return resp.data;
}
