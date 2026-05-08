You maintain a concise global audit memory for future audit agents.

Update the existing global memory by folding in durable observations from the
latest round summary. The goal is an accumulated cross-round audit view, not a
per-round recap.

This memory is optional context only. Findings are stored separately.

Write the updated memory in this exact structure:

# Global Audit Memory

## Scope Touched
- files/contracts/flows that have mattered across rounds, with short issue-direction notes

## Issue Directions Seen
- recurring or promising vulnerability directions seen across the audit

## Useful Context
- compact cross-round observations 

Rules:
- keep it compact
- preserve useful prior context while integrating new durable observations
- prefer stable cross-round patterns over latest-round details
- fold repeated wording into a single clearer observation
- keep the memory descriptive rather than prescriptive

## Existing Global Memory
# Global Audit Memory

## Scope Touched
- `AaveBoost.sol`: persistent hotspot across rounds; `proxyDeposit` and `setPool` drive most security-relevant behavior and failure modes.
- `interfaces/IAavePool.sol`: used mainly as ABI/semantic reference; external `pool.deposit` trust boundary remains important but lightly validated.

## Issue Directions Seen
- Reward extraction paths tied to weak/incorrect deposit accounting (including zero-cost reward accrual scenarios).
- Allowance lifecycle risk around pool rotation and repeated approval patterns (stale unlimited approvals, repeated-max approval edge behavior).
- `proxyDeposit` asset-flow correctness issues: funding source assumptions, fallback/revert behavior, and resulting DoS/broken-path outcomes.
- Pool configuration validation gaps causing misconfiguration-driven risk.

## Useful Context
- Cross-agent convergence is strong on `AaveBoost.sol` core flows; most durable issues come from shared focus on `proxyDeposit` + `setPool`.
- Broader speculative/hygiene directions were explored but repeatedly deprioritized versus exploitability-grounded flow/approval/configuration flaws.
- External pool behavior is a recurring dependency in threat reasoning, but verification depth on that boundary has remained limited.


## Latest Round Summary
# Round 2 Summary

## Agent: codex_1
- files touched: `AaveBoost.sol`, `interfaces/IAavePool.sol`
- files revisited / highest-attention files: `AaveBoost.sol` (constructor, `setPool`, `proxyDeposit` branches), `IAavePool.deposit` signature
- main issue directions investigated: fallback behavior when reward balance is below `REWARD`; interaction between fallback deposit call and previously granted infinite AAVE allowance to pool
- promising but not retained directions: none shown in the log output beyond the retained fallback-drain path

## Agent: opencode_1
- files touched: `AaveBoost.sol`, `interfaces/IAavePool.sol`, `../@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol`
- files revisited / highest-attention files: `AaveBoost.sol` (especially `proxyDeposit` and `setPool`)
- main issue directions investigated: asset/type mismatch in reward path, absence of token recovery/sweep, missing config-change events, zero-recipient handling, `uint128` overflow edge case
- promising but not retained directions: lock/burn/misconfiguration and observability issues (F-007 to F-010 in its output) were explored but not retained after merge; its F-006 framing (type-confusion lock path) also not retained

## Cross-Agent Status
- main overlap in file/area attention: both concentrated on `AaveBoost.sol`, especially `proxyDeposit` control-flow and token movement assumptions
- notable differences in attention: `codex_1` focused on exploitability of fallback + allowance for direct treasury drain; `opencode_1` emphasized UX/misconfiguration and recoverability patterns, and also checked `SafeERC20.sol`
- underexplored but suspicious files/functions if clearly supported by the logs: no additional underexplored Solidity files in scope (only two in-scope files; executable risk surface is primarily `AaveBoost.proxyDeposit`/`setPool`)

## Retained Findings
- `F-006` retained: when `aave.balanceOf(AaveBoost) < REWARD`, fallback `proxyDeposit` can still route contract-held AAVE to attacker-controlled recipient positions (via pool pull and prior allowance), enabling theft of residual AAVE inventory.


Output only markdown.
