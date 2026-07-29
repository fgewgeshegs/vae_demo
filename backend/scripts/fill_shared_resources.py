"""Fill shared course resources without calling the LLM.

This script is for local bootstrapping when course resources must already exist
in the database. It creates or repairs one shared resource set owned by user 1.
"""

from __future__ import annotations

import asyncio
from typing import Any

from sqlalchemy import select

from app.core.database import async_session_factory
from app.models.course import Chapter, Course
from app.models.knowledge_point import KnowledgePoint
from app.models.learning_resource import LearningResource


SHARED_RESOURCE_USER_ID = 1
RESOURCE_TYPES = ["document", "mindmap", "exercise", "code", "reading", "video"]
TYPE_LABELS = {
    "document": "讲义",
    "mindmap": "思维导图",
    "exercise": "练习题",
    "code": "代码案例",
    "reading": "拓展阅读",
    "video": "教学脚本",
}


def base_content(kp: KnowledgePoint) -> str:
    return (
        kp.content
        or f"{kp.title} 是本课程中的一个核心知识点。学习时需要先理解基本概念，再结合例子进行练习。"
    ).strip()


def make_content(resource_type: str, kp: KnowledgePoint) -> str:
    title = kp.title
    intro = base_content(kp)

    if resource_type == "document":
        return f"""# {title} 学习讲义

## 学习目标
- 理解 {title} 的基本含义和应用场景。
- 能够用自己的话解释核心概念。
- 能够结合课程案例完成基础练习。

## 核心内容
{intro}

## 学习建议
1. 先阅读概念说明，标出不理解的关键词。
2. 再结合课程示例复述一遍知识点。
3. 最后完成配套练习，检查是否真正掌握。
"""

    if resource_type == "mindmap":
        return f"""```mermaid
mindmap
  root(({title}))
    核心概念
      定义
      关键术语
      基本原理
    学习重点
      适用场景
      常见方法
      易错点
    实践应用
      案例分析
      练习巩固
      总结复盘
```

说明：围绕“概念-重点-应用”三层结构学习 {title}。
"""

    if resource_type == "exercise":
        return f"""# {title} 练习题

## 选择题
1. 关于 {title}，下列说法最合理的是哪一项？
A. 只需要记住名称即可
B. 需要理解概念、场景和使用方法
C. 与课程其他内容没有关系
D. 只能通过代码学习

参考答案：B
解析：该知识点需要放在课程体系中理解，不能只记忆表面定义。

## 简答题
1. 请用 3-5 句话解释 {title} 的核心含义。
2. 请举一个你认为适合使用 {title} 的场景。

## 反思题
学习完该知识点后，请写出一个仍然不清楚的问题，便于后续问答或复习。
"""

    if resource_type == "code":
        return f"""# {title} 代码案例

```python
# 这是一个用于学习“{title}”的示意代码框架。
# 你可以把课程中的具体算法或模型步骤补充到对应函数中。

def explain_concept():
    concept = "{title}"
    return f"当前学习知识点：{{concept}}"


def run_demo():
    print(explain_concept())
    print("步骤1：明确输入和目标")
    print("步骤2：选择合适的方法或模型")
    print("步骤3：观察输出并进行解释")


if __name__ == "__main__":
    run_demo()
```

使用建议：先运行框架，再把课程中的具体公式、算法步骤或案例填进去。
"""

    if resource_type == "reading":
        return f"""# {title} 拓展阅读

## 阅读方向
- {title} 的基本定义和发展背景。
- {title} 在人工智能系统中的典型应用。
- 与前后知识点之间的联系。

## 阅读提示
{intro}

## 阅读后检查
1. 我能否说清楚这个知识点解决什么问题？
2. 我能否举出一个现实应用例子？
3. 我能否指出它和上一章/下一章内容的联系？
"""

    if resource_type == "video":
        return f"""# {title} 教学脚本

## 开场
今天学习 {title}。先说明它解决什么问题，再看一个简单例子，最后总结常见误区。

## 讲解流程
1. 用一句话解释 {title}。
2. 展示课程中的核心定义或示意图。
3. 通过一个生活化或工程化案例说明用途。
4. 给出一个小练习，要求学生复述或判断。

## 结尾
请学生回答：{title} 的核心作用是什么？它适合用在哪类问题中？
"""

    return intro


def should_repair(resource: LearningResource) -> bool:
    text = f"{resource.title or ''}\n{resource.content or ''}"
    return "生成失败" in text or not resource.content


def metadata_for(kp: KnowledgePoint, resource_type: str, existing: dict[str, Any] | None = None) -> dict[str, Any]:
    metadata = dict(existing or {})
    metadata.update(
        {
            "knowledge_point": kp.title,
            "knowledge_point_id": kp.id,
            "shared_resource": True,
            "local_bootstrap": True,
            "resource_type": resource_type,
        }
    )
    return metadata


async def main() -> None:
    created = 0
    repaired = 0
    async with async_session_factory() as db:
        courses = (
            await db.execute(
                select(Course)
                .where(Course.is_active == True)
                .order_by(Course.id)
            )
        ).scalars().all()

        for course in courses:
            chapters = (
                await db.execute(
                    select(Chapter)
                    .where(Chapter.course_id == course.id)
                    .order_by(Chapter.sort_order)
                )
            ).scalars().all()

            for chapter in chapters:
                kps = (
                    await db.execute(
                        select(KnowledgePoint)
                        .where(KnowledgePoint.chapter_id == chapter.id)
                        .order_by(KnowledgePoint.sort_order)
                    )
                ).scalars().all()

                for kp in kps:
                    existing = (
                        await db.execute(
                            select(LearningResource).where(
                                LearningResource.user_id == SHARED_RESOURCE_USER_ID,
                                LearningResource.course_id == course.id,
                                LearningResource.chapter_id == chapter.id,
                                LearningResource.knowledge_point_id == kp.id,
                            )
                        )
                    ).scalars().all()
                    by_type = {resource.resource_type: resource for resource in existing}

                    for resource_type in RESOURCE_TYPES:
                        resource = by_type.get(resource_type)
                        title = f"{kp.title} - {TYPE_LABELS[resource_type]}"
                        content = make_content(resource_type, kp)
                        if resource is None:
                            db.add(
                                LearningResource(
                                    user_id=SHARED_RESOURCE_USER_ID,
                                    course_id=course.id,
                                    chapter_id=chapter.id,
                                    knowledge_point_id=kp.id,
                                    resource_type=resource_type,
                                    title=title,
                                    content=content,
                                    resource_metadata=metadata_for(kp, resource_type),
                                    is_generated=True,
                                )
                            )
                            created += 1
                        elif should_repair(resource):
                            resource.title = title
                            resource.content = content
                            resource.resource_metadata = metadata_for(
                                kp,
                                resource_type,
                                resource.resource_metadata,
                            )
                            repaired += 1

        await db.commit()

    print(
        {
            "created": created,
            "repaired": repaired,
            "shared_resource_user_id": SHARED_RESOURCE_USER_ID,
        }
    )


if __name__ == "__main__":
    asyncio.run(main())
