import { copy, duplicate, newWorkflow, type Workflow, type Snapshot, type Run, type Trigger } from "./model";
import { execute, errorText } from "./engine";
import { isDue } from "./schedule";
import { parseWorkflow, validateGraph } from "./validation";

interface Database { version: number; workflows: Workflow[]; runs: Run[]; fired: Record<string, number> }
export type Request =
  | { action: "list" }
  | { action: "save"; workflow: Workflow }
  | { action: "create"; name: string; description: string }
  | { action: "copy"; id: string }
  | { action: "delete"; ids: string[] }
  | { action: "import"; json: string }
  | { action: "run"; id: string; triggerId: string | null; extras: Record<string, string> }
  | { action: "cancel"; id: string };
let database: Promise<Database> | null = null;
let writes: Promise<void> = Promise.resolve();
const active = new Map<string, { cancelled: boolean }>();

/** Loads plugin-owned storage exactly once in the main runtime. */
async function load(): Promise<Database> {
  if (database === null) database = initialize();
  return database;
}

/** Marks unfinished records as interrupted after a runtime restart. */
async function initialize(): Promise<Database> {
  const db = await PluginConfig.use<Database>("workflows", { version: 1, workflows: [], runs: [], fired: {} });
  if (db.version !== 1) throw new Error(`不支持的数据版本：${db.version}`);
  const runs = copy(db.runs);
  let changed = false;
  for (const run of runs) {
    if (run.status !== "RUNNING") continue;
    changed = true; run.status = "FAILED"; run.finishedAt = Date.now();
    run.logs.push({ time: Date.now(), nodeId: "", level: "error", message: "运行时已中断；本次执行未完成。" });
    for (const node of Object.values(run.nodes)) if (node.status === "running" || node.status === "pending") { node.status = "failed"; node.output = "运行时中断"; node.finishedAt = Date.now(); }
    const workflow = db.workflows.find(item => item.id === run.workflowId);
    if (workflow) { workflow.failedExecutions++; workflow.lastExecutionStatus = "FAILED"; }
  }
  if (changed) { db.runs = runs; db.workflows = copy(db.workflows); await PluginConfig.flush(db); }
  return db;
}

/** Serializes durable writes and surfaces storage failures to every caller. */
async function persist(db: Database): Promise<void> {
  writes = writes.then(() => PluginConfig.flush(db));
  await writes;
}

/** Returns detached state so UI edits cannot mutate stored definitions. */
async function snapshot(): Promise<Snapshot> {
  const db = await load();
  return copy({ workflows: db.workflows, runs: db.runs });
}

/** Looks up an existing workflow by exact identity. */
function find(db: Database, workflowId: string): Workflow {
  const workflow = db.workflows.find(item => item.id === workflowId);
  if (!workflow) throw new Error(`工作流不存在：${workflowId}`);
  return workflow;
}

/** Rejects changes to a workflow while its saved snapshot is executing. */
function editable(workflowId: string): void {
  if (active.has(workflowId)) throw new Error("工作流正在执行，结束后才能修改或删除");
}

/** Formats the actual tool output without hiding execution errors. */
function output(value: unknown): string {
  if (typeof value === "string") return value;
  const text = JSON.stringify(value);
  if (text === undefined) throw new Error("工具或脚本没有返回可序列化的结果");
  return text;
}

/** Persists node transitions and execution statistics inside the owning runtime. */
async function record(db: Database, run: Run): Promise<void> {
  const previous = db.runs.find(item => item.id === run.id);
  const workflow = find(db, run.workflowId);
  if (!previous) { workflow.totalExecutions++; workflow.lastExecutionTime = run.startedAt; }
  if (run.status !== "RUNNING" && (previous === undefined || previous.status === "RUNNING")) {
    if (run.status === "SUCCESS") workflow.successfulExecutions++;
    if (run.status === "FAILED") workflow.failedExecutions++;
  }
  workflow.lastExecutionStatus = run.status;
  db.workflows = copy(db.workflows);
  const entries = db.runs.filter(item => item.id !== run.id);
  entries.push(copy(run));
  const running = entries.filter(item => item.status === "RUNNING");
  const finished = entries.filter(item => item.status !== "RUNNING").sort((a, b) => b.startedAt - a.startedAt).slice(0, 100);
  db.runs = [...running, ...finished];
  await persist(db);
}

/** Executes a saved workflow independently of its UI route lifetime. */
async function runWorkflow(workflowId: string, triggerId: string | null, extras: Record<string, string>, observer?: (run: Run) => Promise<void>): Promise<void> {
  const db = await load();
  editable(workflowId);
  const workflow = copy(find(db, workflowId));
  if (!workflow.enabled) throw new Error("工作流已停用");
  const control = { cancelled: false };
  active.set(workflowId, control);
  try {
    await execute(workflow, triggerId, extras, {
      /** Invokes host tools with their existing permission and error contracts. */
      call: async (name, params) => output(await toolCall(name, params)),
      /** Executes explicitly authored JavaScript with async host tool access. */
      script: async (code, inputs, trigger) => {
        const evaluate = new Function("inputs", "trigger", "Tools", "toolCall", `"use strict"; return (async function() {\n${code}\n})();`) as (inputs: Record<string, string>, trigger: Record<string, string>, tools: typeof Tools, call: typeof toolCall) => Promise<unknown>;
        return output(await evaluate(inputs, trigger, Tools, toolCall));
      },
      /** Publishes durable progress before notifying an attached UI observer. */
      changed: async run => {
        await record(db, run);
        if (observer) await observer(run);
      },
      /** Checks cooperative cancellation between node executions. */
      cancelled: () => control.cancelled,
    });
  } finally { active.delete(workflowId); }
}

/** Owns all UI and tool mutations, with optimistic revisions for saved graphs. */
export async function dispatch(request: Request, observer?: (run: Run) => Promise<void>): Promise<Snapshot> {
  const db = await load();
  switch (request.action) {
    case "list": return snapshot();
    case "create": {
      if (!request.name.trim()) throw new Error("工作流名称不能为空");
      db.workflows = [...db.workflows, newWorkflow(request.name.trim(), request.description)]; break;
    }
    case "save": {
      editable(request.workflow.id);
      const stored = find(db, request.workflow.id);
      if (stored.revision !== request.workflow.revision) throw new Error("工作流已被其他入口修改，请重新加载后编辑");
      const parsed = parseWorkflow(request.workflow);
      const next = { ...stored, name: parsed.name, description: parsed.description, enabled: parsed.enabled, nodes: parsed.nodes,
        connections: parsed.connections, updatedAt: Date.now(), revision: stored.revision + 1 };
      validateGraph(next, false);
      db.workflows = db.workflows.map(item => item.id === next.id ? next : item); break;
    }
    case "copy": {
      const next = duplicate(find(db, request.id)); next.name += " 副本"; db.workflows = [...db.workflows, next]; break;
    }
    case "delete": {
      request.ids.forEach(editable);
      db.workflows = db.workflows.filter(item => !request.ids.includes(item.id));
      db.runs = db.runs.filter(item => !request.ids.includes(item.workflowId));
      for (const key of Object.keys(db.fired)) if (request.ids.some(workflowId => key.startsWith(workflowId + ":"))) delete db.fired[key];
      db.fired = { ...db.fired }; break;
    }
    case "import": {
      const raw: unknown = JSON.parse(request.json);
      const next = duplicate(parseWorkflow(raw));
      next.enabled = false;
      db.workflows = [...db.workflows, next]; break;
    }
    case "run": await runWorkflow(request.id, request.triggerId, request.extras, observer); return snapshot();
    case "cancel": {
      const control = active.get(request.id);
      if (!control) throw new Error("该工作流没有正在进行的执行");
      control.cancelled = true; return snapshot();
    }
  }
  await persist(db);
  return snapshot();
}

/** Routes cross-runtime requests and keeps progress observers outside execution semantics. */
export async function receive(request: Request, meta: ToolPkg.IpcMeta): Promise<Snapshot> {
  const context = meta.callerContextKey;
  if (request.action !== "run" || context === undefined) return dispatch(request);
  return dispatch(request, async run => {
    // The UI context is awaiting this service call and cannot acknowledge progress yet.
    // Detach a snapshot so notification delivery never holds the execution lock.
    void ToolPkg.ipc.call<Run, boolean>("workflow.progress", copy(run), { targetRuntime: "ui", targetContextKey: context })
      .catch(error => { console.error("[workflow] Progress delivery failed", error); });
  });
}

/** Creates a stable schedule identity including its exact configuration. */
function scheduleKey(workflow: Workflow, node: Trigger): string {
  return `${workflow.id}:${node.id}:${JSON.stringify(Object.entries(node.triggerConfig).sort(([a], [b]) => a.localeCompare(b)))}`;
}

/** Delivers due triggers serially, preventing overlapping runs of one workflow. */
export async function trigger(kind: "schedule" | "app_open" | "event", topic = "", extras: Record<string, string> = {}): Promise<void> {
  const db = await load();
  for (const workflow of copy(db.workflows)) {
    if (!workflow.enabled || active.has(workflow.id)) continue;
    for (const node of workflow.nodes) {
      if (node.type !== "trigger" || node.triggerType !== kind) continue;
      try {
        if (kind === "event" && node.triggerConfig.topic !== topic) continue;
        if (kind === "schedule") {
          const key = scheduleKey(workflow, node);
          const last = Object.prototype.hasOwnProperty.call(db.fired, key) ? db.fired[key] : null;
          if (!isDue(node, last, workflow.createdAt, Date.now())) continue;
          // Commit the firing before tools run so a restart cannot repeat a side effect.
          db.fired = { ...db.fired, [key]: Date.now() }; await persist(db);
        }
        await runWorkflow(workflow.id, node.id, extras);
      } catch (error) {
        console.error(`[workflow] Trigger failed for ${workflow.id}/${node.id}: ${errorText(error)}`);
        throw error;
      }
    }
  }
}
