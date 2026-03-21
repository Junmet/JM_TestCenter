# JM Test Center — Midscene 运行器

后端通过 `node` + `tsx` 调用本目录下的 `src/run.ts`，使用 [@midscene/web](https://midscenejs.com/) 与 Playwright 执行自然语言 UI 自动化。

## 安装

`@midscene/web` 会引用 `@playwright/test`，必须与 `playwright` 一并安装。

```bash
# 仓库根目录下
cd backend/midscene-runner
npm install
npx playwright install chromium
```

## 环境变量（由后端注入，一般无需手工执行）

- `MIDSCENE_OPENAI_BASE_URL` / `MIDSCENE_OPENAI_API_KEY`
- **以及** Midscene 在 default 意图回退时使用的 **`OPENAI_BASE_URL` / `OPENAI_API_KEY`**（与上两项相同；后端会一并注入）
- `MIDSCENE_MODEL_NAME`
- `MIDSCENE_VL_MODE`（如 `qwen3-vl`、`gemini` 等，见 Midscene 文档）
- `MIDSCENE_WORK_DIR`：单次运行的工作目录（报告、视频、result.json）
- `MIDSCENE_CONFIG_JSON`：任务参数（起始 URL、指令、`stepGapMs` 默认 **400**、`stableWaitAfterStep` 默认 **false** 等）
- （可选）`MIDSCENE_STEP_GAP_MS`：覆盖 JSON 里的步骤间隔（毫秒）
- （可选）`MIDSCENE_STABLE_WAIT`：`0` 关闭稳定等待，`1` 强制开启
- （可选）`MIDSCENE_SETTLE_NETWORK_IDLE`：设为 `1` 时在稳定等待中**额外**尝试 `networkidle`（SPA/长连接页面默认**不**开，否则易卡 10s+）
- （可选）`MIDSCENE_AI_ACTION_TIMEOUT_MS`：单步 `aiAction` 最长等待（毫秒）。未设置时 runner 内默认 **300000**（5 分钟）；设为 **0** 关闭单步超时（仍受后端 `MIDSCENE_RUN_TIMEOUT_SECONDS` 总时长限制）
- （可选）`MIDSCENE_REPLANNING_CYCLE_LIMIT`：Midscene 内部单步任务「重规划」次数上限，过大时一步可能极久；可由后端注入

## 步骤间稳定等待（减少「上一步未完成就规划下一步」）

每步 `aiAction` 之后：若 `stableWaitAfterStep` 为 true，会先做轻量 `domcontentloaded` 再睡眠 `stepGapMs`；为 false 时仅睡眠 `stepGapMs`。**不再**默认等待 `networkidle`（很多站点永远达不到，会长时间无响应）。首屏在 `goto` 后同样按上述逻辑。

**推荐**：默认 **400ms** 间隔 + 稳定关；抢步或动画多时可加大间隔、勾选稳定等待，或设 `MIDSCENE_SETTLE_NETWORK_IDLE=1`。

**说明**：单次 `aiAction` 本身要调用视觉大模型，耗时通常 **数秒到数十秒**，与脚本等待无关；若一直无结果，请查模型 API 与网络。

## 步骤编排 `executionSteps`（复杂场景）

当 `MIDSCENE_CONFIG_JSON` 中含非空数组 `executionSteps` 时，**优先按数组顺序执行**，不再使用 `instructions` / `instructionMode`。可与 `aiAction`（Midscene）及下列 **白名单** 步骤混用：

| type | 字段 | 说明 |
|------|------|------|
| `aiAction` | `text`, `timeoutMs?` | 自然语言一步；`timeoutMs` 可单独限制本步（毫秒），`0` 表示本步不套单步超时 |
| `aiWaitFor` | `text`, `timeoutMs?`, `checkIntervalMs?` | 轮询直到页面满足自然语言条件（Midscene `aiWaitFor`） |
| `settle` | `gapMs?`, `stable?` | 额外稳定等待 |
| `wait` | `ms` | 固定睡眠 |
| `goto` | `url` | 当前标签导航 |
| `goBack` | — | 浏览器后退 |
| `switchToLatestTab` | — | 切到最后一个标签（常用于新窗口打开后） |
| `switchToTabIndex` | `index` | 0 起标签下标 |
| `closeOtherTabs` | — | 关闭除当前外的标签 |
| `closeCurrentTab` | — | 关当前并切到相邻标签 |
| `expectTabCount` | `count` | 断言标签数量 |
| `logPageInfo` | — | 向 Node 控制台输出 JSON：`url`、`title`、`tabCount` |
| `scrollToBottom` | — | 滚到底 |
| `screenshot` | `filename?`, `fullPage?` | 保存到 `artifacts/` |
| `assertTitleContains` | `text` | 断言标题子串 |
| `assertUrlContains` | `text` | 断言 URL 子串 |

JM Test Center 前端可选「步骤编排」，编辑 JSON 后提交；`result.json` 中可能含 `pipeline_screenshots`、`pipeline_page_info`。

## 长时间无结果

- 后端 **`MIDSCENE_RUN_TIMEOUT_SECONDS`**（默认 3600）到点会 **终止 Node 子进程** 并标记失败，因此「整小时无结果」常与 **总超时** 或 **某步模型/API 挂起** 有关。
- 已为 **`aiAction` 增加单步超时**（见上 `MIDSCENE_AI_ACTION_TIMEOUT_MS`），避免单步把整段任务拖满一小时才失败。
- 步骤里 **`aiWaitFor` 的 `timeoutMs`** 只约束等待条件，不约束后续 `aiAction`。

## 常见问题：`AI model failed to locate`

`aiAction` 依赖视觉模型在**当前页面**里找元素。若自然语言要求「标题必须包含某某固定词」而页面上没有该文案，会报 **failed to locate**。

**建议**：写「第一条非广告搜索结果」「页面顶部的登录按钮」等**相对位置/可见特征**；需要固定断言时用白名单步骤 `assertTitleContains` / `goto` 已知 URL，而不是把整句文案写死在 `aiAction` 里。

## 说明

- 报告 HTML 位于 `MIDSCENE_WORK_DIR/midscene_run/` 下，由运行脚本解析最新一份。
- Playwright 录屏文件在 `MIDSCENE_WORK_DIR/videos/`。
