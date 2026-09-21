(function() {
    var root = typeof globalThis !== 'undefined'
        ? globalThis
        : (typeof window !== 'undefined' ? window : this);
    var windowRef = typeof window !== 'undefined' ? window : root;

    function expose(name, value) {
        var key = name == null ? '' : String(name).trim();
        if (!key || value === undefined) {
            return;
        }
        root[key] = value;
        windowRef[key] = value;
    }

    expose('__operitExpose', expose);
    root.window = windowRef;

    function ensureCallRegistry() {
        var registry = root.__operitExecutionCallRegistry;
        if (!registry || typeof registry !== 'object') {
            registry = {};
            root.__operitExecutionCallRegistry = registry;
        }
        return registry;
    }

    function normalizeCallId(callId) {
        return callId == null ? '' : String(callId).trim();
    }

    function getCallState(callId) {
        var resolvedCallId = normalizeCallId(callId);
        if (!resolvedCallId) {
            return null;
        }
        return ensureCallRegistry()[resolvedCallId] || null;
    }

    function registerCallSession(callId, params) {
        var resolvedCallId = normalizeCallId(callId);
        if (!resolvedCallId) {
            throw new Error('callId is required');
        }
        var registry = ensureCallRegistry();
        var state = registry[resolvedCallId];
        var callState = state && typeof state === 'object' ? state : {};
        callState.callId = resolvedCallId;
        callState.params = params && typeof params === 'object' ? params : {};
        callState.completed = false;
        callState.safetyTimeout = null;
        callState.safetyTimeoutFinal = null;
        callState.lastExecStage = '';
        callState.lastExecFunction = '';
        callState.lastModulePath = '';
        callState.lastRequireRequest = '';
        callState.lastRequireFrom = '';
        callState.lastRequireResolved = '';
        callState.currentModule = null;
        callState.currentModuleExports = null;
        callState.timerIds = {};
        callState.previousCallId = '';
        callState.previousCallRuntime = null;
        registry[resolvedCallId] = callState;
        return callState;
    }

    function registerCallTimer(callId, timerId) {
        var callState = getCallState(callId);
        if (!callState) {
            return;
        }
        if (!callState.timerIds || typeof callState.timerIds !== 'object') {
            callState.timerIds = {};
        }
        callState.timerIds[String(timerId)] = true;
    }

    function unregisterCallTimer(callId, timerId) {
        var callState = getCallState(callId);
        if (!callState || !callState.timerIds || typeof callState.timerIds !== 'object') {
            return;
        }
        delete callState.timerIds[String(timerId)];
    }

    function clearCallTimers(callState) {
        if (!callState || !callState.timerIds || typeof callState.timerIds !== 'object') {
            return;
        }
        var timerIds = Object.keys(callState.timerIds);
        for (var index = 0; index < timerIds.length; index += 1) {
            var timerId = timerIds[index];
            try {
                delete windowRef[timerId];
            } catch (_deleteTimerError) {
                windowRef[timerId] = undefined;
            }
        }
        callState.timerIds = {};
    }

    function cleanupCallSession(callId) {
        var resolvedCallId = normalizeCallId(callId);
        if (!resolvedCallId) {
            return;
        }
        var registry = ensureCallRegistry();
        clearCallTimers(registry[resolvedCallId]);
        delete registry[resolvedCallId];
    }

    function cancelCallSession(callId) {
        var resolvedCallId = normalizeCallId(callId);
        if (!resolvedCallId) {
            return;
        }
        var callState = getCallState(resolvedCallId);
        if (!callState) {
            return;
        }
        callState.completed = true;
        if (root.__operitCurrentCallId === resolvedCallId) {
            root.__operitCurrentCallId = normalizeCallId(callState.previousCallId);
        }
        if (root.__operit_call_runtime_ref === callState.callRuntime) {
            if (callState.previousCallRuntime && typeof callState.previousCallRuntime === 'object') {
                root.__operit_call_runtime_ref = callState.previousCallRuntime;
            } else {
                delete root.__operit_call_runtime_ref;
            }
        }
        cleanupCallSession(resolvedCallId);
    }

    function buildRuntimeContext(callId) {
        var callState = getCallState(callId);
        var mapping = [
            ['lastExecStage', 'stage'],
            ['lastExecFunction', 'function'],
            ['lastModulePath', 'module'],
            ['lastRequireRequest', 'require'],
            ['lastRequireFrom', 'from'],
            ['lastRequireResolved', 'resolved']
        ];
        var parts = [];
        for (var i = 0; i < mapping.length; i += 1) {
            var key = mapping[i][0];
            var label = mapping[i][1];
            var value = callState ? callState[key] : undefined;
            if (value != null && String(value).trim().length > 0) {
                parts.push(label + '=' + String(value));
            }
        }
        return parts.join(', ');
    }

    expose('__operitGetCallState', getCallState);
    expose('__operitRegisterCallSession', registerCallSession);
    expose('__operitRegisterCallTimer', registerCallTimer);
    expose('__operitUnregisterCallTimer', unregisterCallTimer);
    expose('__operitCleanupCallSession', cleanupCallSession);
    expose('__operitCancelCallSession', cancelCallSession);
    expose('__operitBuildRuntimeContext', buildRuntimeContext);

    expose('__operitGetActiveModuleExports', function() {
        if (
            root.__operitActiveModule &&
            typeof root.__operitActiveModule === 'object' &&
            root.__operitActiveModule.exports
        ) {
            return root.__operitActiveModule.exports;
        }
        var exportsRef = root.__operitActiveModuleExports;
        return exportsRef && typeof exportsRef === 'object' ? exportsRef : exportsRef || null;
    });
})();
