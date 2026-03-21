/**
 * Midscene.js + Playwright 执行入口，由后端通过环境变量注入配置。
 * 支持两种模式：
 * 1) 经典：instructions + instructionMode（multi_line / single_block）
 * 2) 步骤编排：executionSteps 数组，混合 aiAction 与 Playwright 白名单操作（复杂场景）
 */

import * as fs from "node:fs";
import * as path from "node:path";
import type { Browser } from "playwright";

type RunConfig = {
  startUrl: string;
  instructionMode: "multi_line" | "single_block";
  instructions: string;
  headless: boolean;
  recordVideo: boolean;
  stepGapMs?: number;
  stableWaitAfterStep?: boolean;
  /** 若为非空数组，优先按步骤编排执行，忽略 instructions / instructionMode */
  executionSteps?: unknown[];
};

/** 默认步骤间隔；可被前端/JSON 或环境变量 MIDSCENE_STEP_GAP_MS 覆盖 */
const DEFAULT_STEP_GAP_MS = 400;
/** 默认关闭：仅 sleep gap；开启时多一次 domcontentloaded（仍可用 MIDSCENE_STABLE_WAIT=1 强制开） */
const DEFAULT_STABLE_WAIT = false;

function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

function asRecord(s: unknown, stepIndex: number): Record<string, unknown> {
  if (s && typeof s === "object" && !Array.isArray(s)) {
    return s as Record<string, unknown>;
  }
  throw new Error(`步骤 ${stepIndex + 1}: 必须是 JSON 对象`);
}

/**
 * 步骤后「稳定」等待。
 * 旧版会串 load + networkidle（SPA/长连接页面上 networkidle 常卡满 10+ 秒），体感像脚本挂了。
 * 现默认只做轻量 domcontentloaded + 你配置的 gapMs；若页面极难稳再设 MIDSCENE_SETTLE_NETWORK_IDLE=1。
 */
async function settleAfterStep(
  page: import("playwright").Page,
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

  if (process.env.MIDSCENE_SETTLE_NETWORK_IDLE === "1") {
    try {
      await page.waitForLoadState("networkidle", { timeout: 12_000 });
    } catch {
      /* ignore */
    }
  }

  if (gapMs > 0) await sleep(gapMs);
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

function findLatestHtmlUnderMidscene(workDir: string): string | null {
  const base = path.join(workDir, "midscene_run");
  if (!fs.existsSync(base)) return null;
  const htmls = walkFiles(base).filter((f) => f.toLowerCase().endsWith(".html"));
  if (htmls.length === 0) return null;
  htmls.sort((a, b) => fs.statSync(b).mtimeMs - fs.statSync(a).mtimeMs);
  return htmls[0] ?? null;
}

function findVideoFile(videoDir: string): string | null {
  if (!fs.existsSync(videoDir)) return null;
  const all = walkFiles(videoDir);
  const vids = all.filter((f) => /\.(webm|mp4|mkv)$/i.test(f));
  if (vids.length === 0) return null;
  vids.sort((a, b) => fs.statSync(b).mtimeMs - fs.statSync(a).mtimeMs);
  return vids[0] ?? null;
}

function writeResultFile(workDir: string, payload: Record<string, unknown>): void {
  const resultPath = path.join(workDir, "result.json");
  fs.mkdirSync(workDir, { recursive: true });
  fs.writeFileSync(resultPath, JSON.stringify(payload, null, 2), "utf-8");
}

/** 单步 aiAction 最长等待（毫秒）；0 或负数表示不限制。可由步骤 JSON 的 timeoutMs 覆盖 */
function resolveGlobalAiActionTimeoutMs(): number | null {
  const raw = process.env.MIDSCENE_AI_ACTION_TIMEOUT_MS;
  if (raw === undefined || raw === "") return 300_000;
  const n = Number(raw);
  if (!Number.isFinite(n) || n <= 0) return null;
  return n;
}

function resolveAiActionTimeoutMsForStep(rec: Record<string, unknown>): number | null {
  if (typeof rec.timeoutMs === "number" && Number.isFinite(rec.timeoutMs)) {
    if (rec.timeoutMs <= 0) return null;
    return rec.timeoutMs;
  }
  return resolveGlobalAiActionTimeoutMs();
}

function playwrightAgentOpts(): { replanningCycleLimit?: number } {
  const n = Number(process.env.MIDSCENE_REPLANNING_CYCLE_LIMIT);
  if (Number.isFinite(n) && n > 0) return { replanningCycleLimit: n };
  return {};
}

async function withTimeout<T>(
  promise: Promise<T>,
  ms: number | null,
  errMessage: string
): Promise<T> {
  if (ms == null || ms <= 0) return promise;
  let timer: ReturnType<typeof setTimeout> | undefined;
  try {
    return await Promise.race([
      promise,
      new Promise<T>((_, reject) => {
        timer = setTimeout(() => reject(new Error(errMessage)), ms);
      })
    ]);
  } finally {
    if (timer !== undefined) clearTimeout(timer);
  }
}

function resolveStepOptions(config: RunConfig): { gapMs: number; stable: boolean } {
  let gapMs =
    typeof config.stepGapMs === "number" && Number.isFinite(config.stepGapMs) && config.stepGapMs >= 0
      ? config.stepGapMs
      : DEFAULT_STEP_GAP_MS;
  const envGap = Number(process.env.MIDSCENE_STEP_GAP_MS);
  if (Number.isFinite(envGap) && envGap >= 0) {
    gapMs = envGap;
  }

  let stable =
    config.stableWaitAfterStep === undefined ? DEFAULT_STABLE_WAIT : Boolean(config.stableWaitAfterStep);
  if (process.env.MIDSCENE_STABLE_WAIT === "0") stable = false;
  if (process.env.MIDSCENE_STABLE_WAIT === "1") stable = true;

  return { gapMs, stable };
}

type PipelineCtx = {
  workDir: string;
  gapMs: number;
  stable: boolean;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  PlaywrightAgent: new (page: import("playwright").Page, opts?: object) => any;
};

/**
 * 步骤编排：白名单 type，避免任意代码执行
 */
async function runExecutionPipeline(
  steps: unknown[],
  context: import("playwright").BrowserContext,
  initialPage: import("playwright").Page,
  ctx: PipelineCtx
): Promise<{ screenshots: string[]; pageInfoLogs: unknown[] }> {
  const screenshots: string[] = [];
  const pageInfoLogs: unknown[] = [];

  let page = initialPage;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let agent: any = null;

  async function destroyAgent(): Promise<void> {
    if (agent && typeof agent.destroy === "function") {
      await agent.destroy();
    }
    agent = null;
  }

  const agentOpts = playwrightAgentOpts();

  /** 同一页面上连续 ai 步骤复用 Agent，避免每步 new/destroy 的额外开销 */
  async function ensureAgent(): Promise<any> {
    if (!agent) {
      agent = new ctx.PlaywrightAgent(page, Object.keys(agentOpts).length ? agentOpts : undefined);
    }
    return agent;
  }

  const artifactsDir = path.join(ctx.workDir, "artifacts");
  fs.mkdirSync(artifactsDir, { recursive: true });

  for (let i = 0; i < steps.length; i++) {
    const rec = asRecord(steps[i], i);
    const type = String(rec.type ?? "").trim();

    switch (type) {
      case "aiAction": {
        const text = String(rec.text ?? "").trim();
        if (!text) throw new Error(`步骤 ${i + 1} (aiAction): text 不能为空`);
        const a = await ensureAgent();
        const tMs = resolveAiActionTimeoutMsForStep(rec);
        await withTimeout(
          a.aiAction(text),
          tMs,
          `步骤 ${i + 1} (aiAction): 超过 ${tMs ?? "?"}ms 仍未完成（可拆分步骤、调大本步 timeoutMs 或环境变量 MIDSCENE_AI_ACTION_TIMEOUT_MS；设为 0 关闭单步超时）`
        );
        if (i < steps.length - 1) await settleAfterStep(page, ctx.gapMs, ctx.stable);
        break;
      }
      /** Midscene：轮询截图直到自然语言条件满足（见 @midscene/core AgentWaitForOpt） */
      case "aiWaitFor": {
        const text = String(rec.text ?? "").trim();
        if (!text) throw new Error(`步骤 ${i + 1} (aiWaitFor): text 不能为空`);
        const opt: { timeoutMs?: number; checkIntervalMs?: number } = {};
        if (typeof rec.timeoutMs === "number" && Number.isFinite(rec.timeoutMs) && rec.timeoutMs > 0) {
          opt.timeoutMs = rec.timeoutMs;
        }
        if (
          typeof rec.checkIntervalMs === "number" &&
          Number.isFinite(rec.checkIntervalMs) &&
          rec.checkIntervalMs > 0
        ) {
          opt.checkIntervalMs = rec.checkIntervalMs;
        }
        const a = await ensureAgent();
        await a.aiWaitFor(text, Object.keys(opt).length > 0 ? opt : undefined);
        if (i < steps.length - 1) await settleAfterStep(page, ctx.gapMs, ctx.stable);
        break;
      }
      case "settle": {
        const g = typeof rec.gapMs === "number" ? rec.gapMs : ctx.gapMs;
        const st = typeof rec.stable === "boolean" ? rec.stable : ctx.stable;
        await settleAfterStep(page, g, st);
        break;
      }
      case "wait": {
        const ms = Number(rec.ms);
        if (!Number.isFinite(ms) || ms < 0) throw new Error(`步骤 ${i + 1} (wait): ms 无效`);
        await sleep(ms);
        break;
      }
      case "goto": {
        const url = String(rec.url ?? "").trim();
        if (!url) throw new Error(`步骤 ${i + 1} (goto): url 不能为空`);
        await destroyAgent();
        await page.goto(url, { waitUntil: "load", timeout: 120_000 });
        await settleAfterStep(page, ctx.gapMs, ctx.stable);
        break;
      }
      case "goBack": {
        try {
          await page.goBack({ waitUntil: "load", timeout: 60_000 });
        } catch {
          await page.goBack({ waitUntil: "domcontentloaded" });
        }
        await settleAfterStep(page, ctx.gapMs, ctx.stable);
        await destroyAgent();
        break;
      }
      case "switchToLatestTab": {
        await destroyAgent();
        const pages = context.pages();
        if (pages.length === 0) throw new Error(`步骤 ${i + 1}: 没有可用标签页`);
        page = pages[pages.length - 1];
        await page.bringToFront();
        break;
      }
      case "switchToTabIndex": {
        const idx = Number(rec.index);
        if (!Number.isInteger(idx) || idx < 0) throw new Error(`步骤 ${i + 1} (switchToTabIndex): index 无效`);
        await destroyAgent();
        const pages = context.pages();
        if (idx >= pages.length) throw new Error(`步骤 ${i + 1}: index ${idx} 超出范围(共 ${pages.length} 个)`);
        page = pages[idx];
        await page.bringToFront();
        break;
      }
      case "closeOtherTabs": {
        await destroyAgent();
        for (const p of context.pages()) {
          if (p !== page) await p.close();
        }
        break;
      }
      case "closeCurrentTab": {
        const pagesBefore = context.pages();
        if (pagesBefore.length <= 1) {
          throw new Error(`步骤 ${i + 1} (closeCurrentTab): 只剩一个标签页，无法关闭`);
        }
        const idx = pagesBefore.indexOf(page);
        await destroyAgent();
        await page.close();
        const after = context.pages();
        page = after[Math.max(0, idx - 1)] ?? after[0];
        await page.bringToFront();
        break;
      }
      case "expectTabCount": {
        const count = Number(rec.count);
        if (!Number.isInteger(count) || count < 0) throw new Error(`步骤 ${i + 1} (expectTabCount): count 无效`);
        const n = context.pages().length;
        if (n !== count) {
          throw new Error(`步骤 ${i + 1} (expectTabCount): 期望 ${count} 个标签页，实际 ${n} 个`);
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
        pageInfoLogs.push(payload);
        console.log("[JMTEST_PAGE_INFO]", JSON.stringify(payload));
        break;
      }
      case "scrollToBottom": {
        await page.evaluate(() => {
          window.scrollTo(0, document.body.scrollHeight);
        });
        await sleep(500);
        break;
      }
      case "screenshot": {
        const rawName = String(rec.filename ?? `shot-${Date.now()}.png`);
        const safe = rawName.replace(/[^a-zA-Z0-9._-]/g, "_");
        const fp = path.join(artifactsDir, safe);
        await page.screenshot({
          path: fp,
          fullPage: Boolean(rec.fullPage)
        });
        screenshots.push(path.relative(ctx.workDir, fp).split(path.sep).join("/"));
        break;
      }
      case "assertTitleContains": {
        const t = String(rec.text ?? "");
        const title = await page.title();
        if (!title.includes(t)) {
          throw new Error(`步骤 ${i + 1} (assertTitleContains): 标题不含「${t}」，当前: ${title.slice(0, 200)}`);
        }
        break;
      }
      case "assertUrlContains": {
        const t = String(rec.text ?? "");
        const u = page.url();
        if (!u.includes(t)) {
          throw new Error(`步骤 ${i + 1} (assertUrlContains): URL 不含「${t}」，当前: ${u}`);
        }
        break;
      }
      default:
        throw new Error(
          `步骤 ${i + 1}: 未知 type「${type}」。支持: aiAction,aiWaitFor,settle,wait,goto,goBack,switchToLatestTab,switchToTabIndex,closeOtherTabs,closeCurrentTab,expectTabCount,logPageInfo,scrollToBottom,screenshot,assertTitleContains,assertUrlContains`
        );
    }
  }

  await destroyAgent();
  return { screenshots, pageInfoLogs };
}

async function main(): Promise<void> {
  const workDir = process.env.MIDSCENE_WORK_DIR;
  if (!workDir) {
    throw new Error("MIDSCENE_WORK_DIR is required");
  }
  const raw = process.env.MIDSCENE_CONFIG_JSON;
  if (!raw) {
    throw new Error("MIDSCENE_CONFIG_JSON is required");
  }

  const config = JSON.parse(raw) as RunConfig;
  fs.mkdirSync(workDir, { recursive: true });
  const videoDir = path.join(workDir, "videos");
  if (config.recordVideo) {
    fs.mkdirSync(videoDir, { recursive: true });
  }

  const writeResult = (payload: Record<string, unknown>) => {
    writeResultFile(workDir, payload);
  };

  let browser: Browser | undefined;

  try {
    const { chromium } = await import("playwright");
    const { PlaywrightAgent } = await import("@midscene/web/playwright");

    browser = await chromium.launch({
      headless: config.headless,
      args: ["--no-sandbox", "--disable-setuid-sandbox"],
    });

    const context = await browser.newContext({
      viewport: { width: 1280, height: 768 },
      recordVideo: config.recordVideo
        ? {
            dir: videoDir,
            size: { width: 1280, height: 768 },
          }
        : undefined,
    });

    let page = await context.newPage();
    await page.goto(config.startUrl, { waitUntil: "load", timeout: 120_000 });

    const { gapMs, stable } = resolveStepOptions(config);

    const usePipeline = Array.isArray(config.executionSteps) && config.executionSteps.length > 0;

    if (usePipeline) {
      await settleAfterStep(page, gapMs, stable);
      const pipe = await runExecutionPipeline(config.executionSteps!, context, page, {
        workDir,
        gapMs,
        stable,
        PlaywrightAgent
      });
      const reportAbs = findLatestHtmlUnderMidscene(workDir);
      const videoAbs = config.recordVideo ? findVideoFile(videoDir) : null;
      const rel = (abs: string | null) => {
        if (!abs) return null;
        return path.relative(workDir, abs).split(path.sep).join("/");
      };
      writeResult({
        ok: true,
        report_file: rel(reportAbs),
        video_file: rel(videoAbs),
        pipeline_screenshots: pipe.screenshots,
        pipeline_page_info: pipe.pageInfoLogs
      });
    } else {
      const ao = playwrightAgentOpts();
      const agent = new PlaywrightAgent(page, Object.keys(ao).length ? ao : undefined);
      const lineTimeout = resolveGlobalAiActionTimeoutMs();

      const text = (config.instructions ?? "").trim();
      if (!text) {
        throw new Error("instructions 不能为空（未使用 executionSteps 时）");
      }

      await settleAfterStep(page, gapMs, stable);

      if (config.instructionMode === "single_block") {
        await withTimeout(
          agent.aiAction(text),
          lineTimeout,
          `aiAction（single_block）: 超过 ${lineTimeout ?? "?"}ms 仍未完成（见 MIDSCENE_AI_ACTION_TIMEOUT_MS）`
        );
      } else {
        const lines = text
          .split(/\r?\n/)
          .map((s) => s.trim())
          .filter(Boolean);
        for (let i = 0; i < lines.length; i++) {
          await withTimeout(
            agent.aiAction(lines[i]),
            lineTimeout,
            `第 ${i + 1} 行 aiAction: 超过 ${lineTimeout ?? "?"}ms 仍未完成（见 MIDSCENE_AI_ACTION_TIMEOUT_MS）`
          );
          if (i < lines.length - 1) {
            await settleAfterStep(page, gapMs, stable);
          }
        }
      }

      if (typeof (agent as { destroy?: () => Promise<void> }).destroy === "function") {
        await (agent as { destroy: () => Promise<void> }).destroy();
      }

      const reportAbs = findLatestHtmlUnderMidscene(workDir);
      const videoAbs = config.recordVideo ? findVideoFile(videoDir) : null;
      const rel = (abs: string | null) => {
        if (!abs) return null;
        return path.relative(workDir, abs).split(path.sep).join("/");
      };

      writeResult({
        ok: true,
        report_file: rel(reportAbs),
        video_file: rel(videoAbs)
      });
    }

    await context.close();
    await browser.close();
    browser = undefined;
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    if (browser) {
      try {
        await browser.close();
      } catch {
        /* ignore */
      }
    }
    writeResult({
      ok: false,
      error: msg,
      report_file: null,
      video_file: null
    });
    process.exitCode = 1;
  }
}

main().catch((e) => {
  const workDir = process.env.MIDSCENE_WORK_DIR ?? ".";
  const msg = e instanceof Error ? e.message : String(e);
  writeResultFile(workDir, {
    ok: false,
    error: msg,
    report_file: null,
    video_file: null
  });
  process.exit(1);
});
