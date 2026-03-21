# Playwright 步骤编排规范（JM Test Center `executionSteps`）

本文档为 **`PLAYWRIGHT_RUN_CONFIG_JSON`** 与 **`executionSteps`** 的权威说明，与 `src/run.ts` 解析逻辑一致。实现新步骤或定位方式时，请先改 `run.ts`，再同步本文档与 `schema/pipeline.schema.json`。

---

## 1. 顶层配置

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `startUrl` | string | 是 | 浏览器启动后首先 `goto` 的 URL（`load`） |
| `headless` | boolean | 是 | 是否无头 |
| `recordVideo` | boolean | 是 | 是否录屏到工作目录 `videos/` |
| `stepGapMs` | number | 否 | 每步完成后额外等待（毫秒），默认 `200` |
| `stableWaitAfterStep` | boolean | 否 | 每步后是否再轻量等待 `domcontentloaded` + 间隔 |
| `slowMoMs` | number | 否 | **调试录屏**：每个 Playwright 操作之间延迟若干毫秒（如 `300`）；前端对应字段 `slow_mo_ms`，**最大 2000**。便于在 webm 里看出先后，**仍不会出现鼠标指针**。 |
| `executionSteps` | array | 是 | **非空**步骤数组，每项为对象，必须含 `type` |

### 录屏说明

Playwright 生成的 **webm 是视口画面**，**默认不包含鼠标光标**；若页面在点击后变化不明显，看起来会像「没点」。可：`slowMoMs` 放慢、`highlight` 高亮目标、或加大 `stepGapMs`；需要肉眼盯浏览器时请 **关闭无头**（`headless: false`，仅适合本机）。

---

## 2. 步骤通用字段

| 字段 | 说明 |
|------|------|
| `type` | 步骤类型（见第 4 节枚举） |
| `locator` | 见第 3 节；仅部分 `type` 需要 |
| `timeoutMs` | 部分操作超时（毫秒） |
| `force` | `true` 时点击/输入等可走 Playwright `force`（遮罩、hidden 等场景） |
| `first` | `true` 时在最终 Locator 上 `.first()` |
| `nth` | 非负整数，在最终 Locator 上 `.nth(n)`；与 `first` 互斥（优先 `first`） |
| `frame` / `frameSelector` | 字符串，与 `page.frameLocator(selector)` 一致，后续定位在 iframe 内 |

`first` / `nth` / `frame` 可写在**步骤对象顶层**，也可写在 **`locator` 对象内**（locator 内优先）。

---

## 3. 定位器 `locator`（与 Playwright 对齐）

### 3.1 字符串形式

传给 `page.locator(...)` 的简写：

| 写法 | 含义 |
|------|------|
| 普通字符串 | **CSS** 选择器 |
| 以 `//`、`(/`、`(//` 开头，或整段已是 `xpath=...` | **XPath**（内部会加 `xpath=` 前缀） |
| `css=...` | 显式 CSS |
| `xpath=...` | 显式 XPath |

可选：步骤上 `first` / `nth` 用于字符串 Locator。

### 3.2 对象形式（只使用一种「主键」，解析优先级如下）

**优先级从高到低**（命中即停止，勿在同一对象里混多种主键）：

1. **`css`** → `locator(css)`
2. **`xpath`** → `locator(xpath=...)`（可写完整 `xpath=` 或仅表达式）
3. **`testId` / `test_id`** → `getByTestId`
4. **`regex`** → `getByText(RegExp)`
5. **`text`** → `getByText`，可选 **`exact`**
6. **`role`** → `getByRole`，见下表
7. **`placeholder`** → `getByPlaceholder`，可选 **`exact`**
8. **`label`** → `getByLabel`，可选 **`exact`**
9. **`alt`** → `getByAltText`，可选 **`exact`**
10. **`title`** → `getByTitle`（匹配元素的 **`title` 属性**），可选 **`exact`**（与页面标题、`assertTitleContains` 无关）

**`getByRole` 附加字段**（与 Playwright 一致，按需选用）：

- `name`（字符串）或 `nameRegex`（正则字符串，二选一优先 `nameRegex`）
- `exact`、`pressed`、`expanded`、`includeHidden`、`level`、`checked`、`disabled`、`selected`

**iframe**：在步骤或 `locator` 上设 `frame` / `frameSelector`，再写上述字段，等价于在 `page.frameLocator(...)` 上调用同一套工厂方法。

### 3.3 `fill` / `typeInto` 中的占位替换

`value` 中可使用：

- `{{timestamp}}` → 毫秒时间戳
- `{{isoDate}}` → ISO 时间字符串
- `{{date}}` → `YYYY-MM-DD`

---

## 4. 步骤类型 `type` 一览

| `type` | 必填字段 | 说明 |
|--------|----------|------|
| `goto` | `url` | 可选 `timeoutMs`、`waitUntil`：`load` \| `domcontentloaded` \| `networkidle` \| `commit` |
| `click` | `locator` | 可选 `timeoutMs`、`force`；会先 `scrollIntoViewIfNeeded` |
| `highlight` | `locator` | 可选 `ms`（高亮后保持毫秒，默认 `800`）；调试用，元素描边便于录屏辨认 |
| `dblclick` | `locator` | 同上 |
| `hover` | `locator` | 同上 |
| `dragTo` | `locator`, `targetLocator` | 从 `locator` 拖到 `targetLocator`（另一套 locator 对象）；可选 `force` |
| `mouseDrag` | `locator`, `x`, `y` | 从 `locator` 中心拖到视口坐标（CSS 像素）；可选 `steps`（移动分段数，默认 `12`） |
| `fill` | `locator`, `value` | 可选 `timeoutMs`、`force`；`value` 支持占位替换 |
| `typeInto` | `locator`, `value` | 点击后 `pressSequentially`（富文本/Quill）；可选 `delayMs`、`timeoutMs`、`force` |
| `press` | `key` | 可选 `locator`（先聚焦该元素） |
| `wait` | `ms` | 固定睡眠 |
| `settle` | — | 可选 `gapMs`、`stable`（覆盖全局步间策略） |
| `waitForLoadState` | — | 可选 `state`：`load` \| `domcontentloaded` \| `networkidle`（默认 `networkidle`）；`timeoutMs` |
| `waitForSelector` | `locator` | 可选 `timeoutMs`、`state`：`attached`（默认）\| `visible` \| `hidden` |
| `expectVisible` | `locator` | 默认等 `visible` |
| `goBack` / `goForward` | — | |
| `switchToLatestTab` | — | 切到最后一个 tab |
| `switchToTabIndex` | `index` | 从 0 开始 |
| `closeOtherTabs` | — | 关闭除当前外所有 tab |
| `closeCurrentTab` | — | 至少需 2 个 tab |
| `expectTabCount` | `count` | 断言 tab 数量 |
| `scrollToBottom` | — | |
| `scroll` | — | `to`: `bottom` \| `top`；或 `direction`+`pixels` |
| `scrollIntoView` | `locator` | |
| `screenshot` | — | `filename`、`fullPage` |
| `assertTitleContains` | `text` | |
| `assertUrlContains` | `text` | |
| `assertTextContains` | `text` | 整页 `body` 内文本 |
| `verifyText` / `assertText` | `locator` | `text` 或 `contains`，断言**该 locator** 内文本包含子串 |
| `jsClick` | `locator` | DOM `click()` |
| `removeElement` | `locator` | 从 DOM 移除节点（如遮罩） |
| `logPageInfo` | — | 输出 URL/title/tab 数 |

**说明**：后端若使用 Midscene，步骤里**禁止** `aiAction` / `aiWaitFor`（由服务端校验）；纯 Playwright 无此限制。

---

## 5. 校验与 IDE

- JSON Schema：`schema/pipeline.schema.json`
- 在配置 JSON 顶层可加：`"$schema": "./schema/pipeline.schema.json"`（路径按项目调整）
- 命令：`npm run validate -- examples/minimal.pipeline.json`

---

## 6. 与 `run.ts` 的对应关系

解析入口：`getLocator`（定位）、`runPipeline`（`switch(type)`）。新增 `type` 或定位键时，必须更新：

1. `src/run.ts`
2. `PIPELINE_SPEC.md`
3. `schema/pipeline.schema.json`
4. `scripts/validate-pipeline.mjs` 中的枚举（若有）
