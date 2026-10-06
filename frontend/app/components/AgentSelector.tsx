import React, { useEffect, useState } from 'react';
import { Select } from 'antd';

interface AgentSelectorProps {
  value: string;
  onChange: (value: string) => void;
}

const AgentSelector: React.FC<AgentSelectorProps> = ({ value, onChange }) => {
  const [options, setOptions] = useState([
    { value: "enterprise-agent-runtime", label: "公司通用智能体" },
  ]);

  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/agents`)
      .then((response) => response.ok ? response.json() : Promise.reject())
      .then((agents) => setOptions(agents.map((agent: { key: string; name: string }) => ({
        value: agent.key,
        label: agent.name,
      }))))
      .catch(() => undefined);
  }, []);

  return (
    <Select
      value={value}
      className="ml-2 mr-5 w-36"
      onChange={onChange}
      options={options}
    />
  );
};

export default AgentSelector;
