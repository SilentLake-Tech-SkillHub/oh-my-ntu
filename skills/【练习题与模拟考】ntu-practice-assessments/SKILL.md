---
name: ntu-practice-assessments
description: Create source-traceable NTU weekly and themed practice, Quiz/Final mock exams, and read-only Sample Quiz archives with gated answers and bilingual feedback.
---

# 07 题库与模拟考试

先读 [通用默认合同](../../references/defaults.md)，再读本技能的 [出题与验收细则](references/question-bank-contract.md)。默认目录：`01_周练习题`、`02_主题练习题`、`03_Quiz与Final模拟题`、`04_Sample与历史题目`。用户当前 Prompt 可调整结构、题量、语言和样式。

真实 Sample 与原创模拟题分开；Quiz/Final 可能有多次。先按主 SKILL 确认课程使用的学生平台及课程页。出卷前逐次确认考试范围：先逐页检查课程说明、第一份讲义及课程时间表，包括图片中的表格；再主动只读查看该课程的公告、考核页与相关模块，并检索已获取的同学期课堂字幕，与本地官方原件核对学期和版本。记录 Quiz／Final 名称、范围原文、来源页面或 PDF 页码；若来自字幕，另记文件、课次、时间戳及查看时间。对时间表中“考试前讲过的章节”只作候选推断，不当作明示范围。出现日期或范围冲突时列明各来源，以本学期较新的官方说明和用户明确确认处理，不静默挑选。平台列表首屏找不到课程时先用搜索或筛选查找；确实无法定位课程或访问页面时，再主动向用户索取课程链接、截图或范围；不得把“尚未检查”“页面不可访问”“页面未见范围”混称为“范围未发布”。官方范围经查确实未提供时，按[出题与验收细则](references/question-bank-contract.md)提出分次考试候选范围，**在用户明确确认前不得按该范围组卷或标为官方范围**。范围确认后，再据教师材料逐点建蓝图、定位源 PDF/PPT 页或 Notebook Cell，生成考生可独立作答的题面；没有官方答案时写“课件证据支持的本地推定”，不冒充教师答案。模拟卷默认 A/B/C、每套 20 题/100 分；练习集按考点密度。所有题必须在完成整套并提交后才显示答案与中英解析，草稿和历史可恢复。离线答题页可用 [build_practice_page.py](../../scripts/build_practice_page.py) 从 JSON 题库生成；题库是课程数据，放在课程目录和 SKILL 包之外的临时区。生成后用 [verify_practice_page.py](../../scripts/verify_practice_page.py) 在 Chrome 中检查空白卷、草稿恢复、提交门禁、双语反馈、重置与手机宽度；脚本通过不替代人工读题。

交付前分别验证内容正确性、来源对应、评分与状态机、浏览器可见效果；扫描通过不等于人工读题通过。涉及页面时先说明 Computer Use 的测试目标和操作范围，并给用户实际截图。
