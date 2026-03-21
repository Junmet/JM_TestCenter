/** AI 对话页静态数据（后续接后端 / SSE 时替换） */

export type ChatMessage = {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  createdAt: string;
};

export type Conversation = {
  id: string;
  title: string;
  updatedAt: string;
  model: string;
  messages: ChatMessage[];
};

export const MODEL_OPTIONS = [
  { value: "gpt-4o", label: "GPT-4o（示例）" },
  { value: "doubao-pro", label: "豆包 Pro（示例）" },
  { value: "deepseek-chat", label: "DeepSeek Chat（示例）" },
  { value: "qwen-max", label: "通义千问 Max（示例）" },
];

export const INITIAL_CONVERSATIONS: Conversation[] = [
  {
    id: "c1",
    title: "如何写 Vue3 组合式 API",
    updatedAt: "2026-03-21 14:20",
    model: "gpt-4o",
    messages: [
      {
        id: "m1",
        role: "user",
        content: "请用三句话说明 setup 里 ref 和 reactive 的区别。",
        createdAt: "2026-03-21 14:18",
      },
      {
        id: "m2",
        role: "assistant",
        content:
          "1）`ref` 适合原始值与单值，通过 `.value` 读写；2）`reactive` 适合对象/集合，解构会丢响应式，需 `toRefs`；3）二者都可配合 `computed`、`watch` 使用，按数据形状选择即可。\n\n（以上为静态示例文案，未调用真实模型。）",
        createdAt: "2026-03-21 14:18",
      },
    ],
  },
  {
    id: "c2",
    title: "接口鉴权方案讨论",
    updatedAt: "2026-03-20 09:10",
    model: "deepseek-chat",
    messages: [
      {
        id: "m3",
        role: "user",
        content: "JWT 和 Session 各有什么优缺点？",
        createdAt: "2026-03-20 09:08",
      },
      {
        id: "m4",
        role: "assistant",
        content:
          "JWT：无状态、易横向扩展，但要注意泄露与撤销困难；Session：服务端可控、易失效，但需要存储与粘性会话或集中存储。\n\n（静态示例）",
        createdAt: "2026-03-20 09:09",
      },
    ],
  },
];

let idSeq = 100;

export function genId(prefix: string) {
  return `${prefix}-${Date.now()}-${idSeq++}`;
}
