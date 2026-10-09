---
name: ntu-practice-assessments
metadata:
  version: "1.0.1"
description: Create source-traceable NTU weekly and themed practice, Quiz/Final mock exams, and read-only Sample Quiz archives (platform samples plus one sample set per lecture built from the teacher's in-class quizzes) with gated answers and bilingual feedback.
---

# 07 题库与模拟考试

先读 [通用默认合同](../../references/defaults.md)，再读本技能的 [出题与验收细则](references/question-bank-contract.md) 和 [内容验收与旧成品刷新](references/content-acceptance.md)。默认目录：`01_周练习题`、`02_主题练习题`、`03_Quiz与Final模拟题`、`04_Sample与历史题目`。用户当前 Prompt 可调整结构、题量、语言和样式。

官方 Sample 的默认成品是 `04_Sample与历史题目/` 中可离线作答的 HTML；原题 Markdown、配图或来源索引保留为证据，不能作为 HTML 的替代。保留全部题目、选项与作答前必需的配图；题数、每题分值与总分分别标明，不把“得分/总分”读成题目数量。没有官方逐题答案时，交卷后的答案与解析注明本地推定，教师评分细则缺失时注明本地评分规则。

真实 Sample 与原创模拟题分开；Quiz/Final 可能有多次。老师在课上出的小测（Wooclap、Kahoot、投票等）也属于教师 Sample：每堂课的小测整理成一套 Sample Quiz，放在 `04_Sample与历史题目`，规则见[课堂小测样题](references/in-class-quiz-samples.md)。先按主 SKILL 确认课程使用的学生平台及课程页。出卷前逐次确认考试范围：先逐页检查课程说明、第一份讲义及课程时间表，包括图片中的表格；再主动只读查看该课程的公告、考核页与相关模块，并检索已获取的同学期课堂字幕，与本地官方原件核对学期和版本。记录 Quiz／Final 名称、范围原文、来源页面或 PDF 页码；若来自字幕，另记文件、课次、时间戳及查看时间。对时间表中“考试前讲过的章节”只作候选推断，不当作明示范围。出现日期或范围冲突时列明各来源，以本学期较新的官方说明和用户明确确认处理，不静默挑选。平台列表首屏找不到课程时先用搜索或筛选查找；确实无法定位课程或访问页面时，再主动向用户索取课程链接、截图或范围；不得把“尚未检查”“页面不可访问”“页面未见范围”混称为“范围未发布”。官方范围经查确实未提供时，按[出题与验收细则](references/question-bank-contract.md)提出分次考试候选范围，**在用户明确确认前不得按该范围组卷或标为官方范围**。范围确认后，再据教师材料逐点建蓝图、定位源 PDF/PPT 页或 Notebook Cell，生成考生可独立作答的题面；没有官方答案时写“课件证据支持的本地推定”，不冒充教师答案。模拟卷默认 A/B/C、每套 20 题/100 分；练习集按考点密度。所有题必须在完成整套并提交后才显示答案与中英解析，草稿和历史可恢复。每次题库登记 `requirements.allow_code`、`requirements.minimum_visual_questions`，逐题登记 `kind`、`requires_figure`。本次不生成代码题时设 `allow_code: false`，检查文字和图中的程序阅读、运行、补全与纠错；其他任务按其要求登记。需要图题时逐页挑选来源中的可考图表，按蓝图覆盖，不能用装饰图充数或默认填零。

离线答题页用 [build_practice_page.py](../../scripts/build_practice_page.py) 生成前，先用 [audit_practice_bank.py](../../scripts/audit_practice_bank.py) 生成未批准模板，逐题核对条件、选项、源图和答案，填写与实际内容指纹绑定的审核记录。修改题干、选项、图片或任务条件后重新审核。`prompt_image` 提交前显示，`image` 是提交后的答案证据；`points` 和 `answer_basis` 保留原用途。题库与过程证据放在课程目录和 SKILL 包之外的临时区。默认生成必须带通过的 `--review`；未审核的 `--draft` 页面有可见草稿提示且提交关闭。

生成后用 [verify_practice_page.py](../../scripts/verify_practice_page.py) 在 Chrome 检查真实作答流程和题图实际加载，再用 [check_practice_acceptance.py](../../scripts/check_practice_acceptance.py) 核对内容、实际 HTML 和浏览器记录的 Hash。规则升级时同时盘点本次旧成品；已知模板用 [refresh_practice_page.py](../../scripts/refresh_practice_page.py) 备份后最小更新，保留题量、分值、类型、评分与历史，未知变体停止写入并定位适配。每个受影响成品分别验收，不能仅更新 Skill 或拿一个样例代替整批。执行顺序、JSON 字段与宿主 Harness 的证据边界见 [内容验收说明](references/content-acceptance.md)。

交付前分别验证内容正确性、来源对应、评分与状态机、浏览器可见效果；扫描通过不等于人工读题通过。涉及页面时先说明 Computer Use 的测试目标和操作范围，并给用户实际截图。
