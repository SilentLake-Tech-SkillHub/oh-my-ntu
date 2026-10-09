# 内容审核、旧成品刷新与完成证据

## 每次任务先登记条件

必须读出题合同，再把用户本次要求写入题库。`requirements.allow_code` 是布尔值；禁止代码题时为 `false`，包括程序阅读、输出判断、补全和纠错，以及图片中的代码。公式计算、概念和图表分析可以保留。其他任务可以设为 `true`，不得把一次限制变成所有课程的永久规则。

`requirements.minimum_visual_questions` 是本卷需要的读图题最低数量。根据用户要求、源 PDF/PPT 中可考的图表和出题蓝图确定，不能默认填零绕过图题要求。没有相关要求且来源不适合图题时可为零，蓝图注明理由。对可用的源图，先登记文件、页码、局部范围、图中数据及可考概念，再制作情景题；用源图局部或据原数据重构，禁止无关占位图。图必须提供作答所需信息；去掉图仍可回答的装饰不计入读图题覆盖。

每题声明 `kind`（`concept`、`analysis`、`calculation` 或 `code`）和布尔值 `requires_figure`。图题设为 `true`，使用 `prompt_image` 与描述性 `prompt_image_caption`；题库还需现有题干、选项/填空答案、双语解析、来源、知识点和分值。答案证据 `image` 在提交后显示，不计入提交前的图题。官方原题若与本次题型限制冲突，保留原件，说明冲突并确认派生练习范围，不静默删除或改写官方题目。

## 内容审核分为两部分

自动检查发现可确定的缺口：课堂自指、必要图缺失、图题数量不足、未声明题型、本次禁止的代码特征、无效图片格式等。扫描能发现部分表述问题，不能判断所有自然语言条件、选项和正确答案。

逐题读题必须由审核者实际完成：只看考生题面和图，是否有足够的条件得出唯一单选答案、完整多选集合或合理填空答案；单位、坐标、数据、假设和必要定义是否明确；每个选项为什么对或错；题图是否清晰、提供必要信息且不标出答案；是否含本次禁止的代码内容；答案与来源页码是否对应。阅读课堂记录的经历不能充当题目条件。来源留在提交后解析，题干必须能独立作答。

脚本生成未批准的审核模板，所有确认项默认未通过。审核者逐题填写条件说明、来源核对、答案及干扰项理由，有图时另填图的必要性、可读性和无答案泄漏说明。不要为了得到绿灯批量填 `true` 或复制空泛理由。脚本只能核对记录完整、确认项和指纹，不能证明这些说明真实；真正内容验收仍需读题。

审核记录包含审核者、整套内容 SHA256 和逐题 SHA256。题干、选项、答案、图片字节、说明或任务条件改变，旧记录失效。图片路径先解析为内嵌字节，换图但不改文件名也会触发失效。

## 执行顺序与退出码

以下使用占位文件名；题库、审核记录、截图和成品运行证据放在 Skill 包之外的本次临时区。合成样例也不能混入用户课程目录。

```sh
python scripts/audit_practice_bank.py bank.json --review-template review.json --report content-pending.json
# 模板默认未通过，第一步返回 1 是预期结果。实际逐题审核后填写 review.json。
python scripts/audit_practice_bank.py bank.json --review review.json --report content.json
python scripts/build_practice_page.py bank.json paper.html --review review.json
python scripts/verify_practice_page.py paper.html --bank bank.json --review review.json --evidence evidence
python scripts/check_practice_acceptance.py bank.json paper.html --review review.json --verification evidence/verification.json --report acceptance.json
```

内容检查及最终检查只在通过时返回 0；失败返回 1。生成器默认要求内容审核通过；`--draft` 仅允许通过客观检查的未验收预览，页面显示草稿说明且提交关闭。生成成功仍是“内容已审核、浏览器待验证”。旧题库缺少条件/审核记录时补登记并读题，不能绕过为完整交付。

浏览器工具需要 Python Playwright 和 Chrome，可用 `--browser-executable` 指定已安装的浏览器。它打开临时隔离的浏览器存储，检查空白卷、草稿刷新、完整作答门禁、提交后双语反馈、满分评分、重置历史、手机布局，逐张确认提交前题图和提交后证据图实际解码，并拦截外部请求。记录绑定 HTML 字节 SHA256、题库内容 SHA256、渲染器版本、题数、分值和图片数量。失败会先失效旧记录；改过 HTML 后必须重新打开验收。向用户展示实际截图。

## 刷新已经交付的旧文件

更新规则或生成器后，盘点本次涉及的既有 HTML、来源题库、图资源和实际打开入口。不能只更新脚本就把旧页面称为已刷新。逐文件备份，记录旧 Hash；以有明确来源、完成新审核的题库刷新，保持题数、每题分值、作答类型、评分方式和历史。内容变化用新版本，旧尝试不作为新内容的作答恢复，历史成绩仍保留。

```sh
python scripts/refresh_practice_page.py old-paper.html --bank bank.json --review review.json --backup backups/old-paper.html --report refresh.json
# 刷新后仍需上述浏览器验证和最终 acceptance.json。
```

该工具只支持包含 JSON 常量题库、已知题干渲染位置和单行评分函数的模板：最小替换题库、加入题面图及验收元数据，并验证评分函数和历史键不变。新备份不能覆盖已有文件。未知动态题库、评分函数或页面结构会失败且不写原文件；定位变体后另做有证据的适配，不能猜测覆盖。刷新报告的 `refreshed_pending_browser` 表示文件已更新，尚未完成页面验收。对工具支持的页面，也必须核对新题面、每个选项和图，再验证评分与历史的实际表现。

## 与 Harness 收尾衔接

最终 `check_practice_acceptance.py` 从源题库重新审核，读取成品实际数据，并核对浏览器记录及字节 Hash，输出 `scope: content_review_and_browser_acceptance`。任务完成记录须引用报告及对应的成品 Hash；内容检查、浏览器检查、实际生效副本分别列证据，任一缺失时不可写整体完成。

若宿主项目已注册验证/收尾 Hook，可调用该 CLI 并要求退出码为 0，核对报告里的范围与当前文件。该 Skill 不安装或改写全局 Hook/Memory 配置。没有宿主运行时就显式运行 CLI、记录实际证据，并注明没有执行宿主 Hook；报告的 `harness_runtime: not_executed_by_this_tool` 正是这个边界，不能据此声称 Hook 通过。若用户要求修复多个成品，逐文件完成检查，不能用一张样例卷的证据覆盖整批。
