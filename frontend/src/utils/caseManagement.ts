export type RequirementItem = {
  id: string;
  code: string;
  title: string;
  status: "active" | "done";
  statusText: string;
  priority: "p0" | "p1" | "p2";
  priorityText: string;
  caseCount: number;
  owner: string;
  updatedAt: string;
};

export type CaseItem = {
  id: number;
  code: string;
  name: string;
  typeText: string;
  priorityText: string;
  statusText: string;
  lastRunAt: string;
};

type PersistData = {
  requirements: RequirementItem[];
  caseMap: Record<string, CaseItem[]>;
};

const STORAGE_KEY = "jmtestcenter_case_management_data";

const defaultRequirements: RequirementItem[] = [
  {
    id: "REQ-1001",
    code: "REQ-1001",
    title: "登录模块改造",
    status: "active",
    statusText: "进行中",
    priority: "p0",
    priorityText: "P0",
    caseCount: 12,
    owner: "张三",
    updatedAt: "2025-03-19 11:30"
  },
  {
    id: "REQ-1002",
    code: "REQ-1002",
    title: "订单查询优化",
    status: "active",
    statusText: "进行中",
    priority: "p1",
    priorityText: "P1",
    caseCount: 9,
    owner: "李四",
    updatedAt: "2025-03-18 16:10"
  },
  {
    id: "REQ-1003",
    code: "REQ-1003",
    title: "支付回调幂等处理",
    status: "done",
    statusText: "已完成",
    priority: "p0",
    priorityText: "P0",
    caseCount: 15,
    owner: "王五",
    updatedAt: "2025-03-17 14:45"
  }
];

const defaultCaseMap: Record<string, CaseItem[]> = {
  "REQ-1001": [
    {
      id: 1,
      code: "TC-10001",
      name: "登录-正确账号密码",
      typeText: "接口",
      priorityText: "P0",
      statusText: "启用",
      lastRunAt: "2025-03-19 10:32"
    },
    {
      id: 2,
      code: "TC-10002",
      name: "登录-错误密码提示",
      typeText: "UI",
      priorityText: "P1",
      statusText: "启用",
      lastRunAt: "2025-03-19 09:18"
    }
  ],
  "REQ-1002": [
    {
      id: 3,
      code: "TC-20001",
      name: "订单查询-分页参数边界",
      typeText: "接口",
      priorityText: "P1",
      statusText: "启用",
      lastRunAt: "2025-03-18 16:10"
    }
  ],
  "REQ-1003": [
    {
      id: 4,
      code: "TC-30001",
      name: "支付回调-重复通知幂等",
      typeText: "接口",
      priorityText: "P0",
      statusText: "启用",
      lastRunAt: "2025-03-17 14:45"
    }
  ]
};

function nowText() {
  const d = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function readPersist(): PersistData {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return { requirements: defaultRequirements, caseMap: defaultCaseMap };
    }
    const parsed = JSON.parse(raw) as PersistData;
    return {
      requirements: parsed.requirements || defaultRequirements,
      caseMap: parsed.caseMap || defaultCaseMap
    };
  } catch {
    return { requirements: defaultRequirements, caseMap: defaultCaseMap };
  }
}

function writePersist(data: PersistData) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
}

export function getCaseManagementData(): PersistData {
  return readPersist();
}

export function addRequirementWithCases(payload: {
  code: string;
  title: string;
  owner?: string;
  priority?: "p0" | "p1" | "p2";
  cases: Array<{ code: string; name: string; priorityText?: string }>;
}) {
  const current = readPersist();
  const id = payload.code;
  const priority = payload.priority || "p1";
  const priorityText = priority.toUpperCase();
  const mappedCases: CaseItem[] = payload.cases.map((c, idx) => ({
    id: Date.now() + idx,
    code: c.code,
    name: c.name,
    typeText: "功能",
    priorityText: c.priorityText || priorityText,
    statusText: "启用",
    lastRunAt: nowText()
  }));

  const nextReq: RequirementItem = {
    id,
    code: payload.code,
    title: payload.title,
    status: "active",
    statusText: "进行中",
    priority,
    priorityText,
    caseCount: mappedCases.length,
    owner: payload.owner || "当前用户",
    updatedAt: nowText()
  };

  const filtered = current.requirements.filter((r) => r.id !== id);
  const next: PersistData = {
    requirements: [nextReq, ...filtered],
    caseMap: { ...current.caseMap, [id]: mappedCases }
  };
  writePersist(next);
}

export function getNextRequirementCode(): string {
  const { requirements } = readPersist();
  const nums = requirements
    .map((r) => {
      const m = r.code.match(/^REQ-(\d+)$/i);
      return m ? Number(m[1]) : 0;
    })
    .filter((n) => Number.isFinite(n));
  const max = nums.length ? Math.max(...nums) : 1000;
  return `REQ-${max + 1}`;
}
