package com.hicham.llmchat.runtime

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Each test kills one mutant that SURVIVED the upstream suite (scripts/mutation_check.py, docs/EVIDENCE.md).
 * Two of the controls below (scope check, egress data-class check) are ticked as implemented in the
 * upstream review checklist, yet no upstream test failed when the control was removed.
 */
class SafetyBranchCoverageTest {
    private class Counter { var n = 0 }

    private fun sendAction(
        approval: ApprovalMode = ApprovalMode.NEVER,
        plan: (Map<String, String>) -> ActionPlan = { ActionPlan(listOf(CapabilityInvocationSpec("message.send", setOf("outbox")))) }
    ) = ActionDefinition(
        id = "send_message",
        version = 1,
        purpose = "safety branch coverage",
        capabilities = listOf(CapabilityDescriptor("message.send", EffectClass.REVERSIBLE, setOf("outbox"))),
        approvalMode = approval,
        reduce = { _, _ -> ActionExecution() },
        plan = plan
    )

    private fun runtime(action: ActionDefinition, counter: Counter) = AgentRuntime(
        ActionCatalog(listOf(action)),
        PolicyEngine(),
        RegistryCapabilityExecutor(mapOf("message.send" to { _ -> counter.n++; CapabilityExecution() })),
        InMemoryRuntimeStore(),
        InMemoryApprovalStore()
    )

    private fun request(identity: String = "alice") =
        ActivationRequest(ActivationSource.USER_UI, "send_message", mapOf("to" to "c1"), identity)

    /** Kills mutant `denied_approval_executes`. */
    @Test
    fun deniedApprovalEndsDeniedAndNeverExecutes() {
        val c = Counter()
        val rt = runtime(sendAction(ApprovalMode.REQUIRED), c)
        val pending = rt.activate(request())
        assertEquals(RunStatus.WAITING_APPROVAL, pending.status)
        val resolved = rt.resolveApproval(pending.id, pending.approvalId!!, ApprovalDecision.DENIED, "alice")!!
        assertEquals(RunStatus.DENIED, resolved.status)
        assertEquals("Approval denied", resolved.denialReason)
        assertEquals(0, c.n)
    }

    /** Kills mutant `approved_plan_drift_unchecked`: the plan changes between approval request and resolution. */
    @Test
    fun approvalIsRejectedWhenThePlanDriftsAfterItWasRequested() {
        val c = Counter()
        var planCalls = 0
        val action = sendAction(ApprovalMode.REQUIRED) { input ->
            planCalls++
            ActionPlan(listOf(CapabilityInvocationSpec("message.send", setOf("outbox"), mapOf("to" to (input["to"] ?: ""), "variant" to planCalls.toString()))))
        }
        val rt = runtime(action, c)
        val pending = rt.activate(request())
        assertEquals(RunStatus.WAITING_APPROVAL, pending.status)
        val resolved = rt.resolveApproval(pending.id, pending.approvalId!!, ApprovalDecision.APPROVED, "alice")!!
        assertEquals(RunStatus.FAILED, resolved.status)
        assertEquals("Approved operation no longer matches", resolved.denialReason)
        assertEquals(0, c.n)
    }

    /** Kills mutant `scope_escalation_unchecked`. */
    @Test
    fun invocationScopeBeyondTheDeclaredCapabilityScopeIsRejectedBeforeExecution() {
        val c = Counter()
        val action = sendAction { ActionPlan(listOf(CapabilityInvocationSpec("message.send", setOf("outbox", "contacts")))) }
        val run = runtime(action, c).activate(request())
        assertEquals(RunStatus.FAILED, run.status)
        assertTrue(run.denialReason.orEmpty().contains("scope exceeds"))
        assertEquals(0, c.n)
    }

    /** Kills mutant `blank_identity_allowed`. */
    @Test
    fun blankIdentityIsDeniedAndNeverExecutes() {
        val c = Counter()
        val run = runtime(sendAction(), c).activate(request(identity = "  "))
        assertEquals(RunStatus.DENIED, run.status)
        assertEquals(0, c.n)
        assertEquals(PolicyDecision.DENY, PolicyEngine().evaluate(request(identity = ""), sendAction()))
    }

    /** Kills mutant `egress_data_class_unchecked`. */
    @Test
    fun egressDeniesDataClassesOutsideTheAllowedSet() {
        val policy = AllowlistEgressPolicy(setOf("api.example.test"), setOf(EgressDataClass.USER_CONTENT))
        val ok = policy.decide(EgressRequest("https://api.example.test/v1/messages", "chat", setOf(EgressDataClass.USER_CONTENT)))
        assertEquals(EgressDecision.ALLOW, ok)
        val denied = policy.decide(
            EgressRequest("https://api.example.test/v1/messages", "chat", setOf(EgressDataClass.USER_CONTENT, EgressDataClass.CREDENTIAL))
        )
        assertTrue(denied is EgressDecision.DENY)
        assertTrue((denied as EgressDecision.DENY).reason.contains("CREDENTIAL"))
    }
}
