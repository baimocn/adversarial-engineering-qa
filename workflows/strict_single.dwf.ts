/**
 * 单题严格质检（确定性部分）
 *
 * 前置（由编排模型/人完成）：
 *   <workDir>/run-config.json       人选的三类模型
 *   <workDir>/decomposition.json    拆题模型产出的检查
 *   <workDir>/judgments/<id>/       可选：两评审 + 裁决
 *
 * 本 workflow 只调用 scripts/strict_verify.py：校验 -> CPU 检查 -> panel 比对
 * -> 合并 -> verdict。模型不参与裁决。
 */
interface StrictSummary {
  /** PASS / FAIL / INCOMPLETE。 */
  decision: string;
  /** 各类别计数。 */
  counts?: Record<string, number>;
  /** human_required / unknown 的 check id。 */
  open_ids?: string[];
  /** fail 的 check id。 */
  fail_ids?: string[];
}

const repoRoot = String(args.repoRoot ?? "").replace(/[\\/]+$/, "");
const taskRoot = String(args.taskRoot ?? "");
const workDir = String(args.workDir ?? "");
if (!repoRoot || !taskRoot || !workDir) {
  throw new Error("missing args: repoRoot/taskRoot/workDir are required");
}

phase("运行严格检查");
const run = await world.run(
  "python",
  ["-I", `${repoRoot}/scripts/strict_verify.py`,
   "--repo-root", repoRoot, "--task-root", taskRoot, "--work-dir", workDir],
  { timeoutMs: 1_800_000 },
);

let summary: StrictSummary = { decision: "INCOMPLETE" };
try {
  summary = JSON.parse(run.stdout) as StrictSummary;
} catch {
  summary = { decision: "INCOMPLETE", open_ids: [`unparsable output: ${run.stderr.slice(-300)}`] };
}

const lines = [
  `# 严格质检：${taskRoot}`,
  "",
  `**结论：${summary.decision}**`,
  "",
  "## 计数",
  ...Object.entries(summary.counts ?? {}).map(([k, v]) => `- ${k}: ${v}`),
  "",
  "## 失败项",
  ...(summary.fail_ids?.length ? summary.fail_ids.map((id) => `- ${id}`) : ["- 无"]),
  "",
  "## 待人工/未验证",
  ...(summary.open_ids?.length ? summary.open_ids.map((id) => `- ${id}`) : ["- 无"]),
  "",
  "> 本结论由 strict_verify.py 计算；模型只提供证据与判断，不参与最终裁决。",
].join("\n");

await artifact.markdown("strict_verdict", lines, {
  title: `严格质检：${taskRoot.split(/[\\/]/).pop() ?? taskRoot}`,
  description: "确定性检查 + 2+1 主观评审的最终结论",
  primary: true,
});
log(`decision=${summary.decision} exit=${run.exitCode}`);
return { taskRoot, workDir, exitCode: run.exitCode, ...summary };
