"""协调器 Agent - 意图识别 + 任务分发 (LangGraph StateGraph)"""

from __future__ import annotations

from typing import Any, Dict, Optional, TypedDict

from langgraph.graph import StateGraph, END
from loguru import logger


class IntentType:
    PROFILE = "profile"
    RESOURCE = "resource"
    PATH = "path"
    QA = "qa"
    EVAL = "eval"
    UNKNOWN = "unknown"


class AgentState(TypedDict):
    """LangGraph 状态"""
    user_id: int
    course_id: Optional[int]
    message: str
    intent: Optional[str]
    context: Dict[str, Any]
    result: Optional[Dict[str, Any]]
    error: Optional[str]


class CoordinatorAgent:
    """协调器 - 意图识别和任务分发"""

    def __init__(self):
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """构建 LangGraph 状态图"""
        graph = StateGraph(AgentState)

        # 添加节点
        graph.add_node("intent_classify", self._intent_classify)
        graph.add_node("profile", self._handle_profile)
        graph.add_node("resource", self._handle_resource)
        graph.add_node("path", self._handle_path)
        graph.add_node("qa", self._handle_qa)
        graph.add_node("eval", self._handle_eval)

        # 入口 → 意图分类
        graph.set_entry_point("intent_classify")

        # 意图分类 → 条件路由（根据意图分发）
        graph.add_conditional_edges(
            "intent_classify",
            self._route_by_intent,
            {
                "profile": "profile",
                "resource": "resource",
                "path": "path",
                "qa": "qa",
                "eval": "eval",
                "unknown": "qa",
            },
        )

        # 所有处理节点都连接到 END
        for node in ["profile", "resource", "path", "qa", "eval"]:
            graph.add_edge(node, END)

        return graph.compile()

    def _route_by_intent(self, state: AgentState) -> str:
        """根据意图返回路由键（返回字符串，LangGraph 用映射决定下一节点）"""
        return state.get("intent", "unknown")

    async def _intent_classify(self, state: AgentState) -> AgentState:
        """意图分类"""
        message = state.get("message", "").lower()
        intent = "unknown"

        if any(kw in message for kw in ["画像", "我的情况", "我的水平", "了解我"]):
            intent = "profile"
        elif any(kw in message for kw in ["生成资源", "讲义", "思维导图", "练习题", "代码案例", "拓展阅读", "学习资料", "生成"]):
            intent = "resource"
        elif any(kw in message for kw in ["学习路径", "学习计划", "先学什么", "计划"]):
            intent = "path"
        elif any(kw in message for kw in ["评估", "学习评估", "我的得分", "学习报告"]):
            intent = "eval"
        else:
            intent = "qa"

        state["intent"] = intent
        logger.info(f"意图识别: {intent}")
        return state

    async def _handle_profile(self, state: AgentState) -> AgentState:
        """处理画像意图"""
        from app.agents.profile_agent import ProfileAgent
        agent = ProfileAgent()
        state["result"] = await agent.process(state)
        return state

    async def _handle_resource(self, state: AgentState) -> AgentState:
        """处理资源生成意图"""
        state["result"] = {"type": "resource", "message": "资源生成功能将在 Phase 4 实现"}
        return state

    async def _handle_path(self, state: AgentState) -> AgentState:
        """处理路径规划意图"""
        state["result"] = {"type": "path", "message": "路径规划功能将在 Phase 4 实现"}
        return state

    async def _handle_qa(self, state: AgentState) -> AgentState:
        """处理问答意图"""
        from app.agents.qa_agent import QAAgent
        agent = QAAgent()
        state["result"] = await agent.process(state)
        return state

    async def _handle_eval(self, state: AgentState) -> AgentState:
        """处理评估意图"""
        state["result"] = {"type": "eval", "message": "评估功能将在 Phase 5 实现"}
        return state

    async def process(self, user_id: int, course_id: int | None, message: str) -> dict:
        """处理用户消息"""
        initial_state: AgentState = {
            "user_id": user_id,
            "course_id": course_id,
            "message": message,
            "intent": None,
            "context": {},
            "result": None,
            "error": None,
        }
        final_state = await self.graph.ainvoke(initial_state)
        return final_state.get("result", {"message": "处理完成"})


# 全局实例
coordinator = CoordinatorAgent()


async def get_coordinator() -> CoordinatorAgent:
    """获取协调器实例"""
    return coordinator
