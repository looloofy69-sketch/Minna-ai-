package com.hicham.llmchat.runtime

import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * Closes a gap found by mutation testing (docs/EVIDENCE.md, mutant `consumed_approval_executes`):
 * replacing the NOT_PENDING branch of AgentRuntime.resolveApproval with "execute anyway" left every
 * upstream test green.
 *
 * State under test: the approval was already consumed by another resolver, but the Run is still
 * WAITING_APPROVAL (a concurrent resolver that has not yet saved RUNNING, or a restart between
 * consume and execute). A second resolver must fail closed and must never reach the executor.
 */
class ApprovalOneUseUnderContentionTest {
    // No idempotency key on purpose: the effect identity is random, so the effect-replay guard cannot
    // help and only the approval's one-use rule can stop a second execution.
    private fun action() = ActionDefinition(
        id = "send_message",
        version = 1,
        purpose = "one-use approval contention test",
        capabilities = listOf(CapabilityDescriptor("message.send", EffectClass.REVERSIBLE, setOf("outbox"))),
        approvalMode = ApprovalMode.REQUIRED,
        reduce = { _, _ -> ActionExecution(output = mapOf("sent" to "true")) },
        plan = { input -> ActionPlan(listOf(CapabilityInvocationSpec("message.send", setOf("outbox"), mapOf("to" to (input["to"] ?: ""))))) }
    )

    private class Fixture {
        var executions = 0
        val approvals = InMemoryApprovalStore()
        val runtime = AgentRuntime(
            ActionCatalog(listOf(ApprovalOneUseUnderContentionTest().action())),
            PolicyEngine(),
            RegistryCapabilityExecutor(mapOf("message.send" to { _ -> executions++; CapabilityExecution() })),
            InMemoryRuntimeStore(),
            approvals
        )
        fun pending() = runtime.activate(ActivationRequest(ActivationSource.USER_UI, "send_message", mapOf("to" to "customer-1"), "alice"))
    }

    @Test
    fun controlNormalApprovalExecutesExactlyOnce() {
        val f = Fixture()
        val pending = f.pending()
        assertEquals(RunStatus.WAITING_APPROVAL, pending.status)
        val resolved = f.runtime.resolveApproval(pending.id, pending.approvalId!!, ApprovalDecision.APPROVED, "alice")!!
        assertEquals(RunStatus.SUCCEEDED, resolved.status)
        assertEquals(1, f.executions)
    }

    @Test
    fun secondResolverOfAnAlreadyConsumedApprovalFailsClosedAndNeverExecutes() {
        val f = Fixture()
        val pending = f.pending()
        assertEquals(RunStatus.WAITING_APPROVAL, pending.status)
        val context = f.approvals.load(pending.approvalId!!)!!

        // The "first resolver" consumed the approval but has not advanced the Run yet.
        assertEquals(
            ApprovalConsumption.CONSUMED,
            f.approvals.consume(context.approvalId, pending.id, "alice", context.fingerprint, ApprovalDecision.APPROVED, "alice")
        )

        val second = f.runtime.resolveApproval(pending.id, pending.approvalId!!, ApprovalDecision.APPROVED, "alice")!!
        assertEquals(RunStatus.FAILED, second.status)
        assertEquals("Approval already consumed", second.denialReason)
        assertEquals(0, f.executions)
    }
}
