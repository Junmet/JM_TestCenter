<template>
  <div class="page-view ui-auto ui-auto--fill">
    <div class="ui-auto__top">
      <el-alert
        v-if="health && !health.ok"
        type="warning"
        show-icon
        :closable="false"
        class="health-alert"
        :title="health.message"
      />
      <el-alert
        v-if="health && health.ok && form.runner === 'playwright' && !health.playwright_ok"
        type="warning"
        show-icon
        :closable="false"
        class="health-alert"
        title="纯 Playwright 运行器未就绪"
        :description="health.playwright_message || '请在 backend/playwright-runner 目录执行 npm install 与 npx playwright install chromium'"
      />
    </div>

    <div class="ui-auto__split">
      <section class="panel panel--form">
        <div class="flow-header">
          <el-text tag="h2" class="panel-title">模型与指令</el-text>
          <div class="flow-header__actions">
            <el-button @click="saveFlowPreset">保存流程</el-button>
            <el-dropdown trigger="click" @command="onLoadFlowCommand">
              <el-button type="primary">
                载入流程
                <el-icon class="dropdown-caret"><ArrowDown /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item v-for="p in flowPresets" :key="p.id" :command="p.id">{{ p.name }}</el-dropdown-item>
                  <el-dropdown-item v-if="flowPresets.length === 0" disabled>暂无已保存流程</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
            <el-button @click="clearFlowForm">清空表单</el-button>
          </div>
        </div>
        <el-alert
          v-if="submitApiError"
          type="error"
          :closable="false"
          show-icon
          class="form-api-error"
          :title="submitApiError"
        />
        <el-form :model="form" label-width="120px" class="form-grid form-grid--responsive">
        <el-form-item label="执行引擎" required>
          <div class="form-item-with-tip form-item-with-tip--inline">
            <el-radio-group v-model="form.runner" class="form-item-with-tip__main">
              <el-radio value="midscene">Midscene（自然语言 / 视觉模型）</el-radio>
              <el-radio value="playwright">纯 Playwright（selector，无模型，速度快）</el-radio>
            </el-radio-group>
            
          </div>
          <InlineHelpTip>
            选 <strong>纯 Playwright</strong> 时无需填写 API Key，步骤为 JSON（<code>locator</code> 定位 DOM），适合稳定回归。
          </InlineHelpTip>
        </el-form-item>
        <template v-if="form.runner === 'midscene'">
        <el-form-item label="模型服务" required>
          <div class="form-item-with-tip form-item-with-tip--inline">
            <div class="form-item-with-tip__main form-item-with-tip__main--select">
            <el-select v-model="provider" class="select-full" placeholder="请选择服务商">
              <el-option
                v-for="opt in providerOptions"
                :key="opt.value"
                :label="opt.label"
                :value="opt.value"
              />
            </el-select>
            </div>
          </div>
          <InlineHelpTip>
            仅支持<strong>通义千问</strong>与<strong>豆包</strong>；接口地址为
            <code class="mono-tip">{{ form.model.base_url }}</code>
          </InlineHelpTip>
        </el-form-item>
        <el-form-item label="API Key" required>
          <el-input
            v-model="form.model.api_key"
            type="password"
            show-password
            clearable
            placeholder="请输入 API Key（仅用于本次任务，不落库）"
            autocomplete="off"
          />
        </el-form-item>
        <el-form-item label="模型名称" required>
          <div class="form-item-with-tip form-item-with-tip--inline">
            <div class="form-item-with-tip__main form-item-with-tip__main--select">
            <el-select v-model="form.model.name" class="select-full" placeholder="请选择模型">
              <el-option v-for="m in modelNameOptions" :key="m" :label="m" :value="m" />
            </el-select>
            </div>
          </div>
          <InlineHelpTip>
            选项与所选「模型服务」对应；若控制台模型 ID 与列表不一致，请同步到控制台为准。
          </InlineHelpTip>
        </el-form-item>
        <el-form-item label="VL 模式" required>
          <div class="form-item-with-tip form-item-with-tip--inline">
            <div class="form-item-with-tip__main form-item-with-tip__main--select">
            <el-select v-model="form.model.family" class="select-full" placeholder="请选择 VL 模式">
              <el-option v-for="f in familyOptions" :key="f" :label="f" :value="f" />
            </el-select>
            </div>
          </div>
          <InlineHelpTip>
            与所选「模型服务」对应；对应环境变量 MIDSCENE_VL_MODE，须为 Midscene 支持的取值之一。
          </InlineHelpTip>
        </el-form-item>
        </template>
        <el-form-item label="起始 URL" required>
          <div class="start-url-with-tip">
            <el-input
              v-model="form.start_url"
              placeholder="https://www.baidu.com"
              clearable
              class="start-url-input"
            />
            <InlineHelpTip v-if="hintPlaywrightStartUrl">{{ hintPlaywrightStartUrl }}</InlineHelpTip>
          </div>
        </el-form-item>
        <el-form-item v-if="form.runner === 'midscene'" label="任务类型" required>
          <div class="form-item-with-tip form-item-with-tip--inline">
            <el-radio-group v-model="form.task_mode" class="form-item-with-tip__main">
              <el-radio value="classic">简单自然语言（多行 / 整块）</el-radio>
              <el-radio value="pipeline">步骤编排（JSON：AI + 确定性 Playwright）</el-radio>
            </el-radio-group>
          </div>
          <InlineHelpTip>
            复杂流程（后退、多标签、断言、截图、打日志）请用<strong>步骤编排</strong>；仅连续点击/输入可用简单模式。
          </InlineHelpTip>
        </el-form-item>
        <template v-if="form.task_mode === 'classic' && form.runner === 'midscene'">
          <el-form-item label="指令模式" required>
            <div class="form-item-with-tip form-item-with-tip--inline">
              <el-radio-group v-model="form.instruction_mode" class="form-item-with-tip__main">
                <el-radio value="multi_line">多行：一行一步，按顺序执行多条 aiAction</el-radio>
                <el-radio value="single_block">整块：整段文字作为一次 aiAction</el-radio>
              </el-radio-group>
            </div>
            <InlineHelpTip>
              与下方「自然语言」配合使用：换模式后，输入框里的<strong>灰色提示文字</strong>会跟着变。
            </InlineHelpTip>
          </el-form-item>
          <el-form-item label="自然语言" required>
            <div class="textarea-with-tip">
              <el-input
                v-model="form.instructions"
                type="textarea"
                :rows="10"
                :placeholder="instructionsPlaceholder"
                class="instructions-textarea textarea-with-tip__input"
              />
              <InlineHelpTip class="textarea-with-tip__icon">
                <template v-if="form.instruction_mode === 'multi_line'">
                  <strong>多行模式：</strong>每行一条指令，对应多次「看到页面 → 决策 → 操作」。适合步骤固定、容易拆成列表的场景。
                </template>
                <template v-else>
                  <strong>整块模式：</strong>整段描述一个连贯任务，模型会按语义拆成内部步骤。适合一步里包含多句说明、不便强行分行时。
                </template>
              </InlineHelpTip>
            </div>
          </el-form-item>
        </template>
        <template v-else>
          <el-form-item label="步骤 JSON" required>
            <div class="pipeline-json-editor-wrap">
              <PipelineJsonEditor v-model="form.pipeline_steps_json" />
              <div class="pipeline-toolbar pipeline-toolbar--with-tip">
                <el-button @click="formatPipelineJson">格式化 JSON</el-button>
                <el-button v-if="form.runner === 'midscene'" @click="loadPipelineExample">插入 Midscene 示例</el-button>
                <template v-else>
                  <el-button type="primary" @click="loadPlaywrightExample">简短模板（百度搜+截图）</el-button>
                  <el-button type="success" @click="loadPlaywrightComplexExample">复杂规范示例（多标签·滚动·断言）</el-button>
                </template>
                <InlineHelpTip v-if="form.runner === 'midscene'" :max-width="480">
                  数组中每一步为对象，<code>type</code> 为
                  aiAction / aiWaitFor / settle / wait / goto / goBack / switchToLatestTab / switchToTabIndex /
                  closeOtherTabs / closeCurrentTab / expectTabCount / logPageInfo / scrollToBottom / screenshot /
                  assertTitleContains / assertUrlContains。详见 <code>backend/midscene-runner/README.md</code>。
                  <strong>aiAction 提示：</strong>不要用「标题必须含某某」这类强条件——真实页面文案会变，易报
                  <code>AI model failed to locate</code>；改用「第一条非广告结果」「可见的搜索框」等描述。
                </InlineHelpTip>
                <InlineHelpTip v-else :max-width="480">
                  <strong>规范文档（v1.0）：</strong>
                  <code>backend/playwright-runner/PIPELINE_SPEC.md</code>（完整 <code>type</code>、定位器：Role/Text/TestId/Placeholder/Label/Alt/Title、CSS、XPath、<code>first</code>/<code>nth</code>/<code>frame</code>）。
                  按钮「复杂规范示例」对应多标签、滚动、<code>verifyText</code> 等组合流程。
                  <br />
                  <strong>JSON 形状：</strong>可为<strong>步骤数组</strong>，或与 <code>pipeline.schema.json</code> 一致的<strong>对象</strong>（含
                  <code>startUrl</code>、<code>headless</code>、<code>recordVideo</code>、<code>executionSteps</code>）；对象时步骤来自
                  <code>executionSteps</code>，<code>startUrl</code> 可与上方「起始 URL」二选一填写。
                  <br />
                  速查：<code>waitForSelector</code> 默认 <code>attached</code>；多匹配加 <code>first</code> 或 <code>nth</code>；百度推荐
                  <code>fill</code> + <code>press Enter</code>。详见 <code>backend/playwright-runner/PIPELINE_SPEC.md</code>。
                </InlineHelpTip>
                <InlineHelpTip v-if="hintPlaywrightPipeline">{{ hintPlaywrightPipeline }}</InlineHelpTip>
                <InlineHelpTip v-if="hintMidscenePipeline">{{ hintMidscenePipeline }}</InlineHelpTip>
              </div>
            </div>
          </el-form-item>
        </template>
        <el-form-item label="选项">
          <el-checkbox v-model="form.headless">无头模式（服务器推荐）</el-checkbox>
          <el-checkbox v-model="form.record_video">
            录制视频（Playwright，一般为 webm；成功后在抽屉中播放）
          </el-checkbox>
        </el-form-item>
        <el-form-item label="执行策略">
          <div class="form-item-with-tip form-item-with-tip--strategy">
            <el-checkbox v-model="form.stable_wait_after_step" class="strategy-checkbox">
              步骤间稳定等待：每步后先等待 DOM 就绪（domcontentloaded），再睡眠下面的「步骤间隔」（慢页或易抢步再勾选）
            </el-checkbox>
            <span class="strategy-inline-tip">
              <InlineHelpTip>
                默认<strong>关闭</strong>以缩短墙钟时间。默认也<strong>不</strong>等待「网络空闲」（SPA 易卡）；仍抢步可加大间隔或勾选本项；服务端可在
                <code>.env</code> 设 <code>MIDSCENE_SETTLE_NETWORK_IDLE=true</code> 以额外尝试 networkidle。
                单次 <code>aiAction</code> 仍受视觉模型耗时影响（数秒～数十秒属正常）。
              </InlineHelpTip>
            </span>
          </div>
        </el-form-item>
        <el-form-item v-if="form.runner === 'playwright'" label="slowMo(ms)">
          <div class="form-item-with-tip form-item-with-tip--inline form-item-with-tip--align-center">
            <el-input-number
              v-model="form.slow_mo_ms"
              :min="0"
              :max="2000"
              :step="50"
              controls-position="right"
              class="step-gap-input"
            />
            <InlineHelpTip>
              仅纯 Playwright：<strong>0=关闭</strong>，<strong>最大 2000ms</strong>。每个操作之间插入延迟，录屏里更容易看出先后；<strong>仍不会显示鼠标指针</strong>。调试可设
              <strong>200～500</strong>。
            </InlineHelpTip>
          </div>
        </el-form-item>
        <el-form-item label="步骤间隔(ms)">
          <div class="form-item-with-tip form-item-with-tip--inline form-item-with-tip--align-center">
            <el-input-number
              v-model="form.step_gap_ms"
              :min="0"
              :max="120000"
              :step="200"
              controls-position="right"
              class="step-gap-input"
            />
            <InlineHelpTip>
              <template v-if="form.task_mode === 'pipeline'">
                步骤编排：作为各 <code>aiAction</code> / <code>goto</code> / <code>goBack</code> 等后的默认间隔（步骤内可用
                <code>settle</code> 单独覆盖）。默认 <strong>400</strong>；易抢步可 <strong>800～2500</strong>。
              </template>
              <template v-else-if="form.instruction_mode === 'multi_line'">
                多行模式：在「稳定等待」之后，每两行指令之间再睡眠的毫秒数（<strong>无脚本内置下限</strong>）。默认
                <strong>400</strong>；慢页或仍抢步可 <strong>800～2500</strong> 或更高。
              </template>
              <template v-else>
                整块模式：仅影响打开起始 URL 后、执行整段 <code>aiAction</code> 前的首屏等待。
              </template>
            </InlineHelpTip>
          </div>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="submitting" :disabled="!canSubmit" @click="onSubmit">
            开始执行
          </el-button>
        </el-form-item>
        </el-form>
      </section>

      <section class="panel panel--runs history-panel">
        <div class="history-header">
          <el-text tag="h2" class="panel-title">运行记录</el-text>
          <el-button :loading="runsLoading" @click="loadRuns">刷新列表</el-button>
        </div>
        <div v-if="runsLoaded && runsTotal === 0" class="history-empty">暂无运行记录</div>
        <div v-else class="list-table-wrap">
          <div class="list-table-scroll">
            <el-table
              :data="runs"
              stripe
              size="small"
              class="list-table list-table--first-left runs-list"
              table-layout="fixed"
              :row-class-name="runRowClassName"
              @row-click="onRunRowClick"
            >
              <el-table-column label="时间" show-overflow-tooltip>
                <template #default="{ row }">{{ formatRunTime(row.created_at) }}</template>
              </el-table-column>
              <el-table-column label="状态">
                <template #default="{ row }">
                  <el-tag :type="runStatusTagType(row.status)" effect="light">{{ formatRunStatus(row.status) }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="start_url" label="起始 URL" show-overflow-tooltip />
              <el-table-column label="操作">
                <template #default="{ row }">
                  <el-button link type="primary" @click.stop="openRunDetail(row)">查看</el-button>
                  <el-button link type="success" @click.stop="applyRunToForm(row)">载入表单</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
          <div v-if="runsTotal > 0" class="table-pagination">
            <el-pagination
              background
              layout="total, sizes, prev, pager, next, jumper"
              :total="runsTotal"
              :page-size="runsPageSize"
              :current-page="runsPage"
              :page-sizes="[5, 10, 20, 30, 50]"
              @current-change="onRunsPageChange"
              @size-change="onRunsPageSizeChange"
            />
          </div>
        </div>
      </section>
    </div>

    <el-drawer
      v-model="drawerVisible"
      :title="drawerTitle"
      direction="rtl"
      :size="drawerSize"
      append-to-body
      class="ui-auto-detail-drawer"
      @closed="onDrawerClosed"
    >
      <div v-if="selected" class="drawer-inner">
        <div class="drawer-tip-line">
        </div>
        <el-descriptions :column="1" border size="small">
          <el-descriptions-item label="状态">{{ selected.status }}</el-descriptions-item>
          <el-descriptions-item label="是否录制视频">{{
            selected.record_video ? "是（成功时下方应出现播放器或提示）" : "否"
          }}</el-descriptions-item>
          <el-descriptions-item label="起始 URL（自动化打开的页面）">{{ selected.start_url }}</el-descriptions-item>
          <el-descriptions-item label="指令内容">
            <div class="instruction-view-row">
              <el-button type="primary" size="small" @click="instructionDialogVisible = true">查看</el-button>
              <el-text v-if="instructionCharCount > 0" class="instruction-view-meta" type="info" size="small"
                >{{ instructionCharCount }} 字符</el-text
              >
            </div>
          </el-descriptions-item>
          <el-descriptions-item v-if="!isPlaywrightRun" label="模型 API（不可在浏览器当网页打开）">{{
            selected.model_base_url
          }}</el-descriptions-item>
          <el-descriptions-item v-if="!isPlaywrightRun" label="模型 / VL"
            >{{ selected.model_name }} / {{ selected.model_family }}</el-descriptions-item
          >
          <el-descriptions-item v-if="isPlaywrightRun" label="执行引擎">纯 Playwright（无模型调用）</el-descriptions-item>
          <el-descriptions-item label="错误" v-if="selected.error_message">
            <span class="error-inline">{{ selected.error_message }}</span>
          </el-descriptions-item>
         
        </el-descriptions>
         <InlineHelpTip>
            <template v-if="isPlaywrightRun">
              <strong>浏览器实际打开的是「起始 URL」</strong>。下方为 <strong>Playwright</strong> 执行报告（步骤日志 / HTML），可与录屏对照。
            </template>
            <template v-else>
              <strong>浏览器里实际打开的是「起始 URL」</strong>；「模型 API」仅供程序调视觉模型。
              成功时请看 <strong>Midscene</strong> 报告与录屏确认操作是否执行。
            </template>
          </InlineHelpTip>
        <div v-if="selected.status === 'success'" class="preview-wrap">
          <div v-if="selected.report_file" class="preview-block" :class="isPlaywrightRun ? 'preview-block--pw-report' : 'preview-block--midscene-report'">
            <div class="report-shell">
              <div class="report-shell__bar" :class="isPlaywrightRun ? 'report-shell__bar--pw' : 'report-shell__bar--ms'">
                <div class="report-shell__titles">
                  <h3 class="report-shell__title">{{ reportSectionTitle }}</h3>
                  <p class="report-shell__sub">{{ reportSectionSubtitle }}</p>
                </div>
                <el-button
                  v-if="reportBlobUrl"
                  type="primary"
                  size="small"
                  class="report-shell__action"
                  @click="reportFullscreenOpen = true"
                >
                  全屏预览
                </el-button>
              </div>
              <div class="report-shell__frame-wrap">
                <iframe v-if="reportBlobUrl" class="report-frame" title="report" :src="reportBlobUrl" />
                <p v-else class="muted report-shell__loading">加载报告中…</p>
              </div>
            </div>
          </div>
          <div v-if="selected.record_video" class="preview-block video-block">
            <div class="preview-block-head">
              <h3 class="sub-title">录屏（Playwright）</h3>
              <el-button
                v-if="videoBlobUrl"
                type="primary"
                link
                class="preview-zoom-btn"
                @click="enterVideoFullscreen"
              >
                全屏播放
              </el-button>
            </div>
            <video
              v-if="videoBlobUrl"
              ref="videoElRef"
              class="video-el"
              controls
              playsinline
              preload="metadata"
              :src="videoBlobUrl"
            />
            <p v-else-if="videoLoadError" class="error-text">{{ videoLoadError }}</p>
            <p v-else-if="selected.video_file && !videoBlobUrl && !videoLoadError" class="muted">加载视频中…</p>
            <el-alert
              v-else
              type="warning"
              show-icon
              :closable="false"
              title="未生成录屏文件"
              description="本次任务已勾选「录制视频」，但服务端未在运行目录下找到 .webm。请确认 backend/midscene-runner 与 Playwright 版本正常，或到服务器 backend/data/midscene_runs/该任务 id/videos/ 目录手动查看。"
            />
          </div>
          <div v-else-if="!selected.record_video" class="preview-block muted-block">
            <p class="muted">
              本次未勾选「录制视频」。若需要看视频确认操作，请重新执行任务并勾选「录制视频」。
            </p>
          </div>
        </div>
        <p v-else-if="selected.status === 'failed'" class="failed-hint muted">
          任务未成功，无报告/录屏。请根据上方「错误」排查；修复后重新执行。
        </p>
      </div>
    </el-drawer>

    <el-dialog
      v-model="reportFullscreenOpen"
      :title="reportFullscreenTitle"
      fullscreen
      append-to-body
      destroy-on-close
      class="report-fullscreen-dialog"
    >
      <iframe
        v-if="reportBlobUrl"
        class="report-frame report-frame--fullscreen"
        title="report-fullscreen"
        :src="reportBlobUrl"
      />
    </el-dialog>

    <el-dialog
      v-model="instructionDialogVisible"
      :title="instructionDialogTitle"
      width="min(920px, 94vw)"
      append-to-body
      destroy-on-close
      class="instruction-json-dialog"
    >
      <div class="instruction-json-toolbar">
        <el-button type="primary" @click="copyInstructionBody">{{ copyInstructionButtonLabel }}</el-button>
      </div>
      <div class="instruction-json-body">
        <pre ref="instructionPreRef" class="instruction-json-pre">{{ instructionDialogBody }}</pre>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { ArrowDown } from "@element-plus/icons-vue";
import JSON5 from "json5";
import PipelineJsonEditor from "../components/PipelineJsonEditor.vue";
import InlineHelpTip from "../components/InlineHelpTip.vue";
import { http } from "../api/http";
import {
  createMidsceneRunApi,
  getMidsceneHealthApi,
  getMidsceneRunApi,
  listMidsceneRunsApi,
  reportUrl,
  videoUrl,
  type MidsceneRun
} from "../api/uiAutomation";

/** 仅支持通义千问 / 豆包（火山方舟），选项与 VL 模式一一对应 */
const PROVIDER_META = {
  qwen: {
    label: "通义千问（阿里云 DashScope）",
    base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1",
    models: ["qwen-vl-max", "qwen-vl-plus", "qwen2.5-vl-72b-instruct", "qwen3-vl-plus", "qwen-vl-ocr-latest"],
    families: ["qwen3-vl", "qwen-vl"]
  },
  doubao: {
    label: "豆包（火山方舟 Ark）",
    base_url: "https://ark.cn-beijing.volces.com/api/v3",
    models: ["doubao-1.5-vision-pro-32k", "doubao-1.5-vision-lite-32k", "doubao-seed-1.6-vision"],
    families: ["doubao-vision", "vlm-ui-tars-doubao", "vlm-ui-tars-doubao-1.5"]
  }
} as const;

type ProviderKey = keyof typeof PROVIDER_META;

/** 与 backend `step_gap_ms` 默认、midscene-runner `DEFAULT_STEP_GAP_MS` 一致 */
const DEFAULT_STEP_GAP_MS = 400;

const providerOptions = [
  { value: "qwen" as const, label: PROVIDER_META.qwen.label },
  { value: "doubao" as const, label: PROVIDER_META.doubao.label }
];

/** 步骤编排示例：可改为你的业务；复杂场景用确定性步骤减少「模型误判」 */
/** 示例：避免要求「标题必须含某固定文案」——百度搜索结果会变，易触发 AI model failed to locate */
/** 纯 Playwright：百度搜索示例（#kw / #su 为百度首页常见选择器） */
const PIPELINE_PLAYWRIGHT_EXAMPLE = `[
  {"type":"waitForSelector","locator":{"css":"#kw"},"timeoutMs":20000,"state":"attached"},
  {"type":"fill","locator":{"css":"#kw"},"value":"Midscene 自动化测试","force":true},
  {"type":"press","locator":{"css":"#kw"},"key":"Enter","force":true},
  {"type":"waitForSelector","locator":{"css":"#content_left"},"timeoutMs":25000,"state":"attached"},
  {"type":"screenshot","filename":"baidu-serp.png","fullPage":false}
]`;

/** 规范见 playwright-runner/PIPELINE_SPEC.md；回到 SERP 后二次搜索用 goto 直达结果页（SERP 上 #kw 常 hidden，fill+Enter 易不提交） */
const PIPELINE_PLAYWRIGHT_COMPLEX_EXAMPLE = `[
  {"type":"waitForSelector","locator":{"css":"#kw"},"timeoutMs":20000,"state":"attached"},
  {"type":"fill","locator":{"css":"#kw"},"value":"Midscene 自动化测试","force":true},
  {"type":"press","locator":{"css":"#kw"},"key":"Enter","force":true},
  {"type":"waitForSelector","locator":{"css":"#content_left"},"timeoutMs":25000,"state":"attached"},
  {"type":"click","locator":{"css":".result.c-container h3 a","first":true},"force":true},
  {"type":"switchToLatestTab"},
  {"type":"waitForSelector","locator":{"css":"body"},"timeoutMs":15000,"state":"attached"},
  {"type":"assertUrlContains","text":"http"},
  {"type":"scroll","to":"bottom"},
  {"type":"wait","ms":500},
  {"type":"screenshot","filename":"after-first-result.png","fullPage":true},
  {"type":"closeCurrentTab"},
  {"type":"switchToTabIndex","index":0},
  {"type":"goto","url":"https://www.baidu.com/s?wd=Selenium+Playwright+%E5%8C%BA%E5%88%AB","timeoutMs":90000},
  {"type":"waitForSelector","locator":{"css":"#content_left"},"timeoutMs":25000,"state":"attached"},
  {"type":"assertUrlContains","text":"Selenium"},
  {"type":"assertTextContains","text":"Playwright"},
  {"type":"closeOtherTabs"},
  {"type":"logPageInfo"},
  {"type":"expectTabCount","count":1}
]`;

const PIPELINE_EXAMPLE_JSON = `[
  {"type":"aiAction","text":"在百度搜索框中输入「Midscene 自动化测试」并点击「百度一下」"},
  {"type":"settle","gapMs":5000},
  {"type":"aiAction","text":"在搜索结果列表中，点击第一条非「广告」标识的网页标题链接（打开新页面或新标签）"},
  {"type":"switchToLatestTab"},
  {"type":"settle","gapMs":2000},
  {"type":"aiAction","text":"等待页面加载完成后，将页面滚动到最底部"},
  {"type":"screenshot","filename":"page-bottom.png","fullPage":false},
  {"type":"goBack"},
  {"type":"settle","gapMs":400},
  {"type":"aiAction","text":"在搜索框中输入「Selenium Playwright 区别」并点击「百度一下」"},
  {"type":"settle","gapMs":5000},
  {"type":"aiAction","text":"在搜索结果页向下滚动，使第二条搜索结果的标题区域完整可见"},
  {"type":"logPageInfo"},
  {"type":"closeCurrentTab"},
  {"type":"expectTabCount","count":1}
]`;

const provider = ref<ProviderKey>("qwen");

function loadPipelineExample() {
  form.pipeline_steps_json = PIPELINE_EXAMPLE_JSON;
}

function loadPlaywrightExample() {
  form.pipeline_steps_json = PIPELINE_PLAYWRIGHT_EXAMPLE;
}

function loadPlaywrightComplexExample() {
  form.pipeline_steps_json = PIPELINE_PLAYWRIGHT_COMPLEX_EXAMPLE;
}

/** 将步骤 JSON 格式化为标准缩进（先 JSON，失败则 JSON5） */
function formatPipelineJson() {
  const parsed = parseJsonLenient(form.pipeline_steps_json);
  if (parsed === null) {
    ElMessage.warning("当前内容无法解析为 JSON，无法格式化（支持 ``` 代码块、JSON5 注释与尾随逗号）");
    return;
  }
  form.pipeline_steps_json = JSON.stringify(parsed, null, 2);
  ElMessage.success("已格式化");
}

/** 去掉 BOM、零宽字符；支持从 Markdown ``` 代码块中粘贴 */
function normalizePlaywrightJsonInput(raw: string): string {
  let s = raw
    .replace(/^\uFEFF/, "")
    .replace(/[\u200B-\u200D\uFEFF]/g, "")
    .trim();
  if (s.startsWith("```")) {
    const firstNl = s.indexOf("\n");
    if (firstNl !== -1) {
      s = s.slice(firstNl + 1);
    }
    const closing = s.lastIndexOf("```");
    if (closing !== -1) {
      s = s.slice(0, closing);
    }
    s = s.trim();
  }
  return s;
}

/** 先标准 JSON，失败则用 JSON5（注释、尾随逗号等，常见于文档/手写） */
function parseJsonLenient(raw: string): unknown | null {
  const normalized = normalizePlaywrightJsonInput(raw);
  if (!normalized) return null;
  try {
    return JSON.parse(normalized);
  } catch {
    try {
      return JSON5.parse(normalized);
    } catch {
      return null;
    }
  }
}

/**
 * 与 playwright-runner `RunConfig` / `pipeline.schema.json` 对齐：
 * - 顶层「非空数组」= 仅步骤（起始 URL 用表单「起始 URL」）
 * - 顶层对象且含 `executionSteps` 数组 = 完整配置；`startUrl`/`start_url` 可与表单二选一
 */
function parsePlaywrightPipelineSteps(raw: string): {
  steps: Array<Record<string, unknown>>;
  startUrlFromConfig?: string;
} | null {
  const parsed = parseJsonLenient(raw);
  if (parsed === null) return null;
  if (Array.isArray(parsed) && parsed.length > 0) {
    return { steps: parsed as Array<Record<string, unknown>> };
  }
  if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
    const o = parsed as Record<string, unknown>;
    const steps = o.executionSteps ?? o.execution_steps ?? o.steps;
    if (Array.isArray(steps) && steps.length > 0) {
      const out: { steps: Array<Record<string, unknown>>; startUrlFromConfig?: string } = {
        steps: steps as Array<Record<string, unknown>>
      };
      const su = o.startUrl ?? o.start_url;
      if (typeof su === "string" && su.trim()) {
        out.startUrlFromConfig = su.trim();
      }
      return out;
    }
  }
  return null;
}

/** 用于按钮旁提示：为何无法提交 */
function parsePlaywrightPipelineFeedback(raw: string): { ok: true } | { ok: false; message: string } {
  const normalized = normalizePlaywrightJsonInput(raw);
  if (!normalized) return { ok: false, message: "步骤 JSON 为空" };
  const parsed = parseJsonLenient(raw);
  if (parsed === null) {
    return {
      ok: false,
      message: "JSON 无法解析（可粘贴 ``` 代码块；支持 JSON5 注释与尾随逗号）"
    };
  }
  if (Array.isArray(parsed)) {
    if (parsed.length === 0) return { ok: false, message: "步骤数组不能为空" };
    return { ok: true };
  }
  if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
    const o = parsed as Record<string, unknown>;
    const steps = o.executionSteps ?? o.execution_steps ?? o.steps;
    if (!Array.isArray(steps) || steps.length === 0) {
      return {
        ok: false,
        message: "对象中需包含非空的 executionSteps（或 execution_steps / steps）"
      };
    }
    return { ok: true };
  }
  return { ok: false, message: "顶层须为 JSON 数组或对象" };
}

function effectivePlaywrightStartUrl(): string {
  const t = form.start_url.trim();
  if (t) return t;
  const pip = parsePlaywrightPipelineSteps(form.pipeline_steps_json);
  return pip?.startUrlFromConfig ?? "";
}

type UiAutoForm = {
  runner: "midscene" | "playwright";
  model: {
    base_url: string;
    api_key: string;
    name: string;
    family: string;
  };
  start_url: string;
  instructions: string;
  instruction_mode: "multi_line" | "single_block";
  headless: boolean;
  record_video: boolean;
  /** 步间额外等待(ms)，与 runner 内 domcontentloaded + sleep 叠加 */
  step_gap_ms: number;
  /** 仅 playwright-runner：slowMo，0 关闭 */
  slow_mo_ms: number;
  stable_wait_after_step: boolean;
  task_mode: "classic" | "pipeline";
  pipeline_steps_json: string;
};

/** 必须在 computed / watch 之前声明，否则会出现「Cannot access 'form' before initialization」 */
const form = reactive<UiAutoForm>({
  runner: "midscene",
  model: {
    base_url: PROVIDER_META.qwen.base_url,
    api_key: "",
    name: PROVIDER_META.qwen.models[0],
    family: PROVIDER_META.qwen.families[0]
  },
  start_url: "",
  instructions: "",
  instruction_mode: "multi_line",
  headless: true,
  record_video: true,
  step_gap_ms: DEFAULT_STEP_GAP_MS,
  slow_mo_ms: 0,
  stable_wait_after_step: false,
  task_mode: "classic",
  pipeline_steps_json: PIPELINE_EXAMPLE_JSON
});

const modelNameOptions = computed(() => {
  const base = [...PROVIDER_META[provider.value].models] as string[];
  if (form.model.name && !base.includes(form.model.name)) {
    return [form.model.name, ...base];
  }
  return base;
});

const familyOptions = computed(() => {
  const base = [...PROVIDER_META[provider.value].families] as string[];
  if (form.model.family && !base.includes(form.model.family)) {
    return [form.model.family, ...base];
  }
  return base;
});

watch(
  () => form.runner,
  (r, prev) => {
    if (r === "playwright") {
      form.task_mode = "pipeline";
      if (prev === "midscene") {
        form.pipeline_steps_json = PIPELINE_PLAYWRIGHT_EXAMPLE;
      }
    } else if (r === "midscene" && prev === "playwright") {
      form.pipeline_steps_json = PIPELINE_EXAMPLE_JSON;
      form.task_mode = "classic";
    }
  }
);

watch(
  () => [
    form.runner,
    form.start_url,
    form.pipeline_steps_json,
    form.instructions,
    form.task_mode
  ],
  () => {
    submitApiError.value = "";
  }
);

watch(
  provider,
  (p) => {
    form.model.base_url = PROVIDER_META[p].base_url;
    const models = [...PROVIDER_META[p].models] as string[];
    const families = [...PROVIDER_META[p].families] as string[];
    if (!models.includes(form.model.name)) form.model.name = models[0] ?? "";
    if (!families.includes(form.model.family)) form.model.family = families[0] ?? "";
  },
  { immediate: true }
);

/** 自然语言输入框占位：随「指令模式」切换，避免用户不清楚怎么写 */
const instructionsPlaceholder = computed(() => {
  if (form.instruction_mode === "single_block") {
    return [
      "【整块模式】下面整段文字会作为「一次大任务」交给 Midscene 连续执行。",
      "",
      "请用一段话写清：要在哪个页面、先做什么、再做什么。例如：",
      "先找到页面上的搜索框，输入「Midscene」并搜索；在结果里点开第一条；在新页面里找到并点击「文档」入口。",
      "",
      "提示：写清按钮/链接的大致位置（如「顶部」「第一条结果」），识别成功率更高。"
    ].join("\n");
  }
  return [
    "【多行模式】每一行 = 一步操作，从上到下依次执行（适合：登录 → 搜索 → 点链接）。",
    "",
    "示例（请改成你自己的页面与操作）：",
    "在搜索框输入「Midscene」并点击「百度一下」",
    "在搜索结果中点击第一条标题",
    "等待新页面打开后，点击导航栏中的「某某」菜单",
    "",
    "提示：一步一行；尽量写「点哪个按钮、在哪个输入框输入什么」；不要用空行当作一步。"
  ].join("\n");
});

/** 保存的流程（不含 API Key），用于多次回归复用 */
type UiFlowPreset = {
  id: string;
  name: string;
  savedAt: string;
  runner?: "midscene" | "playwright";
  provider: ProviderKey;
  modelName: string;
  modelFamily: string;
  start_url: string;
  instructions: string;
  instruction_mode: "multi_line" | "single_block";
  headless: boolean;
  record_video: boolean;
  step_gap_ms?: number;
  stable_wait_after_step?: boolean;
  task_mode?: "classic" | "pipeline";
  pipeline_steps_json?: string;
};

const FLOW_PRESETS_KEY = "jmtestcenter_ui_automation_flow_presets_v1";

function flowPresetsFromStorage(): UiFlowPreset[] {
  try {
    const raw = localStorage.getItem(FLOW_PRESETS_KEY);
    if (!raw) return [];
    const arr = JSON.parse(raw) as unknown;
    if (!Array.isArray(arr)) return [];
    return arr.filter((x) => x && typeof x === "object" && "id" in x) as UiFlowPreset[];
  } catch {
    return [];
  }
}

function persistFlowPresets(list: UiFlowPreset[]) {
  localStorage.setItem(FLOW_PRESETS_KEY, JSON.stringify(list));
}

const flowPresets = ref<UiFlowPreset[]>([]);

function inferProviderFromBaseUrl(url: string): ProviderKey {
  const u = url.toLowerCase();
  if (u.includes("dashscope")) return "qwen";
  if (u.includes("volces") || u.includes("ark.cn-beijing")) return "doubao";
  return "qwen";
}

function formatRunTime(v: string) {
  if (!v) return "-";
  const d = new Date(v);
  if (Number.isNaN(d.getTime())) return v;
  return d.toLocaleString("zh-CN", { hour12: false });
}

function formatRunStatus(s: string) {
  const m: Record<string, string> = {
    pending: "排队中",
    running: "运行中",
    success: "成功",
    failed: "失败"
  };
  return m[s] ?? s;
}

function runStatusTagType(s: string): "success" | "danger" | "info" | "warning" {
  if (s === "success") return "success";
  if (s === "failed") return "danger";
  if (s === "running") return "warning";
  return "info";
}

function saveFlowPreset() {
  ElMessageBox.prompt("为当前配置命名，便于下次回归一键载入（不会保存 API Key）", "保存流程", {
    confirmButtonText: "保存",
    cancelButtonText: "取消",
    inputPattern: /^[\s\S]{1,80}$/,
    inputErrorMessage: "名称 1～80 字符"
  })
    .then(({ value }) => {
      const name = value.trim();
      if (!name) {
        ElMessage.warning("名称不能为空");
        return;
      }
      const p: UiFlowPreset = {
        id: crypto.randomUUID(),
        name,
        savedAt: new Date().toISOString(),
        runner: form.runner,
        provider: provider.value,
        modelName: form.model.name,
        modelFamily: form.model.family,
        start_url: form.start_url.trim(),
        instructions: form.instructions,
        instruction_mode: form.instruction_mode,
        headless: form.headless,
        record_video: form.record_video,
        step_gap_ms: form.step_gap_ms,
        stable_wait_after_step: form.stable_wait_after_step,
        task_mode: form.task_mode,
        pipeline_steps_json: form.pipeline_steps_json
      };
      flowPresets.value = [p, ...flowPresets.value.filter((x) => x.name !== name)];
      persistFlowPresets(flowPresets.value);
      ElMessage.success("已保存流程");
    })
    .catch(() => {});
}

function applyFlowPreset(p: UiFlowPreset) {
  form.runner = p.runner ?? "midscene";
  provider.value = p.provider;
  form.model.api_key = "";
  form.model.name = p.modelName;
  form.model.family = p.modelFamily;
  form.start_url = p.start_url;
  form.instructions = p.instructions;
  form.instruction_mode = p.instruction_mode;
  form.headless = p.headless;
  form.record_video = p.record_video;
  form.step_gap_ms = typeof p.step_gap_ms === "number" ? p.step_gap_ms : DEFAULT_STEP_GAP_MS;
  form.stable_wait_after_step =
    typeof p.stable_wait_after_step === "boolean" ? p.stable_wait_after_step : false;
  form.task_mode = p.task_mode ?? "classic";
  form.pipeline_steps_json = p.pipeline_steps_json ?? PIPELINE_EXAMPLE_JSON;
  form.model.base_url = PROVIDER_META[p.provider].base_url;
}

function onLoadFlowCommand(id: string) {
  const p = flowPresets.value.find((x) => x.id === id);
  if (!p) {
    ElMessage.warning("未找到该流程");
    return;
  }
  applyFlowPreset(p);
  ElMessage.success(`已载入「${p.name}」`);
}

function clearFlowForm() {
  form.runner = "midscene";
  provider.value = "qwen";
  form.model.api_key = "";
  form.model.name = PROVIDER_META.qwen.models[0];
  form.model.family = PROVIDER_META.qwen.families[0];
  form.model.base_url = PROVIDER_META.qwen.base_url;
  form.start_url = "";
  form.instructions = "";
  form.instruction_mode = "multi_line";
  form.headless = true;
  form.record_video = true;
  form.step_gap_ms = DEFAULT_STEP_GAP_MS;
  form.stable_wait_after_step = false;
  form.task_mode = "classic";
  form.pipeline_steps_json = PIPELINE_EXAMPLE_JSON;
}

function applyRunToForm(row: MidsceneRun) {
  form.runner = row.model_name === "playwright" ? "playwright" : "midscene";
  const p = inferProviderFromBaseUrl(row.model_base_url);
  provider.value = p;
  form.model.api_key = "";
  form.model.base_url = row.model_base_url;
  form.model.name = row.model_name;
  form.model.family = row.model_family;
  form.start_url = row.start_url;
  form.instructions = row.instructions;
  form.instruction_mode = (row.instruction_mode === "single_block" ? "single_block" : "multi_line") as
    | "multi_line"
    | "single_block";
  form.headless = row.headless;
  form.record_video = row.record_video;
  form.step_gap_ms = DEFAULT_STEP_GAP_MS;
  form.stable_wait_after_step = false;
  ElMessage.success(
    "已载入该次运行的配置（请重新填写 API Key；步骤间隔使用默认 " + DEFAULT_STEP_GAP_MS + "ms，因运行记录未保存该字段）"
  );
}

const health = ref<Awaited<ReturnType<typeof getMidsceneHealthApi>> | null>(null);
const runs = ref<MidsceneRun[]>([]);
const runsLoading = ref(false);
const runsLoaded = ref(false);
const runsPage = ref(1);
const runsPageSize = ref(10);
const runsTotal = ref(0);
const selected = ref<MidsceneRun | null>(null);
const submitting = ref(false);
/** 仅接口/提交失败（与表单项校验分离，展示在表单顶部） */
const submitApiError = ref("");

const reportBlobUrl = ref<string | null>(null);
const videoBlobUrl = ref<string | null>(null);
const videoLoadError = ref<string | null>(null);
/** 报告全屏预览对话框 */
const reportFullscreenOpen = ref(false);
const videoElRef = ref<HTMLVideoElement | null>(null);

function enterVideoFullscreen() {
  const el = videoElRef.value;
  if (!el) return;
  const anyEl = el as HTMLVideoElement & { webkitRequestFullscreen?: () => void };
  if (typeof el.requestFullscreen === "function") {
    void el.requestFullscreen();
  } else if (typeof anyEl.webkitRequestFullscreen === "function") {
    anyEl.webkitRequestFullscreen();
  }
}

const drawerVisible = ref(false);
/** 抽屉宽度：窄屏全宽，桌面为像素宽度（随窗口变化） */
const drawerSize = ref<number | string>("90%");

const drawerTitle = computed(() => {
  if (!selected.value) return "运行详情";
  const id = selected.value.id;
  return `运行详情 · ${id.slice(0, 8)}…`;
});

const isPlaywrightRun = computed(() => selected.value?.model_name === "playwright");

/** 运行详情：指令弹窗 */
const instructionDialogVisible = ref(false);
const instructionPreRef = ref<HTMLPreElement | null>(null);

const instructionDialogTitle = computed(() =>
  isPlaywrightRun.value ? "步骤 JSON" : "指令内容"
);

const instructionDialogBody = computed(() => {
  const raw = selected.value?.instructions ?? "";
  if (!raw.trim()) return "（无）";
  try {
    return JSON.stringify(JSON.parse(raw), null, 2);
  } catch {
    return raw;
  }
});

const instructionCharCount = computed(() => (selected.value?.instructions ?? "").trim().length);

const copyInstructionButtonLabel = computed(() => {
  const raw = (selected.value?.instructions ?? "").trim();
  if (!raw) return "复制";
  try {
    JSON.parse(raw);
    return "复制 JSON";
  } catch {
    return "复制全文";
  }
});

async function copyInstructionBody() {
  const text = instructionDialogBody.value;
  if (text === "（无）" || !text.trim()) {
    ElMessage.warning("无内容可复制");
    return;
  }
  try {
    await navigator.clipboard.writeText(text);
    ElMessage.success("已复制到剪贴板");
  } catch {
    try {
      const el = instructionPreRef.value;
      if (el) {
        const range = document.createRange();
        range.selectNodeContents(el);
        const sel = window.getSelection();
        sel?.removeAllRanges();
        sel?.addRange(range);
        document.execCommand("copy");
        sel?.removeAllRanges();
        ElMessage.success("已复制到剪贴板");
        return;
      }
    } catch {
      /* ignore */
    }
    ElMessage.error("复制失败，请手动选择文本后复制");
  }
}

const reportSectionTitle = computed(() =>
  isPlaywrightRun.value ? "Playwright 执行报告" : "Midscene 执行报告"
);

const reportSectionSubtitle = computed(() =>
  isPlaywrightRun.value
    ? "步骤流水与 HTML 报告（playwright-runner）"
    : "步骤截图与页面回放（Midscene）"
);

const reportFullscreenTitle = computed(() =>
  isPlaywrightRun.value
    ? "Playwright 执行报告"
    : "Midscene 执行报告（步骤截图与回放）"
);

/** 表单项下方内联提示（与「开始执行」按钮分离） */
const hintPlaywrightStartUrl = computed(() => {
  if (form.runner !== "playwright") return "";
  if (health.value && !health.value.playwright_ok) return "";
  const fb = parsePlaywrightPipelineFeedback(form.pipeline_steps_json);
  if (fb.ok === false) return "";
  if (!effectivePlaywrightStartUrl()) return "请填写「起始 URL」，或在 JSON 顶层提供 startUrl / start_url";
  return "";
});

const hintPlaywrightPipeline = computed(() => {
  if (form.runner !== "playwright") return "";
  if (health.value && !health.value.playwright_ok) return "";
  const fb = parsePlaywrightPipelineFeedback(form.pipeline_steps_json);
  return fb.ok === false ? fb.message : "";
});

const hintMidscenePipeline = computed(() => {
  if (form.runner !== "midscene" || form.task_mode !== "pipeline") return "";
  try {
    const arr = JSON.parse(form.pipeline_steps_json) as unknown;
    if (!Array.isArray(arr) || arr.length === 0) return "步骤编排至少包含一条步骤";
    return "";
  } catch {
    return "步骤 JSON 格式错误，请检查括号与引号";
  }
});

function syncResponsiveLayout() {
  if (typeof window === "undefined") return;
  const w = window.innerWidth;
  if (w <= 640) {
    drawerSize.value = "100%";
  } else {
    drawerSize.value = Math.min(960, Math.floor(w * 0.92));
  }
}

function onDrawerClosed() {
  revokerBlobs();
}

let pollTimer: ReturnType<typeof setInterval> | null = null;

const canSubmit = computed(() => {
  if (form.runner === "playwright") {
    if (health.value && !health.value.playwright_ok) return false;
    if (!effectivePlaywrightStartUrl()) return false;
    return parsePlaywrightPipelineSteps(form.pipeline_steps_json) !== null;
  }
  if (!form.start_url.trim()) return false;
  const base =
    form.model.base_url.trim() &&
    form.model.api_key.trim() &&
    form.model.name.trim() &&
    form.model.family.trim();
  if (!base) return false;
  if (form.task_mode === "pipeline") {
    try {
      const arr = JSON.parse(form.pipeline_steps_json) as unknown;
      return Array.isArray(arr) && arr.length > 0;
    } catch {
      return false;
    }
  }
  return Boolean(form.instructions.trim());
});

async function loadHealth() {
  try {
    health.value = await getMidsceneHealthApi();
  } catch {
    health.value = null;
  }
}

async function loadRuns() {
  runsLoading.value = true;
  try {
    let data = await listMidsceneRunsApi(runsPage.value, runsPageSize.value);
    runs.value = Array.isArray(data.items) ? data.items : [];
    runsTotal.value = data.total ?? 0;
    runsPage.value = data.page ?? runsPage.value;
    runsPageSize.value = data.page_size ?? runsPageSize.value;
    const maxPage = Math.max(1, Math.ceil(runsTotal.value / runsPageSize.value) || 1);
    if (runs.value.length === 0 && runsTotal.value > 0 && runsPage.value > maxPage) {
      runsPage.value = maxPage;
      data = await listMidsceneRunsApi(runsPage.value, runsPageSize.value);
      runs.value = Array.isArray(data.items) ? data.items : [];
      runsTotal.value = data.total ?? 0;
      runsPage.value = data.page ?? runsPage.value;
      runsPageSize.value = data.page_size ?? runsPageSize.value;
    }
    runsLoaded.value = true;
  } catch (e: unknown) {
    ElMessage.error("刷新运行记录失败，请检查网络或重新登录后再试");
    console.error(e);
    // 不抛出让 Vue 整页崩溃 / 开发环境全屏错误遮罩
  } finally {
    runsLoading.value = false;
  }
}

async function onRunsPageChange(next: number) {
  runsPage.value = next;
  await loadRuns();
}

async function onRunsPageSizeChange(next: number) {
  runsPageSize.value = next;
  runsPage.value = 1;
  await loadRuns();
}

async function onSubmit() {
  submitApiError.value = "";
  submitting.value = true;
  try {
    let execution_steps: Array<Record<string, unknown>> | undefined;
    let instructions = form.instructions.trim();
    let start_url = form.start_url.trim();

    if (form.runner === "playwright") {
      const pip = parsePlaywrightPipelineSteps(form.pipeline_steps_json);
      if (!pip) {
        const fb = parsePlaywrightPipelineFeedback(form.pipeline_steps_json);
        ElMessage.warning(fb.ok === false ? fb.message : "步骤无法识别");
        submitting.value = false;
        return;
      }
      execution_steps = pip.steps;
      start_url = (form.start_url.trim() || pip.startUrlFromConfig || "").trim();
      if (!start_url) {
        ElMessage.warning("请填写起始 URL，或在 JSON 顶层提供 startUrl");
        submitting.value = false;
        return;
      }
      if (!instructions) instructions = "[Playwright]";
    } else if (form.task_mode === "pipeline") {
      let parsed: unknown;
      try {
        parsed = JSON.parse(form.pipeline_steps_json);
      } catch {
        ElMessage.warning("步骤 JSON 格式错误，请检查括号与引号");
        submitting.value = false;
        return;
      }
      if (!Array.isArray(parsed) || parsed.length === 0) {
        ElMessage.warning("步骤编排至少包含一条步骤");
        submitting.value = false;
        return;
      }
      execution_steps = parsed as Array<Record<string, unknown>>;
      if (!instructions) instructions = "[步骤编排]";
    }
    const run = await createMidsceneRunApi({
      runner: form.runner,
      model: { ...form.model },
      start_url,
      instructions,
      instruction_mode: form.instruction_mode,
      headless: form.headless,
      record_video: form.record_video,
      step_gap_ms: form.step_gap_ms,
      stable_wait_after_step: form.stable_wait_after_step,
      ...(form.runner === "playwright" && form.slow_mo_ms > 0 ? { slow_mo_ms: form.slow_mo_ms } : {}),
      ...(execution_steps ? { execution_steps } : {})
    });
    runsPage.value = 1;
    await loadRuns();
    selectRun(run);
    startPolling(run.id);
  } catch (e: unknown) {
    const msg = e && typeof e === "object" && "response" in e ? (e as { response?: { data?: { detail?: string } } }).response?.data?.detail : null;
    submitApiError.value = typeof msg === "string" ? msg : "提交失败";
  } finally {
    submitting.value = false;
  }
}

function runRowClassName({ row }: { row: MidsceneRun }) {
  return selected.value?.id === row.id ? "is-selected-run" : "";
}

function onRunRowClick(row: MidsceneRun) {
  void openRunDetail(row);
}

/**
 * 查看：打开右侧抽屉并拉取最新详情
 */
async function openRunDetail(row: MidsceneRun) {
  try {
    drawerVisible.value = true;
    selected.value = row;
    const fresh = await getMidsceneRunApi(row.id);
    selected.value = fresh;
    runs.value = runs.value.map((r) => (r.id === fresh.id ? fresh : r));
    revokerBlobs();
    if (fresh.status === "pending" || fresh.status === "running") {
      startPolling(fresh.id);
    } else if (fresh.status === "success") {
      await loadArtifacts(fresh.id);
    }
  } catch {
    ElMessage.error("加载详情失败");
    drawerVisible.value = false;
  }
}

function selectRun(row: MidsceneRun) {
  void openRunDetail(row);
}

function revokerBlobs() {
  reportFullscreenOpen.value = false;
  if (reportBlobUrl.value) URL.revokeObjectURL(reportBlobUrl.value);
  if (videoBlobUrl.value) URL.revokeObjectURL(videoBlobUrl.value);
  reportBlobUrl.value = null;
  videoBlobUrl.value = null;
  videoLoadError.value = null;
}

async function fetchBlob(path: string): Promise<Blob> {
  const resp = await http.get(path, { responseType: "blob" });
  return resp.data as Blob;
}

async function loadArtifacts(runId: string) {
  const run = await getMidsceneRunApi(runId);
  selected.value = run;
  revokerBlobs();
  if (run.report_file) {
    try {
      const b = await fetchBlob(reportUrl(runId));
      reportBlobUrl.value = URL.createObjectURL(b);
    } catch {
      reportBlobUrl.value = null;
    }
  }
  if (run.video_file) {
    try {
      const b = await fetchBlob(videoUrl(runId));
      if (!b || b.size === 0) {
        videoLoadError.value = "录屏文件为空";
      } else {
        videoBlobUrl.value = URL.createObjectURL(b);
      }
    } catch (e: unknown) {
      videoLoadError.value =
        e && typeof e === "object" && "message" in e
          ? String((e as { message?: string }).message)
          : "录屏下载失败（请检查登录是否过期或网络）";
    }
  }
}

function startPolling(runId: string) {
  stopPolling();
  pollTimer = setInterval(async () => {
    try {
      const run = await getMidsceneRunApi(runId);
      runs.value = runs.value.map((r) => (r.id === runId ? run : r));
      if (selected.value?.id === runId) {
        selected.value = run;
      }
      if (run.status === "success" || run.status === "failed") {
        stopPolling();
        if (run.status === "success" && selected.value?.id === runId) {
          await loadArtifacts(runId);
        }
      }
    } catch {
      stopPolling();
    }
  }, 3000);
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
}

watch(selected, (v) => {
  if (!v) revokerBlobs();
});

onMounted(async () => {
  flowPresets.value = flowPresetsFromStorage();
  syncResponsiveLayout();
  window.addEventListener("resize", syncResponsiveLayout);
  await loadHealth();
  await loadRuns();
});

onBeforeUnmount(() => {
  window.removeEventListener("resize", syncResponsiveLayout);
  stopPolling();
  revokerBlobs();
});
</script>

<style scoped>
/* 在 main-route 内用 flex 填满（flex-basis:0 + min-height:0 避免子项高度塌成 0） */
.page-view.ui-auto.ui-auto--fill {
  flex: 1 1 0%;
  align-self: stretch;
  width: 100%;
  max-width: 100%;
  margin: 0;
  padding: 24px clamp(12px, 3vw, 24px);
  box-sizing: border-box;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  gap: 16px;
}
.ui-auto__top {
  flex-shrink: 0;
}
.ui-auto__split {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: row;
  align-items: stretch;
  gap: 16px;
}
@media (max-width: 960px) {
  .ui-auto__split {
    flex-direction: column;
  }
}
.panel.panel--form {
  flex: 1 1 48%;
  min-width: 0;
  min-height: 0;
  margin-bottom: 0;
  display: flex;
  flex-direction: column;
  overflow: auto;
}
.panel.panel--runs {
  flex: 1 1 52%;
  min-width: 0;
  min-height: 0;
  margin-bottom: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.panel.panel--runs.history-panel {
  flex: 1 1 52%;
  min-height: 0;
}
.flow-header {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 10px;
}
.flow-header .panel-title {
  margin: 0;
}
.flow-header__actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}
.dropdown-caret {
  margin-left: 4px;
  font-size: 11px;
  opacity: 0.75;
}
.mono-tip {
  font-size: 12px;
  word-break: break-all;
}
.history-header {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}
.history-header .panel-title {
  margin: 0;
}
.history-empty {
  flex: 1;
  min-height: 120px;
  display: flex;
  align-items: center;
  color: #64748b;
  font-size: 13px;
}
.panel.panel--runs .list-table-wrap {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.panel.panel--runs .list-table-scroll {
  flex: 1;
  min-height: 0;
  /* 表格不设 height=100% 时由外层滚动，避免刷新数据后 el-table 重算布局导致整页空白 */
  overflow: auto;
}
.panel.panel--runs .table-pagination {
  flex-shrink: 0;
  padding: 10px 0 0;
  display: flex;
  justify-content: flex-end;
  flex-wrap: wrap;
  row-gap: 8px;
}
.health-alert {
  margin-bottom: 16px;
}
.form-api-error {
  margin-bottom: 12px;
  width: 100%;
  max-width: 100%;
}
.panel {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 20px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}
.panel-title {
  margin: 0 0 16px;
  font-size: 16px;
  color: #374151;
}
.form-grid {
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
}
@media (max-width: 640px) {
  .form-grid--responsive :deep(.el-form-item__label) {
    width: 96px !important;
  }
}
.panel--table {
  overflow-x: auto;
}
.runs-list :deep(tr.is-selected-run > td) {
  background-color: #eef2ff !important;
}
.runs-list :deep(tr.is-selected-run:hover > td) {
  background-color: #e0e7ff !important;
}
.drawer-inner {
  padding-bottom: 8px;
}
.ui-auto-detail-drawer :deep(.el-drawer__body) {
  padding-top: 8px;
}
.select-full {
  width: 100%;
}
.step-gap-input {
  width: 160px;
  flex-shrink: 0;
}
.pipeline-json-editor-wrap {
  width: 100%;
  max-width: 100%;
}
.pipeline-toolbar {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}
.pipeline-toolbar--with-tip {
  justify-content: flex-start;
}
.form-item-with-tip {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  flex-wrap: wrap;
  max-width: 100%;
  box-sizing: border-box;
  margin-right: 10px  ;
}
.form-item-with-tip--inline {
  display: inline-flex;
  width: auto;
  max-width: 100%;
}
.form-item-with-tip--align-center {
  align-items: center;
}
.form-item-with-tip--wrap {
  align-items: flex-start;
}
/** 执行策略：复选框与说明图标同一行（图标在行末、顶对齐，文案可换行） */
.form-item-with-tip--strategy {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
}
.strategy-checkbox {
  min-width: 0;
}
.strategy-checkbox :deep(.el-checkbox__label) {
  white-space: normal;
  line-height: 1.5;
}
.strategy-inline-tip {
  display: inline-flex;
  flex-shrink: 0;
  align-items: center;
  margin-top: 2px;
  padding-top: 6px;
}
.form-item-with-tip__main {
  flex: 0 1 auto;
  min-width: 0;
}
.form-item-with-tip__main--select {
  width: 400px;
  max-width: min(100%, 520px);
}
/** 起始 URL：输入框与提示图标同一行、图标紧跟输入框 */
.start-url-with-tip {
  display: inline-flex;
  align-items: center;
  flex-wrap: nowrap;
  gap: 6px;
  max-width: 100%;
}
.start-url-with-tip .start-url-input {
  width: min(100%, 480px);
  max-width: 100%;
  flex: 0 1 auto;
}
.textarea-with-tip {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
}
.textarea-with-tip__input {
  flex: 1;
  min-width: 0;
}
.textarea-with-tip__icon {
  flex-shrink: 0;
  margin-top: 4px;
}
.drawer-tip-line {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 10px;
}
.instruction-view-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.instruction-view-meta {
  font-size: 12px;
  color: #909399;
}
.instructions-textarea :deep(textarea) {
  font-family: inherit;
  line-height: 1.55;
}
.error-text {
  color: #dc2626;
  font-size: 14px;
}
.preview-panel .sub-title {
  margin: 16px 0 8px;
  font-size: 14px;
}
.preview-wrap {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.preview-block-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}
.preview-block-head .sub-title {
  margin: 0;
}
.preview-zoom-btn {
  flex-shrink: 0;
}
.preview-block--midscene-report {
  margin-top: 4px;
}
.preview-block--pw-report {
  margin-top: 4px;
}
.report-shell {
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 4px 24px rgba(15, 23, 42, 0.08);
  border: 1px solid #e2e8f0;
  background: #fff;
}
.report-shell__bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 18px;
  flex-wrap: wrap;
}
.report-shell__bar--ms {
  background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 45%, #f0fdfa 100%);
  border-bottom: 1px solid #a7f3d0;
}
.report-shell__bar--pw {
  background: linear-gradient(135deg, #eef2ff 0%, #e0e7ff 40%, #f5f3ff 100%);
  border-bottom: 1px solid #c7d2fe;
}
.report-shell__titles {
  min-width: 0;
  flex: 1;
}
.report-shell__title {
  margin: 0 0 4px;
  font-size: 16px;
  font-weight: 600;
  color: #0f172a;
  letter-spacing: 0.02em;
}
.report-shell__sub {
  margin: 0;
  font-size: 12px;
  color: #64748b;
  line-height: 1.45;
}
.report-shell__action {
  flex-shrink: 0;
}
.report-shell__frame-wrap {
  background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
  padding: 12px;
}
.report-shell__loading {
  padding: 24px;
  text-align: center;
}
.report-frame {
  width: 100%;
  min-height: clamp(320px, 58vh, 640px);
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #fff;
  box-shadow: inset 0 1px 2px rgba(15, 23, 42, 0.04);
}
.instructions-pre--mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12px;
}
.report-frame--fullscreen {
  display: block;
  width: 100%;
  height: calc(100vh - 120px);
  min-height: 400px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  background: #fafafa;
}
.report-fullscreen-dialog :deep(.el-dialog__body) {
  padding: 8px 16px 16px;
  box-sizing: border-box;
}
.video-el {
  width: 100%;
  max-width: 100%;
  max-height: min(52vh, 560px);
  border-radius: 6px;
}
.muted {
  color: #9ca3af;
  font-size: 13px;
}
.instructions-pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 13px;
  font-family: inherit;
  max-height: 200px;
  overflow: auto;
}
.error-inline {
  color: #b91c1c;
  white-space: pre-wrap;
  word-break: break-word;
}
.failed-hint {
  margin-top: 12px;
}
</style>

<style>
/* 兼容旧 class：若表格未加 runs-list，仍高亮选中行 */
.el-table .is-selected-run > td {
  background-color: #eef2ff !important;
}
.instruction-json-dialog :deep(.el-dialog__body) {
  padding-top: 8px;
}
.instruction-json-toolbar {
  margin-bottom: 10px;
}
.instruction-json-body {
  max-height: min(70vh, 720px);
  overflow: auto;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fafafa;
}
.instruction-json-pre {
  margin: 0;
  padding: 12px 14px;
  white-space: pre;
  overflow-wrap: normal;
  word-break: normal;
  font-size: 12px;
  line-height: 1.45;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  color: #303133;
}
</style>
