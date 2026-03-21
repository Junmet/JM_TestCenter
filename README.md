# JM Test Genius

JM Test Genius 是一套测试管理与自动化相关的全栈应用：**管理端前端**（Vue 3）与 **后端 API**（FastAPI）同仓维护，支持需求与用例管理、AI 辅助用例生成，以及基于 Midscene.js / 纯 Playwright 的 UI 自动化任务编排与执行。

本仓库即 **JM_TestGenius** 项目根目录（与 `frontend/`、`backend/` 同级）。

---

## 仓库结构

| 目录 | 说明 |
|------|------|
| [**frontend/**](frontend/) | 管理端 Web：Vue 3、Vite、TypeScript、Element Plus；开发与构建方式见该目录 [README](frontend/README.md)。 |
| [**backend/**](backend/) | REST API：FastAPI、MySQL、Alembic；含 UI 自动化子进程（Midscene / Playwright 运行器）与用例生成模块；详见 [README](backend/README.md)。 |

更细的接口、环境变量与脚本说明，请以各子目录文档为准。

---

## 技术栈概览

- **前端**：Vue 3、Vite、Pinia、Vue Router、axios、Element Plus  
- **后端**：Python 3.11+、FastAPI、SQLAlchemy、Alembic、JWT  
- **UI 自动化**：Node.js 子进程执行 `midscene-runner` / `playwright-runner`（Chromium / Playwright）

---

## 快速开始（开发）

1. **数据库**：准备 MySQL，并按 `backend/.env.example` 配置 `backend/.env`。  
2. **后端**（在 `backend/`）：安装依赖、迁移、启动服务 — 见 [backend/README.md](backend/README.md)。  
3. **前端**（在 `frontend/`）：`npm install` 后 `npm run dev` — 见 [frontend/README.md](frontend/README.md)。  

开发时前端通过 Vite 将 `/api` 代理到本机后端（默认与 `frontend/vite.config.ts` 中配置一致）。

---

## 不宜提交到远程仓库的内容（Git）

根目录 **[`.gitignore`](.gitignore)** 已配置常见忽略规则；**`backend/.gitignore`** 已合并原 `testcase/`、`playwright-runner/` 子目录中的忽略项，后端子项目不再单独维护 `.gitignore`。下表便于对照「哪些目录/文件不必上传」。

### 三层 `.gitignore` 如何配合

| 位置 | 作用 |
|------|------|
| **[`.gitignore`](.gitignore)**（仓库根） | 从仓库根执行 `git` 时的全仓规则（含 `frontend/`、`backend/` 路径前缀）。 |
| **[`frontend/.gitignore`](frontend/.gitignore)** | 仅针对前端目录：与根规则**对齐**，在只打开 `frontend/` 子文件夹时同样生效。 |
| **[`backend/.gitignore`](backend/.gitignore)** | 后端统一规则：**`data/`**、Python 缓存、**`testcase/`** 下 `input/` / `output/` 等、**运行器** `node_modules` 与试跑目录等（均写在此文件中）。 |

### 根目录规则摘要（与上表子目录文件一致）

| 类别 | 路径或模式 | 原因 |
|------|------------|------|
| 依赖 | `**/node_modules/` | npm 安装产物，体积大且可复现 |
| 前端构建 | `frontend/dist/`、`*.tsbuildinfo` | `npm run build` 生成，CI/CD 可现编 |
| Python 缓存与包元数据 | `__pycache__/`、`*.egg-info/`、`.venv/`、`venv/` 等 | 本地解释器与构建缓存 |
| 密钥与环境 | 任意目录下的 **`.env`**（**例外**：`**/.env.example` 可提交） | 含数据库密码、JWT、API Key 等 |
| 后端运行数据 | `backend/data/` | UI 自动化任务产物、报告、录屏等 |
| Playwright 本地调试 | `backend/playwright-runner/_test_run/`、`artifacts/` | 本地试跑目录 |
| IDE / 系统 | `.idea/`、`.vscode/`、`.cursor/`、`.DS_Store` 等 | 个人环境，非项目源码 |
| 日志与缓存 | `*.log`、`coverage/`、`.pytest_cache/` 等 | 运行或测试产生 |
| 用例生成目录 | `backend/testcase/input/`、`output/`、`debug/`、`log/` 等 | 见 **`backend/.gitignore`** 中 `testcase/` 段 |

### 建议保留在仓库中的模板文件

- `backend/.env.example`：后端环境变量示例（无真实密钥）  
- 各模块若新增 `*.env.example`，可随代码提交，便于他人复制为本地 `.env`。

---

## 许可证

本项目以 [**MIT License**](LICENSE) 发布。
