"use client";

import React, { useEffect, useState } from "react";
import { Layout } from "antd";
import { BarsOutlined } from "@ant-design/icons";
import { v4 as uuidv4 } from "uuid";
import { LayoutContext } from "./layout-context";
import SessionListItem from "./components/SessionListItem";
import AgentSelector from "./components/AgentSelector";
import SiderComponent from "./components/SiderComponent";

const { Header, Content } = Layout;
type Session = { threadId: string; name: string; lastUpdated: number };

export default function LayoutShell({ children }: { children: React.ReactNode }) {
  const [collapsed, setCollapsed] = useState(false);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentThreadId, setCurrentThreadId] = useState<string | null>(null);
  const [agentId, setAgentId] = useState("enterprise-agent-runtime");

  useEffect(() => {
    try {
      const stored = JSON.parse(localStorage.getItem("chatSessions") || "[]");
      setSessions(Array.isArray(stored) ? stored : []);
    } catch {
      setSessions([]);
    }
  }, []);

  const handleAddSession = (newThreadId: string, startMsg: string) => {
    const threadId = newThreadId || uuidv4();
    const name = (startMsg || `新对话 ${new Date().toLocaleString()}`).substring(0, 10);
    setSessions((prev) => {
      const next = [...prev.filter((session) => session.threadId !== threadId), { threadId, name, lastUpdated: Date.now() }];
      localStorage.setItem("chatSessions", JSON.stringify(next));
      return next;
    });
    setCurrentThreadId(threadId);
    window.history.pushState({}, "", `/chat/${threadId}`);
  };

  useEffect(() => {
    const addSession = (event: Event) => {
      const { threadId, msg } = (event as CustomEvent).detail || {};
      handleAddSession(threadId, msg);
    };
    window.addEventListener("add-session", addSession);
    return () => window.removeEventListener("add-session", addSession);
  }, []);

  const handleDeleteSession = (threadId: string) => {
    setSessions((prev) => {
      const next = prev.filter((session) => session.threadId !== threadId);
      localStorage.setItem("chatSessions", JSON.stringify(next));
      return next;
    });
    localStorage.removeItem(`chatMessages-${threadId}`);
    setCurrentThreadId(null);
    window.history.pushState({}, "", "/chat");
  };

  const handlerNewChat = () => {
    setCurrentThreadId(null);
    window.history.pushState({}, "", "/chat");
  };

  const items = [...sessions].reverse().map((session) => ({
    key: session.threadId,
    label: <SessionListItem session={session} onDelete={handleDeleteSession} />,
  }));

  return (
    <LayoutContext.Provider value={{ agentId, setAgentId, currentThreadId, setCurrentThreadId }}>
      <Layout className="min-h-screen">
        <SiderComponent collapsed={collapsed} onCollapse={setCollapsed} sessions={sessions} handleDeleteSession={handleDeleteSession} handlerNewChat={handlerNewChat} items={items} onSelectSession={(key) => { setCurrentThreadId(key); window.history.pushState({}, "", `/chat/${key}`); }} />
        <Layout>
          <Header className="bg-white p-0 flex flex-nowrap">
            <BarsOutlined onClick={() => setCollapsed(!collapsed)} className="ml-4 text-xl" />
            <div className="flex items-center ml-8 flex-none shrink-0"><span className="text-base">AI 智能体：</span><AgentSelector value={agentId} onChange={(value) => { setAgentId(value); handlerNewChat(); }} /></div>
          </Header>
          <Content className="m-4 p-6 bg-white min-h-[calc(100vh-120px)]">{children}</Content>
        </Layout>
      </Layout>
    </LayoutContext.Provider>
  );
}
