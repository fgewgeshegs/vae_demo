系统设计方案（终版）
一、技术栈决策表
层次	技术选型	运行方式
基础设施	PostgreSQL 17 + pgvector + Redis 8	Docker Compose
后端	Python FastAPI + SQLAlchemy 2.0 async	宿主机 uvicorn 热更新
前端	React 19 + TypeScript + Vite + Ant Design 5 + Zustand	宿主机 npm run dev
多智能体	LangGraph	宿主机 Python
LLM 接入	多供应商抽象层（DeepSeek/GLM/Qwen/OpenAI）+ Mock 模式	宿主机 Python
向量检索	pgvector (PostgreSQL 内置)	Docker 内
文件存储	本地 uploads/ 目录	宿主机
二、启动方式
提供 start.bat（Windows）和 start.sh（Mac/Linux）：
步骤1: docker-compose up -d          # 启动 PostgreSQL + Redis（Docker 容器）
步骤2: 等待 3-5 秒数据库就绪
步骤3: uvicorn app.main:app --reload # 启动后端（宿主机）
步骤4: npm run dev                   # 启动前端（宿主机，或 npm run build 后由后端 serve）
Docker 只在第一步出现，一旦数据库跑起来，你后续开发完全不感知 Docker 存在。代码改了，uvicorn --reload 自动重启后端，Vite 自动热更新前端，开发体验丝滑。
三、多智能体协作框架
用户对话 → 前端 SSE → FastAPI → Coordinator（LangGraph 状态图）
                                  │
                    ┌─────────────┴─────────────┐
                    │    意图识别 + 任务分派       │
                    └─────────────┬─────────────┘
                                  │
        ┌───────────┬───────────┬─┴─┬───────────┬───────────┐
        ▼           ▼           ▼   ▼           ▼           ▼
   ProfileAgent ResourceAgent  PathAgent  QAAgent   EvalAgent
        │         Agent群         │          │           │
        │    ┌──┬──┬──┬──┬──┐    │          │           │
        │    │文│思│练│代│拓│    │          │           │
        │    │档│维│习│码│展│    │          │           │
        │    │生│导│题│示│阅│    │          │           │
        │    │成│图│目│例│读│    │          │           │
        │    └──┴──┴──┴──┴──┘    │          │           │
        ▼           ▼           ▼           ▼           ▼
    ┌─────────────────────────────────────────────────────┐
    │              学习策略引擎（贯穿所有 Agent）               │
    │  间隔重复 | 费曼学习法 | 主动回忆 | 交错练习 | 双重编码    │
    └─────────────────────────────────────────────────────┘
四、各 Agent 详细设计
ProfileAgent（画像构建Agent）
● 输入：用户自然语言对话（学习目标、专业背景、知识水平等）
● 处理：对话信息抽取 → 特征分类 → 6维度映射
● 输出：画像 JSON（知识基础、认知风格、学习目标、知识短板、学习节奏、兴趣方向、易错点）
● 约束：用户不可手动编辑画像维度，只能通过继续对话让 Agent 更新
● 更新机制：每次新对话触发增量更新，旧维度加权衰减
ResourceAgent群（6种子Agent并行协作）
● Coordinator 接收请求 → 并行派发到6个子Agent
● 每个子Agent 读取画像 + 对应知识点 + RAG 检索切片 → 生成内容
● DocumentAgent：生成课程讲义文档（结构化 Markdown）
● MindMapAgent：生成知识点思维导图（Mermaid 语法 → 渲染）
● ExerciseAgent：生成练习题（选择题/填空题/简答题/编程题）
● CodeAgent：生成代码实操案例（含注释和运行说明）
● ReadingAgent：生成拓展阅读材料（论文导读/延伸概念）
● VideoAgent：生成教学动画脚本（Manim 语法 → 渲染）
PathAgent（路径规划Agent）
● 输入：画像 + 课程知识图谱 + 学习者目标
● 策略引擎：综合考虑知识短板权重、学习节奏偏好、间隔重复时间点
● 输出：分步学习计划（先学什么 → 再学什么 → 什么时候复习）
● 动态调整：EvalAgent 反馈后自动修正路径
QAAgent（智能辅导Agent）
● RAG 检索知识库切片 → 结合画像个性化回答
● 支持多模态输出：文字解答 + 图解说明（Mermaid）+ 短视频脚本
● 费曼学习法集成：引导式追问，确认用户真正理解
EvalAgent（评估Agent）
● 数据源：学习进度、练习正确率、资源使用情况、停留时长
● 输出：雷达图（各维度得分）+ 改进建议 + 策略调整信号
● 反馈闭环：调整 PathAgent 的路径节奏和 ResourceAgent 的生成难度
五、数据库表设计
users                     # 用户认证
courses                   # 课程（支持多门，但种子为《人工智能导论》）
chapters                  # 章节（含排序）
knowledge_points          # 知识点（含前置依赖关系）
documents                 # 上传的教材/文档
document_chunks           # 文档切片，含 pgvector 向量
student_profiles          # 学生画像（6+维度，JSONB）
learning_resources        # Agent生成的6类资源
study_paths               # 学习路径（节点数组 + 进度）
qa_records                # 问答记录（含引用的资源ID）
learning_behaviors        # 学习行为日志（时间戳 + 动作类型）
evaluations               # 评估报告（各维度得分 + 建议）
system_configs            # 运行时配置（API Key 等，支持热替换）
六、前端页面
页面	路由	说明
登录注册	/login	JWT 认证
学习仪表盘	/dashboard	课程概览、进度、待办、系统状态
对话画像	/profile	对话构建画像 + 可视化面板（雷达图）
学习路径	/path	路径时间线 + 节点状态 + 资源直达
资源中心	/resources	6类资源分类浏览 + 预览
智能辅导	/qa	对话式问答 + 图文/视频答案
学习评估	/evaluation	评估雷达图 + 历史曲线 + 改进建议
课程管理	/courses	课程卡片 + 章节树 + 文档上传
知识检索	/search	课程语义搜索 + 切片引用展示
系统设置	/settings	API Key / 模型切换（热生效）
七、项目目录结构
ai-learning-platform/
├── docker-compose.yml          # PostgreSQL 17 + pgvector + Redis
├── start.bat / start.sh        # 一键启动脚本
├── init.sql                    # 初始化数据库 + pgvector 扩展
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── database.py     # SQLAlchemy 2.0 async
│   │   │   ├── llm_gateway.py  # 多供应商LLM + Mock
│   │   │   └── security.py     # JWT
│   │   ├── models/             # 12张表 SQLAlchemy models
│   │   ├── schemas/            # Pydantic
│   │   ├── api/v1/             # 10个路由模块
│   │   ├── agents/             # LangGraph 智能体
│   │   │   ├── coordinator.py  # 协调器（意图路由）
│   │   │   ├── profile_agent.py
│   │   │   ├── resource_agent/ # 6个子Agent
│   │   │   ├── path_agent.py
│   │   │   ├── qa_agent.py
│   │   │   └── eval_agent.py
│   │   ├── services/           # 业务服务
│   │   │   ├── document_parser.py
│   │   │   ├── chunker.py
│   │   │   ├── embedder.py
│   │   │   ├── vector_store.py
│   │   │   ├── retriever.py
│   │   │   └── learning_strategies.py
│   │   └── prompts/            # Agent 提示词模板
│   ├── knowledge_base/         # 种子课程入库脚本
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── pages/              # 10个页面
│   │   ├── components/         # 通用组件
│   │   ├── services/api.ts
│   │   ├── store/              # Zustand
│   │   └── types/
│   ├── package.json
│   └── vite.config.ts
│
└── 开源工具清单.md
八、分阶段实施路径
Phase	内容	预计产出
Phase 1	Docker 环境 + FastAPI 骨架 + React 骨架 + 数据库模型 + 基础API（用户/课程/文档CRUD）+ 登录页面	可启动项目
Phase 2	文档解析管线（PDF/DOCX/PPTX/MD）→ 切片 → Embedding → pgvector 存储 → RAG 检索	知识库就绪
Phase 3	ProfileAgent（对话画像构建 + 6维度更新）+ 画像可视化页面 + Coordinator 编排	核心画像完成
Phase 4	ResourceAgent群（6种子Agent并行）+ PathAgent（路径规划）+ 学习策略引擎	核心学习功能
Phase 5	QAAgent（智能辅导）+ EvalAgent（学习评估）+ 费曼/主动回忆策略集成	完整系统
Phase 6	UI打磨 + 种子课程知识库填充 + 演示数据 + Docker评审 + 文档整理	可参赛交付
九、已做关键决策（实施者无需再决策）
● 数据库：PostgreSQL 17 + pgvector，Docker 运行
● 缓存：Redis 8，Docker 运行
● 后端：FastAPI + SQLAlchemy 2.0 async，宿主机 uvicorn --reload
● 前端：React 19 + TypeScript + Vite + Ant Design 5 + Zustand，宿主机 npm run dev
● 多智能体框架：LangGraph
● LLM：多供应商抽象层（DeepSeek/GLM/Qwen/OpenAI）+ Mock 模式优先开发
● 种子课程：《人工智能导论》，支持上传1-N本教材 PDF
● 画像构建：纯对话自动抽取，用户不可手动编辑
● 画像维度：知识基础、认知风格、学习目标、知识短板、学习节奏、兴趣方向、易错点
● 学习策略：间隔重复、费曼学习法、主动回忆、交错练习、双重编码、精细加工
● 启动方式：start.bat / start.sh 一键脚本（Docker infra + 原生 app）
● 开源工具：所有工具在 开源工具清单.md 标注名称/来源/协议