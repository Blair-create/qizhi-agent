import { message } from "antd";
import { Message } from "../types/chat.types";
import { Dispatch, SetStateAction, useRef } from "react";

// 后端以 SSE 发送 data: {...}，本 Hook 负责读取事件并更新聊天 UI。

interface UseStreamChatProps {
  currentThreadId: string;
  agentId: string;
  setMessages: Dispatch<SetStateAction<Message[]>>;
  isStreaming: boolean;
  setIsStreaming: (value: boolean) => void;
}


export const useStreamChat = ({
  currentThreadId,
  agentId,
  setMessages,
  isStreaming,
  setIsStreaming,
}: UseStreamChatProps) => {
  const abortControllerRef = useRef<AbortController | null>(null);

  const stopStream = () => {
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    setMessages((prev) => {
      const lastMessage = prev[prev.length - 1];
      if (lastMessage?.type === "ai" && !lastMessage.content && !lastMessage.toolCall?.calls.length) {
        return prev.slice(0, -1);
      }
      return prev;
    });
    setIsStreaming(false);
  };

  const handleStream = async (input: string, threadId = currentThreadId, approvedActions: string[] = []) => {
    if (!input.trim() || isStreaming) return;
    setIsStreaming(true);
    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    const newUserMessage: Message = {
      id: `user_${Date.now()}`,
      type: "user",
      content: input,
    };
    const newAiMessage: Message = {
      id: `ai_${Date.now()}`,
      type: "ai",
      content: "",
      status: "running",
      requestMessage: input,
    };
    setMessages((prev: Message[]) => [...prev, newUserMessage, newAiMessage]);

    try {
    // 运行时事件流覆盖规划、行动、观察、反思的完整生命周期。
    const requestMsg = {
        thread_id: threadId,
        role: "user",
        message: input,
        user_id: "web-user",
        approved_actions: approvedActions,
      };

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/agent/runs/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestMsg),
        signal: abortController.signal,
      });
      if (!response.ok || !response.body) {
        throw new Error(`服务请求失败（HTTP ${response.status}）`);
      }
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      const consumeEvent = (rawEvent: string) => {
        const dataLine = rawEvent.split("\n").find((line) => line.startsWith("data: "));
        if (!dataLine) return;
        const data = JSON.parse(dataLine.slice(6));
        switch (data.type) {
          case "run_completed":
            setMessages((prev) => prev.map((msg, i) => i === prev.length - 1
              ? { ...msg, content: data.answer, status: "completed", runId: data.run_id }
              : msg));
            break;
          case "run_failed":
            setMessages((prev) => prev.map((msg, i) => i === prev.length - 1
              ? { ...msg, content: `执行失败：${data.error}`, status: "failed", runId: data.run_id }
              : msg));
            break;
          case "approval_required":
            setMessages((prev) => prev.map((msg, i) => i === prev.length - 1
              ? { ...msg, status: "waiting_approval", approval: data, runId: data.run_id }
              : msg));
            break;
          case "end": setIsStreaming(false); return;
          default:
            setMessages((prev) => prev.map((msg, i) => i === prev.length - 1
              ? { ...msg, runtimeEvents: [...(msg.runtimeEvents || []), data], runId: data.run_id, status: "running" }
              : msg));
        }
      };

      // 网络分块不等于 SSE 事件边界，保留未完成片段供下一次读取。
      while (reader) {
        const { done, value } = await reader.read();
        buffer += decoder.decode(value, { stream: !done }).replace(/\r\n/g, "\n");
        const events = buffer.split("\n\n");
        buffer = events.pop() || "";
        events.forEach(consumeEvent);
        if (done) break;
      }
      if (buffer.trim()) consumeEvent(buffer);
      setIsStreaming(false);
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") {
        return;
      }
      console.error("请求失败：", error);
      message.error(error instanceof Error ? error.message : "请求失败，请稍后重试。");
      setMessages((prev) => prev.filter((msg, index) =>
        !(index === prev.length - 1 && msg.type === "ai" && !msg.content)
      ));
    } finally {
      if (abortControllerRef.current === abortController) {
        abortControllerRef.current = null;
      }
      setIsStreaming(false);
    }
  };

  const handleMessageData = (content: any) => {
    if (content.type === "ai" && Array.isArray(content.tool_calls) && content.tool_calls.length > 0) {
      setMessages((prev) => {
        const currentCalls = prev[prev.length - 1]?.toolCall?.calls || [];
        const callsById = new Map(currentCalls.map((call) => [call.id, call]));
        content.tool_calls.forEach((call: any) => {
          callsById.set(call.id, { ...callsById.get(call.id), ...call });
        });
        return prev.map((msg, i) =>
          i === prev.length - 1
            ? {
                ...msg,
                toolCall: { calls: Array.from(callsById.values()) },
              }
            : msg
        );
      });
    }else if (content.type === "ai" && content.content) {
      setMessages((prev) =>
        prev.map((msg, i) =>
          i === prev.length - 1 ? { ...msg, content: content.content } : msg
        )
      );
    }
    if (content.type === "tool") {
      setMessages((prev) => {
        const calls = prev[prev.length - 1]?.toolCall?.calls || [];
        const updatedCalls = calls.map((call) =>
          call.id === content.tool_call_id
            ? { ...call, result: content.content }
            : call
        );
        return prev.map((msg, i) =>
          i === prev.length - 1
            ? {
                ...msg,
                toolCall: { ...msg.toolCall, calls: [...updatedCalls] },
              }
            : msg
        );
      });
    }
  };

  const handleTokenData = (token: string) => {
    setMessages((prev) =>
      prev.map((msg, i) =>
        i === prev.length - 1 ? { ...msg, content: msg.content + token } : msg
      )
    );
  };


  return { handleStream, stopStream };
};
