# Merge View - Round 2

## Summary
- total findings: 6
- new findings: 1
- updated existing findings: 1
- rejected candidates: 5

## Finding Actions
- existing_preserved: 4
- existing_rewritten: 1
- rewritten_agent_signal: 1

## New Or Updated Findings
| id | action | severity | confidence | source | title | best match |
| --- | --- | --- | --- | --- | --- | --- |
| F-003 | existing_rewritten | High | medium | codex_1,opencode_1 | `proxyDeposit` does not source the deposited `asset` from user, causing broken deposits and DoS paths | opencode_1:0.406 proxyDeposit allows address(0) recipient — tokens may be burned depending on pool implementation |
| F-006 | rewritten_agent_signal | High | medium | codex_1 | Fallback branch can drain remaining AAVE from the contract when rewards are below threshold | codex_1:0.552 Fallback branch allows free theft of remaining AAVE once balance drops below REWARD |

## Rejection Reasons
- low_impact_or_operational: 2
- other: 2
- trust_or_owner_model: 1

## Rejected Candidates
| category | source | title | reason |
| --- | --- | --- | --- |
| other | opencode_1 | proxyDeposit reward path transfers aave but deposits arbitrary asset — type confusion causes permanent fund lock when asset != aave | If `pool.deposit` reverts, the whole transaction reverts and the prior `safeTransferFrom` is rolled back; user AAVE is not permanently locked by this path. |
| low_impact_or_operational | opencode_1 | No token sweep function — ERC20 tokens sent directly to the contract are permanently locked | Primarily an operational/design limitation for unsolicited token transfers, not a concrete exploitable protocol vulnerability from this code. |
| low_impact_or_operational | opencode_1 | setPool does not emit events for pool or REWARD state changes | Informational observability issue without direct security impact. |
| other | opencode_1 | proxyDeposit allows address(0) recipient — tokens may be burned depending on pool implementation | Heavily dependent on unknown downstream pool behavior and mostly user-self-inflicted; no concrete protocol-level exploit demonstrated from this contract alone. |
| trust_or_owner_model | opencode_1 | uint128 overflow in amount + REWARD expression causes theoretical DoS for reward-path deposits | Requires extreme privileged misconfiguration near `type(uint128).max`; treated as unrealistic/theoretical rather than a reportable protocol-risk condition. |
