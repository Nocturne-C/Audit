# Merge View - Round 1

## Summary
- total findings: 5
- new findings: 5
- updated existing findings: 0
- rejected candidates: 9

## Finding Actions
- rewritten_agent_signal: 5

## New Or Updated Findings
| id | action | severity | confidence | source | title | best match |
| --- | --- | --- | --- | --- | --- | --- |
| F-001 | rewritten_agent_signal | Critical | high | codex_1,opencode_1 | `proxyDeposit` can be farmed with zero amount to drain reward treasury | codex_1:0.553 Unbounded reward farming allows near-zero-cost drain of reward treasury |
| F-002 | rewritten_agent_signal | High | high | codex_1,opencode_1 | Historical pools retain unlimited AAVE allowance after `setPool` | opencode_1:0.62 setPool does not revoke infinite AAVE allowance from the old pool |
| F-003 | rewritten_agent_signal | High | medium | codex_1,opencode_1 | `proxyDeposit` does not source the deposited `asset` from user, causing broken deposits and DoS paths | opencode_1:0.554 proxyDeposit never transfers the deposit asset from the user to the contract |
| F-004 | rewritten_agent_signal | Medium | high | opencode_1 | `setPool` cannot update reward on same pool due max-allowance overflow in `safeIncreaseAllowance` | opencode_1:0.461 REWARD update coupled to pool change — safeIncreaseAllowance overflow blocks same-pool updates |
| F-005 | rewritten_agent_signal | Low | medium | codex_1,opencode_1 | `setPool` lacks zero/non-contract validation and can brick deposits if misconfigured | codex_1:0.486 Pool address can be set to non-contract/zero, enabling user-fund capture without real deposit |

## Rejection Reasons
- duplicate_or_subsumed: 1
- low_impact_or_operational: 1
- other: 4
- trust_or_owner_model: 2
- unsupported_or_speculative: 1

## Rejected Candidates
| category | source | title | reason |
| --- | --- | --- | --- |
| trust_or_owner_model | opencode_1 | No withdrawal function — tokens permanently locked in the contract | Not reliably true as a security issue in this design scope; locked-recovery behavior may be intentional, and owner can already redirect AAVE via pool-allowance control. More of design/governance policy than exploitable vulnerability. |
| duplicate_or_subsumed | opencode_1 | Owner can set malicious pool to drain all AAVE via infinite allowance | Privileged-owner trust assumption, not a permissionless exploit. This is expected capability of `onlyOwner` and overlaps with governance risk rather than a standalone vulnerability. |
| unsupported_or_speculative | opencode_1 | Unrestricted asset parameter allows draining any token held by the contract | Contract only approves AAVE to pool; draining arbitrary tokens via `pool.deposit(asset,...)` is not generally feasible without corresponding allowance/funding and is unsupported by current code. |
| other | opencode_1 | Potential re-entrancy through pool.deposit call after AAVE transfer | No exploitable mutable state dependency was identified; claimed amplification is unnecessary because repeated direct calls already achieve reward draining. |
| low_impact_or_operational | opencode_1 | Missing events for all state-changing functions | Observability issue only; no direct protocol-level fund-loss/theft/insolvency/DoS impact. |
| other | opencode_1 | No zero-address validation for recipient and asset in proxyDeposit | Primarily caller-self-harm/input-sanity concern; no clear permissionless protocol exploit established from current code alone. |
| other | opencode_1 | REWARD uses uint128 but allowance and deposits operate on uint256 | Type-width difference is intentional/benign under checked arithmetic and does not create a concrete exploit path. |
| other | codex_1,opencode_1 | Pool address can be set to non-contract/zero, enabling user-fund capture without real deposit | The specific fund-capture claim is overstated for Solidity 0.8.4 high-level external calls (invalid target reverts). Retained a downgraded misconfiguration-DoS variant instead. |
| trust_or_owner_model | opencode_1 | setPool does not validate that newReward_ is non-zero | `REWARD=0` is a parameter choice, not inherently exploitable; economic undesirability alone is governance/configuration policy, not a standalone vulnerability. |
