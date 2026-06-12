"""种子课程《人工智能导论》入库脚本"""

from __future__ import annotations

import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory, init_db
from app.models.course import Course, Chapter
from app.models.knowledge_point import KnowledgePoint

SEED_COURSE = {
    "title": "人工智能导论",
    "description": "本课程系统介绍人工智能的基本概念、方法和技术，包括搜索、知识表示、机器学习、深度学习、自然语言处理、计算机视觉等核心领域，为学习者构建完整的 AI 知识体系。",
    "seed_course": True,
    "chapters": [
        {
            "title": "人工智能概述",
            "description": "AI 的定义、发展历史、主要流派与应用领域",
            "sort_order": 1,
            "knowledge_points": [
                {"title": "AI 的定义与目标", "difficulty": "easy", "sort_order": 1},
                {"title": "AI 发展简史", "difficulty": "easy", "sort_order": 2},
                {"title": "AI 主要流派（符号主义/连接主义/行为主义）", "difficulty": "medium", "sort_order": 3},
                {"title": "AI 应用领域概览", "difficulty": "easy", "sort_order": 4},
                {"title": "AI 伦理与安全", "difficulty": "medium", "sort_order": 5},
            ],
        },
        {
            "title": "搜索与问题求解",
            "description": "经典搜索算法、启发式搜索、对抗搜索",
            "sort_order": 2,
            "knowledge_points": [
                {"title": "问题形式化与搜索空间", "difficulty": "medium", "sort_order": 1},
                {"title": "无信息搜索（BFS/DFS/迭代加深）", "difficulty": "medium", "sort_order": 2},
                {"title": "启发式搜索（A* 算法）", "difficulty": "hard", "sort_order": 3},
                {"title": "对抗搜索与博弈（Minimax/Alpha-Beta 剪枝）", "difficulty": "hard", "sort_order": 4},
                {"title": "约束满足问题", "difficulty": "medium", "sort_order": 5},
            ],
        },
        {
            "title": "知识表示与推理",
            "description": "逻辑表示、语义网络、本体、不确定性推理",
            "sort_order": 3,
            "knowledge_points": [
                {"title": "命题逻辑与谓词逻辑", "difficulty": "medium", "sort_order": 1},
                {"title": "语义网络与框架表示", "difficulty": "medium", "sort_order": 2},
                {"title": "本体论与知识图谱", "difficulty": "hard", "sort_order": 3},
                {"title": "不确定性推理（贝叶斯网络）", "difficulty": "hard", "sort_order": 4},
                {"title": "模糊逻辑与证据理论", "difficulty": "hard", "sort_order": 5},
            ],
        },
        {
            "title": "机器学习基础",
            "description": "监督学习、无监督学习、半监督学习、强化学习基本概念",
            "sort_order": 4,
            "knowledge_points": [
                {"title": "机器学习基本概念（训练/验证/测试）", "difficulty": "easy", "sort_order": 1},
                {"title": "线性回归与逻辑回归", "difficulty": "medium", "sort_order": 2},
                {"title": "决策树与随机森林", "difficulty": "medium", "sort_order": 3},
                {"title": "支持向量机（SVM）", "difficulty": "hard", "sort_order": 4},
                {"title": "K-Means 聚类与层次聚类", "difficulty": "medium", "sort_order": 5},
                {"title": "PCA 降维与特征选择", "difficulty": "hard", "sort_order": 6},
                {"title": "过拟合与正则化", "difficulty": "medium", "sort_order": 7},
            ],
        },
        {
            "title": "深度学习",
            "description": "神经网络基础、CNN、RNN、Transformer、生成模型",
            "sort_order": 5,
            "knowledge_points": [
                {"title": "神经元与感知机", "difficulty": "medium", "sort_order": 1},
                {"title": "反向传播与梯度下降", "difficulty": "hard", "sort_order": 2},
                {"title": "卷积神经网络（CNN）", "difficulty": "hard", "sort_order": 3},
                {"title": "循环神经网络（RNN/LSTM）", "difficulty": "hard", "sort_order": 4},
                {"title": "注意力机制与 Transformer", "difficulty": "hard", "sort_order": 5},
                {"title": "生成对抗网络（GAN）", "difficulty": "hard", "sort_order": 6},
                {"title": "自编码器与变分自编码器（VAE）", "difficulty": "hard", "sort_order": 7},
            ],
        },
        {
            "title": "自然语言处理",
            "description": "词表示、序列标注、文本生成、大语言模型",
            "sort_order": 6,
            "knowledge_points": [
                {"title": "词袋模型与 TF-IDF", "difficulty": "easy", "sort_order": 1},
                {"title": "词嵌入（Word2Vec/GloVe）", "difficulty": "medium", "sort_order": 2},
                {"title": "序列标注（NER/POS）", "difficulty": "medium", "sort_order": 3},
                {"title": "机器翻译与 Seq2Seq", "difficulty": "hard", "sort_order": 4},
                {"title": "大语言模型（GPT/BERT）", "difficulty": "medium", "sort_order": 5},
                {"title": "Prompt Engineering", "difficulty": "medium", "sort_order": 6},
                {"title": "RAG 与智能体系统", "difficulty": "hard", "sort_order": 7},
            ],
        },
        {
            "title": "计算机视觉",
            "description": "图像分类、目标检测、图像分割、多模态",
            "sort_order": 7,
            "knowledge_points": [
                {"title": "图像表示与预处理", "difficulty": "easy", "sort_order": 1},
                {"title": "图像分类（AlexNet/VGG/ResNet）", "difficulty": "medium", "sort_order": 2},
                {"title": "目标检测（YOLO/Faster R-CNN）", "difficulty": "hard", "sort_order": 3},
                {"title": "图像分割（U-Net/Mask R-CNN）", "difficulty": "hard", "sort_order": 4},
                {"title": "多模态学习（CLIP）", "difficulty": "hard", "sort_order": 5},
            ],
        },
        {
            "title": "强化学习",
            "description": "MDP、Q-Learning、策略梯度、深度强化学习",
            "sort_order": 8,
            "knowledge_points": [
                {"title": "马尔可夫决策过程（MDP）", "difficulty": "hard", "sort_order": 1},
                {"title": "动态规划与值迭代", "difficulty": "hard", "sort_order": 2},
                {"title": "Q-Learning 与 DQN", "difficulty": "hard", "sort_order": 3},
                {"title": "策略梯度方法", "difficulty": "hard", "sort_order": 4},
                {"title": "Actor-Critic 方法", "difficulty": "hard", "sort_order": 5},
            ],
        },
        {
            "title": "AI 系统与工程实践",
            "description": "MLOps、模型部署、AI 系统架构",
            "sort_order": 9,
            "knowledge_points": [
                {"title": "机器学习流水线", "difficulty": "medium", "sort_order": 1},
                {"title": "模型评估与调优", "difficulty": "medium", "sort_order": 2},
                {"title": "模型部署与服务化", "difficulty": "medium", "sort_order": 3},
                {"title": "AI 系统架构设计", "difficulty": "hard", "sort_order": 4},
                {"title": "AI 项目实战案例", "difficulty": "hard", "sort_order": 5},
            ],
        },
    ],
}


async def seed_course():
    """入库种子课程"""
    async with async_session_factory() as db:
        # 检查是否已存在
        result = await db.execute(
            select(Course).where(Course.seed_course == True, Course.title == SEED_COURSE["title"])
        )
        if result.scalar_one_or_none():
            print(f"种子课程《{SEED_COURSE['title']}》已存在，跳过")
            return

        # 创建课程
        course = Course(
            title=SEED_COURSE["title"],
            description=SEED_COURSE["description"],
            seed_course=True,
        )
        db.add(course)
        await db.flush()

        # 创建章节和知识点
        for ch_data in SEED_COURSE["chapters"]:
            chapter = Chapter(
                course_id=course.id,
                title=ch_data["title"],
                description=ch_data.get("description", ""),
                sort_order=ch_data["sort_order"],
            )
            db.add(chapter)
            await db.flush()

            # 创建知识点
            for kp_data in ch_data.get("knowledge_points", []):
                kp = KnowledgePoint(
                    chapter_id=chapter.id,
                    title=kp_data["title"],
                    difficulty=kp_data.get("difficulty", "medium"),
                    sort_order=kp_data.get("sort_order", 0),
                )
                db.add(kp)

        await db.commit()
        print(f"种子课程《{SEED_COURSE['title']}》入库成功")


async def main():
    await init_db()
    await seed_course()


if __name__ == "__main__":
    asyncio.run(main())
