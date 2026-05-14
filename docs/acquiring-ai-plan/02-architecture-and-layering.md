# 总体架构与分层设计

## 总体分层

### 1. 渠道层

- Web工作台
- 企业微信
- 内部系统嵌入
- OpenAPI

职责：负责多入口接入，不承载业务规则。

### 2. 业务域层

- 商户AI
- 代理商AI
- 运营支持
- 数据支持

职责：承接不同业务域的场景，不直接耦合具体外部系统。

### 3. Agent编排层

- Router Agent
- Domain Agents
- Session Context
- Task Routing

职责：负责路由、编排、上下文协调，不直接承担高风险最终决策。

### 4. 能力层

- Skills
- Tools
- Workflows
- Knowledge

职责：承载规则、动作、流程和依据，是扩展性的核心。

### 5. 平台底座层

- Auth / RBAC
- Approval / HITL
- Audit
- Observability / Eval
- Memory / Config
- Model Gateway

职责：统一治理、统一观测、统一模型接入。

## 为什么要拆成 Skill / Tool / Workflow / Knowledge

### Skill

解决“怎么做”。

- 承载业务规则
- 承载 SOP
- 承载判断逻辑
- 承载输出格式

### Tool

解决“做什么动作”。

- 查询系统
- 提交流程
- 获取数据
- 生成报表
- 发起工单

### Workflow

解决“按什么顺序做”。

- 承载确定性流程
- 审批流
- 回退流
- 人工确认节点

### Knowledge

解决“依据是什么”。

- 制度文档
- FAQ
- 案例库
- 监管口径
- 业务文档

## 一句话理解

- Skill 是方法
- Tool 是动作
- Workflow 是流程
- Knowledge 是依据

## 为什么必须分层

1. 便于治理
2. 便于复用
3. 便于审计
4. 便于扩展
5. 便于迭代

## 扩展性设计原则

1. 业务域独立扩展
2. 能力按标准形态接入
3. 高风险动作统一收口
4. 规则配置化
5. 模型可替换
6. 权限贯穿全链路
7. 新场景像装模块，不像改系统

## 新增场景的标准接入方式

新增一个业务场景时，原则上只新增：

- 一个业务域配置
- 一组 skills
- 一组 tools
- 一个或多个 workflows
- 一套 evals

而不是改动全局主干。

## 推荐的稳定内核与可变业务包拆分

### 稳定内核

- 权限
- 审批
- 审计
- Tool 网关
- Workflow 引擎
- Knowledge 检索
- 评测与监控
- 模型接入

### 可变业务包

- 商户AI
- 代理商AI
- 运营支持
- 数据支持
- 后续新增的清算、风控、合规专项助手
