---
name: brainstorm
description: |
  当需要探索方案、头脑风暴、创意思维时自动使用此 Skill。

  触发场景：
  - 不知道怎么设计
  - 需要多种方案
  - 创意探索
  - 架构讨论
  - 功能规划
  - 业务扩展

  触发词：头脑风暴、方案、怎么设计、有什么办法、创意、讨论、探索、想法、建议、怎么做、如何实现、有哪些方式、能不能做、可以实现吗
---

# 头脑风暴框架

## ⚠️ 核心原则：决策点必须询问用户

**遇到以下情况，必须使用 `AskUserQuestion` 工具询问用户，不得擅自决定**：

| 决策类型 | 触发条件 | 示例问题 |
|---------|---------|---------|
| **方案选择** | 列出 2+ 个方案后 | "以上方案您倾向于哪个？" |
| **模块归属** | 功能可挂靠多个模块时 | "新功能是挂靠 module_admin 还是新建模块？" |
| **技术选型** | 同类技术有多种选择时 | "实时推送用 WebSocket 还是 SSE？" |
| **实施范围** | MVP vs 完整版不明确时 | "先做 MVP 还是一次性实现完整版？" |
| **数据库兼容** | 不确定是否需要多库支持时 | "需要同时支持 MySQL 和 PostgreSQL 吗？" |
| **新增依赖** | 需引入项目外部新库时 | "此方案需要引入 [xxx] 库，是否同意？" |

> **禁止**：分析完后直接给出"推荐方案 X"并开始实施，必须先通过 `AskUserQuestion` 让用户确认选择。

---

## 本项目技术约束（头脑风暴边界）

> **重要**：所有方案必须在以下技术栈约束内思考

### 后端已集成技术栈

| 层面 | 技术 | 说明 |
|------|------|------|
| **框架** | FastAPI 0.116.1 + fastapi[all] | 核心框架，含 uvicorn、httpx |
| **ORM** | SQLAlchemy 2.0.43（异步） | 数据持久层 |
| **数据库** | MySQL（asyncmy）/ PostgreSQL（psycopg） | 多数据库支持 |
| **SQL转译** | sqlglot 27.8.0 | 跨数据库 SQL 兼容转换 |
| **缓存** | Redis 6.4.0 | 分布式缓存、消息队列（Streams）|
| **定时任务** | APScheduler 3.11.0 | 任务调度 |
| **认证** | PyJWT 2.10.1 | JWT 权限认证 |
| **实时通信** | WebSocket + SSE | 双向通信 / 服务端推送（已集成）|
| **文件存储** | 本地文件存储 | upload_util 管理，OSS 需自行扩展 |
| **数据加密** | passlib[bcrypt] 1.7.4 | 密码哈希 |
| **日志** | loguru 0.7.3 | 结构化日志记录 |
| **Excel** | openpyxl 3.1.5 | 导入导出 |
| **数据处理** | pandas 2.3.2 | 数据分析与处理 |
| **图片处理** | Pillow 11.3.0 | 图片生成与处理 |
| **参数验证** | pydantic-validation-decorator 0.1.4 | @ValidateFields 装饰器 |
| **数据库迁移** | Alembic 1.16.4 | Schema 版本管理 |

### 已有业务模块

| 模块 | 路径 | 功能 |
|------|------|------|
| **系统管理** | `module_admin/` | 用户、角色、菜单、字典、部门、岗位、日志、定时任务、通知、PPT生成 |
| **代码生成** | `module_generator/` | 根据表结构自动生成 CRUD 代码 |
| **AI 服务** | `module_aiserver/` | OpenAI/Anthropic 协议转换代理 |

### 需自行扩展的技术

| 技术 | 场景 | 说明 |
|------|------|------|
| **Celery** | 高吞吐分布式任务 | 简单场景用 Redis Streams，复杂再引入 |
| **MQTT/paho-mqtt** | IoT 设备通信 | 需自行引入 |
| **OSS/S3** | 云对象存储 | 当前为本地存储，云存储需自行扩展 |
| **LangChain** | AI 工作流编排 | module_aiserver 已有基础，复杂流程可扩展 |
| **SMS 短信** | 短信通知 | 需自行对接阿里云/腾讯云 SMS SDK |
| **支付** | 微信/支付宝 | 需自行开发 |

### 可复用的 Utils 工具

```
核心响应: response_util（ResponseUtil.success/failure/error）
分页处理: page_util（PageUtil.paginate）
异常处理: ServiceException（raise ServiceException(message='xxx')）
日志记录: log_util（logger.info/error/debug）
Excel: excel_util（ExcelUtil）
文件上传: upload_util（UploadUtil）
密码处理: pwd_util（PwdUtil）
通信: websocket_manager, sse
装饰器: @Log、@ValidateFields、CheckUserInterfaceAuth
```

---

## 核心架构（三层，必须遵守）

```
Controller → Service → DAO
     ↓           ↓       ↓
  APIRouter   业务逻辑  查询构建
  参数校验    事务管理  SQL封装
```

> 每层的支撑产物：Entity(DO) = SQLAlchemy Model(Base)，Schema(VO/BO) = Pydantic BaseModel

> ⚠️ **禁止**在 Service 层直接写查询，必须封装到 DAO 层

---

## 头脑风暴执行流程（四个阶段）

### 阶段一：信息收集与问题澄清

启动头脑风暴前，先主动澄清不明确的需求：

```
需要确认的信息：
1. 功能的业务价值是什么？解决什么问题？
2. 是系统内置功能（module_admin）还是独立业务（新 module_xxx）？
3. 数据量级？对性能有特殊要求吗？
4. 是否需要同时支持 MySQL 和 PostgreSQL？
5. 需要权限控制吗？数据权限还是接口权限？
```

> **如果以上信息不完整，先用 `AskUserQuestion` 澄清，再进入下一阶段。**

---

### 阶段二：发散探索（列方案）

**思路框架（发散，先不评判）**：

1. **复用优先** — 现有 utils/module 能解决多少？
2. **组合思维** — 已有模块如何组合？
3. **类比借鉴** — 项目内哪个功能最像？参考它的实现
4. **反向思考** — 让问题更糟会怎样？反过来就是解法
5. **渐进实现** — MVP 是什么？完整版再迭代

**收敛筛选（选方案时评估）**：

1. **三层架构** — 各层职责如何划分（Controller/Service/DAO）？
2. **模块归属** — 属于 module_admin 还是新建 module_xxx？
3. **可行性** — 现有技术栈能否覆盖？需要引入新依赖吗？
4. **多数据库** — 需要兼容 MySQL/PostgreSQL 吗？（sqlglot 已支持）
5. **开发成本** — 工作量与价值比合理吗？

---

### 阶段三：用户决策（必须执行，不可跳过）

列出 2+ 个方案后，**必须通过 `AskUserQuestion` 让用户选择**，格式如下：

#### 决策点 1：方案选择

```
呈现内容：
- 每个方案的核心思路（1-2句话）
- 优缺点对比
- 开发量估算（小/中/大）

询问用户：请选择您倾向的方案
```

#### 决策点 2：模块归属（如有歧义）

```
询问用户：
- 选项A：挂靠 module_admin（减少维护成本，适合系统功能）
- 选项B：新建 module_xxx（职责清晰，适合独立业务）
```

#### 决策点 3：实施范围（如有歧义）

```
询问用户：
- 选项A：MVP 版（核心功能，快速上线）
- 选项B：完整版（包含导出、权限、日志等）
```

---

### 阶段四：制定实施计划（基于用户决策）

**用户决策完成后**，才输出实施步骤：

```markdown
**确认方案 [X]**，基于您的选择，实施步骤：

1. [ ] 数据库设计 → 激活 `database-ops` Skill
2. [ ] 三层代码开发 → 激活 `crud-development` Skill
3. [ ] 接口文档同步 → 激活 `api-doc-sync` Skill
4. [ ] 代码规范检查 → 运行 `/check`

**风险与应对**：
| 风险 | 应对策略 |
|------|---------|
| [风险1] | [策略] |
```

---

## 决策矩阵（辅助多方案评估）

```markdown
| 方案 | 复用度(30%) | 架构合规(25%) | 多DB兼容(20%) | 开发量(25%) | 总分 |
|------|-------------|---------------|---------------|-------------|------|
| 方案A |      9      |       9       |      10       |      8      | 9.00 |
| 方案B |      6      |      10       |       8       |      9      | 8.25 |
| 方案C |     10      |       7       |       6       |      6      | 7.45 |

评分：1-10分，越高越好
- 复用度：复用现有 utils/模块/代码的程度
- 架构合规：是否符合三层架构规范
- 多DB兼容：跨 MySQL/PostgreSQL 的兼容性
- 开发量：工作量（分数越高 = 工作量越少）
```

> **用途**：矩阵仅用于辅助分析，最终方案由用户通过 `AskUserQuestion` 决定。

---

## 方案探索模板（含决策节点）

### 1. 问题定义

```markdown
## [功能名] 方案探索

### 基本信息
- **需求描述**：[具体要实现什么]
- **业务价值**：[解决什么问题]
- **当前状态**：[现有系统是否有类似功能]

### 项目约束（待确认）
- **模块归属**：module_admin / module_xxx（❓ 待用户确认）
- **数据库兼容**：只需 MySQL
- **是否需要 AI 能力**：是 / 否（❓ 待用户确认）
```

### 2. 可复用资源盘点

```markdown
### 可复用的工具
| 工具 | 是否可用 | 用途 |
|------|---------|------|
| ResponseUtil | ✅ | 统一响应格式 |
| PageUtil | ✅ | 分页查询 |
| ServiceException | ✅ | 业务异常 |
| @Log | ✅ | 操作日志 |
| ExcelUtil | ❓ | Excel 导出 |
| UploadUtil | ❓ | 文件上传 |

### 可参考的现有实现
| 功能 | 位置 | 借鉴点 |
|------|------|--------|
| 用户管理 | module_admin/controller/user_controller.py | 完整 CRUD 模式 |
| 字典管理 | module_admin/controller/dict_controller.py | 配置管理模式 |
| 定时任务 | module_admin/controller/job_controller.py | 任务管理模式 |
| AI 代理 | module_aiserver/controller/ | AI 集成模式 |
| PPT 生成 | module_admin/controller/ppt_controller.py | 文档生成模式 |
```

### 3. 方案对比（呈现给用户，待决策）

```markdown
### 方案 A：最大复用（优先评估）
- **核心思路**：基于现有模块/工具组合实现
- **复用**：[list 具体复用的内容]
- **新开发**：[只列必须新写的部分]
- **优点**：快、稳定、维护成本低
- **缺点**：[约束或局限]
- **开发量**：小

### 方案 B：适度扩展
- **核心思路**：在现有基础上扩展新功能点
- **复用**：[list]
- **新开发**：[list]
- **优点**：平衡复用与定制需求
- **缺点**：[约束或局限]
- **开发量**：中

### 方案 C（仅必要时）：全新开发
- **什么时候选这个**：A/B 方案都不能满足核心需求时
- **风险**：开发量大、经验积累少、维护成本高
- **开发量**：大

---
⚠️ **[决策节点]** 请通过 AskUserQuestion 询问用户选择哪个方案
```

### 4. 实施计划（用户决策后输出）

```markdown
**已选方案 [X]**，实施路径：

1. [ ] 数据库设计（`database-ops` Skill）
2. [ ] 三层代码开发（`crud-development` Skill）
3. [ ] 高级装饰器配置（`backend-annotations` Skill）
4. [ ] 接口文档同步（`api-doc-sync` Skill）
5. [ ] 代码规范检查（`/check`）
```

---

## 本项目典型场景速查

### 场景 1：新增业务管理模块

```
需求示例：新增"合同管理"功能

头脑风暴路径：
├── [决策点] 模块归属 → AskUserQuestion
│   ├── 选项A：挂靠 module_admin（减少新模块维护）
│   └── 选项B：新建 module_contract（职责清晰）✅ 通常推荐
│
├── 功能拆解（三层实现）
│   ├── contract_controller.py → APIRouter 路由
│   ├── contract_service.py    → 业务逻辑
│   ├── contract_dao.py        → SQLAlchemy 查询
│   ├── entity/do/contract_do.py  → SQLAlchemy Model
│   └── entity/vo/contract_vo.py + contract_bo.py → Pydantic 模型
│
├── 可复用
│   ├── module_admin/controller/user_controller.py → 完整 CRUD 模板
│   ├── ResponseUtil / PageUtil / ServiceException → 工具
│   ├── APScheduler → 合同到期提醒定时任务
│   └── ExcelUtil → 合同导出 Excel
│
├── [决策点] 实施范围 → AskUserQuestion
│   ├── 选项A：MVP（基础 CRUD）
│   └── 选项B：完整版（含导出、审批、提醒）
│
└── 关键决策
    ├── 表前缀：自定义（如 biz_contract）
    ├── API 路径：/contract/list、/contract/{id}
    └── 装饰器：@Log + @ValidateFields + CheckUserInterfaceAuth
```

### 场景 2：AI / 大模型功能集成

```
需求示例：实现 AI 智能问答或内容生成

头脑风暴路径：
├── 现有基础
│   ├── module_aiserver → 已有 OpenAI/Anthropic 协议转换
│   └── SSE（已集成）→ 流式响应直接可用
│
├── [决策点] 集成方式 → AskUserQuestion
│   ├── 选项A：扩展 module_aiserver（推荐，复用现有代理）
│   └── 选项B：在业务模块直接调用 AI API（AI 功能与业务深度绑定时）
│
├── [决策点] 历史消息存储 → AskUserQuestion
│   ├── 选项A：Redis 临时存储（会话期间）
│   └── 选项B：数据库持久化（需要会话表/消息表）
│
├── 技术选型
│   ├── 调用方式 → openai SDK（使用 openai-interaction Skill）
│   ├── 流式推送 → SSE（已集成）
│   ├── 上下文存储 → Redis（已集成）
│   └── 模型推荐 → DeepSeek（便宜）/ Claude API（能力强）
│
└── 需要新开发
    ├── 会话表 / 消息表（若选持久化）
    ├── AI 配置管理（已有 llm_config_controller.py）
    └── 敏感词过滤（可选）
```

### 场景 3：文档 / 文件生成（PPT、Excel、Word）

```
需求示例：根据数据生成 PPT 报告

头脑风暴路径：
├── 现有基础
│   ├── module_admin/controller/ppt_controller.py → 已有 PPT 生成接口
│   ├── Pillow（已集成）→ 图片处理
│   ├── openpyxl（已集成）→ Excel 生成
│   └── pandas（已集成）→ 数据处理
│
├── [决策点] 文件格式 → AskUserQuestion
│   ├── 选项A：Excel → 直接用 ExcelUtil（无需引入新库）✅
│   ├── 选项B：PPT → 需引入 python-pptx
│   └── 选项C：Word → 需引入 python-docx
│
├── [决策点] 生成方式 → AskUserQuestion
│   ├── 选项A：同步生成（文件小、简单）
│   └── 选项B：后台异步任务 + 进度推送（大文件，推荐）
│
└── 注意事项
    ├── 大文件生成放后台任务（APScheduler 异步 + SSE/WebSocket 进度推送）
    └── 生成结果缓存（Redis 存文件路径）
```

### 场景 4：实时通信 / 消息推送

```
需求示例：实现任务状态实时推送

头脑风暴路径：
├── [决策点] 通信方式 → AskUserQuestion
│   ├── 选项A：WebSocket（已集成）→ 双向通信（推荐：需要客户端主动发消息时）
│   ├── 选项B：SSE（已集成）→ 服务端单向推送（推荐：AI流式输出、通知推送）
│   └── 选项C：轮询 → 不推荐（浪费资源）
│
├── 消息类型决策
│   ├── 系统通知 → 广播（所有连接）
│   ├── 个人消息 → 点对点（特定用户 token）
│   └── AI 流式输出 → SSE（单向、天然适配）
│
└── 多实例同步
    └── Redis Pub/Sub → 跨实例消息同步（已有 Redis 集成）
```

### 场景 5：数据统计 / 报表

```
需求示例：业务数据汇总报表

头脑风暴路径：
├── [决策点] 数据量级与方案 → AskUserQuestion
│   ├── 选项A：< 50万行 → 实时查询（加好索引）
│   ├── 选项B：50万~500万 → 预计算 + Redis 缓存
│   └── 选项C：> 500万 → 考虑 ClickHouse 或预聚合表
│
├── 可复用
│   ├── pandas → 数据聚合计算（已集成）
│   ├── ExcelUtil → Excel 导出（已集成）
│   ├── APScheduler → 定时预计算（已集成）
│   └── Redis → 统计结果缓存
│
└── 多数据库兼容
    └── sqlglot → 自动转换 MySQL/PostgreSQL 聚合函数差异
```

### 场景 6：第三方服务集成

```
需求示例：接入物流查询 / 短信通知

头脑风暴路径：
├── HTTP 调用 → httpx（fastapi[all] 已含）
├── API 密钥存储 → sys_config 表 + pwd_util 加密
├── 结果缓存 → Redis（TTL 5-30分钟）
├── 失败处理 → ServiceException + logger.error
│
├── [决策点] 短信服务商 → AskUserQuestion（如涉及短信）
│   ├── 选项A：阿里云 SMS SDK（aliyun-python-sdk-dysmsapi）
│   └── 选项B：腾讯云 SMS SDK
│
└── 参考实现模式（来自项目内）
    └── module_admin/service/login_service.py → 第三方服务调用范式
```

---

## 创意激发技巧

### 1. 模块组合法

```
问题：如何实现活动签到功能？

已有模块组合：
├── Redis INCRBY → 签到计数/排行榜（原子操作）
├── @Log → 签到操作日志
├── APScheduler → 每日签到重置任务
├── WebSocket → 签到实时排名推送
└── ExcelUtil → 签到记录导出

结论：无需引入新技术，组合现有能力即可
→ [决策点] AskUserQuestion 确认此方案是否满足需求
```

### 2. 现有功能类比法

```
问题：如何实现申请审批功能？

类比分析：
├── 类似通知管理 → 消息创建/状态流转
├── 类似定时任务 → 状态机（待审/通过/拒绝）
└── 类似用户管理 → 操作日志记录

优化路径：复用通知/日志模式，扩展状态机
→ [决策点] AskUserQuestion 确认状态流转设计
```

### 3. AI 增强现有功能法

```
问题：如何在现有功能上叠加 AI 能力？

思路：
├── 现有功能（如报表）→ AI 自动分析生成总结
├── 现有搜索 → AI 自然语言查询转 SQL（sqlglot 辅助）
└── 现有审批 → AI 辅助决策建议

复用：module_aiserver 已有 AI 调用基础
→ [决策点] AskUserQuestion 确认 AI 能力集成深度
```

---

## 与其他 Skill 联动路径

```
brainstorm（确定方案后）
    │
    ├── 需要建表 / 数据库设计 → database-ops
    │
    ├── 需要后端 CRUD 开发 → crud-development
    │   └── 需要高级装饰器 → backend-annotations
    │
    ├── 需要 AI / LLM 集成 → openai-interaction
    │   └── 参考现有：module_aiserver/
    │
    ├── 需要定时任务 → scheduled-jobs
    │
    ├── 需要 WebSocket/SSE → websocket-sse
    │
    ├── 需要 Redis 缓存方案 → redis-cache
    │
    ├── 需要接口文档输出 → api-doc-sync
    │
    ├── 需要安全/权限设计 → security-guard
    │
    ├── 需要数据权限隔离 → data-permission
    │
    └── 需要技术选型对比 → tech-decision（brainstorm 内解决不了再用）
```

### 快速 Skill 跳转表

| 头脑风暴结论 | 下一步 | 触发方式 |
|-------------|--------|---------|
| 确定新建业务表 | `database-ops` | "帮我设计 xxx 表" |
| 确定做 CRUD 模块 | `crud-development` | "帮我开发 xxx 模块" |
| 确定集成 AI/LLM | `openai-interaction` | "帮我调用大模型接口" |
| 确定做定时任务 | `scheduled-jobs` | "帮我做一个定时任务" |
| 确定做消息推送 | `websocket-sse` | "帮我实现实时推送" |
| 确定需要权限控制 | `security-guard` | "怎么配置接口权限" |
| 确定需要数据缓存 | `redis-cache` | "怎么用 Redis 缓存" |

---

## 常见技术选择速查

| 问题 | 推荐 | 理由 |
|------|------|------|
| 新功能放哪个模块？ | 业务相关 → 新 module_xxx；系统相关 → module_admin | 职责清晰 |
| 实时推送用什么？ | WebSocket（双向） / SSE（AI流式/单向） | 都已集成 |
| 消息队列用什么？ | Redis Streams（已集成）优先，复杂再用 Celery | 够用不引入新依赖 |
| ORM 还是原生 SQL？ | SQLAlchemy 优先（已集成） | 保持一致性 |
| 多数据库兼容怎么做？ | sqlglot 转译 + SQL 脚本双版本 | 项目已有 sqlglot |
| 异步还是同步？ | 异步（async/await）| FastAPI 原生支持 |
| 日志怎么记录？ | loguru（已集成）+ @Log 装饰器 | 统一方式 |
| AI 模型怎么调用？ | openai SDK + module_aiserver 代理 | 已有基础 |
| 文件怎么存储？ | 本地存储（UploadUtil）| 当前方案；云存储需自行扩展 |
| 密码/密钥怎么存？ | passlib（已集成）/ pwd_util | 统一加密 |
| 数据处理/聚合？ | pandas（已集成）| 直接可用 |
| 图片处理？ | Pillow（已集成）| 直接可用 |
