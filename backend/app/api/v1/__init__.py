from fastapi import APIRouter

from app.api.v1 import auth, users, courses, chapters, knowledge_points, documents, resources, study_paths, qa, evaluations, system_configs, search, behaviors, chat, tasks, videos, profile_conversation, chapter_plans, dashboard

from app.api.v1 import learning_runs

v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(learning_runs.router, prefix="/learning-runs", tags=["Chapter learning loop"])
v1_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])

v1_router.include_router(auth.router, prefix="/auth", tags=["认证"])
v1_router.include_router(users.router, prefix="/users", tags=["用户"])
v1_router.include_router(courses.router, prefix="/courses", tags=["课程"])
v1_router.include_router(chapters.router, prefix="/chapters", tags=["章节"])
v1_router.include_router(knowledge_points.router, prefix="/knowledge-points", tags=["知识点"])
v1_router.include_router(documents.router, prefix="/documents", tags=["文档"])
v1_router.include_router(resources.router, prefix="/resources", tags=["学习资源"])
v1_router.include_router(study_paths.router, prefix="/study-paths", tags=["学习路径"])
v1_router.include_router(qa.router, prefix="/qa", tags=["智能辅导"])
v1_router.include_router(evaluations.router, prefix="/evaluations", tags=["学习评估"])
v1_router.include_router(system_configs.router, prefix="/settings", tags=["系统设置"])
v1_router.include_router(search.router, prefix="/search", tags=["知识检索"])
v1_router.include_router(behaviors.router, prefix="/behaviors", tags=["学习行为"])
v1_router.include_router(chat.router, prefix="/chat", tags=["对话Agent"])
v1_router.include_router(tasks.router, prefix="/tasks", tags=["学习任务"])
v1_router.include_router(videos.router, prefix="", tags=["视频生成"])
v1_router.include_router(profile_conversation.router, prefix="/profile-conversation", tags=["画像构建"])
v1_router.include_router(chapter_plans.router, prefix="/chapter-plans", tags=["章节学习计划"])
