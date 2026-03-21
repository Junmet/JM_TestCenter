# JM Test Center — Backend

基于 **FastAPI** 的 HTTP 服务，提供认证、需求与用例管理、AI 用例生成、UI 自动化任务（Midscene / 纯 Playwright）等能力；数据持久化使用 **MySQL**，通过 **Alembic** 管理表结构。

---

## 后端服务说明

| 能力 | 说明 |
|------|------|
| **HTTP API** | 路由挂载在应用根路径，业务接口前缀为 `/api/v1/...`（见下表）。 |
| **认证** | JWT：`POST /api/v1/auth/login` 获取访问令牌，后续请求在 Header 中携带 `Authorization: Bearer <token>`。 |
| **健康检查** | `GET /healthz` 返回 `{"ok": true}`，不鉴权。 |
| **UI 自动化** | 创建任务后由后台线程启动 **Node 子进程** 执行 `midscene-runner` 或 `playwright-runner` 中的 `src/run.ts`；产物写入 `data/midscene_runs/<run_id>/`。 |
| **用例生成** | `CaseGenerationService` 将 `testcase/` 加入 `sys.path`，并读取 `backend/testcase/.env`（如 DeepSeek 等配置）。 |

### 主要 API 前缀（节选）

| 前缀 | 用途 |
|------|------|
| `/api/v1/auth` | 登录 |
| `/api/v1` | 管理员接口（如 `POST /api/v1/admin/users` 创建用户） |
| `/api/v1/system` | 系统信息 |
| `/api/v1/case-gen` | 用例生成 |
| `/api/v1/case-management` | 需求与用例管理 |
| `/api/v1/ui-automation` | UI 自动化任务、健康检查、报告下载等 |

更细的请求体与路径以 `app/api/v1/routes/` 下各模块为准。

---

## 子项目与脚本说明

后端仓库内除 Python 包 `app` 外，还包含下列可被主服务调用或独立调试的组件。

### 1. `midscene-runner`（Midscene.js + Playwright）

- **作用**：自然语言 / 步骤编排驱动的 UI 自动化；由后端通过 `node` + `tsx` 调用 `src/run.ts`，一般**不需要**手工反复执行 `npm run run`（除非本地调试运行器）。
- **安装**：在 `backend/midscene-runner` 执行 `npm install` 与 `npx playwright install chromium`。
- **package.json 脚本**：
  - `npm run run` → `tsx src/run.ts`（与后端子进程命令一致；依赖后端注入的环境变量，见该目录 `README.md`）。

环境变量、步骤类型、故障排查等详见 [**midscene-runner/README.md**](midscene-runner/README.md)。

### 2. `playwright-runner`（无 LLM，纯 Playwright）

- **作用**：按 JSON 步骤编排执行 Chromium；后端同样通过 `tsx src/run.ts` 拉起子进程。
- **安装**：在 `backend/playwright-runner` 执行 `npm install` 与 `npx playwright install chromium`。
- **package.json 脚本**：
  - `npm run run` → `tsx src/run.ts`
  - `npm run validate` → `node scripts/validate-pipeline.mjs`（校验 pipeline JSON）
  - `npm run validate:example` → 校验内置示例 `examples/minimal.pipeline.json`

步骤规范与 Schema 见 [**playwright-runner/PIPELINE_SPEC.md**](playwright-runner/PIPELINE_SPEC.md) 与 [**playwright-runner/README.md**](playwright-runner/README.md)。

### 3. `testcase`（Python 用例生成）

- **作用**：需求文档解析、用例生成等逻辑；与后端同仓，由 `CaseGenerationService` 动态加载。
- **配置**：开发/部署时在 **`backend/testcase/.env`** 配置模型与密钥等。
- **注意**：修改 `testcase/` 下代码时，uvicorn 的 `--reload` 默认可能不监视该目录，需使用下文「带 `testcase` 重载」的启动命令或手动重启。

---

## 服务启动

### 1. 环境要求

- Python **3.11+**
- **MySQL**（连接信息在 `.env` 或 `app/core/config.py` 默认值中配置）
- Node.js **18+**（仅在使用 UI 自动化时需要，用于两个 runner）

### 2. 配置与依赖

1. 复制 `.env.example` 为 `.env` 并按环境填写（含 MySQL、JWT 等）。
2. 安装 Python 依赖：在 **`backend`** 目录执行  
   `pip install -e .`
3. 初始化数据库表：  
   `python -m alembic upgrade head`
4. （可选）写入开发用户：  
   `python -m app.db.seed`

### 3. 启动 API 服务（uvicorn）

在 **`backend`** 目录下执行：

```bash
uvicorn app.main:app --reload --port 8080
```

若会修改 **`testcase/`** 子目录下的代码，请**手动重启** uvicorn，或使用（确保监视 `testcase` 变更）：

```bash
uvicorn app.main:app --reload --reload-dir . --reload-dir testcase --port 8080
```

**端口说明**：仓库中前端开发代理默认将 `/api` 转发到 `http://127.0.0.1:8080`（见 `frontend/vite.config.ts`）。若你改用其他端口（例如 `8000`），请同时修改前端的 `proxy.target`，否则页面请求无法到达后端。

### 4. UI 自动化前置（按需）

1. 按上文完成 **`midscene-runner`** 和/或 **`playwright-runner`** 的 `npm install` 与浏览器安装。
2. 迁移包含 `midscene_runs` 等表的版本：`python -m alembic upgrade head`。
3. 产物目录默认为 **`backend/data/midscene_runs/`**（运行记录、HTML 报告、录屏等）。
4. （可选）在 `.env` 中配置例如：`MIDSCENE_SETTLE_NETWORK_IDLE`、`MIDSCENE_RUN_TIMEOUT_SECONDS`；自定义 runner 路径可使用 `MIDSCENE_RUNNER_DIR`、`PLAYWRIGHT_RUNNER_DIR`（**绝对路径**）。

---

## 相关文档

- [testcase/README.md](testcase/README.md) — 用例生成模块说明  
- [midscene-runner/README.md](midscene-runner/README.md) — Midscene 运行器与环境变量  
- [playwright-runner/README.md](playwright-runner/README.md) — 纯 Playwright 步骤与校验脚本  
