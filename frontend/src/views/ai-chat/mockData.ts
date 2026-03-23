/** AI 对话页：模型选项与前端会话类型（数据来自服务端数据库） */

export type ChatMessage = {
  id: number;
  role: "user" | "assistant" | "system";
  content: string;
  createdAt: string;
};

export type Conversation = {
  id: number;
  title: string;
  model: string;
  updatedAt: string;
  messages: ChatMessage[];
  /** 是否已从 GET /messages 拉取过 */
  messagesLoaded: boolean;
};

export const MODEL_OPTIONS = [
  { value: "deepseek-chat", label: "DeepSeek Chat" },
  { value: "deepseek-reasoner", label: "DeepSeek Reasoner" }
];
