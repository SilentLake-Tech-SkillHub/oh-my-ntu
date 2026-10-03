---
name: ntu-media-gallery-video-download
description: 当录播视频位于 NTULearn Media Gallery / Kaltura 频道（Recorded Lectures 等 LTI 入口），需要把流媒体录播下载为本地 MP4 时使用。仅适用于技术上可抓取的 Kaltura HLS 流；官方附件 MP4 直接下载走 01 原始课件流程，不属本 Skill。触发词：下载录播、Media Gallery 视频、Kaltura 视频下载、录播保存本地。
---

# Media Gallery（Kaltura）录播视频下载

## 适用范围与前提

本 Skill 只处理**发布在 Media Gallery / Kaltura 频道里的流媒体录播**（课程页 Recorded Lectures 等 LTI 入口，播放器域名为 `ntulearnv1.ntu.edu.sg` 等 Kaltura 系域名）。这类视频**没有官方下载按钮**，但通过浏览器网络请求可以拿到未加密的 HLS 流地址，技术上可下载——这正是它与以往"不能下载"的录播的区别：能否下载取决于发布形态（Media Gallery 开放流 ≠ DRM 加密流），不是一刀切。

与 06（ntu-class-recordings）的关系：06 的默认规则是"没有官方下载控制时不得绕过签名链接或分段流、不下载音视频"。**本 Skill 是该规则的显式例外通道**，只有在用户明确要求下载录播、并完成下方强制确认后才可执行；否则仍按 06 处理（只登记缺口）。

## 第一步：确认是否可下载（先做，必做）

按 local-chrome-for-kimi 的方式在用户已登录 Chrome 中操作（Apple Events 通道，只读探测）：

1. 打开视频播放页，查官方下载入口：`a,button` 中含 download/下载 字样、播放器菜单、"Details/Attachments/Share" 之外的 Download 标签。**有官方下载入口就用官方的**，本 Skill 的抓流流程不再适用。
2. 无官方入口时，执行以下 JS 探测流形态：
   ```javascript
   performance.getEntriesByType('resource').map(r=>r.name)
     .filter(n=>/m3u8|mp4|manifest|serveFlavor|playManifest/i.test(n))
   ```
3. 判定：
   - 命中 `serveFlavor/.../index.m3u8` 或 `playManifest/.../a.m3u8`（Kaltura HLS）→ **可下载**；
   - 流为 Widevine/FairPlay 加密（manifest 带 DRM 标识、分片无法直接解码）→ **不可下载**，停止并告知用户，不尝试破解；
   - 未命中任何流 → 视频未加载，先播放几秒再探测。

## 第二步：强制用户确认（不可跳过）

确认可下载后，**必须停下并明确询问用户**：

> 是否确认下载？学习资料不可外传，因下载导致的所有后果由用户负责。

得到用户明确确认后才继续。禁止在首次触发时未经确认直接下载；批量下载多集时一次确认可覆盖当次列明的全部条目，但条目清单要先给用户看。

## 第三步：下载与归档

1. 在播放页提取直链 flavor 地址（形如 `https://cfvod.<region>.ovp.kaltura.com/hls/p/<pid>/sp/<sp>/serveFlavor/entryId/<id>/v/<v>/ev/<ev>/flavorId/<fid>/name/a.mp4/index.m3u8`）；若该地址需会话令牌，从 playManifest 请求中取 `ks` 参数拼入。
2. 下载合并：`ffmpeg -headers "Referer: https://ntulearnv1.ntu.edu.sg/" -i "<m3u8>" -c copy "<输出.mp4>"`（只转封装不重编码）。
3. 校验：`ffprobe` 时长与频道列表标注时长一致（容忍秒级差）、文件可解码、首尾帧非黑屏；记录 SHA-256、entryId、抓取日期。
4. 归档：按课程目录规则放 `01_课程课件/WeekN_.../视频/`，命名遵循该课已有前缀约定（如 `WeekN_Thu_录播_<主题>.mp4`）；教师原始条目名与本地归档名的对应关系写进 `00_课程设置与资料清单.md` 和 `06_课堂录播字幕/00_课程与考核信息_来源状态.md`，并注明"Kaltura 流媒体抓取，无官方下载入口，经用户确认后下载，仅限个人学习"。
5. 逐集下载间隔几秒，不并发打流服务器；失败重试不超过 3 次。

## 合规红线

- 仅供用户本人学习使用，**不可外传、不可上传任何第三方平台**；不在产物中嵌入可对外传播的直链（m3u8 地址含会话令牌，记入清单时脱敏）。
- 不在课堂直播进行中抓流；只抓已发布的录播。
- 用户撤销授权或学校明确禁止时，立即停止并删除已抓取的文件（用户确认后）。
