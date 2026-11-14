# auto2768 2026-11-14 平台官方反馈报告原件

本目录只收平台飞书附件中的官方反馈原件。原始 zip 与各文本/JSON 文件均按下载字节原样保存；本仓库自动值守生成的 `findings.json`、`fix_report.md` 未纳入。

| 目录 | report key | decision | 被审包/后续修复 | 关键项 | 原始附件 | zip sha256 |
|---|---|---|---|---|---|---|
| `20261114-auto2768-official-review-r1-G03-QA05-QA11-A03/` | `cafe7056db84f6cf9e7d9ec98cac230d43fee47ecb77f7fae17bd2bad1f2bf8f` | PASS | v30 | 通过 | `auto2768-1107-final-cafe7056db84f6cf.zip` | `e38e982b75163e124e034f7fd04949c549ee7651ca26a250b11487cca39b82d2` |
| `20261114-auto2768-official-review-r2-H02/` | `a3aa8f703b0b83fa135b47a0430e32c28f89531cba95d954fca70ba1d0fddfca` | FAIL | v30 | H04 | `auto2768-1107-final-a3aa8f703b0b83fa.zip` | `78db926cb771775045fc347cbb80fcf3c9ed63ee39420f9fbc4f692b5599b545` |
| `20261114-auto2768-official-review-r3-H04/` | `18dfe9fcbff6c29ff75c9d0532f161f8d1422603378051b36a46dac5d134a156` | FAIL | v29 | H02 | `auto2768-1107-final-18dfe9fcbff6c29f.zip` | `1bdea28eae781664f79cffc1f73142a619a978ddd1d5cc15c4305786a0e4651b` |
| `20261114-auto2768-official-review-r4-PASS/` | `358adb2c5633372203f659222491b34fec87daef979ec35b4527b4accb2cf0bd` | FAIL | v28 | G03/QA05/QA11/A03 | `auto2768-1107-final-358adb2c56333722.zip` | `4eb74c8f1669c13bd8202e2707b4875a98733f6c5c06314fe835c788f6d0404d` |

## 原样性说明

- 每个目录包含原始下载 zip 与 zip 内 9 个官方文件：`decision.txt`、`identity.json`、`last-message.txt`、`previous-feedback.txt`、`report.json`、`report.md`、`report.txt`、`return_to_expert.txt`、`review.json`。
- `archive-manifest.json` 是新增的归档索引，不改写任何官方文件；记录附件 token、key、sha256 与来源字段。
- 报告中有平台内部 ID、记录 ID、附件 token 与事件号；这些是平台反馈原件的定位信息，本次按用户要求原样保留。
- 已扫描常见凭据模式（GitHub/Slack/AWS/OpenAI token、私钥头、Authorization/Bearer、通用 secret 赋值）；四份原始 zip 未检出。
- 平台最终 PASS 报告 `r4-PASS` 对应 v30 包 sha256 `f7cf4557bffa6d980d7554c281ed4a1b11782190bdac9f8899cf5a71d348fdd8`。
