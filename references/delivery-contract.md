# 资料身份、可读名称与集合交付

适用于03–07派生资料及相关作业说明。教师原件、不同课次真实样题保留来源身份；同一用途／套卷／载体只交付当前一份，不建立旧版区、旧页跳转或兼容副本。规则修改、诊断或用户暂不处理文件时，仅在临时样例验证，不修改课程实体。

## 身份与显示分别设计

课程、学期、正式对象名称与范围从来源或用户确认确定，Quiz2不随意改称Final。`collection_id`、`subject.id`和可选`objects[].id`保持稳定；修订产物有新的`artifact_id`和递增`revision`。真正更名在原稳定id下记`rename_basis`。A/B/C是不同套卷，HTML/Notebook是不同载体，不能互当旧版。

`date`、`revision`、`review_state`、来源与范围用于追溯，不机械拼进文件名。用户看到的名称由身份内的`presentation`与用途生成：

`[阅读顺序_][必要上下文_]主题_用途[_套卷或区分项]_载体.扩展名`

- `presentation.topic`说明实际内容，不用`ch6`等内部代码代替；技术术语可保留，必要时附中文含义。
- `presentation.context`只放防止误认所需的课程、考试、范围或真实课次日期。目录已说明且不独立分发时可省略；分发、跨周汇总和不同课次同名材料需补足。
- `presentation.sequence`可省略；使用时是实际阅读顺序，不能假装版本号。
- `purpose`区分课件中英对照、代码讲解、教师答案、原创模拟等；`variant`中的A/B/C显示，“总册/总览”不机械重复。
- `presentation.carriers`可指定载体词，默认`.html`为阅读版、`.ipynb`为可编辑笔记、`.md`为文字说明；模拟卷HTML应指定作答页。其他格式先提供适配。

例如同一资料可命名为`01_生成式AI课件_逐页中英对照_阅读版.html`和`01_生成式AI课件_逐页中英对照_可编辑笔记.ipynb`；资源目录写`【勿删】生成式AI课件原图`。这是命名例子，不规定课程主题。用于确认能否看懂的标准是：脱离聊天上下文能否判断主题、用途、打开方式，以及必要时先读哪份；不能只检查字段齐全。普通文件列表截断了名称后半部分时，前部仍应传达主要内容。

`filename(identity, suffix)`与`title(identity)`从同一结构生成文件名和显示标题，二者允许承担不同信息量。页面标题不再强制重复日期与版本；审核状态和实际修订信息仍需在页内说明或Notebook元数据可查。未经用户确认保持审阅状态，不以文件名“final”冒充已验收。

## 关联不同载体与聚合资料

用集合的`objects`关联同一份资料的当前产物和资源；不要从修改时间、排序或相似文件名猜关系：

```json
{"id":"lesson-six","artifacts":["reader-v2","notebook-v2"],
 "resources":["03/Week06/【勿删】生成式AI课件原图/page1.png"]}
```

同一对象的载体默认共享topic/purpose/variant。必要时`shared_presentation:false`允许不同用途，但须填写`relation_basis`写清用途关系。一份总册来自多份Notebook时，用独立总册对象的`source_objects`引用成员对象；不强制一对一。对象图不能循环、缺成员或把同一产物归入两组。声明objects时须覆盖集合全部当前产物；明确取消对象用`removed_objects:[{id,reason}]`，不可静默丢掉。

## 更新与替换

1. 先在课程与Skill之外记录已有路径、实体指纹和已知入口，盘点包括旧件；不得只登记新生成文件。多目录／全课程请求另按[任务范围合同](task-delivery.md)建立独立请求范围快照。
2. 临时区准备新版，核对来源、正文、命名、关系与显示；事务旧字节只用于切换恢复。正文可保留，不等于名称、组织和入口免检。
3. 获得课程文件处理授权后替换正式文件及全部入口，移除被替代旧件和无引用的专属资源，共用资源和原件按真实依赖保留。失败恢复上次可用状态，不留下新旧混杂冒充完成。
4. 内容变更使用新修订id及递增revision；相同可读文件名可在安全切换时被当前实体替换，不为区分修订而强制把版本放进名字。旧作答不按新题目重新解释。
5. 成功切换和检查后清除事务旧字节，不建立长期历史成品库。集合检查、任务覆盖与用户内容验收分别报告。

## 集合schema与生成器

当前`check_course_delivery.py`使用`ntu-course-delivery-v3`。旧v2是旧证据，不能凭旧格式通过重新声称可读性合格；首次采用v3如实建立before元数据并按update迁移，不为升级自动改课程文件。

| 字段 | 用途 |
|---|---|
| collection_id、course、period | 稳定集合身份 |
| subject | `{id,label,provenance:{kind,reference,locator}}`；kind为official/classroom/user_confirmed；更名记rename_basis |
| scope | `{revision,label,basis}`；范围变化推进revision |
| operation、previous_sha256 | create或update；update绑定外部before清单 |
| inventory_roots、active_dirs | 这个集合实际核对的目录，不能据此推断整个用户任务范围 |
| required | 用途/套卷/扩展名完整列表，每组恰好一份当前产物 |
| artifacts | 当前实体的id、kind、path、sha256、status:current、identity；可用depends_on关联当前产物 |
| objects | 关联载体、资源与聚合关系；如上 |
| entrypoints | 所有本集合学习导航HTML，每个完整展示当前集合 |
| resources | `{path,sha256,reason}`；不得把学习页冒充资源 |
| exclusions | 无关来源或其他对象的真实路径与理由；不能排除旧版区逃避清理 |
| removed_families、removed_objects | 取消用途/对象的键或id及理由 |
| inventory_transitions、inventory_removals | 目录移动/清除的路径和理由，验收确认旧目录不再残留 |

identity示例（不同载体有各自artifact_id，presentation主体一致）：

```json
{
 "collection_id":"demo-term-lesson6","subject_id":"lesson6","artifact_id":"reader-v2",
 "course":"DEMO","subject_label":"第6周","purpose":"逐页中英对照","variant":"总册",
 "scope_revision":"scope2","scope_label":"本周课件","date":"20260102",
 "revision":"v2","review_state":"审阅版",
 "presentation":{"topic":"生成式AI课件","sequence":"01"}
}
```

HTML用唯一title/h1及`html_identity(identity)`；Notebook用`metadata.course_delivery`和首个一级标题；Markdown用`<!-- course-delivery-identity {JSON} -->`和一级标题。其他载体先有适配，不用文件存在替代验收。已验收版另需user_acceptance的reference和locator。

`build_practice_page.py`、`refresh_practice_page.py`从identity.presentation生成可读名称和标题。`build_course_reader.py --identity IDENTITY.json --output <生成的可读名> NOTEBOOK...`从完成的Notebook生成阅读版，保留原件页图和译文；`--diagnostic --title ...`仅用于未验收的临时预览。

practice还需practice_check的bank/review/verification，均为清单工作区内的相对路径、位于课程外。整批检查重新核对各卷实际题库与浏览器证据，不借用其他卷结果；题库身份及presentation也绑定题目审核指纹。

导航只有一个本集合当前区：`<section data-delivery-collection="..." data-delivery-status="current">`。同一对象的所有当前载体都在区内展示，不放旧版或历史区。工具检查完整入口和当前HTML，不只检查新插入片段。

## 审核与完成边界

```sh
python -B scripts/check_course_delivery.py work/delivery.json --root COURSE_DIR --previous work/before.json --review-template work/review.json --report work/pending.json
# 模板全为未批准；实际核对后填写具体依据。
python -B scripts/check_course_delivery.py work/delivery.json --root COURSE_DIR --previous work/before.json --review work/review.json --report work/collection.json
```

新建集合省略previous。review绑定清单及全部当前实体、完整导航指纹，记录reviewer，分别核对source_identity、scope_consistency、entry_clarity、usability、obsolete_removed。`usability`另按每个artifact id填写topic、purpose、open_with、first_action、evidence_locator；需要实际在其目录/阅读器里确认，不复制空泛理由或自动批量批准。数据、正文、标题或入口有变动即重新核对。

自动检查不能证明来源真实或人已理解资料。集合通过始终报告`acceptance_level:collection_only`、`task_coverage:not_checked_use_check_course_task`；多目录或全课程任务须继续[任务范围验收](task-delivery.md)。无断链、文件数量、某一单页通过或几份集合通过，均不能提升为整个请求已完成。07的page-only也只用于单页诊断。用户内容验收及宿主Hook是否执行另记，不能与工具通过合并。
