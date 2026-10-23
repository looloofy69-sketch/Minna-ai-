package com.hicham.llmchat.runtime

import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * Characterization tests. They pin CURRENT upstream behaviour that is acceptable for a single-user,
 * on-device runtime but is a gap for a product that acts on a user's behalf or serves several users.
 * They are NOT endorsements: each names the milestone expected to flip it (docs/BUILD_PLAN.md).
 * When a gap is closed, change the assertion in the same commit so the change is deliberate.
 */
class KnownGapCharacterizationTest {
    private val request = ActivationRequest(ActivationSource.USER_UI, "ship_parcel", emptyMap(), "alice")

    private fun highImpactAction(approval: ApprovalMode) = ActionDefinition(
        id = "ship_parcel",
        version = 1,
        purpose = "characterization",
        capabilities = listOf(CapabilityDescriptor("courier.parcel.create", EffectClass.HIGH_IMPACT, setOf("courier"))),
        approvalMode = approval,
        reduce = { _, _ -> ActionExecution() },
        plan = { ActionPlan(listOf(CapabilityInvocationSpec("courier.parcel.create", setOf("courier")))) }
    )

    /** GAP-02 (flips in M1): once HIGH_IMPACT is enabled, approval is opt-in per Action, not enforced by policy. */
    @Test
    fun gap02_highImpactWithoutDeclaredApprovalIsAllowedWhenHighImpactIsEnabled() {
        val decision = PolicyEngine(allowHighImpact = true).evaluate(request, highImpactAction(ApprovalMode.NEVER))
        assertEquals(PolicyDecision.ALLOW, decision)
    }

    /** Control for GAP-02: the same Action is denied under the upstream default (HIGH_IMPACT disabled). */
    @Test
    fun gap02_control_highImpactIsDeniedByDefault() {
        assertEquals(PolicyDecision.DENY, PolicyEngine().evaluate(request, highImpactAction(ApprovalMode.NEVER)))
    }

    /** GAP-03 (flips in M3, before any multi-user surface): the approver identity is recorded but never authorized. */
    @Test
    fun gap03_anyApproverIdentityCanResolveAnApproval() {
        var executions = 0
        val action = ActionDefinition(
            id = "send_message",
            version = 1,
            purpose = "characterization",
            capabilities = listOf(CapabilityDescriptor("message.send", EffectClass.REVERSIBLE, setOf("outbox"))),
            approvalMode = ApprovalMode.REQUIRED,
            reduce = { _, _ -> ActionExecution() },
            plan = { ActionPlan(listOf(CapabilityInvocationSpec("message.send", setOf("outbox")))) }
        )
        val approvals = InMemoryApprovalStore()
        val runtime = AgentRuntime(
            ActionCatalog(listOf(action)),
            PolicyEngine(),
            RegistryCapabilityExecutor(mapOf("message.send" to { _ -> executions++; CapabilityExecution() })),
            InMemoryRuntimeStore(),
            approvals
        )
        val pending = runtime.activate(ActivationRequest(ActivationSource.USER_UI, "send_message", emptyMap(), "alice"))
        val resolved = runtime.resolveApproval(pending.id, pending.approvalId!!, ApprovalDecision.APPROVED, "mallory")!!
        assertEquals(RunStatus.SUCCEEDED, resolved.status)
        assertEquals("mallory", approvals.load(pending.approvalId!!)?.resolvedBy)
        assertEquals(1, executions)
    }
}
