---
name: ntu-course-workflow
description: Route NTU course-material tasks to the output-specific course skills for source files, assignments, pre-study notebooks and Tutorial collections, revision notes, quick references, recordings, exam briefings, and practice exams.
metadata:
  version: "1.0.1"
---

# NTU 课程材料工作流

**第一步是识别当前课程使用的学生平台及课程页，并按本次用户请求复查官方更新。** 从用户提供的链接、课程原件或已获授权的浏览器页面确认平台与课程身份；不能根据学校、课程代码或以往项目默认某个平台。每次处理课程任务，先在当前可访问的官方课程入口检查与本次请求相关的课件、Tutorial、配套 Notebook/数据、录播/字幕和公告是否新增或改版，按 Week／文件与本地实体逐项比对；旧清单的“当时尚未发布”不能当作今天的结论。发现新资料时，先按 01/06 的来源规则取得和验证原件，再以最新已核实范围制作用户要求的派生产物；不能把“页面已看到”写成“已下载”或“已完成”。同时查课程说明、第一份讲义及其课程日程／考核页（包括表格和嵌入图片）；若已取得该学期相关课堂字幕，同时检索字幕中的课程信息与教师说明，按课次和时间戳回查。字幕是补充来源，不替代正式公告；未取得字幕不阻断其他检索。不能因课程列表首屏未显示而断言该课不可访问，应先用平台搜索或筛选查找。以上只读核对后，识别用户要做的产物并读取相应子 SKILL。确实无法定位平台或课程入口时再向用户询问。若用户明确只要求处理已提供的离线材料，则按该范围执行并标明没有核对平台。七类默认目录与命名规则见 [默认合同](references/defaults.md)；用户当前 Prompt 的具体要求优先。不要把某门课的考试比例、时间、题目或配色推广为所有课程的规则。课程 SKILL 不负责 Codex 的 Plan、Memory、Hook 或流水治理。

| 请求的真实产物 | 读取 |
|---|---|
| 教师 PDF/PPT、Tutorial 原件及配套代码/数据的获取、核对、归位 | [01 原始课件](skills/【原始课件整理】ntu-source-courseware/SKILL.md) |
| 大作业要求、DDL、评分标准、提交模板 | [02 大作业初始化](skills/【大作业初始化】ntu-assignment-setup/SKILL.md) |
| 课前预习：教师课件逐页原图和可编辑中文解析 Notebook、同周离线 HTML 阅读版，以及 Tutorial 原件副本与翻译、讲解、解答合集 | [03 课件 Notebook](skills/【课件预习笔记】ntu-courseware-to-notebook/SKILL.md) |
| 周度、主题、代码复习 | [04 复习笔记](skills/【复习笔记】ntu-review-notes/SKILL.md) |
| 考前速记、术语对照、五分钟速览 | [05 速记术语](skills/【考前速记与术语】ntu-exam-quick-reference/SKILL.md) |
| 录播字幕、课堂讲解、课程日程、考试或 Presentation 信息与原通知 | [06 录播与课程信息](skills/【录播与课程信息】ntu-class-recordings/SKILL.md) |
| 录播视频下载（仅限 Media Gallery/Kaltura 开放流，须用户确认） | [06a 录播视频下载](skills/【录播视频下载】ntu-media-gallery-video-download/SKILL.md) |
| Media Gallery/Kaltura 自动字幕（WebVTT）获取（须用户确认） | [06b Media Gallery 字幕获取](skills/【自动字幕获取】ntu-media-gallery-captions/SKILL.md) |
| 某次 Quiz/Midterm/Final/Presentation 的考试信息汇报：时间地点座位、范围、题型、计分、重点（课堂小测/Tutorial/不考）、备考、原始内容对照，附截图的 HTML | [06c 考试信息汇报](skills/【考试信息汇报】ntu-exam-briefing/SKILL.md) |
| 周练、主题练习、Quiz/Final 模拟卷、Sample Quiz（含每堂课的课堂小测，一堂课一套） | [07 题库考试](skills/【练习题与模拟考】ntu-practice-assessments/SKILL.md) |

练习与模拟卷任务必须读取 07 的出题合同和[内容验收与旧成品刷新](skills/【练习题与模拟考】ntu-practice-assessments/references/content-acceptance.md)，先登记本次题型限制及图题覆盖，再逐题审核完整题面和源图。规则/生成器升级涉及已有成品时同时核对实际打开的旧文件。内容审核、浏览器验收和宿主收尾证据分别记录；只有结构或交互通过不能作为整套内容完成的结论。

官方 Sample Quiz 默认交付 07 的离线 HTML 作答页，保留题面配图、全部题目与选项，整套提交后展示答案及中英解析；Markdown 存档是来源记录，不能替代已要求的 HTML 成品。平台的得分／总分与题数分别核对，页面同时显示题数、单题分值和总分。附件必须完成浏览器下载或原生保存窗口，并确认本地目标文件可读后才登记“已取得”；具体核对见 01。

归属按用途，不按扩展名：Tutorial 属课前预习，其翻译、讲解与解答 Notebook 归 03，不归 04，并在 03 的 Tutorial 合集中放与 01 正本逐字节一致的原件副本；考试/Presentation 通知属 06，不是 01。任务跨域时仅加载实际涉及的子 SKILL，并使来源与派生产物各有一个实体归属（Tutorial 原件在 03 的核对副本是唯一例外），不制作快捷方式或符号链接替身。课程目录只交付用户需要的实体原件、成品及运行所必需资源；不要因执行本 Skill 在课程根目录新建 `流程管理` 等 Codex 治理目录，过程文件按[默认合同](references/defaults.md)放在课程目录和 SKILL 包之外的临时区，用户验收后清理。

涉及 Quiz／Final／Sample 或其考试范围时，同时读取 06 与 07；用户要的是考试信息汇总或汇报（而不是模拟题）时，改读 06 与 06c：先逐页查课程说明、首份讲义及课程时间表，再查已识别学生平台上的公告、考核页和相关模块，并检索已获取的当期课堂字幕；比较学期、日期、字幕课次与原文冲突，不能仅因本地没有范围文件或列表首屏未显示课程就停止查找。官方范围确实未提供时，才按 07 的分次考试兜底规则提出候选范围，须先取得用户确认。获取需登录内容前，说明 Computer Use 将查看的课程页面及只读边界；登录或 OTP 由用户完成。仍无法访问时，请用户提供对应课程链接、截图或范围，不把“未检查”写成“未发布”或“已确认没有”。不把可访问推断为已下载、已验收。网页或 Notebook 界面交付要做实际打开和可见性检查；若使用 Computer Use，向用户说明并在对话中给出结果截图。不编造事实或答案。处理中发现的同类缺口（例如只有原件没有讲解的 Tutorial 单元、未按默认合同分类的目录、指向旧路径的断链）属于本次任务范围，直接补齐并验证；技术风险（如生成器写死路径）先查清并一并修复，不作为停下的理由。只有需要用户做决定的事项（如章节与周的对应、有意改动的保留与否）才停下询问，并在询问前完成其余可独立推进的部分。
