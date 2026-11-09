----------------------------- MODULE TurnHandoff -----------------------------
(***************************************************************************)
(* Turn-boundary execution handoff of one chat session in an Operit2       *)
(* device space.                                                           *)
(*                                                                         *)
(*   Proto = "current"  abstracts the implementation at upstream/main      *)
(*                      0c53fae18 (Binding compare-and-set, local          *)
(*                      execution lease, pre-commit sync, immediate        *)
(*                      install, AfterChangeRoute with transported         *)
(*                      history, (createdAt, origin) conflict order).      *)
(*   Proto = "fenced"   is the protocol proposed in the v3 whitepaper:     *)
(*                      generation-first conflict order, owner-only        *)
(*                      relinquish while holding the lease, commit-time    *)
(*                      self-fencing, idempotent continuation per          *)
(*                      generation, facts shipped with the handoff.        *)
(*   Takeover = "user"  adds an explicit, user-confirmed takeover when the *)
(*                      owner is unreachable (fenced protocol only).       *)
(*                                                                         *)
(* The mapping from actions to source code is in ../03-model.md.          *)
(***************************************************************************)
EXTENDS Naturals, FiniteSets, TLC

CONSTANTS N,                \* number of CoreNodes; nodes are 1..N, node 1 owns the chat initially
          MaxGen,           \* largest Binding generation explored
          MaxTs,            \* largest wall-clock value used as createdAt
          MaxSends,         \* user sends
          MaxHandoffs,      \* agent switches, user device changes and takeovers
          MaxCrashes,       \* node crashes (volatile state lost, durable state kept)
          MaxCuts,          \* link cuts (partitions)
          MaxDups,          \* redeliveries of an already delivered lifecycle message
          Proto,            \* "current" or "fenced"
          Takeover,         \* "none" or "user"
          EnableAgentSwitch,\* the model may call switch_core at a turn boundary
          EnableUserChange, \* a user may change the execution device from any node
          AllowSkew,        \* node wall clocks are not synchronized
          HoldLease         \* current protocol only: minimal patch that keeps the source
                            \* lease until the Binding commit (closes the X1 window)

ASSUME /\ N \in 2..4
       /\ Proto \in {"current", "fenced"}
       /\ Takeover \in {"none", "user"}
       /\ EnableAgentSwitch \in BOOLEAN
       /\ EnableUserChange \in BOOLEAN
       /\ AllowSkew \in BOOLEAN
       /\ HoldLease \in BOOLEAN

Nodes  == 1..N
NoNode == 0

VARIABLES
  log,       \* log[n]: Binding operations stored at n (durable)
  cache,     \* cache[n]: Binding operation currently selected in memory at n
  ver,       \* ver[n]: conflict key of the newest operation applied at n
  clock,     \* clock[n]: wall clock of n (createdAt source)
  facts,     \* facts[n]: committed turn results known at n (durable)
  up,        \* nodes that are running
  cut,       \* unordered pairs whose direct link is down
  lease,     \* lease[n]: local ChatExecutionLease held
  run,       \* run[n]: 0 when idle, otherwise the generation the running turn started under
  ho,        \* ho[n]: route-change procedure driven by node n
  msgs,      \* lifecycle messages in flight
  accepted,  \* accepted[n]: highest generation accepted for continuation (fenced, durable)
  execs,     \* history: every turn start [node, gen, kind, hist]
  cont,      \* history: cont[g] = continuations started for generation g
  stale,     \* history: a turn started under an older generation than one already started
  unfenced,  \* history: results committed after the node learned that it no longer owns the chat
  downStarts,\* history: starts while the owner of the newest generation was down
  nSends, nHo, nCrash, nCut, nDup, nFacts

vars == <<log, cache, ver, clock, facts, up, cut, lease, run, ho, msgs, accepted,
          execs, cont, stale, unfenced, downStarts,
          nSends, nHo, nCrash, nCut, nDup, nFacts>>

-----------------------------------------------------------------------------
InitOp == [owner |-> 1, gen |-> 1, ts |-> 1, origin |-> 1, kind |-> "init", wm |-> {}]

\* Conflict order.  The implementation compares (createdAt, originDeviceId,
\* sequence); the fenced protocol compares the generation first.
Key(op) == IF Proto = "current" THEN <<0, op.ts, op.origin>>
                                ELSE <<op.gen, op.ts, op.origin>>

Greater(k1, k2) ==
  \/ k1[1] > k2[1]
  \/ (k1[1] = k2[1] /\ k1[2] > k2[2])
  \/ (k1[1] = k2[1] /\ k1[2] = k2[2] /\ k1[3] > k2[3])

MaxOp(S) == CHOOSE op \in S : \A o2 \in S : ~Greater(Key(o2), Key(op))
MaxNat(S) == CHOOSE x \in S : \A y \in S : y <= x

AllOps    == UNION {log[n] : n \in Nodes}
Committed == UNION {facts[n] : n \in Nodes}

Connected(a, b) == a = b \/ {a, b} \notin cut
Reach(a, b)     == b \in up /\ Connected(a, b)

NextTs(n) == IF AllowSkew THEN clock[n] ELSE MaxNat({op.ts : op \in AllOps}) + 1
Tick(n)   == IF AllowSkew THEN [clock EXCEPT ![n] = @ + 1] ELSE clock

NewestOwner == (CHOOSE op \in AllOps : \A o2 \in AllOps : o2.gen <= op.gen).owner

Idle == [st |-> "idle", tgt |-> NoNode, exp |-> NoNode, resume |-> FALSE,
         hist |-> {}, op |-> InitOp]

\* Per-hop Binding resolution as in CoreNodeRouter.callSpaceWithOrigin.
RECURSIVE Route(_, _)
Route(n, ttl) ==
  IF cache[n].owner = n THEN n
  ELSE IF ttl = 0 THEN NoNode
  ELSE IF Reach(n, cache[n].owner) THEN Route(cache[n].owner, ttl - 1)
  ELSE NoNode

\* Minimal patch: a source that kept its lease for the route change releases
\* it when the procedure commits or aborts.
Held(h)    == Proto = "current" /\ HoldLease /\ ho[h].resume
Release(h) == IF Held(h) THEN [lease EXCEPT ![h] = FALSE] ELSE lease

\* The node still believes it owns the chat under the generation its turn started with.
CommitOK(n) == cache[n].owner = n /\ cache[n].gen = run[n]

\* A turn starts on d under generation g with model history hist.
Start(d, g, kind, hist) ==
  /\ lease' = [lease EXCEPT ![d] = TRUE]
  /\ run' = [run EXCEPT ![d] = g]
  /\ execs' = execs \cup {[node |-> d, gen |-> g, kind |-> kind, hist |-> hist]}
  /\ stale' = (stale \/ \E e \in execs : e.gen > g)
  /\ downStarts' = IF NewestOwner \notin up THEN downStarts + 1 ELSE downStarts

\* Two-way persistence synchronization pass between a and b.
Exchange(a, b) ==
  LET U    == log[a] \cup log[b]
      F    == facts[a] \cup facts[b]
      incA == log[b] \ log[a]
      incB == log[a] \ log[b]
      appA == incA # {} /\ Greater(Key(MaxOp(incA)), ver[a])
      appB == incB # {} /\ Greater(Key(MaxOp(incB)), ver[b])
  IN /\ log' = [log EXCEPT ![a] = U, ![b] = U]
     /\ facts' = [facts EXCEPT ![a] = F, ![b] = F]
     /\ cache' = [cache EXCEPT ![a] = IF appA THEN MaxOp(incA) ELSE @,
                               ![b] = IF appB THEN MaxOp(incB) ELSE @]
     /\ ver' = [ver EXCEPT ![a] = IF appA THEN Key(MaxOp(incA)) ELSE @,
                           ![b] = IF appB THEN Key(MaxOp(incB)) ELSE @]

\* Applies one directly transported Binding operation at t.
Apply(t, op) ==
  /\ log' = [log EXCEPT ![t] = @ \cup {op}]
  /\ IF Greater(Key(op), ver[t])
       THEN /\ cache' = [cache EXCEPT ![t] = op]
            /\ ver' = [ver EXCEPT ![t] = Key(op)]
       ELSE UNCHANGED <<cache, ver>>

-----------------------------------------------------------------------------
Init ==
  /\ log = [n \in Nodes |-> {InitOp}]
  /\ cache = [n \in Nodes |-> InitOp]
  /\ ver = [n \in Nodes |-> Key(InitOp)]
  /\ clock \in [Nodes -> IF AllowSkew THEN 2..3 ELSE {2}]
  /\ facts = [n \in Nodes |-> {}]
  /\ up = Nodes
  /\ cut = {}
  /\ lease = [n \in Nodes |-> FALSE]
  /\ run = [n \in Nodes |-> 0]
  /\ ho = [n \in Nodes |-> Idle]
  /\ msgs = {}
  /\ accepted = [n \in Nodes |-> IF n = 1 THEN 1 ELSE 0]
  /\ execs = {}
  /\ cont = [g \in 1..MaxGen |-> 0]
  /\ stale = FALSE
  /\ unfenced = FALSE
  /\ downStarts = 0
  /\ nSends = 0 /\ nHo = 0 /\ nCrash = 0 /\ nCut = 0 /\ nDup = 0 /\ nFacts = 0

-----------------------------------------------------------------------------
(* Execution on the node selected by the local Binding view.               *)

UserSend(n) ==
  /\ n \in up /\ nSends < MaxSends
  /\ LET d == Route(n, N) IN
       /\ d # NoNode
       /\ ~lease[d] /\ run[d] = 0
       /\ Start(d, cache[d].gen, "user", facts[d])
  /\ nSends' = nSends + 1
  /\ UNCHANGED <<log, cache, ver, clock, facts, up, cut, ho, msgs, accepted,
                 cont, unfenced, nHo, nCrash, nCut, nDup, nFacts>>

\* The turn ends normally.  The fenced protocol discards results of a turn
\* whose node no longer owns the chat (commit-time self-fencing).
EndTurn(n) ==
  /\ n \in up /\ run[n] > 0
  /\ IF Proto = "fenced" /\ ~CommitOK(n)
       THEN UNCHANGED <<facts, nFacts, unfenced>>
       ELSE /\ facts' = [facts EXCEPT ![n] = @ \cup {[gen |-> run[n], id |-> nFacts + 1]}]
            /\ nFacts' = nFacts + 1
            /\ unfenced' = (unfenced \/ ~CommitOK(n))
  /\ run' = [run EXCEPT ![n] = 0]
  /\ lease' = [lease EXCEPT ![n] = FALSE]
  /\ UNCHANGED <<log, cache, ver, clock, up, cut, ho, msgs, accepted,
                 execs, cont, stale, downStarts, nSends, nHo, nCrash, nCut, nDup>>

\* switch_core: the turn's results are committed, then the route change starts.
\* The implementation releases the local lease before the Binding commit
\* (MessageProcessingDelegate.releaseExecutionForRoute); the fenced protocol
\* keeps it until the relinquish write.
AgentSwitch(n, t) ==
  /\ EnableAgentSwitch
  /\ n \in up /\ run[n] > 0 /\ t \in Nodes \ {n} /\ Reach(n, t)
  /\ nHo < MaxHandoffs /\ cache[n].gen < MaxGen /\ ho[n].st = "idle"
  /\ Proto = "fenced" => CommitOK(n)
  /\ LET newFacts == facts[n] \cup {[gen |-> run[n], id |-> nFacts + 1]} IN
       /\ facts' = [facts EXCEPT ![n] = newFacts]
       /\ ho' = [ho EXCEPT ![n] = [st |-> "begun", tgt |-> t, exp |-> cache[n].owner,
                                   resume |-> TRUE, hist |-> newFacts, op |-> InitOp]]
  /\ nFacts' = nFacts + 1
  /\ unfenced' = (unfenced \/ ~CommitOK(n))
  /\ run' = [run EXCEPT ![n] = 0]
  /\ lease' = IF Proto = "current" /\ ~HoldLease THEN [lease EXCEPT ![n] = FALSE] ELSE lease
  /\ nHo' = nHo + 1
  /\ UNCHANGED <<log, cache, ver, clock, up, cut, msgs, accepted,
                 execs, cont, stale, downStarts, nSends, nCrash, nCut, nDup>>

\* A user selects another execution device from node h (no continuation).
\* The implementation runs changeRoute on h itself; the fenced protocol
\* sends a transfer request to the owner that h believes in.
UserChange(h, t) ==
  /\ EnableUserChange
  /\ h \in up /\ t \in Nodes /\ t # cache[h].owner
  /\ nHo < MaxHandoffs /\ cache[h].gen < MaxGen
  /\ IF Proto = "current"
       THEN /\ ho[h].st = "idle"
            /\ ho' = [ho EXCEPT ![h] = [st |-> "begun", tgt |-> t, exp |-> cache[h].owner,
                                        resume |-> FALSE, hist |-> {}, op |-> InitOp]]
            /\ UNCHANGED msgs
       ELSE /\ msgs' = msgs \cup {[type |-> "xfer", dst |-> cache[h].owner, tgt |-> t,
                                   op |-> InitOp, wm |-> {}, resume |-> FALSE, hist |-> {}]}
            /\ UNCHANGED ho
  /\ nHo' = nHo + 1
  /\ UNCHANGED <<log, cache, ver, clock, facts, up, cut, lease, run, accepted,
                 execs, cont, stale, unfenced, downStarts, nSends, nCrash, nCut, nDup, nFacts>>

-----------------------------------------------------------------------------
(* Current implementation: RuntimeRemoteLinkService.changeRoute.            *)

\* BeforeChangeRoute: acquire and release the lease on the node that the
\* expected owner resolves to.
Probe(h) ==
  /\ Proto = "current" /\ h \in up /\ ho[h].st = "begun"
  /\ LET o  == ho[h].exp
         d  == IF Reach(h, o) THEN Route(o, N) ELSE NoNode
         ok == d # NoNode /\ (~lease[d] \/ (Held(h) /\ d = h))
     IN /\ ho' = [ho EXCEPT ![h] = IF ok THEN [ho[h] EXCEPT !.st = "probed"] ELSE Idle]
        /\ lease' = IF ok THEN lease ELSE Release(h)
  /\ UNCHANGED <<log, cache, ver, clock, facts, up, cut, run, msgs, accepted,
                 execs, cont, stale, unfenced, downStarts, nSends, nHo, nCrash, nCut, nDup, nFacts>>

\* synchronizeReachablePeerForReason between the initiator and the target.
PreSync(h) ==
  /\ Proto = "current" /\ h \in up /\ ho[h].st = "probed"
  /\ LET t == ho[h].tgt IN
       IF t = h
         THEN /\ ho' = [ho EXCEPT ![h].st = "synced"]
              /\ UNCHANGED <<log, cache, ver, facts>>
         ELSE IF Reach(h, t)
           THEN /\ Exchange(h, t)
                /\ ho' = [ho EXCEPT ![h].st = "synced"]
           ELSE /\ ho' = [ho EXCEPT ![h] = Idle]
                /\ UNCHANGED <<log, cache, ver, facts>>
  /\ lease' = IF ho'[h].st = "idle" THEN Release(h) ELSE lease
  /\ UNCHANGED <<clock, up, cut, run, msgs, accepted,
                 execs, cont, stale, unfenced, downStarts, nSends, nHo, nCrash, nCut, nDup, nFacts>>

\* CoreNodeBindingStore.compareAndSet on the initiator's local store.
CAS(h) ==
  /\ Proto = "current" /\ h \in up /\ ho[h].st = "synced"
  /\ IF cache[h].owner = ho[h].exp /\ ho[h].tgt # cache[h].owner /\ NextTs(h) <= MaxTs
       THEN LET op == [owner |-> ho[h].tgt, gen |-> cache[h].gen + 1, ts |-> NextTs(h),
                       origin |-> h, kind |-> "cas", wm |-> {}] IN
            /\ log' = [log EXCEPT ![h] = @ \cup {op}]
            /\ cache' = [cache EXCEPT ![h] = op]
            /\ ver' = [ver EXCEPT ![h] = Key(op)]
            /\ clock' = Tick(h)
            /\ ho' = [ho EXCEPT ![h].st = "committed", ![h].op = op]
       ELSE /\ ho' = [ho EXCEPT ![h] = Idle]
            /\ UNCHANGED <<log, cache, ver, clock>>
  /\ lease' = Release(h)
  /\ UNCHANGED <<facts, up, cut, run, msgs, accepted,
                 execs, cont, stale, unfenced, downStarts, nSends, nHo, nCrash, nCut, nDup, nFacts>>

\* installRouteBindingOnTarget: applyImmediateOperation on the target.
Install(h) ==
  /\ Proto = "current" /\ h \in up /\ ho[h].st = "committed"
  /\ LET t == ho[h].tgt IN
       IF t = h
         THEN /\ ho' = [ho EXCEPT ![h].st = "installed"]
              /\ UNCHANGED <<log, cache, ver>>
         ELSE IF Reach(h, t)
           THEN /\ Apply(t, ho[h].op)
                /\ ho' = [ho EXCEPT ![h].st = "installed"]
           ELSE /\ ho' = [ho EXCEPT ![h] = Idle]
                /\ UNCHANGED <<log, cache, ver>>
  /\ UNCHANGED <<clock, facts, up, cut, lease, run, msgs, accepted,
                 execs, cont, stale, unfenced, downStarts, nSends, nHo, nCrash, nCut, nDup, nFacts>>

\* AfterChangeRoute carrying the transported runtime history.
SendAfter(h) ==
  /\ Proto = "current" /\ h \in up /\ ho[h].st = "installed"
  /\ msgs' = IF ho[h].resume
               THEN msgs \cup {[type |-> "after", dst |-> ho[h].tgt, tgt |-> ho[h].tgt,
                                op |-> ho[h].op, wm |-> {}, resume |-> TRUE, hist |-> ho[h].hist]}
               ELSE msgs
  /\ ho' = [ho EXCEPT ![h] = Idle]
  /\ UNCHANGED <<log, cache, ver, clock, facts, up, cut, lease, run, accepted,
                 execs, cont, stale, unfenced, downStarts, nSends, nHo, nCrash, nCut, nDup, nFacts>>

\* The lifecycle call is resolved by the Binding view at its destination and
\* resumes with the transported history.  keep = TRUE models a transport
\* resubmission after a lost response (route_forwarding).
DeliverAfter(m, keep) ==
  /\ Proto = "current" /\ m \in msgs /\ m.type = "after" /\ m.dst \in up
  /\ keep => nDup < MaxDups
  /\ msgs' = IF keep THEN msgs ELSE msgs \ {m}
  /\ nDup' = IF keep THEN nDup + 1 ELSE nDup
  /\ LET d == Route(m.dst, N) IN
       IF d # NoNode /\ ~lease[d] /\ run[d] = 0
         THEN /\ Start(d, cache[d].gen, "cont", m.hist)
              /\ cont' = [cont EXCEPT ![cache[d].gen] = @ + 1]
         ELSE UNCHANGED <<lease, run, execs, stale, downStarts, cont>>
  /\ UNCHANGED <<log, cache, ver, clock, facts, up, cut, ho, accepted,
                 unfenced, nSends, nHo, nCrash, nCut, nFacts>>

-----------------------------------------------------------------------------
(* Fenced protocol.                                                         *)

\* The owner writes (target, g+1) while it still holds its lease, then
\* releases the lease and ships the facts it committed.  A node that has
\* learned that it no longer owns the chat aborts the procedure.
Relinquish(o) ==
  /\ Proto = "fenced" /\ o \in up /\ ho[o].st = "begun"
  /\ IF cache[o].owner = o /\ NextTs(o) <= MaxTs
       THEN LET t  == ho[o].tgt
                op == [owner |-> t, gen |-> cache[o].gen + 1, ts |-> NextTs(o),
                       origin |-> o, kind |-> "cas", wm |-> facts[o]] IN
            /\ log' = [log EXCEPT ![o] = @ \cup {op}]
            /\ cache' = [cache EXCEPT ![o] = op]
            /\ ver' = [ver EXCEPT ![o] = Key(op)]
            /\ clock' = Tick(o)
            /\ msgs' = msgs \cup {[type |-> "handoff", dst |-> t, tgt |-> t, op |-> op,
                                   wm |-> facts[o], resume |-> ho[o].resume, hist |-> {}]}
       ELSE UNCHANGED <<log, cache, ver, clock, msgs>>
  /\ lease' = [lease EXCEPT ![o] = FALSE]
  /\ ho' = [ho EXCEPT ![o] = Idle]
  /\ UNCHANGED <<facts, up, cut, run, accepted,
                 execs, cont, stale, unfenced, downStarts, nSends, nHo, nCrash, nCut, nDup, nFacts>>

\* The target persists the shipped facts, applies the Binding by
\* generation-first order and starts the continuation at most once per
\* generation.
DeliverHandoff(m, keep) ==
  /\ Proto = "fenced" /\ m \in msgs /\ m.type = "handoff" /\ m.dst \in up
  /\ keep => nDup < MaxDups
  /\ msgs' = IF keep THEN msgs ELSE msgs \ {m}
  /\ nDup' = IF keep THEN nDup + 1 ELSE nDup
  /\ LET t     == m.dst
         op    == m.op
         newer == Greater(Key(op), ver[t])
         c2    == IF newer THEN op ELSE cache[t]
         owns  == c2 = op /\ op.owner = t
         hist  == facts[t] \cup m.wm
         go    == m.resume /\ owns /\ accepted[t] < op.gen /\ ~lease[t] /\ run[t] = 0
     IN /\ log' = [log EXCEPT ![t] = @ \cup {op}]
        /\ facts' = [facts EXCEPT ![t] = hist]
        /\ cache' = [cache EXCEPT ![t] = c2]
        /\ ver' = [ver EXCEPT ![t] = IF newer THEN Key(op) ELSE @]
        /\ accepted' = IF owns /\ accepted[t] < op.gen
                         THEN [accepted EXCEPT ![t] = op.gen] ELSE accepted
        /\ IF go
             THEN /\ Start(t, op.gen, "cont", hist)
                  /\ cont' = [cont EXCEPT ![op.gen] = @ + 1]
             ELSE UNCHANGED <<lease, run, execs, stale, downStarts, cont>>
  /\ UNCHANGED <<clock, up, cut, ho, unfenced, nSends, nHo, nCrash, nCut, nFacts>>

\* A device-change request reaches the node that the requester believes owns
\* the chat; only an idle owner begins a relinquish.
DeliverXfer(m) ==
  /\ Proto = "fenced" /\ m \in msgs /\ m.type = "xfer" /\ m.dst \in up
  /\ msgs' = msgs \ {m}
  /\ LET o == m.dst IN
       IF cache[o].owner = o /\ ~lease[o] /\ run[o] = 0 /\ ho[o].st = "idle"
          /\ m.tgt # o /\ cache[o].gen < MaxGen
         THEN /\ lease' = [lease EXCEPT ![o] = TRUE]
              /\ ho' = [ho EXCEPT ![o] = [Idle EXCEPT !.st = "begun", !.tgt = m.tgt]]
         ELSE UNCHANGED <<lease, ho>>
  /\ UNCHANGED <<log, cache, ver, clock, facts, up, cut, run, accepted,
                 execs, cont, stale, unfenced, downStarts, nSends, nHo, nCrash, nCut, nDup, nFacts>>

\* Explicit takeover confirmed by a user at m while the owner is unreachable.
TakeoverAt(m) ==
  /\ Proto = "fenced" /\ Takeover = "user"
  /\ m \in up /\ cache[m].owner # m /\ ~Reach(m, cache[m].owner)
  /\ ~lease[m] /\ run[m] = 0 /\ ho[m].st = "idle"
  /\ nHo < MaxHandoffs /\ cache[m].gen < MaxGen /\ NextTs(m) <= MaxTs
  /\ LET op == [owner |-> m, gen |-> cache[m].gen + 1, ts |-> NextTs(m),
                origin |-> m, kind |-> "takeover", wm |-> facts[m]] IN
       /\ log' = [log EXCEPT ![m] = @ \cup {op}]
       /\ cache' = [cache EXCEPT ![m] = op]
       /\ ver' = [ver EXCEPT ![m] = Key(op)]
       /\ accepted' = [accepted EXCEPT ![m] = op.gen]
       /\ Start(m, op.gen, "takeover", facts[m])
  /\ clock' = Tick(m)
  /\ nHo' = nHo + 1
  /\ UNCHANGED <<facts, up, cut, ho, msgs, cont, unfenced, nSends, nCrash, nCut, nDup, nFacts>>

-----------------------------------------------------------------------------
(* Environment.                                                             *)

Sync(a, b) ==
  /\ a < b /\ a \in up /\ b \in up /\ Connected(a, b)
  /\ Exchange(a, b)
  /\ UNCHANGED <<clock, up, cut, lease, run, ho, msgs, accepted,
                 execs, cont, stale, unfenced, downStarts, nSends, nHo, nCrash, nCut, nDup, nFacts>>

Crash(n) ==
  /\ nCrash < MaxCrashes /\ n \in up
  /\ up' = up \ {n}
  /\ lease' = [lease EXCEPT ![n] = FALSE]
  /\ run' = [run EXCEPT ![n] = 0]
  /\ ho' = [ho EXCEPT ![n] = Idle]
  /\ nCrash' = nCrash + 1
  /\ UNCHANGED <<log, cache, ver, clock, facts, cut, msgs, accepted,
                 execs, cont, stale, unfenced, downStarts, nSends, nHo, nCut, nDup, nFacts>>

\* Restart rebuilds the cache from the durable log (materializeBindingRecords).
Recover(n) ==
  /\ n \notin up
  /\ up' = up \cup {n}
  /\ cache' = [cache EXCEPT ![n] = MaxOp(log[n])]
  /\ ver' = [ver EXCEPT ![n] = Key(MaxOp(log[n]))]
  /\ UNCHANGED <<log, clock, facts, cut, lease, run, ho, msgs, accepted,
                 execs, cont, stale, unfenced, downStarts, nSends, nHo, nCrash, nCut, nDup, nFacts>>

CutLink(a, b) ==
  /\ a < b /\ nCut < MaxCuts /\ {a, b} \notin cut
  /\ cut' = cut \cup {{a, b}}
  /\ nCut' = nCut + 1
  /\ UNCHANGED <<log, cache, ver, clock, facts, up, lease, run, ho, msgs, accepted,
                 execs, cont, stale, unfenced, downStarts, nSends, nHo, nCrash, nDup, nFacts>>

HealLink(a, b) ==
  /\ a < b /\ {a, b} \in cut
  /\ cut' = cut \ {{a, b}}
  /\ UNCHANGED <<log, cache, ver, clock, facts, up, lease, run, ho, msgs, accepted,
                 execs, cont, stale, unfenced, downStarts, nSends, nHo, nCrash, nCut, nDup, nFacts>>

-----------------------------------------------------------------------------
Next ==
  \/ \E n \in Nodes :
       \/ UserSend(n) \/ EndTurn(n)
       \/ Probe(n) \/ PreSync(n) \/ CAS(n) \/ Install(n) \/ SendAfter(n)
       \/ Relinquish(n) \/ TakeoverAt(n)
       \/ Crash(n) \/ Recover(n)
  \/ \E n, t \in Nodes : AgentSwitch(n, t) \/ UserChange(n, t)
  \/ \E a, b \in Nodes : Sync(a, b) \/ CutLink(a, b) \/ HealLink(a, b)
  \/ \E m \in msgs, keep \in BOOLEAN : DeliverAfter(m, keep) \/ DeliverHandoff(m, keep)
  \/ \E m \in msgs : DeliverXfer(m)

Spec == Init /\ [][Next]_vars

-----------------------------------------------------------------------------
(* Properties (see ../03-model.md for their correspondence to S1-S5, L1).   *)

\* At most one node executes the chat at any time.
Mutex == Cardinality({n \in Nodes : run[n] > 0}) <= 1

\* S1: every generation is advanced by one node only.
SingleGen == \A e1, e2 \in execs : e1.gen = e2.gen => e1.node = e2.node

\* S1 under takeover: a generation is advanced by two nodes only after an
\* explicit takeover at that or an earlier generation (forks start at takeovers).
SingleGenUnlessTakeover ==
  \A e1, e2 \in execs :
    (e1.gen = e2.gen /\ e1.node # e2.node) =>
      \E op \in AllOps : op.kind = "takeover" /\ op.gen <= e1.gen

\* S2: no turn starts under a generation older than one that already started.
NoStaleStart == ~stale

\* S2: no results are committed after the node learned it is not the owner.
NoUnfencedCommit == ~unfenced

\* S3: a turn of generation g sees every committed fact of older generations.
FactsComplete == \A e \in execs : \A f \in Committed : f.gen < e.gen => f \in e.hist

\* S3 under takeover: every missing fact is explained by a takeover whose
\* generation lies between the fact's and the turn's generation, so that the
\* generation tags identify the fork.
ForkOnlyAtTakeover ==
  \A e \in execs : \A f \in Committed :
    (f.gen < e.gen /\ f \notin e.hist) =>
      \E op \in AllOps : op.kind = "takeover" /\ f.gen <= op.gen /\ op.gen <= e.gen

\* S4: at most one continuation per generation.
ContOnce == \A g \in 1..MaxGen : cont[g] <= 1

\* L1 witness: no progress while the newest owner is down.
NoProgressWhileOwnerDown == downStarts = 0

\* Convergence: once every node is up and connected, all logs are equal and
\* nothing is in flight, all nodes select the same Binding and every route
\* resolves to an owner.
Quiescent ==
  /\ msgs = {} /\ up = Nodes /\ cut = {}
  /\ \A a, b \in Nodes : log[a] = log[b]
  /\ \A n \in Nodes : ho[n].st = "idle"
ConvergedRoutes ==
  Quiescent => /\ \A a, b \in Nodes : cache[a] = cache[b]
               /\ \A n \in Nodes : Route(n, N) # NoNode
=============================================================================
