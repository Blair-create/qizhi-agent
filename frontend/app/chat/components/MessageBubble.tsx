import React from 'react';
import { Avatar, Button, Collapse, Spin, Tag, Timeline } from 'antd';
import { UserOutlined, RobotOutlined, CheckCircleOutlined, ToolOutlined, BulbOutlined, CloseCircleOutlined } from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';
import { Message } from '../types/chat.types';


interface MessageBubbleProps {
  message: Message;
  isStreaming: boolean;
  onApprove?: (message: Message) => void;
}

const renderContent = (content: string) => {
  const lines = content.split(/\r?\n/);
  const header = lines.findIndex((line) => /^\s*\|.*\|\s*$/.test(line));
  const separator = header >= 0 && lines[header + 1] && /^\s*\|?\s*:?-{3,}/.test(lines[header + 1]);
  if (header >= 0 && separator) {
    const before = lines.slice(0, header).join('\n').trim();
    const tableLines: string[] = [];
    let i = header;
    while (i < lines.length && /^\s*\|.*\|\s*$/.test(lines[i])) tableLines.push(lines[i++]);
    const cells = (line: string) => line.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map((v) => v.trim());
    const rows = tableLines.filter((_, index) => index !== 1).map(cells);
    return <>
      {before && <ReactMarkdown>{before}</ReactMarkdown>}
      <div className="my-2 overflow-x-auto"><table className="min-w-full border-collapse text-sm"><thead><tr>{rows[0].map((cell, index) => <th key={index} className="border border-gray-300 bg-gray-100 px-2 py-1 text-left">{cell}</th>)}</tr></thead><tbody>{rows.slice(1).map((row, ri) => <tr key={ri}>{row.map((cell, ci) => <td key={ci} className="border border-gray-300 px-2 py-1">{cell}</td>)}</tr>)}</tbody></table></div>
      {i < lines.length && <ReactMarkdown>{lines.slice(i).join('\n')}</ReactMarkdown>}
    </>;
  }
  return <ReactMarkdown>{content}</ReactMarkdown>;
};

const MessageBubble: React.FC<MessageBubbleProps> = ({ message, isStreaming, onApprove }) => {
  const { type, content, toolCall, runtimeEvents = [], status, approval } = message;
  const plan = runtimeEvents.find((event) => event.type === 'plan_created')?.plan;
  const timeline = runtimeEvents.filter((event) => ['memory_saved', 'memory_loaded', 'step_started', 'tool_started', 'tool_completed', 'tool_failed', 'reflection', 'recovery'].includes(event.type));

  return (
    <div className={`mb-4 ${type === 'user' ? 'text-right flex justify-end' : 'text-left'}`}>
      <div className={`flex ${type === 'user' ? 'flex-row-reverse' : 'flex-row'} items-start gap-3 max-w-2xl`}>
        <Avatar
          size={40}
          className={`${type === 'user' ? 'bg-blue-500' : 'bg-gray-500'} text-white`}
        >
          {type === 'user' ? <UserOutlined /> : <RobotOutlined />}
        </Avatar>
        <div className={`p-3 rounded-lg ${type === 'user' ? 'bg-blue-50' : 'bg-gray-50'} flex-1`}>
          {type === 'ai' && status && (
            <div className="mb-2 flex items-center gap-2">
              <Tag color={status === 'completed' ? 'green' : status === 'failed' ? 'red' : status === 'waiting_approval' ? 'orange' : 'blue'}>
                {status === 'completed' ? '已完成' : status === 'failed' ? '失败' : status === 'waiting_approval' ? '等待审批' : '执行中'}
              </Tag>
              {status === 'running' && <Spin size="small" />}
              {message.runId && <span className="text-xs text-gray-400">运行编号 {message.runId.slice(0, 8)}</span>}
            </div>
          )}
          {type === 'ai' && (plan || timeline.length > 0) && (
            <Collapse className="mb-3" size="small" items={[{
              key: 'execution', label: `执行过程${plan?.steps ? `（${plan.steps.length} 步）` : ''}`,
              children: <>
                {plan && <div className="mb-3"><p className="font-medium"><BulbOutlined /> {plan.goal}</p>
                  <ol className="list-decimal pl-5 text-sm text-gray-600">{plan.steps.map((step: any) => <li key={step.id}>{step.objective}</li>)}</ol>
                </div>}
                <Timeline items={timeline.map((event, index) => ({
                  key: `${event.type}-${index}`,
                  dot: event.type === 'tool_failed' ? <CloseCircleOutlined /> : event.type.startsWith('tool') ? <ToolOutlined /> : event.type === 'reflection' ? <CheckCircleOutlined /> : undefined,
                  color: event.type === 'tool_failed' ? 'red' : event.type === 'recovery' || event.passed === false ? 'orange' : 'blue',
                  children: event.type === 'memory_saved' ? `记忆已保存：${event.content}`
                    : event.type === 'memory_loaded' ? `已加载记忆：${event.short_term_count} 条会话消息，${event.long_term_count} 条长期记忆`
                    : event.type === 'step_started' ? `开始：${event.step?.objective}`
                    : event.type === 'tool_started' ? `调用工具：${event.name}`
                    : event.type === 'tool_completed' ? `工具完成：${event.name}`
                    : event.type === 'tool_failed' ? `工具失败：${event.name}，${event.error}`
                    : event.type === 'reflection' ? `校验：${event.reasoning_summary || (event.passed ? '通过' : '未通过')}`
                    : `恢复：${event.strategy === 'retry_with_reflection' ? '根据反思结果重试' : event.strategy}`,
                }))} />
              </>
            }]} />
          )}
          {approval && <div className="mb-3 border border-amber-300 bg-amber-50 p-3 text-sm">
            <p className="font-medium">需要确认：{approval.tool}</p><p>{approval.reason}</p>
            <Button className="mt-2" size="small" type="primary" disabled={isStreaming} onClick={() => onApprove?.(message)}>确认并继续</Button>
          </div>}
          {type === 'ai' && isStreaming && content === '' && runtimeEvents.length === 0 ? <Spin size="small" /> : (
            <> 
              {toolCall?.calls && toolCall.calls.length > 0 && (
                <Collapse
                  className="mb-2"
                  size="small"
                  items={[
                    {
                      key: 'tool-calls',
                      label: `工具调用（${toolCall.calls.length}）`,
                      children: (
                        <div className="space-y-3">
                          {toolCall.calls.map((call: any, index: number) => (
                            <div key={call.id || index} className="border-b border-gray-200 pb-3 last:border-0 last:pb-0">
                              <p className="font-medium">工具 {index + 1}：{call.name}</p>
                              <p className="break-all text-sm text-gray-600">输入：{JSON.stringify(call.args)}</p>
                              {call.result && <p className="break-all text-sm text-gray-600">结果：{call.result}</p>}
                            </div>
                          ))}
                        </div>
                      ),
                    },
                  ]}
                />
              )}
              {renderContent(content)}
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default MessageBubble;
