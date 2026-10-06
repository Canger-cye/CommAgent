# CommAgent 系统架构说明

## 1. 设计目标

| 目标 | 落地手段 |
|------|----------|
| 通信专业可信 | 数值仿真独立于 LLM，公式可追溯 |
| 智能体名副其实 | 意图识别 → 任务编排 → 工具调用 → 结果解释 |
| 答辩不翻车 | MockLLM 离线全链路可跑 |
| 可扩展 | Agent 注册式路由，新增能力只加类 |

## 2. 分层架构

```
┌─────────────────────────────────────────────┐
│                 Web 控制台                    │
│   对话 / 链路 / 波束 / 干扰 / 诊断 / 拓扑 / 报告   │
└────────────────────┬────────────────────────┘
                     │ HTTP /api/*
┌────────────────────▼────────────────────────┐
│              FastAPI (backend.main)          │
│  REST · 静态资源 · 参数校验 (Pydantic)          │
└────────────────────┬────────────────────────┘
                     │
┌────────────────────▼────────────────────────┐
│           Orchestrator 多智能体编排            │
│  classify_intent → route → Agent.run → 汇总   │
└───┬─────────┬─────────┬─────────┬───────────┘
    │         │         │         │
 Link     Beam     Diagnose   Optimize / Report
 Agent    Agent     Agent      Agent
    │         │         │         │
┌───▼─────────▼─────────▼─────────▼───────────┐
│            Simulation Engine                 │
│  link_budget · beamforming · interference    │
│  network scenario · power optimization       │
└────────────────────┬────────────────────────┘
                     │
        Knowledge Base (RAG-lite)  +  LLM Port
                     │
              MockLLM / OpenAILLM
```

## 3. 关键数据流（以「诊断」为例）

1. 用户输入：`SINR 是 -2dB，BLER 0.12，帮我诊断`
2. `classify_intent` → `intent=diagnose`, `entities={db_value:-2, ...}`
3. `Orchestrator` 路由到 `DiagnosisAgent`
4. `diagnose_from_metrics` 产出结构化 findings（等级/原因/建议）
5. LLM（Mock 或 API）生成一句面向工程师的总结
6. 前端渲染 KPI 卡 + 根因卡片 + 建议

## 4. 算法说明

### 4.1 链路预算
- 路损（UMa NLOS 简化）：`PL = 13.54 + 39.08*log10(d) + 20*log10(fc)`
- 接收功率：`Prx = Ptx + Gtx + Grx - PL`
- 热噪声：`N = -174 + 10*log10(B*1e6) + NF`
- 香农容量：`C = B * log2(1 + SINR)`

### 4.2 波束赋形
- ULA 阵列因子：`AF = |sin(Nπd sinθ) / (N sin(πd sinθ))|`
- 合成方向图 = 单元方向图 + 阵列因子，再归一化到目标峰值增益

### 4.3 干扰
- 干扰线性相加：`I_total = Σ 10^(Prx_i/10)`
- `SINR = Prx_s - 10*log10(N + I_total)`

### 4.4 功率优化（启发式）
- 聚合各基站下用户平均 SINR
- 低于目标-5dB → 升 2dB（上限 46dBm）
- 高于目标+10dB → 回退 2dB（降邻区干扰）
- 重新计算场景 KPI，输出 Δ 吞吐

## 5. 可插拔 LLM

```python
settings.llm_mode = "mock" | "api"
```

- `MockLLM`：确定性意图说明，保证离线演示
- `OpenAILLM`：OpenAI 兼容 `/chat/completions`，可用国产大模型端点

**原则**：LLM 不直接输出 SNR/吞吐等指标，只做自然语言组织与解释；指标一律来自仿真引擎。

## 6. 扩展点

| 想加什么 | 怎么加 |
|----------|--------|
| 新 Agent | 继承 `Agent`，实现 `run()`，在 `Orchestrator._routes` 注册 |
| 新仿真 | `backend/simulation/` 加模块，Agent 调用 |
| 真实数据源 | 在 Agent 内对接告警/网管 API |
| 语音 | 前端加 Web Speech / 离线 ASR |
| 导出 PDF | ReportAgent 产出 Markdown → pdf 套件渲染 |
