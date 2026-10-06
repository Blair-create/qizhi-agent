import React from "react";
import { Button, Input } from "antd";
import { SendOutlined, StopOutlined } from "@ant-design/icons";

interface MessageInputProps {
  input: string;
  setInput: (value: string) => void;
  handleSend: () => void;
  handleStop: () => void;
  isStreaming: boolean;
}

const MessageInput: React.FC<MessageInputProps> = ({ input, setInput, handleSend, handleStop, isStreaming }) => {
  return (
    <div className="p-4 border-t">
      <div className="flex gap-2 items-center">
        <Input.TextArea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="输入消息..."
          onKeyPress={(e) => e.key === "Enter" && handleSend()}
          // Ctrl + Enter 换行。
          onKeyDown={(e) => {
            if (e.key === "Enter" && e.ctrlKey) {
              e.preventDefault();
              setInput(input + "\n");
            }
          }}
          disabled={isStreaming}
          className="flex-1 min-h-[80px] p-3 rounded-lg border border-gray-300 focus:border-blue-500 focus:ring-blue-500 transition-colors"
          autoSize={{ minRows: 3, maxRows: 5 }}
        />
        <Button
          type={isStreaming ? "default" : "primary"}
          danger={isStreaming}
          icon={isStreaming ? <StopOutlined /> : <SendOutlined />}
          className={`h-24 px-6 rounded-lg transition-colors font-semibold shadow-md ${isStreaming ? "" : "bg-blue-500 hover:bg-blue-600 text-white"}`}
          onClick={isStreaming ? handleStop : handleSend}
          disabled={!isStreaming && !input.trim()}
        >
          {isStreaming ? "停止" : "发送"}
        </Button>
      </div>
    </div>
  );
};

export default MessageInput;
