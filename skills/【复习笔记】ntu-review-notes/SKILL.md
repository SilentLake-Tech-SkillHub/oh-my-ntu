---
name: ntu-review-notes
description: Produce source-backed NTU revision notes that explain weekly learning, develop knowledge themes across lectures, or analyse course code; rebuild shallow or misclassified revision materials. Tutorial solutions belong to the 03 pre-study collection.
---

# 04 复习笔记

新增或更新派生学习资料及入口时，读取[身份、修订与整批交付合同](../../references/delivery-contract.md)，保持对象名称及当前范围一致，移除被替代版本、只保留最新版并完成整批验收。规则修改或只读诊断不授权改动课程文件。

读取 [通用默认合同](../../references/defaults.md)。默认二级目录：`01_周度回顾复习笔记`、`02_分主题分析笔记`，以及有实际内容才建立的 `03_【如有】代码分析与复习笔记`。产物需能回到教师文件与页/Cell/题号；不同维度要有真实内容差异，不复制同一文件或用链接替身。

制作、刷新或修复周度笔记时，读取 [周度笔记的重建、教学与验收](references/weekly-notes.md)。默认交付一份完整 HTML，同页按 Week 分区并提供可跳转目录。各周须能独立学习，按结论、支持理由和例证展开；刷新须核对实际旧文件、来源增量、教学质量与全部入口，不能只加链接或纠错补记。个人速记、03 的逐页预习 Notebook、纯代码手册不能冒充周度成品。

制作或修复分主题笔记时，读取 [分主题组织、深度与验收](references/thematic-notes.md)。主题按学生需要理解和解决的知识问题组织，从本次已核实的课程来源推导主题树；不能把几篇阅读、一份全章总复习或一组速记卡当作主题覆盖。先核对主题树与来源覆盖，再写能够独立学习的解释、推导、案例和边界。主题数量、合并与拆分由课程内容决定，不套固定清单。

代码笔记仅在课程有代码时建立；若用户要求按某次考试切分但范围未确定，先从正式来源核对，仍不明时请用户确认；普通主题复习不因缺少考试范围而停工。逐段解释函数/方法、参数、返回、原地修改、执行条件、输出与常见错误；运行结果来自实际执行或明确标推导。

Tutorial 的原件副本、翻译、讲解与解答 Notebook 属课前预习，按 [03 Tutorial 合集规则](../【课件预习笔记】ntu-courseware-to-notebook/SKILL.md) 放在 03；04 不另建 Tutorial 单元，也不复制其讲解。复习笔记可以引用 Tutorial 题号或 Cell 作为来源，链接指向 01 正本或 03 讲解。

有运行输出和数字结论时，可用 [只读数字审计工具](../../scripts/audit_notebook_numbers.py) 对照保存的输出，再人工逐条核对；它不能执行代码或证明数字正确，不是无数据产物的必跑步骤。验收分别报告来源覆盖、教学内容和实际页面/Notebook 渲染；文件数、体积、标题齐全及链接通过均不能代替内容验收。用户要求重做时，把规则修复应用到其指出的成品，不能只改 Skill 后结束。
