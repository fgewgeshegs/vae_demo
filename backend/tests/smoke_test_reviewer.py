"""Quick smoke test for ResourceReviewer — runs without heavy app imports."""
import importlib.util
import sys
import json

spec = importlib.util.spec_from_file_location(
    "resource_reviewer",
    "app/agents/resource_agent/resource_reviewer.py",
)
mod = importlib.util.module_from_spec(spec)
sys.modules["resource_reviewer"] = mod
spec.loader.exec_module(mod)

ResourceReviewer = mod.ResourceReviewer
ReviewResult = mod.ReviewResult

reviewer = ResourceReviewer()
passed = 0
failed = 0

def check(label, resource_type, content, expect_status, expect_min_score=None):
    global passed, failed
    result = reviewer.review(resource_type, content)
    ok = result.status == expect_status
    if expect_min_score is not None:
        ok = ok and result.score >= expect_min_score
    if ok:
        passed += 1
        print(f"  PASS: {label} -> status={result.status}, score={result.score}")
    else:
        failed += 1
        print(f"  FAIL: {label} -> status={result.status}, score={result.score}, issues={result.issues}")

print("=== Empty content ===")
check("None content", "document", None, "needs_review")
check("Empty string", "mindmap", "", "needs_review")
check("Whitespace only", "code", "   \n  ", "needs_review")

print("\n=== Mindmap ===")
check("Mermaid fence", "mindmap", "```mermaid\ngraph TD\nA-->B\n```", "passed", 1.0)
check("Graph keyword", "mindmap", "graph LR\n  Root --> Child", "passed")
check("Mindmap keyword", "mindmap", "mindmap\n  Root\n    分支", "passed")
check("Flowchart", "mindmap", "flowchart TD\n  Start --> End", "passed")
check("No mermaid syntax", "mindmap", "普通文本没有mermaid语法", "needs_review")

print("\n=== Exercise ===")
check("答案 marker", "exercise", "题目：1+1=?\n答案：2", "passed", 1.0)
check("解析 marker", "exercise", "题目：什么是闭包？\n解析：闭包是指...", "passed")
check("参考答案", "exercise", "1. 问题\n参考答案：详见下文", "passed")
check("No answer markers", "exercise", "题目1\n题目2\n题目3", "needs_review")

print("\n=== Code ===")
check("Code fence", "code", "```python\ndef hello():\n    pass\n```", "passed", 1.0)
check("Python def", "code", "def calculate(a, b):\n    return a + b", "passed")
check("Import statement", "code", "import os\nfrom pathlib import Path", "passed")
check("JS function", "code", "function greet(name) {\n  return `Hi ${name}`;\n}", "passed")
check("No code markers", "code", "这是一段代码说明但没有实际代码", "needs_review")

print("\n=== Document ===")
check("Substantive text", "document", "# 标题\n\n" + "这是一段足够长的文本内容用于测试文档审查功能。\n" * 5, "passed", 1.0)
check("Too short", "document", "短", "needs_review")

print("\n=== Reading ===")
check("Substantive text", "reading", "# 拓展阅读\n\n" + "这是一段足够长的拓展阅读文本内容用于测试阅读审查功能需要至少二十个字符。\n" * 5, "passed", 1.0)
check("Too short", "reading", "短", "needs_review")

print("\n=== Video ===")
valid_video = {
    "mode": "video_like_slides",
    "title": "测试微课",
    "duration_seconds": 180,
    "slides": [{
        "start": 0, "end": 30,
        "title": "学习目标",
        "bullets": ["要点1：事实", "要点2：解释", "要点3：例子", "要点4：易错点"],
        "core_question": "问题？",
        "key_points": ["k1", "k2", "k3"],
        "case_detail": "这是一个足够长的案例详情描述，用于通过视频质量校验。这里包含具体的教材案例背景、风险分析和详细说明，确保内容充实且具有教学价值。",
        "misconception": "误解",
        "self_check": "自测",
        "caption": "字幕文本六十到一百字的内容描述在这里",
        "teacher_script": "教师讲解稿一百二十到一百八十字的内容要像课堂讲解一样自然流畅地进行说明。",
        "examples": ["例子1", "例子2"],
        "interaction_question": "互动",
        "visual": {"type": "concept", "keywords": ["k1", "k2", "k3", "k4"]},
    }],
}
check("Valid video JSON", "video", json.dumps(valid_video, ensure_ascii=False), "passed", 1.0)
check("Invalid JSON", "video", "not json", "needs_review")
check("Wrong mode", "video", json.dumps({"mode": "text", "slides": []}), "needs_review")
check("Empty slides", "video", json.dumps({"mode": "video_like_slides", "slides": []}), "needs_review")

bad_video = {
    "mode": "video_like_slides",
    "slides": [{
        "start": 0, "end": 30,
        "title": "标题",
        "bullets": ["标题", "标题", "标题", "标题"],
        "core_question": "q",
        "key_points": ["k1"],
        "case_detail": "短",
        "misconception": "",
        "self_check": "",
        "caption": "字幕",
        "teacher_script": "这一页围绕标题展开讲解。",
        "examples": [],
        "interaction_question": "",
        "visual": {"type": "concept", "keywords": []},
    }],
}
check("Quality issues", "video", json.dumps(bad_video), "needs_review")

print("\n=== Unknown type ===")
check("Unknown type", "unknown_xyz", "content", "needs_review")

print(f"\n=== Results: {passed} passed, {failed} failed ===")
if failed > 0:
    sys.exit(1)
