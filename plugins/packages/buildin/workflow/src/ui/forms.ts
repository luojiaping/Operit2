import type { ComposeDslContext, ComposeNode } from "../../../../../types/compose-dsl";
import { copy, type Workflow, type WorkflowNode, type Value, type Trigger } from "../model";
import { parseNode } from "../validation";

/** Creates a keyed, controlled text field. */
export function field(ctx: ComposeDslContext, key: string, label: string, value: string, change: (value: string) => void, multiline = false): ComposeNode {
  return ctx.UI.OutlinedTextField({ key, label, value, onValueChange: change, singleLine: !multiline, minLines: multiline ? 3 : 1, maxLines: multiline ? 5 : 1, fillMaxWidth: true });
}

/** Presents the outlined dropdown used by the Kotlin node dialogs. */
export function choose(ctx: ComposeDslContext, key: string, label: string, value: string, options: { value: string; label: string }[], change: (value: string) => void): ComposeNode {
  const option = options.find(item => item.value === value);
  return ctx.UI.DropdownMenu({ key, label, text: option === undefined ? value : option.label,
    fillMaxWidth: true, onClick: (index: number) => change(options[index].value),
  }, options.map(item => ctx.UI.Text({ text: item.label, paddingVertical: 8 })));
}

/** Builds choices whose values and labels are identical. */
export function options(values: string[]): { value: string; label: string }[] { return values.map(value => ({ value, label: value })); }

/** Edits a literal value or an exact upstream-node reference. */
function parameterField(ctx: ComposeDslContext, key: string, label: string, value: Value, workflow: Workflow, self: string, change: (value: Value) => void): ComposeNode {
  const referenced = "nodeId" in value;
  return ctx.UI.Column({ fillMaxWidth: true, spacing: 6 }, [
    ctx.UI.Row({ verticalAlignment: "center", spacing: 8 }, [ctx.UI.Text({ text: label, weight: 1 }), ctx.UI.Text({ text: "引用节点", style: "labelSmall" }),
      ctx.UI.Switch({ checked: referenced, onCheckedChange: checked => {
        if (checked) {
          const source = workflow.nodes.find(node => node.id !== self);
          if (source === undefined) { void ctx.showToast("请先创建上游节点"); return; }
          change({ nodeId: source.id });
        } else change({ value: "" });
      } })]),
    referenced ? choose(ctx, key, "来源", value.nodeId, workflow.nodes.filter(node => node.id !== self).map(node => ({ value: node.id, label: `${node.name} · ${node.id.slice(-6)}` })), nodeId => change({ nodeId }))
      : field(ctx, key, "静态值", value.value, text => change({ value: text }), true),
  ]);
}

/** Edits integral values with visible validation instead of silently coercing text. */
function integer(ctx: ComposeDslContext, key: string, label: string, value: number, change: (value: number) => void): ComposeNode {
  return field(ctx, key, label, String(value), text => {
    if (!/^-?\d+$/.test(text) || !Number.isSafeInteger(Number(text))) { void ctx.showToast("请输入完整整数"); return; }
    change(Number(text));
  });
}

/** Builds schedule-specific inputs using the original configuration names. */
export function scheduleForm(ctx: ComposeDslContext, node: Trigger, change: (node: WorkflowNode) => void): ComposeNode[] {
  const c = node.triggerConfig;
  /** Replaces one configured schedule field. */
  const set = (key: string, value: string): void => change({ ...node, triggerConfig: { ...c, [key]: value } });
  return [
    choose(ctx, `${node.id}:schedule`, "定时类型", c.schedule_type, [{ value: "interval", label: "间隔执行" }, { value: "specific_time", label: "指定时间" }, { value: "cron", label: "Cron 表达式" }], value => {
      const config = { enabled: "true", repeat: "true", schedule_type: value };
      if (value === "interval") change({ ...node, triggerConfig: { ...config, interval_ms: "900000" } });
      if (value === "specific_time") change({ ...node, triggerConfig: { ...config, repeat: "false", specific_time: "2026-12-31 12:00:00" } });
      if (value === "cron") change({ ...node, triggerConfig: { ...config, cron_expression: "0 9 * * *" } });
    }),
    ...(c.schedule_type === "interval" ? [field(ctx, `${node.id}:interval`, "间隔（毫秒，最小 60000）", c.interval_ms, value => set("interval_ms", value))] : []),
    ...(c.schedule_type === "specific_time" ? [field(ctx, `${node.id}:time`, "本地时间 YYYY-MM-DD HH:mm:ss", c.specific_time, value => set("specific_time", value))] : []),
    ...(c.schedule_type === "cron" ? [field(ctx, `${node.id}:cron`, "Cron：分 时 日 月 周", c.cron_expression, value => set("cron_expression", value)),
      choose(ctx, `${node.id}:presets`, "常用定时", c.cron_expression, [{ value: "0 9 * * *", label: "每天 09:00" }, { value: "0 9 * * 1-5", label: "工作日 09:00" }, { value: "*/15 * * * *", label: "每 15 分钟" }], value => set("cron_expression", value))] : []),
    ctx.UI.Row({ spacing: 8, verticalAlignment: "center" }, [ctx.UI.Text({ text: "重复", weight: 1 }), ctx.UI.Switch({ checked: c.repeat === "true", onCheckedChange: value => set("repeat", String(value)) })]),
    ctx.UI.Row({ spacing: 8, verticalAlignment: "center" }, [ctx.UI.Text({ text: "启用定时", weight: 1 }), ctx.UI.Switch({ checked: c.enabled === "true", onCheckedChange: value => set("enabled", String(value)) })]),
    ctx.UI.Text({ text: "按宿主本地时间检查，精度为一分钟。后台运行能力取决于宿主生命周期。", style: "bodySmall", color: "onSurfaceVariant" }),
  ];
}

/** Renders all node-specific settings with typed parameter references. */
export function nodeForm(ctx: ComposeDslContext, workflow: Workflow, node: WorkflowNode, change: (node: WorkflowNode) => void, configureSchedule: () => void): ComposeNode[] {
  const UI = ctx.UI;
  const content: ComposeNode[] = [
    field(ctx, `${node.id}:name`, "节点名称", node.name, name => change({ ...node, name })),
    field(ctx, `${node.id}:description`, "说明", node.description, description => change({ ...node, description })),
  ];
  if (node.type === "trigger") {
    content.push(choose(ctx, `${node.id}:trigger`, "触发方式", node.triggerType, [{ value: "manual", label: "手动" }, { value: "schedule", label: "定时" }, { value: "app_open", label: "应用冷启动" }, { value: "event", label: "宿主事件" }], value => {
      const next = copy(node);
      next.triggerType = value as Trigger["triggerType"];
      next.triggerConfig = value === "schedule" ? { schedule_type: "interval", interval_ms: "900000", enabled: "true", repeat: "true" } : value === "event" ? { topic: "app.lifecycle.resumed" } : {};
      change(next);
    }));
    if (node.triggerType === "schedule") content.push(UI.Button({ text: "配置定时触发", fillMaxWidth: true, onClick: configureSchedule }), UI.Text({ text: "已配置定时触发", style: "bodySmall", color: "primary" }));
    if (node.triggerType === "app_open") content.push(UI.Text({ text: "应用启动后自动触发此工作流。", style: "bodySmall", color: "onSurfaceVariant" }));
    if (node.triggerType === "event") content.push(choose(ctx, `${node.id}:topic`, "事件", node.triggerConfig.topic,
      options(["app.lifecycle.resumed", "system.network.changed", "system.power.connected", "system.power.disconnected", "system.screen.on", "system.screen.off", "system.battery.low", "system.battery.okay"]), topic => change({ ...node, triggerConfig: { topic } })));
  }
  if (node.type === "execute") {
    content.push(field(ctx, `${node.id}:tool`, "工具名称（支持 包名:工具名）", node.actionType, actionType => change({ ...node, actionType })));
    content.push(choose(ctx, `${node.id}:tools`, "常用工具", node.actionType, options(["send_message_to_ai", "http_request", "read_file", "write_file", "sleep", "send_notification", "execute_hidden_terminal_command"]), actionType => change({ ...node, actionType })));
    for (const [key, value] of Object.entries(node.actionConfig)) content.push(UI.Column({ spacing: 4, fillMaxWidth: true }, [
      parameterField(ctx, `${node.id}:param:${key}`, key, value, workflow, node.id, next => change({ ...node, actionConfig: { ...node.actionConfig, [key]: next } })),
      UI.Button({ text: `移除参数 ${key}`, onClick: () => { const config = { ...node.actionConfig }; delete config[key]; change({ ...node, actionConfig: config }); } }),
    ]));
    const [key, setKey] = ctx.useState(`parameter-name:${node.id}`, "");
    content.push(field(ctx, `${node.id}:new-param`, "新参数名称", key, setKey), UI.Button({ text: "添加参数", onClick: () => {
      if (!key.trim() || Object.prototype.hasOwnProperty.call(node.actionConfig, key.trim())) { void ctx.showToast("参数名为空或已存在"); return; }
      change({ ...node, actionConfig: { ...node.actionConfig, [key.trim()]: { value: "" } } }); setKey("");
    } }));
    content.push(UI.Row({ spacing: 8, verticalAlignment: "center" }, [UI.Text({ text: "JavaScript 执行模式", weight: 1 }), UI.Switch({ checked: node.jsCode !== null, onCheckedChange: value => change({ ...node, jsCode: value ? "return inputs;" : null }) })]));
    if (node.jsCode !== null) content.push(field(ctx, `${node.id}:js`, "脚本（return 返回结果，支持 await）", node.jsCode, jsCode => change({ ...node, jsCode }), true), UI.Text({ text: "可用 inputs、trigger、Tools 和 toolCall。脚本直接运行在插件环境中。", style: "bodySmall" }));
  }
  if (node.type === "condition") content.push(
    parameterField(ctx, `${node.id}:left`, "左值", node.left, workflow, node.id, left => change({ ...node, left })),
    choose(ctx, `${node.id}:operator`, "比较方式", node.operator, [
      { value: "EQ", label: "等于 (==)" }, { value: "NE", label: "不等于 (!=)" }, { value: "GT", label: "大于 (>)" },
      { value: "GTE", label: "大于等于 (>=)" }, { value: "LT", label: "小于 (<)" }, { value: "LTE", label: "小于等于 (<=)" },
      { value: "CONTAINS", label: "包含" }, { value: "NOT_CONTAINS", label: "不包含" }, { value: "IN", label: "属于" }, { value: "NOT_IN", label: "不属于" },
    ], operator => change(parseNode({ ...node, operator }))),
    parameterField(ctx, `${node.id}:right`, "右值（IN 使用 JSON 数组）", node.right, workflow, node.id, right => change({ ...node, right })),
  );
  if (node.type === "logic") content.push(choose(ctx, `${node.id}:logic`, "逻辑运算", node.operator, [{ value: "AND", label: "与 AND" }, { value: "OR", label: "或 OR" }], operator => change(parseNode({ ...node, operator }))), UI.Text({ text: "对输入连线中成功完成的布尔结果运算。", style: "bodySmall" }));
  if (node.type === "extract") {
    content.push(choose(ctx, `${node.id}:mode`, "运算模式", node.mode, [
      { value: "REGEX", label: "正则提取" }, { value: "JSON", label: "JSON 提取" }, { value: "SUB", label: "截取字符串" },
      { value: "CONCAT", label: "拼接字符串" }, { value: "RANDOM_INT", label: "随机整数" }, { value: "RANDOM_STRING", label: "随机字符串" },
    ], mode => change(parseNode({ ...node, mode }))));
    if (node.mode !== "RANDOM_INT" && node.mode !== "RANDOM_STRING") content.push(parameterField(ctx, `${node.id}:source`, "源数据", node.source, workflow, node.id, source => change({ ...node, source })));
    if (node.mode === "REGEX" || node.mode === "JSON") content.push(field(ctx, `${node.id}:expression`, node.mode === "JSON" ? "JSON 路径，例如 $.data[0].name" : "正则表达式", node.expression, expression => change({ ...node, expression })));
    if (node.mode === "REGEX") content.push(integer(ctx, `${node.id}:group`, "捕获组（0 表示整个匹配）", node.group, group => change({ ...node, group })));
    if (node.mode === "SUB") content.push(integer(ctx, `${node.id}:start`, "起点", node.startIndex, startIndex => change({ ...node, startIndex })), integer(ctx, `${node.id}:length`, "长度（-1 表示到结尾）", node.length, length => change({ ...node, length })));
    if (node.mode === "CONCAT") {
      node.others.forEach((value, index) => content.push(parameterField(ctx, `${node.id}:other:${index}`, `拼接值 ${index + 1}`, value, workflow, node.id, next => change({ ...node, others: node.others.map((item, i) => i === index ? next : item) }))));
      content.push(UI.Button({ text: "添加拼接值", onClick: () => change({ ...node, others: [...node.others, { value: "" }] }) }), UI.Button({ text: "移除最后一项", enabled: node.others.length > 0, onClick: () => change({ ...node, others: node.others.slice(0, -1) }) }));
    }
    if (node.mode === "RANDOM_INT" || node.mode === "RANDOM_STRING") {
      content.push(UI.Row({ spacing: 8, verticalAlignment: "center" }, [UI.Text({ text: "使用固定值", weight: 1 }), UI.Switch({ checked: node.useFixed, onCheckedChange: useFixed => change({ ...node, useFixed }) })]));
      if (node.useFixed) content.push(field(ctx, `${node.id}:fixed`, "固定值", node.fixedValue, fixedValue => change({ ...node, fixedValue })));
      else if (node.mode === "RANDOM_INT") content.push(integer(ctx, `${node.id}:min`, "最小值", node.randomMin, randomMin => change({ ...node, randomMin })), integer(ctx, `${node.id}:max`, "最大值（包含）", node.randomMax, randomMax => change({ ...node, randomMax })));
      else content.push(integer(ctx, `${node.id}:randomLength`, "长度", node.randomStringLength, randomStringLength => change({ ...node, randomStringLength })), field(ctx, `${node.id}:charset`, "字符集", node.randomStringCharset, randomStringCharset => change({ ...node, randomStringCharset })));
    }
  }
  return content;
}
