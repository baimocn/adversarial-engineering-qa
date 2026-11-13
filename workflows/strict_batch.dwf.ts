/**
 * 多题严格质检（确定性部分）
 *
 * args.tasks: [{taskRoot, workDir}, ...]
 * 每题的前置文件同 strict_single.dwf.ts。
 * 每题独立 workDir、独立 strict_verify.py；互不共享上下文。
 */
interface TaskSpec {
  /** 题包 harbor_task 根目录。 */
  taskRoot: string;
  /** 该题的工作目录（含 run-config/decomposition/judgments）。 */
  workDir: string;
}

interface TaskOutcome {
  /** 题包根目录。 */
  taskRoot: string;
  /** PASS / FAIL / INCOMPLETE。 */
  decision: string;
  /** 进程退出码。 */
  exitCode: number;
  /** 待人工/未验证项。 */
  openIds: string[];
  /** 失败项。 */
  failIds: string[];
}

const repoRoot = String(args.repoRoot ?? "").replace(/[\\/]+$/, "");
const rawTasks = args.tasks;
const tasks: TaskSpec[] = Array.isArray(rawTasks)
  ? (rawTasks as TaskSpec[])
  : (typeof rawTasks === "string" ? (JSON.parse(rawTasks) as TaskSpec[]) : []);
if (!repoRoot || tasks.length === 0) {
  throw new Error("missing args: repoRoot and a non-empty tasks list are required");
}

artifact.table("strict_batch", {
  title: "多题严格质检结果",
  columns: [
    { field: "task", label: "题包" },
    { field: "decision", label: "结论" },
    { field: "open", label: "待人工" },
    { field: "fail", label: "失败项" },
  ],
});

phase("并行运行各题严格检查");
const outcomes: TaskOutcome[] = await Promise.all(
  tasks.map(async (task) => {
    const run = await world.run(
      "python",
      ["-I", `${repoRoot}/scripts/strict_verify.py`,
       "--repo-root", repoRoot, "--task-root", task.taskRoot, "--work-dir", task.workDir],
      { timeoutMs: 1_800_000 },
    );
    let decision = "INCOMPLETE";
    let openIds: string[] = [];
    let failIds: string[] = [];
    try {
      const parsed = JSON.parse(run.stdout) as {
        decision?: string;
        open_ids?: string[];
        fail_ids?: string[];
      };
      decision = String(parsed.decision ?? "INCOMPLETE");
      openIds = parsed.open_ids ?? [];
      failIds = parsed.fail_ids ?? [];
    } catch {
      openIds = [`unparsable output: ${run.stderr.slice(-200)}`];
    }
    return { taskRoot: task.taskRoot, decision, exitCode: run.exitCode, openIds, failIds };
  }),
);

for (const outcome of outcomes) {
  report({
    task: outcome.taskRoot.split(/[\\/]/).pop() ?? outcome.taskRoot,
    decision: outcome.decision,
    open: String(outcome.openIds.length),
    fail: String(outcome.failIds.length),
  }, "strict_batch");
}

const counts = outcomes.reduce<Record<string, number>>((acc, item) => {
  acc[item.decision] = (acc[item.decision] ?? 0) + 1;
  return acc;
}, {});
const lines = [
  "# 多题严格质检",
  "",
  `共 ${outcomes.length} 题。`,
  "",
  "## 结论分布",
  ...Object.entries(counts).map(([k, v]) => `- ${k}: ${v}`),
  "",
  "## 逐题",
  ...outcomes.map((o) => `- ${o.taskRoot}: ${o.decision}（open=${o.openIds.length}, fail=${o.failIds.length}）`),
  "",
  "> 每题独立运行 strict_verify.py；任一题 FAIL 不阻断其他题。",
].join("\n");

await artifact.markdown("strict_batch_summary", lines, {
  title: "多题严格质检汇总",
  description: "每题独立结论与待人工项",
  primary: true,
});
log(`tasks=${outcomes.length} counts=${JSON.stringify(counts)}`);
return { tasks: outcomes, counts };
