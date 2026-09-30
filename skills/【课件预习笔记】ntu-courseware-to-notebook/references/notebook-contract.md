# Notebook 组装与映射样例

本文件提供可适配的单元格式与来源映射，不包含真实课件翻译。沿用目标 notebook 已确认的结构时，保持同等信息与保护能力即可。

## 每页单元样例

原图 Markdown 单元：

```markdown
## Chapter 4.3 · Slide 9 — Journey Mapping

![Chapter 4.3 Slide 9 英文原图](【勿删】CAXXXX_Week04_课件中英对照_原页图片/chapter_4_3_slide_09.png)
```

紧邻的翻译 Markdown 单元：

```markdown
### 中文翻译：用户旅程图

#### 图示术语

| 原文 | 中文 | 原图中的含义 |
|---|---|---|
| Journey Phases | 旅程阶段 | 按时间顺序排列的主要阶段 |
| Actions | 行动 | 用户采取的行为和步骤 |
| Mindsets | 心态 | 用户的想法、问题与动机 |
| Emotions | 情绪 | 体验中情绪的起伏 |

#### 阶段内容

- **定义（Define）**：在此填写该阶段全部原文的中文翻译。
- **比较（Compare）**：在此填写该阶段全部原文的中文翻译。
```

以上只演示排版，不是完整译文。真实页必须覆盖所有标签、阶段内容、气泡和来源；提交前删除样例占位句。正文页可直接使用完整段落与列表，不必每页强行划分多个小标题。

## 来源映射

建议把映射保存在 notebook 自定义 metadata 中；需要复杂裁切或重复构建时，可以使用独立 JSON manifest，并用相对路径关联。不要重复维护彼此不一致的多份清单。

```json
{
  "schema_version": 1,
  "course": "CAXXXX",
  "week": "Week04",
  "source_pdf": "../../01_课程课件/Week4/Week4 - Sat - Chapter 4.3 - Finding AI Opportunities.pdf",
  "source_sha256": "实际计算得到的 SHA-256",
  "chapter": "4.3",
  "pdf_page_1based": 5,
  "slide_label": "9",
  "position": "top",
  "crop": {
    "unit": "pixel",
    "render_dpi": 240,
    "box_xywh": [192, 343, 1598, 900]
  },
  "image": "【勿删】CAXXXX_Week04_课件中英对照_原页图片/chapter_4_3_slide_09.png",
  "pair_id": "caxxxx-week4-ch43-slide09",
  "image_cell_id": "ch43s09-image",
  "translation_cell_id": "ch43s09-zh"
}
```

坐标仅来自一次历史版式，必须对当前 PDF 重新测量。原文没有印刷页码时，用物理页和页内位置生成稳定 ID，并说明来源，不要伪造印刷页码。
`source_pdf` 只是相对于 `【预习用】03_Notebook课件中英文对照解析/Week04/` 的示意路径；真实课件文件名与目录必须从当前课程核对，不得照抄此例。图片相对路径须与同周实体资源目录完全一致；改名或移动时逐一复验。

为新单元设置 `metadata.courseware`，包含 `pair_id`、`role`（`original_image` 或 `translation`）、来源定位和上次生成内容哈希。单元合并格式可以用 `role: "paired"`。历史 `week4_translation` 等 metadata 可以继续识别，不必为统一格式重写用户文件。

## 保存与重跑

1. 读取 notebook，保存原始文件备份和哈希；记录现有单元及图片资产。
2. 先构建内容候选，再逐页核对原文。所有候选图片可先写入独立临时目录。
3. 按稳定 `pair_id` 查找现有生成页。若当前 `source` 与上次生成哈希不同，说明可能有用户编辑，保留并合并，不整页覆盖。缺少旧哈希时也不能假定内容未变。
4. 写入前检查磁盘哈希与读取时一致；有变化则重新读文件、处理并发修改。保存完整有效的 JSON，再复读验证。
5. 保留现有 code cell 的代码、outputs、execution_count，以及 markdown attachments 和未知 metadata。不要为了方便只重建生成单元而丢掉其他字段。

## 验收记录最小内容

- 源文件、源哈希、用户选择范围与实际配对数量。
- 未纳入范围的页及原因；范围内不可辨认的文字单独记录。
- 原图、译文、图表和代码的逐页审校结果。
- 最终 notebook 解析、全部图片路径、重复 ID、原有内容保护检查。
- 实际 notebook 检查的章节／页码、代表性截图与尚未验证项。

代码和静态检查只用于发现结构问题。配对数量正确、中文字符很多或没有空列表，都不能替代逐页翻译审校。
