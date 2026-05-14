# 一期需求当前交付状态

## 当前已完成

### 1. 方案与实施文档

- 整体规划
- 架构分层
- 一期范围与路线图
- 实施分解
- WBS 与推进计划
- 场景、Skill、审批、Tool、知识源模板

### 2. 一期工程骨架

- FastAPI 主服务
- `/health`
- `/api/chat`
- `/api/knowledge/search`
- `/api/approvals`
- `/api/approvals/{approval_id}/decision`
- 主控路由 + 业务能力 Agent 注册机制
- registry 抽象层、Nacos 注册发现、远程代理骨架

### 3. 一期三条业务线骨架

- 商户AI
- 运营支持
- 数据支持

### 3.1 已注册的一期业务能力

- merchant.qa
- merchant.issue_handling
- merchant.ops_analysis
- operations.quota_review
- operations.onboarding_review
- operations.merchant_change_review
- data_support.direct_sales_data
- data_support.compliance_report

### 4. 一期首批技能占位

- merchant_qa
- merchant_issue_handling
- quota_review
- merchant_onboarding_review
- merchant_change_review
- direct_sales_data_assistant
- compliance_report_generation

## 当前实现边界

当前版本是“一期 MVP 骨架”，主要用于：

- 固化项目目录
- 固化接口边界
- 固化主平台与业务能力的解耦边界
- 为后续接数据库、模型、审批流和内部系统提供落点

当前尚未完成：

- 真实 Agno 接入
- 数据库存储
- 企业统一认证
- 企业内部系统联调
- 真正的审批中心
- 真正的知识库和向量检索
- 真实 Nacos 客户端通信与远程 capability 调用
- 真实远程 capability 服务拆分与多实例负载策略

## 下一步建议实施顺序

1. 接入 PostgreSQL，落地审批、审计、会话表
2. 接入企业统一认证与 RBAC
3. 接入 Agno 和模型推理
4. 接入首批只读 Tool
5. 接入知识源与搜索
6. 接入调额审核真实审批流

## 适合作为下个迭代的具体任务

- 持久化 approval tasks
- 持久化 audit logs
- 把 `/api/chat` 的规则路由替换为 Agno Router
- 把知识检索替换为真实 Knowledge/RAG
- 把运营支持 workflow 拆成独立模块
- 补齐 Nacos 注册、心跳、查询和远程 capability 代理
