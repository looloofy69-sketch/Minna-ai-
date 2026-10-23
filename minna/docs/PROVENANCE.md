# Provenance

Upstream: https://github.com/Loofy147/llms-mcp-android, branch main, commit `78afd5d3d7716fe31a5f109a5796eb3db7f99970` (read 2026-10-11/12).

The 15 files below were copied unchanged: each has the same SHA-256 as its upstream original (checked by script, 15 identical, 0 different). Only the directory changed: `app/src/{main,test}/java/...` became `core/src/{main,test}/kotlin/...`; package names are kept.

| Extracted file | SHA-256 |
|---|---|
| `core/src/main/kotlin/com/hicham/llmchat/runtime/ActionCatalog.kt` | `59b361166b162f88fe6de87ada75df3981c19ddc7ce722d46f5643d6301a5ab9` |
| `core/src/main/kotlin/com/hicham/llmchat/runtime/AgentRuntime.kt` | `e6a33367e52fab9660b539b2fa6794369d61a844091355c8ae61d8b24769129c` |
| `core/src/main/kotlin/com/hicham/llmchat/runtime/ApprovalStore.kt` | `c76517e5536aec2da8fb0afa188feb8a819cb38c7dd52146a6cda260f4c54c86` |
| `core/src/main/kotlin/com/hicham/llmchat/runtime/CapabilityExecutor.kt` | `85eced49a7fe50e51a0253bb34746dd9afc896b683863d0372633eb39b6a3310` |
| `core/src/main/kotlin/com/hicham/llmchat/runtime/EgressPolicy.kt` | `7b3ae7bd789abe12b47e451ce3a45ee65a2255b5b4c8488a7259299ddc57e951` |
| `core/src/main/kotlin/com/hicham/llmchat/runtime/NativeActions.kt` | `5972ee60b561b37daa3d8129e0203a8aa2ff266441b3a385433b8f375e5dfc59` |
| `core/src/main/kotlin/com/hicham/llmchat/runtime/PolicyEngine.kt` | `8e6efe730dcd6324a42037aa1d5b07f1587280602ec156997b5d59e50379c89d` |
| `core/src/main/kotlin/com/hicham/llmchat/runtime/RuntimeModel.kt` | `bcdf2e60323231a5735c59a673de44f33aaeea865eff924986137ecebb71a889` |
| `core/src/main/kotlin/com/hicham/llmchat/runtime/RuntimeStore.kt` | `5dd9830be71339923d8ab9192c46a3a97cf126a4f98036f773b5c8852a79747e` |
| `core/src/test/kotlin/com/hicham/llmchat/runtime/AgentRuntimeTest.kt` | `e2b7ab51836493f97291baf835cadea4e601b4e4f6628972a2855e57e8ac182d` |
| `core/src/test/kotlin/com/hicham/llmchat/runtime/ControlPlaneGateTest.kt` | `4f7b715323cb7a7c7b8e740f5601f8e1c1722778caa97cd31e40cd84bae0cecf` |
| `core/src/test/kotlin/com/hicham/llmchat/runtime/EffectBoundaryTest.kt` | `c62d06cbd6e683be8970dde6f162e23f4f37f800e204a0479bcc8d030927a88f` |
| `core/src/test/kotlin/com/hicham/llmchat/runtime/EgressPolicyTest.kt` | `60ed22a6e337bfacd43c06d0589cf14d7751d4c6aef7ae45858728a09db4f037` |
| `core/src/test/kotlin/com/hicham/llmchat/runtime/PersistentApprovalTest.kt` | `7477ceffdf0b848d38d8a63b9919cff2ceae42933210d511f0fc73f72b32a114` |
| `core/src/test/kotlin/com/hicham/llmchat/runtime/UnknownEffectReconciliationTest.kt` | `526c71405198d4933c973f4e39f306f4471603a511e05fb0e041d0fa874eaa33` |

New files (not from upstream): `core/src/test/kotlin/com/hicham/llmchat/runtime/{ApprovalOneUseUnderContentionTest,KnownGapCharacterizationTest,SafetyBranchCoverageTest}.kt`, everything under `scripts/`, `docs/`, the Gradle files and CI workflow.

## Not extracted, and why

| Upstream file(s) | Reason |
|---|---|
| `runtime/AndroidRuntimeFactory.kt` | 1 Android import; it is the Android composition root |
| `runtime/t2/*` | Android service and store (5 Android imports) |
| `data/CredentialStore.kt`, `data/SettingsStore.kt` | Android Keystore and Context |
| `data/ToolRegistry.kt`, `data/RuntimeToolGateway.kt`, `data/AnthropicClient.kt`, `data/ModelProvider.kt`, `model/ChatModels.kt` | Use org.json and OkHttp, which need Maven Central to build; not verifiable in the authoring sandbox. Candidates for a later extraction step |
| `ui/*`, `MainActivity.kt`, `AssistantRuntime.kt` | Android UI and facade |
