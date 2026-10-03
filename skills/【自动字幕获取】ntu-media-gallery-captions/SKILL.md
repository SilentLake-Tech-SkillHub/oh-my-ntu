---
name: ntu-media-gallery-captions
description: 从 NTULearn Media Gallery / Kaltura 频道的录播视频中获取自动字幕（WebVTT）时使用。适用于官方没有提供可下载 .srt/.vtt 附件、但播放器加载了 Kaltura serveWebVTT 字幕的场景。触发词：抓取字幕、Media Gallery 字幕、Kaltura 字幕、录播文字稿、auto captions。
---

# Media Gallery（Kaltura）自动字幕获取

## 与 06（ntu-class-recordings）的分工

06 处理**官方附件字幕**（课程页直接提供的 .srt/.vtt 下载）。本 Skill 处理 06 覆盖不到的场景：Media Gallery/Kaltura 录播**没有官方字幕附件**，但播放器实际加载了自动字幕流（Kaltura `serveWebVTT` 接口）。两者互补，不冲突：

- 有官方附件 → 走 06，本 Skill 不介入；
- 无官方附件、有 Kaltura 自动字幕 → 走本 Skill；
- 两者都没有 → 按 06 如实登记缺口，不自行 ASR 重转写冒充。

**Kaltura 自动字幕是机器转写，必须在文件名、文件头部注释和登记文档中标注"自动字幕，非教师原文，未经逐句校对"**，引用其中的"考试重点/老师说"类表述时按 06 的规则回查原文时间戳并标低置信度。

## 第一步：确认字幕是否可取（先做，必做）

按 local-chrome-for-kimi 的方式在用户已登录 Chrome 中打开视频播放页，执行：

```javascript
performance.getEntriesByType('resource').map(r=>r.name)
  .filter(n=>/caption|serveWebVTT|vtt/i.test(n))
```

判定：

- 命中 `caption_captionasset/action/serveWebVTT/captionAssetId/<id>/...` → **可取**；
- 播放页有"SEARCH IN VIDEO"或按语音内容生成的关键词标签，也是自动字幕存在的旁证，但以 serveWebVTT 请求为准；
- 频道页的 Captions 筛选器选 "Available" 可批量预筛有字幕的条目；
- 未命中 → 该集无字幕或尚未生成，登记缺口。

## 第二步：强制用户确认（不可跳过）

确认可取后，**必须停下并明确询问用户**：

> 是否确认获取字幕？学习资料不可外传，因获取（下载）导致的所有后果由用户负责。

得到用户明确确认后才继续。批量多集一次确认，但条目清单先给用户看。

## 第三步：抓取与归档

1. serveWebVTT 地址通常带 `ks` 会话令牌与 HLS 分段索引（`segmentDuration=300/.../a.m3u8` 形式表示分段 VTT 清单）。优先直接取该地址返回的内容；若为分段清单，逐段抓取后按时间轴拼接为完整 VTT，保持原始时间戳不偏移。
2. 保存原始 `.vtt` 到 `06_课堂录播字幕/WeekNN/`，命名与对应录播条目一致（如 `weekN_lectM_<场次>.auto.vtt`），`.auto.` 中缀标明自动字幕；不覆盖同名官方字幕。
3. 登记：字幕来源（Kaltura 自动转写）、captionAssetId（脱敏令牌）、抓取日期、对应录播条目、字节数与 SHA-256，写入 `06_课堂录播字幕/00_课程与考核信息_来源状态.md`。
4. 派生整理件（课堂讲解笔记等）单独成文件，与原文分开，按 06 规则标注证据位置。

## 合规红线

- 仅供用户本人学习使用，不可外传；登记文档中不落含 `ks` 令牌的完整 URL。
- 自动字幕不作为教师原文引用；与公告/讲义冲突时以正式来源为准并并列标注。
