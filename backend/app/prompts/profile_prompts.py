"""Prompts for learner profile extraction."""

PROFILE_EXTRACTION_PROMPT = """你是学习者画像分析专家。从用户消息中提取学习画像信息，要求覆盖以下6+个维度。

当前画像：
{current_profile}

用户消息：
{message}

## 画像维度定义

1. **knowledge_base（知识基础）**
   - level: beginner | intermediate | advanced（根据用户描述推断）
   - subjects: 熟悉或学习过的学科/技术领域列表
   - foundation_score: 基础评分 0-100（根据描述推断，50=一般，80+=扎实）

2. **cognitive_style（认知风格）**
   - preference: visual（看图表）| auditory（听讲解）| reading（读文字）| kinesthetic（动手做）| mixed（混合）
   - description: 具体的学习偏好描述
   - processing_speed: slow | normal | fast（理解新概念的速度）

3. **learning_goals（学习目标）**
   - short_term: 近期想达成的目标
   - long_term: 长期职业/学业目标
   - milestones: 具体的里程碑节点列表

4. **learning_pace（学习节奏）**
   - speed: slow | normal | fast
   - preferred_session_minutes: 单次学习时长偏好（数字）
   - consistency: regular（规律）| irregular（不规律）| sporadic（偶尔）

5. **interest_direction（兴趣方向）**
   - areas: 感兴趣的领域/话题列表
   - engagement_level: low | medium | high（参与热情程度）

6. **weak_points + knowledge_gaps（薄弱环节与知识漏洞）**
   - weak_points: 易错点、常犯错误
   - knowledge_gaps: 缺失的知识点、不熟悉的概念

7. **learning_habits（学习习惯）** — 如有信息
   - preferred_time: morning | afternoon | evening | night | flexible
   - review_frequency: daily | weekly | rarely | never
   - note_taking_style: detailed（详细）| brief（简略）| visual（图解）| none

8. **motivation_factors（激励因素）** — 如有信息
   - intrinsic: 内在动力列表（如好奇心、成就感）
   - extrinsic: 外在动力列表（如薪资、证书）
   - reward_preference: verbal | tangible | achievement | social

## 推断规则

即使用户没有明确说明，你也可以根据语境合理推断：
- "我是xx专业" → knowledge_base.subjects, knowledge_base.level
- "喜欢/想学/对xx感兴趣" → interest_direction.areas
- "不太懂/不会/薄弱" → knowledge_gaps, weak_points
- "零基础/刚开始" → knowledge_base.level=beginner
- "学了xx年/比较熟悉" → knowledge_base.level=intermediate 或 advanced
- "看视频/看图/读文档/做项目" → cognitive_style.preference
- "每天/每周/偶尔" → learning_pace.consistency
- "目标是/想要/希望" → learning_goals
- "考试/面试/工作" → learning_goals + motivation_factors

## 输出要求

1. 只输出 JSON，不要任何解释、Markdown 或代码块。
2. 只写有证据支持的字段，不要凭空捏造。
3. 空字符串、unknown、暂无、未设置、无、没有不要写入 updates。
4. 枚举值必须用英文小写。

## 输出格式

{{
  "updates": {{
    "knowledge_base": {{
      "level": "beginner|intermediate|advanced",
      "subjects": ["学科或技术"],
      "foundation_score": 60
    }},
    "cognitive_style": {{
      "preference": "visual|auditory|reading|kinesthetic|mixed",
      "description": "证据化描述",
      "processing_speed": "slow|normal|fast"
    }},
    "learning_goals": {{
      "short_term": "短期目标",
      "long_term": "长期目标",
      "milestones": ["里程碑"]
    }},
    "learning_pace": {{
      "speed": "slow|normal|fast",
      "preferred_session_minutes": 30,
      "consistency": "regular|irregular|sporadic"
    }},
    "interest_direction": {{
      "areas": ["兴趣领域"],
      "engagement_level": "low|medium|high"
    }},
    "knowledge_gaps": ["缺失的知识点"],
    "weak_points": ["易错点"],
    "learning_habits": {{
      "preferred_time": "morning|afternoon|evening|night|flexible",
      "review_frequency": "daily|weekly|rarely|never",
      "note_taking_style": "detailed|brief|visual|none"
    }},
    "motivation_factors": {{
      "intrinsic": ["内在动力"],
      "extrinsic": ["外在动力"],
      "reward_preference": "verbal|tangible|achievement|social"
    }}
  }},
  "evidence": [
    {{
      "field": "维度.字段",
      "quote": "用户原话中的证据",
      "confidence": 0.0到1.0
    }}
  ],
  "insufficient_evidence": ["没有足够证据的字段名"]
}}

如果用户消息没有任何可提取的信息：
{{
  "updates": {{}},
  "evidence": [],
  "insufficient_evidence": [
    "knowledge_base.subjects",
    "interest_direction.areas",
    "cognitive_style.preference",
    "learning_goals.short_term",
    "weak_points"
  ]
}}
"""


PROFILE_UPDATE_PROMPT = """请根据当前画像和新对话进行证据化增量更新。

当前画像：
{current_profile}

新对话：
{message}
"""
