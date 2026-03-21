/**
 * 轻量校验：顶层必填、executionSteps 非空、每步含 type 且 type 在允许列表中。
 * 完整语义以 src/run.ts 为准；JSON Schema 见 schema/pipeline.schema.json
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.join(__dirname, "..");

const ALLOWED_TYPES = new Set([
  "goto",
  "click",
  "dblclick",
  "fill",
  "typeInto",
  "press",
  "hover",
  "wait",
  "settle",
  "waitForLoadState",
  "waitForSelector",
  "expectVisible",
  "goBack",
  "goForward",
  "switchToLatestTab",
  "switchToTabIndex",
  "closeOtherTabs",
  "closeCurrentTab",
  "expectTabCount",
  "scrollToBottom",
  "scroll",
  "scrollIntoView",
  "screenshot",
  "assertTitleContains",
  "assertUrlContains",
  "assertTextContains",
  "jsClick",
  "highlight",
  "removeElement",
  "verifyText",
  "assertText",
  "logPageInfo"
]);

const file = process.argv[2];
if (!file) {
  console.error("用法: node scripts/validate-pipeline.mjs <config.json>");
  process.exit(1);
}

const abs = path.isAbsolute(file) ? file : path.join(process.cwd(), file);
const raw = fs.readFileSync(abs, "utf8");
let data;
try {
  data = JSON.parse(raw);
} catch (e) {
  console.error("JSON 解析失败:", e instanceof Error ? e.message : e);
  process.exit(1);
}

const errs = [];
for (const k of ["startUrl", "headless", "recordVideo", "executionSteps"]) {
  if (!(k in data)) errs.push(`缺少必填字段: ${k}`);
}
if (!Array.isArray(data.executionSteps) || data.executionSteps.length === 0) {
  errs.push("executionSteps 必须为非空数组");
}

data.executionSteps?.forEach((step, i) => {
  if (!step || typeof step !== "object") {
    errs.push(`步骤 ${i + 1}: 不是对象`);
    return;
  }
  const t = String(step.type ?? "").trim();
  if (!t) errs.push(`步骤 ${i + 1}: 缺少 type`);
  else if (!ALLOWED_TYPES.has(t)) errs.push(`步骤 ${i + 1}: 未知 type「${t}」`);
});

if (errs.length) {
  console.error("校验失败:\n", errs.join("\n"));
  process.exit(1);
}
console.log("校验通过:", abs);
