// 聊天消息类型
export interface Message {
  id: string;
  type: "user" | "ai" | "tool";
  content: string;
  toolCall?: { calls: any[] };
  runId?: string;
  status?: "running" | "waiting_approval" | "completed" | "failed";
  runtimeEvents?: RuntimeEvent[];
  approval?: { tool: string; reason: string; action_key: string; arguments: Record<string, unknown> };
  requestMessage?: string;
}

export interface RuntimeEvent {
  type: string;
  run_id?: string;
  [key: string]: any;
}

// 聊天组件属性
export interface ChatComponentProps {
  threadId: string;
}
