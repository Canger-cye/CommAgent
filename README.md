# CommAgent · 6G 通感算智网络智能运维体

> 全球校园人工智能算法精英大赛 · **AI+软件创新** 参赛作品  
> 用自然语言下达运维意图 → 多智能体编排 → **确定性通信仿真** → 可解释结论与报告

[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

## 为什么不是「聊天机器人」

| 常规 LLM 应用 | CommAgent |
|---------------|-----------|
| 大模型直接「编」出 SNR / 吞吐 | 数值来自 3GPP / 香农 / 阵列因子等**可复现公式** |
| 只能对话 | 对话 + 仿真 + 诊断 + 优化 + 报告闭环 |
| 断网不可用 | **本地演示引擎**离线可完整答辩 |

## 功能

- **运维对话**：多轮自然语言，知识库原理融入回答
- **链路预算**：UMa 路损、SNR、香农容量、覆盖曲线
- **波束赋形**：ULA 方向图、3dB 波束、多用户分配
- **干扰分析**：同频合并、SINR、主干扰源
- **KPI 诊断**：覆盖 → 干扰 → 负载 → 参数 根因链
- **功率优化**：干扰受限下的功率局部搜索（实测吞吐 +）
- **运维报告**：自动汇编
- **模型设置**：本地演示 / OpenAI / DeepSeek / Kimi / 千问 / GLM 热切换

## 快速开始

```bash
git clone https://github.com/<you>/commagent.git
cd commagent
pip install -r requirements.txt
python run.py --llm mock --port 8787
# 浏览器打开 http://127.0.0.1:8787
```

Windows 亦可双击源码目录中的 `scripts/start_windows.bat`。

### 云端大模型（可选）

```powershell
$env:COMMAGENT_LLM_MODE = "api"
$env:COMMAGENT_LLM_API_BASE = "https://api.deepseek.com/v1"
$env:COMMAGENT_LLM_API_KEY  = "sk-..."
$env:COMMAGENT_LLM_MODEL    = "deepseek-chat"
python run.py --llm api
```

或在网页右上角 **「模型设置」** 中可视化配置（保存于本机 `outputs/llm_config.json`，请勿提交）。

### 打包桌面版

```bash
python build_exe.py
# 产物：dist/CommAgent/CommAgent.exe
```

## 测试

```bash
python scripts/test_formulas.py      # 公式 12 项
python scripts/test_casual_chat.py   # 闲聊/意图
python scripts/test_conversation.py  # 多轮对话
python scripts/test_llm_config.py    # 模型切换
```

## 项目结构

```
commagent/
├── backend/
│   ├── main.py              # FastAPI
│   ├── agents/              # 多智能体编排
│   ├── simulation/          # 链路/波束/干扰/网络/优化
│   ├── llm/                 # MockLLM / OpenAILLM
│   └── knowledge/           # 通信知识库
├── frontend/                # Web 运维台
├── docs/                    # 软件说明 / 架构 / 评分对标
├── scripts/                 # 测试与启动
├── run.py                   # 源码启动
├── app_entry.py             # 桌面启动入口
└── build_exe.py             # PyInstaller 打包
```

## 文档

- [软件说明文档](docs/软件说明文档.md)
- [系统架构](docs/ARCHITECTURE.md)
- [评分对标](docs/SCORING.md)

## 安全提示

- `outputs/llm_config.json` 含 API Key，已在 `.gitignore` 中排除
- 请复制 [`llm_config.example.json`](llm_config.example.json) 作为本地配置模板

## License

[MIT](LICENSE)
