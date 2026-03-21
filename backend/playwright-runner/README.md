# JM Test Center — 纯 Playwright 运行器

无 LLM，按 JSON **步骤编排**驱动 Chromium。后端注入 `PLAYWRIGHT_WORK_DIR` 与 `PLAYWRIGHT_RUN_CONFIG_JSON`，进程写入 `result.json` 与 `report/playwright-report.html`。

## 规范（必读）

| 文档 | 说明 |
|------|------|
| [**PIPELINE_SPEC.md**](./PIPELINE_SPEC.md) | **步骤类型、定位器优先级、字段说明**（与 `src/run.ts` 同步） |
| [**schema/pipeline.schema.json**](./schema/pipeline.schema.json) | JSON Schema，可在配置中加 `"$schema"` 供 IDE 提示 |

定位方式覆盖 Playwright 常用 API：`locator`(CSS/XPath 字符串)、`getByRole`、`getByText`/`regex`、`getByTestId`、`getByPlaceholder`、`getByLabel`、`getByAltText`、`getByTitle`，以及 `frame`/`frameLocator`、多匹配时的 `first`/`nth`。

## 安装

```bash
# 仓库根目录下
cd backend/playwright-runner
npm install
npx playwright install chromium
```

## 环境变量

- `PLAYWRIGHT_WORK_DIR`：单次任务目录  
- `PLAYWRIGHT_RUN_CONFIG_JSON`：整段 JSON 字符串（配置结构见 PIPELINE_SPEC.md）

## 校验 JSON

```bash
npm run validate -- examples/minimal.pipeline.json
```

## 本地调试

```bash
set PLAYWRIGHT_WORK_DIR=./_local_run
set PLAYWRIGHT_RUN_CONFIG_JSON=<从文件读取的 UTF-8 整段 JSON>
npx tsx src/run.ts
```

（Windows PowerShell 请用 `[IO.File]::ReadAllText` 或 Node 读文件设置环境变量，避免编码损坏中文。）

## 与 Midscene 的差异

- 禁止在步骤中使用 `aiAction` / `aiWaitFor`（**仅**当任务走 Midscene 时由后端校验；纯 Playwright 任务不受影响）。
- 报告为自生成 HTML。
