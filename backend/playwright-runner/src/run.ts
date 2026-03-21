/**
 * 纯 Playwright 执行器：无 LLM，按 JSON 步骤执行，用于高效、可预期回归。
 * 环境：PLAYWRIGHT_WORK_DIR、PLAYWRIGHT_RUN_CONFIG_JSON
 */

import * as fs from "node:fs";
import * as path from "node:path";
import type { Browser, BrowserContext, FrameLocator, Locator, Page } from "playwright";

/** 主文档或 iframe 内（与 Page 相同的一组 locator 工厂） */
type LocatorRoot = Page | FrameLocator;

type RunConfig = {
  startUrl: string;
  headless: boolean;
  recordVideo: boolean;
  stepGapMs?: number;
  stableWaitAfterStep?: boolean;
  /** 调试录屏：每个 Playwright 操作之间延迟若干毫秒，便于在 webm 里看出先后 */
  slowMoMs?: number;
  executionSteps: unknown[];
};

const DEFAULT_GAP_MS = 200;

function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

function asRecord(s: unknown, stepIndex: number): Record<string, unknown> {
  if (s && typeof s === "object" && !Array.isArray(s)) {
    return s as Record<string, unknown>;
  }
  throw new Error(`步骤 ${stepIndex + 1}: 必须是 JSON 对象`);
}

async function settleAfterStep(
  page: Page,
  gapMs: number,
  stable: boolean
): Promise<void> {
  if (!stable) {
    if (gapMs > 0) await sleep(gapMs);
    return;
  }
  try {
    await page.waitForLoadState("domcontentloaded", { timeout: 8000 });
  } catch {
    /* ignore */
  }
  if (gapMs > 0) await sleep(gapMs);
}

function parseWaitState(
  rec: Record<string, unknown>,
  defaultState: "visible" | "attached"
): "visible" | "attached" | "hidden" {
  const s = String(rec.state ?? "").trim().toLowerCase();
  if (s === "visible" || s === "attached" || s === "hidden") return s;
  return defaultState;
}

function applyStrictDisambiguation(base: Locator, o: Record<string, unknown>): Locator {
  if (o.first === true) return base.first();
  if (typeof o.nth === "number" && Number.isInteger(o.nth) && o.nth >= 0) return base.nth(o.nth);
  return base;
}

/** 步骤级 `first`/`nth`/`frame` 可与 `locator` 对象内字段合并（locator 优先） */
function mergeDisambiguation(locObj: Record<string, unknown>, stepRec: Record<string, unknown>): Record<string, unknown> {
  const out = { ...locObj };
  if (out.first === undefined && stepRec.first !== undefined) out.first = stepRec.first;
  if (out.nth === undefined && stepRec.nth !== undefined) out.nth = stepRec.nth;
  if (out.frame === undefined && stepRec.frame !== undefined) out.frame = stepRec.frame;
  if (out.frameSelector === undefined && stepRec.frameSelector !== undefined) {
    out.frameSelector = stepRec.frameSelector;
  }
  return out;
}

function getLocatorRoot(page: Page, o: Record<string, unknown>): LocatorRoot {
  const f = o.frame ?? o.frameSelector;
  if (typeof f === "string" && f.trim()) return page.frameLocator(f.trim());
  return page;
}

/** Playwright getByRole 的 JSON 可序列化选项（name 可与 nameRegex 二选一） */
function getByRoleOptionsFromLocator(o: Record<string, unknown>): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  if (typeof o.nameRegex === "string" && o.nameRegex.trim()) {
    try {
      out.name = new RegExp(o.nameRegex.trim());
    } catch (e) {
      throw new Error(`locator.nameRegex 不是合法正则: ${e instanceof Error ? e.message : String(e)}`);
    }
  } else if (typeof o.name === "string" && o.name.trim()) {
    out.name = o.name.trim();
  }
  if (o.exact !== undefined) out.exact = Boolean(o.exact);
  if (typeof o.pressed === "boolean") out.pressed = o.pressed;
  if (typeof o.expanded === "boolean") out.expanded = o.expanded;
  if (typeof o.includeHidden === "boolean") out.includeHidden = o.includeHidden;
  if (typeof o.level === "number" && Number.isInteger(o.level)) out.level = o.level;
  if (typeof o.checked === "boolean") out.checked = o.checked;
  if (typeof o.disabled === "boolean") out.disabled = o.disabled;
  if (typeof o.selected === "boolean") out.selected = o.selected;
  return out;
}

/** 字符串简写：`css` 默认；`//` / `(/` 开头或已带 `xpath=` 视为 XPath；`css=` 前缀可显式写 CSS */
function selectorFromStringShorthand(raw: string): string {
  const s = raw.trim();
  const lower = s.toLowerCase();
  if (lower.startsWith("xpath=") || lower.startsWith("css=")) return s;
  if (s.startsWith("//") || s.startsWith("(/") || /^\(\/\//.test(s)) return `xpath=${s}`;
  return s;
}

/** JSON 字符串里写 `{{timestamp}}` / `{{isoDate}}` 等，在 fill/typeInto 时替换 */
function expandValueTemplate(raw: string): string {
  const ts = String(Date.now());
  const iso = new Date().toISOString();
  return raw
    .replace(/\{\{timestamp\}\}/g, ts)
    .replace(/\{\{isoDate\}\}/g, iso)
    .replace(/\{\{date\}\}/g, iso.slice(0, 10));
}

function parseGotoWaitUntil(
  rec: Record<string, unknown>
): "load" | "domcontentloaded" | "networkidle" | "commit" {
  const w = String(rec.waitUntil ?? "load").trim().toLowerCase();
  if (w === "domcontentloaded" || w === "networkidle" || w === "commit" || w === "load") return w;
  return "load";
}

function parseForce(rec: Record<string, unknown>): boolean {
  const f = rec.force;
  if (f === true || f === 1) return true;
  if (f === false || f === 0) return false;
  if (typeof f === "string") {
    const t = f.trim().toLowerCase();
    return t === "true" || t === "1" || t === "yes";
  }
  return false;
}

function getLocator(page: Page, loc: unknown, stepIndex: number, stepRec?: Record<string, unknown>): Locator {
  const label = `步骤 ${stepIndex + 1}`;
  const sr = stepRec ?? {};

  if (typeof loc === "string" && loc.trim()) {
    const root = getLocatorRoot(page, mergeDisambiguation({}, sr));
    let base = root.locator(selectorFromStringShorthand(loc));
    if (sr.first === true) base = base.first();
    else if (typeof sr.nth === "number" && Number.isInteger(sr.nth) && sr.nth >= 0) base = base.nth(sr.nth);
    return base;
  }
  if (!loc || typeof loc !== "object") {
    throw new Error(`${label}: locator 无效（需 string 或对象，见 README 定位器）`);
  }
  const o = mergeDisambiguation(loc as Record<string, unknown>, sr);
  const root = getLocatorRoot(page, o);

  if (typeof o.css === "string" && o.css.trim()) {
    return applyStrictDisambiguation(root.locator(o.css.trim()), o);
  }
  if (typeof o.xpath === "string" && o.xpath.trim()) {
    const x = o.xpath.trim();
    const selector = x.toLowerCase().startsWith("xpath=") ? x : `xpath=${x}`;
    return applyStrictDisambiguation(root.locator(selector), o);
  }
  const testId =
    typeof o.testId === "string" && o.testId.trim()
      ? o.testId.trim()
      : typeof o.test_id === "string" && o.test_id.trim()
        ? o.test_id.trim()
        : "";
  if (testId) {
    return applyStrictDisambiguation(root.getByTestId(testId), o);
  }
  if (typeof o.regex === "string" && o.regex.trim()) {
    let pattern: RegExp;
    try {
      pattern = new RegExp(o.regex.trim());
    } catch (e) {
      throw new Error(`${label}: locator.regex 不是合法正则: ${e instanceof Error ? e.message : String(e)}`);
    }
    return applyStrictDisambiguation(root.getByText(pattern), o);
  }
  if (typeof o.text === "string" && o.text.trim()) {
    return applyStrictDisambiguation(root.getByText(o.text.trim(), { exact: Boolean(o.exact) }), o);
  }
  if (typeof o.role === "string" && o.role.trim()) {
    const roleOpts = getByRoleOptionsFromLocator(o);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    return applyStrictDisambiguation(root.getByRole(o.role.trim() as any, roleOpts as any), o);
  }
  if (typeof o.placeholder === "string") {
    return applyStrictDisambiguation(
      root.getByPlaceholder(o.placeholder, { exact: Boolean(o.exact) }),
      o
    );
  }
  if (typeof o.label === "string") {
    return applyStrictDisambiguation(root.getByLabel(o.label, { exact: Boolean(o.exact) }), o);
  }
  if (typeof o.alt === "string" && o.alt.trim()) {
    return applyStrictDisambiguation(root.getByAltText(o.alt.trim(), { exact: Boolean(o.exact) }), o);
  }
  if (typeof o.title === "string" && o.title.trim()) {
    return applyStrictDisambiguation(root.getByTitle(o.title.trim(), { exact: Boolean(o.exact) }), o);
  }
  throw new Error(
    `${label}: locator 需含 css / xpath / testId / text / regex / role / placeholder / label / alt / title（见 PIPELINE_SPEC.md）`
  );
}

function writeResultFile(workDir: string, payload: Record<string, unknown>): void {
  fs.mkdirSync(workDir, { recursive: true });
  fs.writeFileSync(path.join(workDir, "result.json"), JSON.stringify(payload, null, 2), "utf-8");
}

function writeHtmlReport(
  workDir: string,
  lines: { step: number; type: string; ok: boolean; detail: string; ms: number }[]
): string {
  const esc = (s: string) =>
    s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  const rows = lines
    .map(
      (l) =>
        `<tr><td>${l.step}</td><td>${esc(l.type)}</td><td>${l.ok ? "OK" : "FAIL"}</td><td>${l.ms}ms</td><td>${esc(l.detail)}</td></tr>`
    )
    .join("\n");
  const html = `<!DOCTYPE html><html><head><meta charset="utf-8"/><title>Playwright 执行报告</title>
<style>body{font-family:system-ui,sans-serif;margin:16px;}table{border-collapse:collapse;width:100%;}td,th{border:1px solid #ccc;padding:8px;text-align:left;}th{background:#f5f5f5;}</style>
</head><body><h1>JM Test Center 纯 Playwright 报告</h1><p>共 ${lines.length} 步</p><table><thead><tr><th>#</th><th>type</th><th>结果</th><th>耗时</th><th>说明</th></tr></thead><tbody>${rows}</tbody></table></body></html>`;
  const rel = "report/playwright-report.html";
  const abs = path.join(workDir, rel);
  fs.mkdirSync(path.dirname(abs), { recursive: true });
  fs.writeFileSync(abs, html, "utf-8");
  return rel.replace(/\\/g, "/");
}

function walkFiles(dir: string): string[] {
  if (!fs.existsSync(dir)) return [];
  const out: string[] = [];
  for (const name of fs.readdirSync(dir)) {
    const p = path.join(dir, name);
    const st = fs.statSync(p);
    if (st.isDirectory()) out.push(...walkFiles(p));
    else out.push(p);
  }
  return out;
}

function findVideoFile(videoDir: string): string | null {
  if (!fs.existsSync(videoDir)) return null;
  const vids = walkFiles(videoDir).filter((f) => /\.(webm|mp4|mkv)$/i.test(f));
  if (vids.length === 0) return null;
  vids.sort((a, b) => fs.statSync(b).mtimeMs - fs.statSync(a).mtimeMs);
  return vids[0] ?? null;
}

async function runPipeline(
  steps: unknown[],
  context: import("playwright").BrowserContext,
  initialPage: Page,
  gapMs: number,
  stable: boolean
): Promise<{ lines: { step: number; type: string; ok: boolean; detail: string; ms: number }[] }> {
  const lines: { step: number; type: string; ok: boolean; detail: string; ms: number }[] = [];
  let page = initialPage;

  for (let i = 0; i < steps.length; i++) {
    const rec = asRecord(steps[i], i);
    const type = String(rec.type ?? "").trim();
    const t0 = Date.now();
    let ok = true;
    let detail = "done";

    try {
      switch (type) {
        case "goto": {
          const url = String(rec.url ?? "").trim();
          if (!url) throw new Error("goto: url 不能为空");
          const timeout = typeof rec.timeoutMs === "number" ? rec.timeoutMs : 120_000;
          const waitUntil = parseGotoWaitUntil(rec);
          await page.goto(url, { waitUntil, timeout });
          break;
        }
        case "click": {
          const loc = getLocator(page, rec.locator, i, rec);
          const timeout = typeof rec.timeoutMs === "number" ? rec.timeoutMs : 30_000;
          await loc.scrollIntoViewIfNeeded({ timeout }).catch(() => undefined);
          await loc.click({ timeout, force: parseForce(rec) });
          break;
        }
        case "dblclick": {
          const loc = getLocator(page, rec.locator, i, rec);
          const timeout = typeof rec.timeoutMs === "number" ? rec.timeoutMs : 30_000;
          await loc.dblclick({ timeout, force: parseForce(rec) });
          break;
        }
        case "fill": {
          const loc = getLocator(page, rec.locator, i, rec);
          const value = expandValueTemplate(String(rec.value ?? ""));
          const t = typeof rec.timeoutMs === "number" ? rec.timeoutMs : 30_000;
          await loc.fill(value, {
            timeout: t,
            force: parseForce(rec)
          });
          break;
        }
        /** 富文本/Quill 等：点击后逐字输入（避免 fill 对 contenteditable 不生效） */
        case "typeInto": {
          const loc = getLocator(page, rec.locator, i, rec);
          const text = expandValueTemplate(String(rec.value ?? ""));
          const delay = typeof rec.delayMs === "number" && rec.delayMs >= 0 ? rec.delayMs : 15;
          const timeout = typeof rec.timeoutMs === "number" ? rec.timeoutMs : 30_000;
          await loc.click({ timeout, force: parseForce(rec) });
          await loc.pressSequentially(text, { delay });
          break;
        }
        case "press": {
          const key = String(rec.key ?? "").trim();
          if (!key) throw new Error("press: key 不能为空");
          if (rec.locator !== undefined && rec.locator !== null) {
            await getLocator(page, rec.locator, i, rec).press(key);
          } else {
            await page.keyboard.press(key);
          }
          break;
        }
        case "hover": {
          const timeout = typeof rec.timeoutMs === "number" ? rec.timeoutMs : 30_000;
          await getLocator(page, rec.locator, i, rec).hover({ timeout, force: parseForce(rec) });
          break;
        }
        /** 拖到另一元素：Playwright `dragTo` */
        case "dragTo": {
          const src = getLocator(page, rec.locator, i, rec);
          const tl = rec.targetLocator;
          if (tl === undefined || tl === null) {
            throw new Error("dragTo: targetLocator 不能为空");
          }
          const tgt = getLocator(page, tl, i, rec);
          await src.dragTo(tgt, { force: parseForce(rec) });
          break;
        }
        /** 从 locator 中心拖到视口坐标 (x,y)，单位 CSS 像素；可选 steps 为移动分段数（默认 12） */
        case "mouseDrag": {
          const src = getLocator(page, rec.locator, i, rec);
          const ex = Number(rec.x);
          const ey = Number(rec.y);
          if (!Number.isFinite(ex) || !Number.isFinite(ey)) {
            throw new Error("mouseDrag: x、y 必填（视口 CSS 像素）");
          }
          const nSteps = typeof rec.steps === "number" && rec.steps >= 1 ? Math.floor(rec.steps) : 12;
          await src.scrollIntoViewIfNeeded({ timeout: 15_000 }).catch(() => undefined);
          const box = await src.boundingBox();
          if (!box) throw new Error("mouseDrag: 源元素不可见或无尺寸");
          const sx = box.x + box.width / 2;
          const sy = box.y + box.height / 2;
          await page.mouse.move(sx, sy);
          await page.mouse.down();
          await page.mouse.move(ex, ey, { steps: nSteps });
          await page.mouse.up();
          break;
        }
        case "wait": {
          const ms = Number(rec.ms);
          if (!Number.isFinite(ms) || ms < 0) throw new Error("wait: ms 无效");
          await sleep(ms);
          break;
        }
        case "settle": {
          const g = typeof rec.gapMs === "number" ? rec.gapMs : gapMs;
          const st = typeof rec.stable === "boolean" ? rec.stable : stable;
          await settleAfterStep(page, g, st);
          break;
        }
        case "waitForLoadState": {
          const raw = String(rec.state ?? "networkidle").trim().toLowerCase();
          const st: "load" | "domcontentloaded" | "networkidle" =
            raw === "load" || raw === "domcontentloaded" || raw === "networkidle" ? raw : "networkidle";
          const timeout = typeof rec.timeoutMs === "number" ? rec.timeoutMs : 60_000;
          await page.waitForLoadState(st, { timeout });
          break;
        }
        case "waitForSelector": {
          const loc = getLocator(page, rec.locator, i, rec);
          const timeout = typeof rec.timeoutMs === "number" ? rec.timeoutMs : 30_000;
          /** 默认 attached：百度 #kw 等常被标为 hidden，等 visible 会误超时 */
          const state = parseWaitState(rec, "attached");
          await loc.waitFor({ state, timeout });
          break;
        }
        case "expectVisible": {
          const loc = getLocator(page, rec.locator, i, rec);
          const timeout = typeof rec.timeoutMs === "number" ? rec.timeoutMs : 15_000;
          const state = parseWaitState(rec, "visible");
          await loc.waitFor({ state, timeout });
          break;
        }
        case "goBack": {
          try {
            await page.goBack({ waitUntil: "load", timeout: 60_000 });
          } catch {
            await page.goBack({ waitUntil: "domcontentloaded" });
          }
          break;
        }
        case "goForward": {
          await page.goForward({ waitUntil: "load", timeout: 60_000 });
          break;
        }
        case "switchToLatestTab": {
          const pages = context.pages();
          if (pages.length === 0) throw new Error("没有可用标签页");
          page = pages[pages.length - 1];
          await page.bringToFront();
          break;
        }
        case "switchToTabIndex": {
          const idx = Number(rec.index);
          if (!Number.isInteger(idx) || idx < 0) throw new Error("switchToTabIndex: index 无效");
          const pages = context.pages();
          if (idx >= pages.length) throw new Error(`index ${idx} 超出范围(共 ${pages.length} 个)`);
          page = pages[idx];
          await page.bringToFront();
          break;
        }
        case "closeOtherTabs": {
          for (const p of context.pages()) {
            if (p !== page) await p.close();
          }
          break;
        }
        case "closeCurrentTab": {
          const pagesBefore = context.pages();
          if (pagesBefore.length <= 1) throw new Error("只剩一个标签页，无法关闭");
          const idx = pagesBefore.indexOf(page);
          await page.close();
          const after = context.pages();
          page = after[Math.max(0, idx - 1)] ?? after[0];
          await page.bringToFront();
          break;
        }
        case "expectTabCount": {
          const count = Number(rec.count);
          if (!Number.isInteger(count) || count < 0) throw new Error("expectTabCount: count 无效");
          const n = context.pages().length;
          if (n !== count) throw new Error(`期望 ${count} 个标签页，实际 ${n}`);
          break;
        }
        case "scrollToBottom": {
          await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
          await sleep(300);
          break;
        }
        case "scrollIntoView": {
          await getLocator(page, rec.locator, i, rec).scrollIntoViewIfNeeded({
            timeout: typeof rec.timeoutMs === "number" ? rec.timeoutMs : 15_000
          });
          break;
        }
        case "screenshot": {
          const rawName = String(rec.filename ?? `shot-${Date.now()}.png`);
          const safe = rawName.replace(/[^a-zA-Z0-9._-]/g, "_");
          const dir = path.join(process.env.PLAYWRIGHT_WORK_DIR ?? ".", "artifacts");
          fs.mkdirSync(dir, { recursive: true });
          const fp = path.join(dir, safe);
          await page.screenshot({ path: fp, fullPage: Boolean(rec.fullPage) });
          detail = `saved ${safe}`;
          break;
        }
        case "assertTitleContains": {
          const t = String(rec.text ?? "");
          const title = await page.title();
          if (!title.includes(t)) throw new Error(`标题不含「${t}」，当前: ${title.slice(0, 200)}`);
          break;
        }
        case "assertUrlContains": {
          const t = String(rec.text ?? "");
          const u = page.url();
          if (!u.includes(t)) throw new Error(`URL 不含「${t}」，当前: ${u}`);
          break;
        }
        case "assertTextContains": {
          const sub = String(rec.text ?? "");
          const body = await page.locator("body").innerText();
          if (!body.includes(sub)) throw new Error(`正文不含「${sub.slice(0, 80)}」`);
          break;
        }
        case "highlight": {
          const loc = getLocator(page, rec.locator, i, rec);
          await loc.scrollIntoViewIfNeeded({ timeout: 15_000 }).catch(() => undefined);
          await loc.highlight();
          const hold = typeof rec.ms === "number" && Number.isFinite(rec.ms) && rec.ms >= 0 ? rec.ms : 800;
          await sleep(hold);
          break;
        }
        case "jsClick": {
          const loc = getLocator(page, rec.locator, i, rec);
          await loc.evaluate((el: HTMLElement) => el.click());
          break;
        }
        /** 从 DOM 移除匹配节点（如 demo.metersphere.com 的 .maxkb-mask 挡点击） */
        case "removeElement": {
          const loc = getLocator(page, rec.locator, i, rec);
          await loc.evaluate((el: HTMLElement) => el.remove()).catch(() => undefined);
          break;
        }
        case "scroll": {
          const toRaw = rec.to !== undefined ? String(rec.to).trim().toLowerCase() : "";
          if (toRaw === "bottom") {
            await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
            await sleep(300);
            break;
          }
          if (toRaw === "top") {
            await page.evaluate(() => window.scrollTo(0, 0));
            await sleep(200);
            break;
          }
          const dir = String(rec.direction ?? "down").toLowerCase();
          const px = typeof rec.pixels === "number" && Number.isFinite(rec.pixels) ? rec.pixels : 400;
          const d = dir === "up" ? -px : px;
          await page.evaluate((delta) => window.scrollBy(0, delta), d);
          await sleep(200);
          break;
        }
        case "verifyText":
        case "assertText": {
          const loc = getLocator(page, rec.locator, i, rec);
          const expect = String(rec.text ?? rec.contains ?? "").trim();
          if (!expect) throw new Error("verifyText: text 或 contains 不能为空");
          const actual = (await loc.innerText()).trim();
          if (!actual.includes(expect)) {
            throw new Error(`verifyText: 期望含「${expect.slice(0, 120)}」，实际「${actual.slice(0, 200)}」`);
          }
          break;
        }
        case "logPageInfo": {
          const payload = {
            step: i + 1,
            url: page.url(),
            title: await page.title(),
            tabCount: context.pages().length,
            ts: new Date().toISOString()
          };
          detail = JSON.stringify(payload);
          console.log("[JMTEST_PAGE_INFO]", detail);
          break;
        }
        default:
          throw new Error(
            `未知 type「${type}」。支持: goto,click,highlight,jsClick,removeElement,dblclick,fill,typeInto,press,hover,dragTo,mouseDrag,wait,settle,waitForLoadState,waitForSelector,expectVisible,goBack,goForward,switchToLatestTab,switchToTabIndex,closeOtherTabs,closeCurrentTab,expectTabCount,scrollToBottom,scroll,scrollIntoView,screenshot,assertTitleContains,assertUrlContains,assertTextContains,verifyText,assertText,logPageInfo`
          );
      }
    } catch (e) {
      ok = false;
      detail = e instanceof Error ? e.message : String(e);
      lines.push({ step: i + 1, type, ok, detail, ms: Date.now() - t0 });
      throw new Error(`步骤 ${i + 1} (${type}): ${detail}`);
    }

    lines.push({ step: i + 1, type, ok, detail, ms: Date.now() - t0 });
    if (i < steps.length - 1) await settleAfterStep(page, gapMs, stable);
  }

  return { lines };
}

async function main(): Promise<void> {
  const workDir = process.env.PLAYWRIGHT_WORK_DIR;
  if (!workDir) throw new Error("PLAYWRIGHT_WORK_DIR is required");
  const raw = process.env.PLAYWRIGHT_RUN_CONFIG_JSON;
  if (!raw) throw new Error("PLAYWRIGHT_RUN_CONFIG_JSON is required");

  const config = JSON.parse(raw) as RunConfig;
  fs.mkdirSync(workDir, { recursive: true });
  const videoDir = path.join(workDir, "videos");
  if (config.recordVideo) fs.mkdirSync(videoDir, { recursive: true });

  let browser: Browser | undefined;
  let context: BrowserContext | undefined;

  const writeResult = (payload: Record<string, unknown>) => {
    writeResultFile(workDir, payload);
  };

  try {
    const { chromium } = await import("playwright");
    const SLOW_MO_MS_MAX = 2000;
    const slowMo =
      typeof config.slowMoMs === "number" && Number.isFinite(config.slowMoMs) && config.slowMoMs >= 0
        ? Math.min(config.slowMoMs, SLOW_MO_MS_MAX)
        : undefined;
    browser = await chromium.launch({
      headless: config.headless,
      ...(slowMo !== undefined ? { slowMo } : {}),
      args: ["--no-sandbox", "--disable-setuid-sandbox"]
    });

    context = await browser.newContext({
      viewport: { width: 1280, height: 768 },
      recordVideo: config.recordVideo
        ? { dir: videoDir, size: { width: 1280, height: 768 } }
        : undefined
    });

    let page = await context!.newPage();
    const gapMs =
      typeof config.stepGapMs === "number" && Number.isFinite(config.stepGapMs) && config.stepGapMs >= 0
        ? config.stepGapMs
        : DEFAULT_GAP_MS;
    const stable = Boolean(config.stableWaitAfterStep);

    await page.goto(config.startUrl, { waitUntil: "load", timeout: 120_000 });
    await settleAfterStep(page, gapMs, stable);

    const steps = config.executionSteps;
    if (!Array.isArray(steps) || steps.length === 0) {
      throw new Error("executionSteps 必须为非空数组");
    }

    const { lines } = await runPipeline(steps, context!, page, gapMs, stable);
    const reportRel = writeHtmlReport(workDir, lines);
    const videoAbs = config.recordVideo ? findVideoFile(videoDir) : null;
    const rel = (abs: string | null) => {
      if (!abs) return null;
      return path.relative(workDir, abs).split(path.sep).join("/");
    };

    writeResult({
      ok: true,
      report_file: reportRel,
      video_file: rel(videoAbs),
      pipeline_log: lines
    });

    await context!.close();
    context = undefined;
    await browser.close();
    browser = undefined;
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    /** 必须先关 context，录屏才会完整落盘（直接 browser.close 会截断 webm） */
    if (context) {
      try {
        await context.close();
      } catch {
        /* ignore */
      }
      context = undefined;
    }
    if (browser) {
      try {
        await browser.close();
      } catch {
        /* ignore */
      }
      browser = undefined;
    }
    const videoAbs =
      config.recordVideo && fs.existsSync(videoDir) ? findVideoFile(videoDir) : null;
    const rel = (abs: string | null) => {
      if (!abs) return null;
      return path.relative(workDir, abs).split(path.sep).join("/");
    };
    writeResult({
      ok: false,
      error: msg,
      report_file: null,
      video_file: rel(videoAbs),
      pipeline_log: []
    });
    process.exitCode = 1;
  }
}

main().catch((e) => {
  const workDir = process.env.PLAYWRIGHT_WORK_DIR ?? ".";
  const msg = e instanceof Error ? e.message : String(e);
  writeResultFile(workDir, {
    ok: false,
    error: msg,
    report_file: null,
    video_file: null
  });
  process.exit(1);
});
