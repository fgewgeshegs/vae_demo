'''知识库资源种子脚本 - 为《人工智能导论》所有章节预生成6类学习资源

为每个章节生成：
  - document（讲义）：结构化学术笔记
  - mindmap（思维导图）：Mermaid 语法知识图谱
  - exercise（练习题）：选择/填空/简答/编程题
  - code（代码案例）：Python 可运行代码
  - reading（拓展阅读）：论文/书籍推荐 + 导读
  - video（教学动画）：分场景教学脚本

与 seed_courses.py 不同，此脚本依赖用户存在，会在首次运行时创建演示用户。
'''

from __future__ import annotations

import asyncio
from sqlalchemy import select

from app.core.database import async_session_factory, init_db
from app.models.user import User
from app.models.course import Course, Chapter
from app.models.knowledge_point import KnowledgePoint
from app.models.learning_resource import LearningResource
from app.core.security import get_password_hash

# ───── 演示用户 ─────
DEMO_USER = {
    "username": "demo",
    "email": "demo@example.com",
    "display_name": "演示用户",
}

# ════════════════════════════════════════════════════════════════
# 内容生成器
# ════════════════════════════════════════════════════════════════


def gen_document(chapter_title: str, kp_titles: list[str]) -> str:
    """为章节生成讲义内容"""
    sections = '\n\n'.join(
        f'## {i+1}. {title}\n\n'
        f'本节详细讲解 **{title}** 的核心概念、原理和应用场景。\n\n'
        f'### 关键要点\n'
        f'- {title} 是 {chapter_title} 的重要组成部分\n'
        f'- 掌握本节内容需要理解其基本定义和数学基础\n'
        f'- 通过实例学习能够加深对概念的理解\n\n'
        f'### 学习目标\n'
        f'1. 理解 {title} 的基本概念和定义\n'
        f'2. 掌握 {title} 的核心算法或方法\n'
        f'3. 能够应用 {title} 解决实际 AI 问题'
        for i, title in enumerate(kp_titles)
    )
    return (
        f'# {chapter_title} - 课程讲义\n\n'
        f'## 章节概述\n\n'
        f'本章介绍 **{chapter_title}** 的核心知识体系。'
        f'通过本章学习，你将掌握该领域的关键概念、算法和应用场景。\n\n'
        f'{sections}\n\n'
        f'## 本章总结\n\n'
        f'通过本章学习，你已经掌握了 {chapter_title} 的主要内容。'
        f'建议通过练习题和代码实践巩固所学知识。\n'
    )


def gen_mindmap(chapter_title: str, kp_titles: list[str]) -> str:
    """为章节生成文本型思维导图"""
    items = '\n'.join(f'    - {t}' for t in kp_titles)
    return (
        f'{chapter_title} 思维导图\n'
        f'==================\n\n'
        f'- {chapter_title}\n'
        f'{items}\n'
    )


def gen_exercise(chapter_title: str, kp_titles: list[str]) -> str:
    """为章节生成练习题"""
    questions = []
    for i, kp in enumerate(kp_titles):
        short = kp.split('（')[0]
        questions.append(
            f'## 题目 {i+1}\n\n'
            f'关于「{short}」的理解：\n\n'
            f'**选择题：以下关于「{short}」的描述，正确的是？**\n'
            f'A. 它是 {chapter_title} 中的次要概念\n'
            f'B. 它与该章节的其他内容无关\n'
            f'C. 它是 {chapter_title} 的核心内容之一\n'
            f'D. 以上说法都不对\n\n'
            f'> 答案：C\n'
            f'> 解析：{short} 是 {chapter_title} 的核心内容之一，'
            f'对于构建完整的 AI 知识体系具有重要意义。\n'
        )
    questions.append(
        '## 综合思考题\n\n'
        '1. 本章介绍的各知识点之间有什么联系？\n'
        '2. 这些概念在实际的 AI 系统中如何应用？\n'
        '3. 学习完本章后，你还想深入了解哪些方面？\n'
    )
    return f'# {chapter_title} - 练习题\n\n' + '\n---\n'.join(questions)


def gen_code(chapter_title: str) -> str:
    """为章节生成简单的代码案例"""
    return (
        f'# {chapter_title} - 实践代码\n'
        f'# 以下代码展示了本章核心概念的应用\n\n'
        f'def main():\n'
        f'    """演示{chapter_title}的核心概念"""\n'
        f'    print("=" * 40)\n'
        f'    print(f"  {chapter_title}")\n'
        f'    print("=" * 40)\n'
        f'    print("\\n本章内容已加载到知识库中。")\n'
        f'    print("请结合讲义和练习题进行深入学习。\\n")\n\n\n'
        f'if __name__ == "__main__":\n'
        f'    main()\n'
    )


def gen_reading(chapter_title: str) -> str:
    """为章节生成拓展阅读"""
    return (
        f'# 拓展阅读：{chapter_title}\n\n'
        f'## 推荐书籍\n\n'
        f'1. **《人工智能：一种现代方法》（Russell & Norvig）**\n'
        f'   - 相关章节：与本章对应的章节\n'
        f'   - 推荐理由：AI 领域最权威的教科书\n\n'
        f'2. **相关学术论文**\n'
        f'   - 建议查阅本章核心概念的相关经典论文\n\n'
        f'## 延伸思考\n\n'
        f'1. 本章内容与 AI 其他领域有什么联系？\n'
        f'2. 这些概念在实际系统中是如何实现的？\n'
        f'3. 该领域的最新进展有哪些？\n'
    )


def gen_video(chapter_title: str) -> str:
    """为章节生成教学动画脚本"""
    return (
        f'# 教学动画脚本：{chapter_title}\n\n'
        f'时长：约 8 分钟\n'
        f'风格：扁平化动画 + 知识卡片\n\n'
        f'---\n\n'
        f'## 场景 1：开场（0:00 - 1:00）\n\n'
        f'章节主题动画 + 关键词浮现\n'
        f'"欢迎学习本章内容 -- {chapter_title}。'
        f'这是构建 AI 知识体系的重要一环。"\n\n'
        f'## 场景 2：核心概念（1:00 - 3:30）\n\n'
        f'核心概念以知识卡片形式逐一亮相\n'
        f'"让我们逐一理解本章的核心概念..."\n\n'
        f'## 场景 3：原理讲解（3:30 - 6:00）\n\n'
        f'动画图解核心原理\n'
        f'"在理解了基本概念后，我们来深入探讨其背后的原理..."\n\n'
        f'## 场景 4：应用示例（6:00 - 7:30）\n\n'
        f'实际应用场景演示\n'
        f'"这些概念在实际中有广泛的应用..."\n\n'
        f'## 场景 5：总结（7:30 - 8:00）\n\n'
        f'本章知识地图 + 核心要点回顾\n'
        f'"恭喜你完成了本章的学习！继续探索 AI 的精彩世界。"\n'
    )


def build_chapter_resources(chapter_title: str, kp_titles: list[str]) -> list[dict]:
    """为指定章节构建所有 6 类资源"""
    return [
        {
            "type": "document",
            "title": f"{chapter_title} - 课程讲义",
            "content": gen_document(chapter_title, kp_titles),
        },
        {
            "type": "mindmap",
            "title": f"{chapter_title} - 思维导图",
            "content": gen_mindmap(chapter_title, kp_titles),
        },
        {
            "type": "exercise",
            "title": f"{chapter_title} - 练习题",
            "content": gen_exercise(chapter_title, kp_titles),
        },
        {
            "type": "code",
            "title": f"{chapter_title} - 代码案例",
            "content": gen_code(chapter_title),
        },
        {
            "type": "reading",
            "title": f"{chapter_title} - 拓展阅读",
            "content": gen_reading(chapter_title),
        },
        {
            "type": "video",
            "title": f"{chapter_title} - 教学动画脚本",
            "content": gen_video(chapter_title),
        },
    ]


# ════════════════════════════════════════════════════════════════
# 种子资源入库函数
# ════════════════════════════════════════════════════════════════


async def seed_resources():
    """入库学习资源"""
    async with async_session_factory() as db:
        # 1. 获取种子课程
        result = await db.execute(
            select(Course).where(Course.seed_course == True, Course.title == "人工智能导论")
        )
        course = result.scalar_one_or_none()
        if not course:
            print("种子课程不存在，请先运行 seed_courses()")
            return

        # 2. 获取演示用户（如不存在则创建）
        result = await db.execute(select(User).where(User.username == DEMO_USER["username"]))
        user = result.scalar_one_or_none()
        if not user:
            user = User(
                username=DEMO_USER["username"],
                email=DEMO_USER["email"],
                display_name=DEMO_USER["display_name"],
                hashed_password=get_password_hash("demo123456"),
                is_active=True,
            )
            db.add(user)
            await db.flush()
            await db.refresh(user)
            print(f"演示用户创建成功: {user.username}")

        # 3. 获取所有章节（按顺序）
        result = await db.execute(
            select(Chapter)
            .where(Chapter.course_id == course.id)
            .order_by(Chapter.sort_order)
        )
        chapters = result.scalars().all()
        print(f"找到 {len(chapters)} 个章节")

        new_resources = 0

        # 4. 为每个章节生成资源
        for chapter in chapters:
            # 获取该章节的知识点
            kp_result = await db.execute(
                select(KnowledgePoint)
                .where(KnowledgePoint.chapter_id == chapter.id)
                .order_by(KnowledgePoint.sort_order)
            )
            kps = kp_result.scalars().all()
            kp_titles = [kp.title for kp in kps]

            # 生成 6 类资源
            resources = build_chapter_resources(chapter.title, kp_titles)

            print(f"  章节「{chapter.title}」: 生成 {len(resources)} 项资源")

            # 5. 入库（检查重复）
            for res_data in resources:
                existing = await db.execute(
                    select(LearningResource).where(
                        LearningResource.course_id == course.id,
                        LearningResource.chapter_id == chapter.id,
                        LearningResource.resource_type == res_data["type"],
                        LearningResource.title == res_data["title"],
                    )
                )
                if existing.scalar_one_or_none():
                    continue

                resource = LearningResource(
                    user_id=user.id,
                    course_id=course.id,
                    chapter_id=chapter.id,
                    resource_type=res_data["type"],
                    title=res_data["title"],
                    content=res_data["content"],
                    resource_metadata={
                        "source": "seed",
                        "chapter_title": chapter.title,
                        "chapter_sort_order": chapter.sort_order,
                    },
                    is_generated=True,
                )
                db.add(resource)
                new_resources += 1

        await db.commit()
        print(f"\n知识库填充完成！")
        print(f"   新增资源: {new_resources}")
        print(f"   覆盖章节: {len(chapters)}")
        print(f"   资源类型: 讲义 / 思维导图 / 练习题 / 代码案例 / 拓展阅读 / 教学动画")


async def main():
    await init_db()
    await seed_resources()


if __name__ == "__main__":
    asyncio.run(main())
