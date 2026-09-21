"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.EVENT_TOPICS = exports.ROUTE = void 0;
exports.registerToolPkg = registerToolPkg;
exports.onClock = onClock;
exports.onOpen = onOpen;
exports.onEvent = onEvent;
const web_1 = __importDefault(require("./ui/web"));
const service_1 = require("./service");
exports.ROUTE = "toolpkg:com.operit.workflow:ui:workflow";
exports.EVENT_TOPICS = ["app.lifecycle.resumed", "system.network.changed", "system.power.connected", "system.power.disconnected", "system.screen.on", "system.screen.off", "system.battery.low", "system.battery.okay"];
// Main-runtime IPC loads this module without invoking the metadata registration function.
ToolPkg.ipc.on("workflow.service", service_1.receive);
ToolPkg.ipc.on("workflow.web", request => (0, service_1.dispatch)(request));
/** Registers the plugin UI, public service and host-owned trigger sources. */
function registerToolPkg() {
    ToolPkg.registerUiRoute({ id: "workflow", route: exports.ROUTE, screen: web_1.default, runtime: "compose_dsl", keepAlive: true, title: { zh: "工作流", en: "Workflow" } });
    ToolPkg.registerNavigationEntry({ id: "workflow_sidebar", route: exports.ROUTE, surface: "main_sidebar_plugins", title: { zh: "工作流", en: "Workflow" }, icon: "AccountTree", order: 140 });
    ToolPkg.registerNavigationEntry({ id: "workflow_toolbox", route: exports.ROUTE, surface: "toolbox", title: { zh: "工作流", en: "Workflow" }, icon: "AccountTree", order: 140 });
    ToolPkg.registerHostEventHook({ id: "workflow_clock", source: "interval", trigger: { kind: "interval", intervalMs: 60000 }, function: onClock });
    ToolPkg.registerAppLifecycleHook({ id: "workflow_open", event: "application_on_create", function: onOpen });
    for (const topic of exports.EVENT_TOPICS)
        ToolPkg.registerHostEventHook({ id: `workflow_${topic}`, source: "broadcast", trigger: { kind: "broadcast", topic }, function: onEvent });
    return true;
}
/** Checks persisted schedules when the host emits the plugin clock event. */
async function onClock() { await (0, service_1.trigger)("schedule"); }
/** Runs cold-start entry nodes through the application lifecycle contract. */
async function onOpen() { await (0, service_1.trigger)("app_open"); }
/** Forwards normalized host events to matching workflow entry nodes. */
async function onEvent(event) {
    await (0, service_1.trigger)("event", event.eventPayload.payload.topic, { event: JSON.stringify(event.eventPayload.payload) });
}
