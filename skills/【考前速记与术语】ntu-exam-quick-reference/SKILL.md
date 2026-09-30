---
name: ntu-exam-quick-reference
description: Build source-linked NTU exam quick-reference HTML, English-Chinese terminology pages, and short overviews without confusing them with full revision notes.
---

# 05 考前速记与术语

读取 [通用默认合同](../../references/defaults.md)。默认结构：`01_速记手册/data/`、`02_中英术语对照/`、`03_五分钟速览/`；仅建立有产物的目录。速记手册默认按 Week 制作离线单文件 HTML，提供 Week 筛选、搜索、重置及可见状态反馈。每模块写原理、概念、用法、语法/参数/返回、易错点、最小例子，并标 Week、课件名、页或 Notebook Cell。无代码概念不强塞语法项，但需解释为何不适用。

专有名词进入页内独立中英记忆区，附中文释义、易混项或记忆钩子及来源。术语对照页支持英中双向搜索并显示 Week 与定位；五分钟速览只做高密度复盘，不冒充完整笔记。覆盖 JSON 与相应手册同名配对放 `data/`，由来源清单计算真实覆盖，不以卡片数量声称全覆盖。

不要在页面放 `<base>` 等劫持相对链接的标签或硬编码旧绝对路径；引用只指向当前真实文件。实际打开 HTML 检查搜索、筛选、移动端与来源链接，并将截图给用户。版本未经用户内容验收仅写审阅状态，不写 final。
