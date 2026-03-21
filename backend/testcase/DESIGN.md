## 项目设计说明（DESIGN）

### 1. 背景与目标

- **背景**：传统手工从 PRD/需求文档中提炼测试点与测试用例，耗时长、容易遗漏、难以全覆盖。
- **目标**：
  - 从需求文档（Word/Markdown/Text）自动抽取文本；
  - 利用 LangChain + DeepSeek 生成：
    - **测试点思维导图（Mermaid mindmap）**；
    - **大批量结构化测试用例（Markdown 表格 + Excel）**；
  - 输出到 `output/` 目录，便于评审、导入测试管理工具。

核心要求：

- 支持多种文档格式（`.docx / .md / .markdown / .txt`）。
- 能生成**较多**测试用例（几十~上百），而不是只给少量示例。
- 代码结构清晰、可维护，便于后续扩展（更多字段、更多模型/供应商）。

---

### 2. 整体架构

自上而下分为三层：

- **CLI 层**：`src/main.py`
  - 负责参数解析、遍历输入文件、组织调用各个模块、打印进度、汇总输出。
- **业务逻辑层**：
  - 文档解析：`src/parsers.py`
  - Prompt 设计：`src/prompts.py`
  - LLM 调用与 JSON 解析：`src/llm.py`
  - 结果建模：`src/models.py`
  - 输出写入：`src/writers.py`
- **基础设施层**：
  - 配置加载：`src/config.py`
  - 环境依赖：`requirements.txt`、`.env`

处理流程示意：

1. CLI 读取命令行参数，加载配置，初始化 LLM。
2. 遍历 `input/` 中的每个文档：
   - 文档解析 → 纯文本。
   - 调用 LLM 生成**大纲**（摘要 + 测试点 + mindmap）。
   - 按测试点循环，分批调用 LLM 生成**用例批次**，直到达到目标条数。
   - 汇总结果，写出 mindmap / Markdown 表格 / Excel / meta。

---

### 3. 模块设计与职责

#### 3.1 `src/config.py` —— 配置模块

- **核心类型**：
  - `AppConfig`：
    - `deepseek_api_key`：调用 DeepSeek 的 API Key。
    - `deepseek_base_url`：OpenAI 兼容接口基础地址（如 `https://api.deepseek.com`）。
    - `deepseek_model`：模型名称（如 `deepseek-chat`）。
    - `language`：输出语言（`zh` / `en`）。
- **核心方法**：
  - `load_config(override_language: Optional[str]) -> AppConfig`：
    - 从 `.env` / 环境变量加载上述配置。
    - 优先使用当前项目根目录的 `.env`（`load_dotenv(override=True)`），避免被 Conda/系统旧变量覆盖。
    - 对 `base_url` 做规范化（去掉结尾 `/` 或 `/v1`）。

设计要点：

- 用 `@dataclass` 封装配置，明确字段意义，易于在其他模块中传递。

#### 3.2 `src/models.py` —— 数据模型

- **`TestCase`**：
  - 用例编号 `id`（如 `TC_CART_001`）。
  - 标题 `title`。
  - 模块 `module`。
  - 优先级 `priority`：P0~P3 / High/Medium/Low。
  - 前置条件 `preconditions`。
  - 步骤 `steps: List[str]`。
  - 期望结果 `expected: List[str]`。
  - 类型 `test_type`（功能/异常/边界/兼容/安全/性能等）。
  - 数据 `data`。
  - 备注 `remarks`。
- **`GenerationResult`**：
  - `source_name`：源文件名。
  - `language`：输出语言。
  - `context_summary`：从文档提炼的**摘要**，用于后续分批生成用例时复用，降低 token 消耗。
  - `mindmap_mermaid`：Mermaid mindmap 文本（不带 ``` 包裹）。
  - `test_points: List[str]`：测试点列表。
  - `test_cases: List[TestCase]`：完整用例集合。
  - `assumptions / risks / out_of_scope`：假设、风险、不在范围的说明。

设计要点：

- 使用 Pydantic `BaseModel`，方便：
  - LLM 输出的 JSON 进行结构校验；
  - 序列化/反序列化；
  - 后续扩展字段时保持类型安全。

#### 3.3 `src/parsers.py` —— 文档解析模块

- 支持的后缀：`SUPPORTED_SUFFIXES = {".docx", ".md", ".markdown", ".txt"}`。
- **核心类型**：
  - `ParsedDocument`：包含：
    - `path`：文件路径。
    - `text`：从文件中抽取出的规范化文本。
- **核心方法**：
  - `iter_input_files(input_dir: Path) -> Iterable[Path]`：
    - 遍历 `input/` 目录下所有支持的文件，按名称排序。
  - `parse_document(path: Path, encoding="utf-8") -> ParsedDocument`：
    - 根据后缀调用 `_parse_docx()` 或 `_parse_text()`。
    - 最后通过 `_normalize_text()` 统一换行、压缩多余空行。
  - `_parse_docx(path: Path) -> str`：
    - 使用 `python-docx` 读取 `.docx` 文件。
    - 抽取所有段落（非空）与表格（按行拼接单元格内容）。
  - `_parse_text(path: Path, encoding: str) -> str`：
    - 读取 `.md/.markdown/.txt` 文本。
  - `_normalize_text(text: str) -> str`：
    - 把 `\r\n/\r` 统一成 `\n`。
    - 将 3 个以上连续空行压缩成 2 行。

设计要点：

- 将“解析格式差异”的复杂度集中在这里，其余模块只需要面对统一的纯文本。

#### 3.4 `src/prompts.py` —— Prompt 模板模块

- **System Prompt**：
  - `SYSTEM_ZH` / `SYSTEM_EN`：
    - 指定角色为“资深测试工程师 / QA Lead”。
    - 强调输出必须是**严格 JSON**，字段完全匹配 schema。
    - 规定 mindmap 语法（第一行 `mindmap`，无 ``` 围栏）。
    - 规定用例优先级格式、步骤/期望要用列表等。
- **User Prompt 模板**：
  - `USER_TEMPLATE`：
    - 旧版“一次性生成测试点 + 用例”的通用模板。
  - `OUTLINE_USER_TEMPLATE`：
    - 只用于**大纲阶段**：
      - 要求生成 `context_summary`、`test_points`、`mindmap_mermaid` 等。
  - `CASES_BATCH_USER_TEMPLATE`：
    - 用于**按测试点分批生成用例**：
      - 提供 `context_summary`（无需模型重复复述）。
      - 提供当前测试点 `test_point`。
      - 提供本批目标条数 `batch_size`。
      - 提供已生成标题列表 `existing_titles` 用于去重。

设计要点：

- 所有“长 prompt”集中在一个文件管理，便于迭代、调优和多语言扩展。

#### 3.5 `src/llm.py` —— LLM 调用与两阶段生成

- **构建模型**：
  - `build_llm(cfg: AppConfig) -> ChatOpenAI`：
    - 基于 `cfg` 构造 `ChatOpenAI` 实例：
      - `api_key` / `base_url` / `model`。
      - `temperature=0.2`（偏保守、稳定）。
      - `timeout=120`。
      - `model_kwargs={"response_format": {"type": "json_object"}}`：尽可能约束模型返回 JSON。

- **数据结构**：
  - `OutlineResult`：
    - 用于接收大纲阶段 JSON。
  - `CasesBatchResult`：
    - 用于接收批量用例阶段 JSON。

- **老接口（兼容保留）**：
  - `generate_from_text(...) -> GenerationResult`：
    - 早期“一次性生成测试点 + 全部用例”的接口；
    - 容易超长被截断，目前不走这个流程，但保留以备后续实验。

- **新流程——两阶段生成**：
  1. `generate_outline(...) -> OutlineResult`
     - 任务：
       - 生成 `context_summary`（摘要）；
       - 生成 `test_points`（覆盖正常/异常/边界/权限/幂等等维度）；
       - 生成 `mindmap_mermaid`；
       - 生成 `assumptions / risks / out_of_scope`。
     - 实现：
       - 组装 System + `OUTLINE_USER_TEMPLATE` 消息；
       - 调用 `llm.invoke()`，拿到字符串；
       - 用 `_parse_or_debug()` + `_safe_json_loads()` + Pydantic 转为 `OutlineResult`。
  2. `generate_cases_batch(...) -> CasesBatchResult`
     - 任务：
       - 针对单个 `test_point`，在给定 `batch_size` 下生成若干条用例。
     - 入参：
       - `context_summary`：摘要，用于避免每批都贴整篇文档。
       - `test_point`：当前扩展的测试点。
       - `batch_size`：本批期望条数。
       - `existing_titles`：已生成的标题列表（末尾若干条），用于降低重复。
     - 同样通过 `llm.invoke()` + JSON 解析 + Pydantic 校验。

- **健壮性——JSON 解析与 Debug**：
  - `_safe_json_loads(s: str) -> Any`：
    - 去除 BOM、首尾空白。
    - 如果整体是 ```json 代码块，先剥离围栏与语言标签。
    - 若字符串整体是 `{...}`，直接 `json.loads`。
    - 否则从中截取第一个 `{ ... }` 片段尝试解析。
  - `_parse_or_debug(raw: str, debug_stem: str)`：
    - 如解析成功，返回结构化数据；
    - 如解析失败，把原始返回写入 `output/debug_{debug_stem}_时间.txt`，再抛出 `RuntimeError`。

设计要点：

- 通过“两阶段 + 分批”的架构，既能要很多用例，又能绕开单次 token 限制。
- 利用 Pydantic + debug 文件，便于定位和修正 prompt/模型行为。

#### 3.6 `src/writers.py` —— 输出模块

- `write_outputs(result: GenerationResult, output_dir: Path) -> list[Path]`：
  - 根据 `result.source_name` 生成 4 个文件：
    - `*.mindmap.md`：包含 mermaid mindmap 和一些元信息注释。
    - `*.testcases.md`：Markdown 表格，用于快速查看和简单评审。
    - `*.testcases.xlsx`：Excel 文件，适合详细评审和导入 TMS。
    - `*.meta.md`：元信息，包括测试点清单、假设、风险、不在范围。
  - 返回所有输出路径列表，供 CLI 汇总展示。
- `_render_mindmap_md()` / `_render_testcases_md()` / `_write_testcases_xlsx()` / `_render_meta_md()`：
  - 负责具体的 Markdown/Excel 文本结构和格式；
  - 对 mindmap 增加兜底逻辑，防止渲染失败。

#### 3.7 `src/main.py` —— CLI 入口

- `main()`：
  - 解析参数；
  - 加载配置、初始化 LLM；
  - 遍历 `input/` 中的每个文档，按上述流程生成结果；
  - 调用 `write_outputs()` 写出文件；
  - 使用 `rich` 打印汇总表。
- `_parse_args()`：
  - 定义并解析：
    - `--input`：输入目录（默认 `input`）。
    - `--output`：输出目录（默认 `output`）。
    - `--language`：覆盖默认语言。
    - `--encoding`：文本编码。
    - `--max-cases`：每个文档最多生成多少条用例。
    - `--batch-size`：每批次请求希望生成多少条用例。
    - `--max-chars`：文档最大参与生成的字符数。

设计要点：

- 把“业务流程控制”集中在一个文件中，便于阅读和调试。

---

### 4. 运行与使用方式

#### 4.1 环境准备

```bash
pip install -r requirements.txt
```

复制 `.env.example` 为 `.env` 并填写 DeepSeek 相关配置。

#### 4.2 放入需求文档

- 将需求文档放入 `input/` 目录：
  - 支持：`.docx` / `.md` / `.markdown` / `.txt`
  - 示例：`input/购物车功能需求文档（PRD）.docx`

#### 4.3 运行命令

- 最简单用法：

```bash
python -m src.main
```

- 指定用例数量与批次大小：

```bash
python -m src.main --max-cases 200 --batch-size 20
```

- 文档很长/多时，控制参与生成的最大字符数，避免 token 超限：

```bash
python -m src.main --max-cases 200 --batch-size 20 --max-chars 15000
```

#### 4.4 查看输出

每个文档对应生成 4 类输出文件（位于 `output/`）：

- `xxx.mindmap.md`：思维导图（Mermaid）。
- `xxx.testcases.md`：测试用例 Markdown 表格。
- `xxx.testcases.xlsx`：测试用例 Excel。
- `xxx.meta.md`：元信息（测试点、假设、风险、范围外）。

如遇模型输出非合法 JSON 或被截断，程序会在 `output/` 下生成 `debug_*.txt`，可打开查看原始返回，配合本设计文档中的 prompt 和流程说明进行调整与优化。

---

### 5. 后续优化方向（可选）

- 支持更多文档来源：
  - 直接从 wiki/接口文档系统拉取；
  - 支持 PDF（可用额外解析库）。
- 引入“多文档”检索能力：
  - 把多个 PRD/接口说明构建为知识库，用检索 + 生成覆盖跨模块测试场景。
- 更细粒度的失败重试与自动修复：
  - 对 JSON 解析错误加自动“修正器”（例如尝试补逗号、删除尾逗号）。
  - 对 `LengthFinishReasonError` 自动降低 `max-chars` 并重试。
- 预先定义用例模板/覆盖矩阵：
  - 按测试类型（边界、异常、幂等、权限等）预生成 slot，让模型在 slot 中补充具体内容，进一步提升覆盖率与一致性。

