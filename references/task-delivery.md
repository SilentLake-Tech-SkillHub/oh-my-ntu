# 用户请求范围与完成判定

本合同解决“若干集合通过，但用户指定的目录仍漏检”的问题。用户要求多目录、每个文件夹、全课程或跨用途刷新时使用；单页诊断或仅修改Skill时不扩大到课程实体。通用工具不推断自然语言请求，执行者必须据当前用户消息如实记录范围和检查维度。

## 独立建立范围

在课程与Skill之外保存request.json：

```json
{
 "reference":"用户本次请求原文或可核对引用",
 "locator":"当前会话对应消息",
 "requested_roots":["课程甲","课程乙"],
 "required_dimensions":["content","naming_organization","file_integrity","display"]
}
```

路径相对CLI的root，`.`表示该root本身。目录取自用户授权范围，不从将要生成的文件列表或集合inventory_roots反推。维度只选本次确实要求的方面；例如纯改名可只要求命名组织与文件完整性，但不能据此汇报正文也已重做。显式记录scope不是追加授权，不扩大来源访问、训练、提交、日历或其他操作。

处理前运行：

```sh
python -B scripts/check_course_task.py --snapshot --request work/request.json --root WORKSPACE --report work/before.json
```

工具独立遍历所有请求目录，绑定请求SHA、真实路径和文件指纹；小文件用SHA256，大文件用大小/修改时间并在结果中单列，不能冒称媒体内容哈希。默认不跟随符号链接，不用目录级排除跳过相关生成件。取得快照后不能缩小request来迎合部分集合；真正变更须有新的用户范围依据与明确重新盘点。

## 每个文件都有处置

任务清单task.json使用`ntu-course-task-v1`，包含request、before（相对于清单工作区的路径）、before_sha256与records。每项有稳定记录id、role、action、reason，以及适用的before_path/path。当前实体记录fingerprint，与snapshot产生的格式相同。

- action：keep_verified、refresh、replace、remove、blocked。保留不是免检；rename用replace并记录旧新路径；移除项只保留before_path。
- role：derived、entrypoint、source、resource、auxiliary。source需source_basis；变更原件另需source_update_basis。resource需used_by指向实际当前消费者。系统元数据可说明为auxiliary；学习HTML/Markdown/Notebook不可伪装resource或auxiliary。
- 当前新文件无before_path；旧文件移除无path；同一路径不能被多项重复认领。快照所有旧文件与当前磁盘所有新文件都必须被覆盖，没有记录就是漏项，不能凭人工汇总数补齐。
- 明确不适用的质量维度需要逐项理由；来源不足或尚未检查记录blocked/not_checked，不能写成通过。教师原件保护与派生件可用性分别核对。

需要集合级身份/范围/题库验收时，在collections列出对应manifest/root/review/previous，工具重新调用集合验收器；集合清单位于工作区内，root相对总root。它们补充内容与格式证据，但不定义或缩小请求覆盖范围。

## 分维度审核，按最弱项判完成

```sh
python -B scripts/check_course_task.py work/task.json --root WORKSPACE --review-template work/task-review.json --report work/pending.json
# 模板按每条处置记录、每个维度标not_checked，不能自动批准。
python -B scripts/check_course_task.py work/task.json --root WORKSPACE --review work/task-review.json --report work/task-acceptance.json
```

审核绑定任务清单SHA和已绑定的当前文件指纹，记录reviewer。每个请求维度填写status、note、evidence_locator：

| 维度 | 审核应回答 |
|---|---|
| content | 来源是否对应，正文机制/算例是否正确，旧范围和状态是否失效；保留的内容据何复核 |
| naming_organization | 脱离聊天能否判断主题、用途、打开方式与必要顺序；配对、聚合、目录与唯一当前版是否清楚 |
| file_integrity | 当前文件/来源指纹、依赖、链接、用户原有单元与输出是否受保护；旧件是否实际移除 |
| display | 在实际使用载体打开后，文字、图片、表格/公式和必要交互是否可见可用；静态预览不能冒充Notebook原生渲染 |

派生件和入口的适用维度不能用not_applicable略过；原件、资源和已移除项可说明具体不适用原因。passed需具体证据定位；未检查、失败、blocked或缺记录，任务整体不得通过。脚本检验记录/指纹/状态的完整一致性，无法替代真实阅读或用户验收。

完成报告分别列请求覆盖、内容、命名组织、文件完整性、显示和用户验收，明确哪些维度未被本次要求。不要把“6个集合通过”“零断链”“删除若干文件”当作所有文件夹完成。只完成部分时，报告已完成范围与实际漏项，不让用户靠截图发现未处理目录。

本工具只写指定的外部元数据、审核模板和报告，不修改资料，不安装全局Hook或更新Memory。Skill本身更新时，在临时合成目录测试命名、配对与漏目录等行为；不能因此重做课程正文。

## 维护规则的回归验证

在有`markdown-it-py`的Python环境运行`python -B -m unittest discover -s scripts/tests -v`。测试使用临时合成文件，覆盖可读配对、实际集合通过但漏03、保留正文却未审命名、聚合多Notebook、旧件残留和只读边界；不把测试中的审核占位记录当作真实课程验收。生成器或输出结构变化时，再以合成产物实际打开验证必要显示与交互，报告为合成回归，不能借此声称课程Notebook或题库已经重新验收。
