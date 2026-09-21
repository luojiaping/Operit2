import screen from "./ui/web";
import { dispatch, receive, trigger } from "./service";

export const ROUTE = "toolpkg:com.operit.workflow:ui:workflow";
export const EVENT_TOPICS: ToolPkg.BroadcastTopic[] = ["app.lifecycle.resumed", "system.network.changed", "system.power.connected", "system.power.disconnected", "system.screen.on", "system.screen.off", "system.battery.low", "system.battery.okay"];

// Main-runtime IPC loads this module without invoking the metadata registration function.
ToolPkg.ipc.on("workflow.service", receive);
ToolPkg.ipc.on("workflow.web", request => dispatch(request as import("./service").Request));

/** Registers the plugin UI, public service and host-owned trigger sources. */
export function registerToolPkg(): boolean {
  ToolPkg.registerUiRoute({ id: "workflow", route: ROUTE, screen, runtime: "compose_dsl", keepAlive: true, title: { zh: "工作流", en: "Workflow" } });
  ToolPkg.registerNavigationEntry({ id: "workflow_sidebar", route: ROUTE, surface: "main_sidebar_plugins", title: { zh: "工作流", en: "Workflow" }, icon: "AccountTree", order: 140 });
  ToolPkg.registerNavigationEntry({ id: "workflow_toolbox", route: ROUTE, surface: "toolbox", title: { zh: "工作流", en: "Workflow" }, icon: "AccountTree", order: 140 });
  ToolPkg.registerHostEventHook({ id: "workflow_clock", source: "interval", trigger: { kind: "interval", intervalMs: 60000 }, function: onClock });
  ToolPkg.registerAppLifecycleHook({ id: "workflow_open", event: "application_on_create", function: onOpen });
  for (const topic of EVENT_TOPICS) ToolPkg.registerHostEventHook({ id: `workflow_${topic}`, source: "broadcast", trigger: { kind: "broadcast", topic }, function: onEvent });
  return true;
}

/** Checks persisted schedules when the host emits the plugin clock event. */
export async function onClock(): Promise<void> { await trigger("schedule"); }

/** Runs cold-start entry nodes through the application lifecycle contract. */
export async function onOpen(): Promise<void> { await trigger("app_open"); }

/** Forwards normalized host events to matching workflow entry nodes. */
export async function onEvent(event: ToolPkg.HostEventBroadcastHookEvent<ToolPkg.BroadcastTopic>): Promise<void> {
  await trigger("event", event.eventPayload.payload.topic, { event: JSON.stringify(event.eventPayload.payload) });
}
