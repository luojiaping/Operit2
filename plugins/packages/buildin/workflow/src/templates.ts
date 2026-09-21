import { id, newNode, newWorkflow, type Workflow } from "./model";

/** Builds local editable templates without executing tools during import. */
export function templates(): Workflow[] {
  const notify = newWorkflow("手动通知");
  notify.nodes.push(newNode("trigger"));
  notify.description = "手动触发后发送一条系统通知。";
  const notification = newNode("execute", 260, 40);
  if (notification.type !== "execute") throw new Error("节点类型不一致");
  notification.name = "发送通知"; notification.actionType = "send_notification";
  notification.actionConfig = { title: { value: "工作流" }, message: { value: "工作流已执行" } };
  notify.nodes.push(notification);
  notify.connections.push({ id: id("edge"), sourceNodeId: notify.nodes[0].id, targetNodeId: notification.id, condition: null });
  const branch = newWorkflow("随机数条件分支");
  branch.nodes.push(newNode("trigger"));
  branch.description = "生成随机数，比较大小，并沿 true / false 连线显示不同结果；不调用外部工具。";
  const random = newNode("extract", 240, 40);
  if (random.type !== "extract") throw new Error("节点类型不一致");
  random.name = "随机数 0–100"; random.mode = "RANDOM_INT";
  const condition = newNode("condition", 440, 40);
  if (condition.type !== "condition") throw new Error("节点类型不一致");
  condition.name = "大于等于 50"; condition.left = { nodeId: random.id }; condition.operator = "GTE"; condition.right = { value: "50" };
  const yes = newNode("extract", 640, 0), no = newNode("extract", 640, 160);
  if (yes.type !== "extract" || no.type !== "extract") throw new Error("节点类型不一致");
  yes.name = "较大的数"; yes.mode = "CONCAT"; yes.source = { value: "数值 ≥ 50" };
  no.name = "较小的数"; no.mode = "CONCAT"; no.source = { value: "数值 < 50" };
  branch.nodes.push(random, condition, yes, no);
  branch.connections = [[branch.nodes[0].id, random.id, null], [random.id, condition.id, null], [condition.id, yes.id, "true"], [condition.id, no.id, "false"]].map(([source, target, test]) => {
    if (source === null || target === null) throw new Error("模板连线缺少节点");
    return { id: id("edge"), sourceNodeId: source, targetNodeId: target, condition: test };
  });
  return [notify, branch];
}
