import React, { useState, useRef, useEffect } from "react";
import { v4 as uuidv4 } from "uuid";
import MessageInput from "../components/MessageInput";
import { useLayoutContext } from '../../layout-context';
import { Message, ChatComponentProps } from '../types/chat.types';
import { useStreamChat } from '../hooks/useStreamChat';
import MessageBubble from '../components/MessageBubble';
import useChatActions from '../hooks/useChatActions';

const ChatComponent: React.FC<ChatComponentProps> = ({
  threadId,
}) => {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const messagesEndRef = useRef(null);
  const messagesRef = useRef<Message[]>([]);
  const loadedThreadIdRef = useRef<string | null>(threadId || null);
  const skipNextSaveRef = useRef(false);
  const { agentId, setAgentId, currentThreadId, setCurrentThreadId } = useLayoutContext()

  useEffect(() => {
    if(threadId){
      setCurrentThreadId(threadId)
    }
  }, [threadId, setCurrentThreadId]);
  
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => scrollToBottom(), [messages]);

  const { handleNewChat } = useChatActions({ setMessages, setInput, isStreaming, setIsStreaming });

  useEffect(() => {
    console.log("当前线程 ID", currentThreadId);
    if (loadedThreadIdRef.current === currentThreadId) return;

    if (loadedThreadIdRef.current && messagesRef.current.length > 0) {
      localStorage.setItem(
        "chatMessages-" + loadedThreadIdRef.current,
        JSON.stringify(messagesRef.current)
      );
    }

    loadedThreadIdRef.current = currentThreadId;
    skipNextSaveRef.current = true;
    if(!currentThreadId || currentThreadId === "") {
      handleNewChat();
      return;
    }
    const storedMessages = localStorage.getItem(
      "chatMessages-" + currentThreadId
    );
    if (storedMessages) {
      setMessages(JSON.parse(storedMessages));
    } else {
      setMessages([]);
    }
  }, [currentThreadId]);

  useEffect(() => {
    messagesRef.current = messages;
    if (skipNextSaveRef.current) {
      skipNextSaveRef.current = false;
      return;
    }
    if (loadedThreadIdRef.current && messages.length > 0) {
      localStorage.setItem(
        "chatMessages-" + loadedThreadIdRef.current,
        JSON.stringify(messages)
      );
    }
  }, [messages]);

  const { handleStream, stopStream } = useStreamChat({ currentThreadId, agentId, setMessages, isStreaming, setIsStreaming });

  const handleSend = async () => {
    const message = input.trim();
    if (!message || isStreaming) return;
    setInput("");
    let activeThreadId = currentThreadId;
    if (!activeThreadId) {
      activeThreadId = uuidv4();
      loadedThreadIdRef.current = activeThreadId;
      setCurrentThreadId(activeThreadId);
      window.dispatchEvent(
        new CustomEvent("add-session", {
          detail: { threadId: activeThreadId, msg: message },
        })
      );
    }
    await handleStream(message, activeThreadId);
  };

  return (
    <div className="h-full">
      <div className="chat-messages overflow-y-auto p-4 h-[calc(100vh-280px)]">
        {messages.length === 0 && (
          <div className="flex flex-col justify-center items-center min-h-full text-gray-600 space-y-2">
            <div className="text-2xl font-medium">欢迎使用企知 Agent</div>
            <div className="text-base">
            现在可以输入问题，我会帮助你解答！            </div>
          </div>
        )}
        {messages.map((msg) => (
          <MessageBubble
            key={msg.id}
            message={msg}
            isStreaming={isStreaming}
            onApprove={(pending) => {
              if (pending.approval && pending.requestMessage) {
                handleStream(pending.requestMessage, currentThreadId, [pending.approval.action_key]);
              }
            }}
          />
        ))}
        <div ref={messagesEndRef} />
      </div>
      <MessageInput
        input={input}
        setInput={setInput}
        handleSend={handleSend}
        handleStop={stopStream}
        isStreaming={isStreaming}
      />
    </div>
  );
};

export default ChatComponent;
