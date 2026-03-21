# 需求文档 → 测试用例 自动生成器

基于 **LangChain** 与 **DeepSeek**，从产品/系统需求文档中自动生成结构化测试用例（Markdown 表格 + Excel），便于评审与导入测试管理平台。

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

在 **JM Test Center** 仓库中，本目录位于 **`backend/testcase`**，由后端 `CaseGenerationService` 动态加载；配置 **`backend/testcase/.env`**，部署与热重载说明见 **`backend/README.md`**。

---

## 功能概览

- **多格式需求文档**：支持 `.docx`（Word）、`.pdf`、`.md` / `.markdown`、`.txt`
- **两阶段生成**：先根据文档生成测试大纲（摘要 + 测试点），再按测试点分批生成用例，避免单次输出过长被截断
- **结构化输出**：每条用例包含 ID、优先级、模块、测试标题、摘要、前置条件、测试步骤、期望结果、实际结果（可留空）、类型、测试数据、备注
- **双格式导出**：`*.testcases.md`（Markdown 表格）+ `*.testcases.xlsx`（Excel），便于评审与导入 TMS
- **元信息输出**：`*.meta.md` 记录测试点列表、假设、风险、不在范围等，便于与产品/开发对齐

---

## 环境要求

- **Python** 3.10 或以上
- **DeepSeek API Key**（使用 [DeepSeek 开放平台](https://platform.deepseek.com/) 的 OpenAI 兼容接口）

---

## 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/Junmet/test_case.git
cd test_case
```

### 2. 安装依赖

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / macOS
# source .venv/bin/activate

pip install -r requirements.txt
```

### 3. 配置 API Key

复制环境变量示例并填写你的 DeepSeek API Key：

```bash
# Windows
copy .env.example .env
# Linux / macOS
# cp .env.example .env
```

编辑 `.env`，至少填写：

```env
DEEPSEEK_API_KEY=你的_API_Key
```

可选配置：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DEEPSEEK_BASE_URL` | API 基础地址 | `https://api.deepseek.com` |
| `DEEPSEEK_MODEL` | 模型名称 | `deepseek-chat` |
| `DEEPSEEK_TIMEOUT` | 请求超时（秒） | `120` |
| `DEEPSEEK_MAX_TOKENS` | 单次回复最大 token 数 | `16384` |
| `APP_LANGUAGE` | 输出语言 | `zh`（中文）/ `en`（英文） |

### 4. 放入需求文档并运行

项目中的 `input/` 目录**不会随仓库提交**（每人本地自行放置需求文档）。如果目录不存在，程序会自动创建该目录；把需求文档放入后再运行即可：

```bash
# 若无 input 目录则创建
mkdir input
# 将你的 .docx / .md / .txt 等需求文档放入 input/ 后执行
```

然后执行：

```bash
python -m src.main
```

生成结果会出现在 `output/` 目录，每个文档对应一组文件（见下方「输出说明」）。

---

## 输出说明

对每个输入文档，会在 `output/` 下生成四个文件（以 `需求文档.pdf` 为例）：

| 文件 | 说明 |
|------|------|
| `需求文档.xmind` | **思维导图**（XMind 格式），含「测试点」与「测试用例」两个分支，可用 XMind 打开 |
| `需求文档.testcases.md` | 测试用例的 **Markdown 表格**，便于在 Git/文档中查看 |
| `需求文档.testcases.xlsx` | 测试用例的 **Excel 表格**，便于评审、筛选与导入禅道/TestLink 等 |
| `需求文档.meta.md` | **元信息**：测试点列表、假设（assumptions）、风险（risks）、不在范围（out_of_scope） |

**用例表格列**：ID、优先级、模块、测试标题、摘要、前置条件、测试步骤、期望结果、实际结果（可为空）、类型、测试数据、备注。

---

## 命令行参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--input` | `input` | 需求文档所在目录 |
| `--output` | `output` | 生成结果输出目录 |
| `--language` | 同 `.env` 中 `APP_LANGUAGE` | 输出语言：`zh` / `en` |
| `--encoding` | `utf-8` | 读取 .md / .txt 时的编码 |
| `--max-cases` | `80` | 每个文档最多生成的用例条数 |
| `--batch-size` | `15` | 每批请求模型生成的用例条数（建议 10～20） |
| `--max-chars` | `15000` | 参与生成的文档最大字符数，超出部分会被截断 |

示例：

```bash
# 生成更多用例（每文档最多 200 条，每批 20 条）
python -m src.main --max-cases 200 --batch-size 20

# 指定输入/输出目录与语言
python -m src.main --input ./docs --output ./out --language zh

# 长文档时适当减小参与生成的字符数，避免 token 超限
python -m src.main --max-chars 12000
```

---

## 项目结构

```
test_case/
├── input/                 # 放置需求文档（docx / pdf / md / txt）
├── output/                # 生成结果（含 .xmind 思维导图、.testcases.md、.testcases.xlsx、.meta.md）
├── src/
│   ├── main.py            # 命令行入口
│   ├── config.py          # 配置加载（.env）
│   ├── models.py          # 数据模型（TestCase、GenerationResult）
│   ├── parsers.py         # 文档解析（docx / pdf / md / txt）
│   ├── prompts.py         # LLM 提示模板
│   ├── llm.py             # LangChain + DeepSeek 调用与 JSON 解析
│   └── writers.py        # 结果写出（Markdown / Excel / meta）
├── .env.example           # 环境变量示例
├── requirements.txt       # Python 依赖
├── DESIGN.md              # 设计说明（模块职责、流程、扩展建议）
└── README.md              # 本文件
```

更详细的模块说明与设计思路见 [DESIGN.md](DESIGN.md)。

---

## 常见问题

**Q：推送/拉取 GitHub 报 443 超时？**  
A：多为网络或代理问题。若使用代理，可配置 `git config --global http.https://github.com.proxy http://127.0.0.1:端口`；或改用 SSH 地址 `git@github.com:Junmet/test_case.git` 并配置 SSH Key。

**Q：报 `ModuleNotFoundError: No module named 'fitz'`？**  
A：PDF 解析依赖 PyMuPDF，请执行 `pip install pymupdf`（或重新安装依赖 `pip install -r requirements.txt`）。

**Q：模型返回 JSON 解析失败？**  
A：脚本已做简单修复（尾逗号、缺逗号）与批量生成失败重试。若仍报错，可查看 debug/ 目录下的 debug_*.txt 原始返回；必要时减小 `--batch-size`（如 10）或重试运行。

**Q：文档很长，会不会丢内容？**  
A：当前超过 `--max-chars` 的部分会被截断，只保留前 N 个字符参与生成。可适当增大 `--max-chars`（注意接口 token 限制），或将长文档拆成多份分别生成。

---

## 开源协议

本项目采用 [MIT License](LICENSE)。欢迎提交 Issue 与 Pull Request。

**仓库地址**：[https://github.com/Junmet/test_case](https://github.com/Junmet/test_case)
