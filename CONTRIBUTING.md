# 参与贡献

欢迎通过问题反馈和拉取请求改进企知 Agent。请先阅读 README 并完成本地配置。

注释、提示词、用户文案和说明文档使用中文；函数名、接口字段、事件类型、环境变量和第三方协议保留约定的英文标识符。修改模型提示词时，同步维护依赖提示词的测试桩。

提交前运行：

```powershell
cd frontend
pnpm typecheck
pnpm build
cd ../backend
$env:PYTHONPATH="app"
uv run --locked python -m unittest discover -s tests -p "test_*.py" -v
```

提交源码、示例配置与依赖锁文件，不提交虚拟环境、真实配置、密钥、员工数据、聊天记录或向量库。请在拉取请求中说明具体问题、最终行为和验证结果。
