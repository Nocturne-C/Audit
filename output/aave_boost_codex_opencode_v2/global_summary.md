# Global Audit Memory

## Scope Touched
- `AaveBoost.sol`: consistent hotspot; `proxyDeposit` and `setPool` remain the dominant security surface, especially fallback branches and pool-approval interactions.
- `interfaces/IAavePool.sol`: recurring trust-boundary/ABI reference for `deposit`; external pool pull semantics materially affect exploitability assumptions.
- `@openzeppelin/.../SafeERC20.sol`: briefly reviewed as dependency context; no durable independent issue direction from this file.

## Issue Directions Seen
- Reward-path/accounting flaws enabling value extraction, including low/zero-cost reward accrual and fallback-triggered misuse when reward funding is insufficient.
- `proxyDeposit` asset-flow correctness risk: funding-source assumptions, branch/revert behavior, and recipient-controlled routing outcomes.
- Allowance lifecycle and pool-rotation risk: persistent concern around stale/infinite approvals and their interaction with fallback deposit paths.
- Configuration validation gaps in pool setup that can turn misconfiguration into security-relevant behavior.

## Useful Context
- Cross-round convergence remains strong on `AaveBoost.sol` core flows; exploitability-grounded conclusions repeatedly come from `proxyDeposit` + `setPool` interplay.
- A durable retained pattern is fallback behavior under low reward balance combining with prior pool allowance to expose contract-held AAVE to recipient-directed drain scenarios.
- Broader UX/observability/recoverability ideas were explored multiple times but have not remained primary versus flow/approval/configuration exploit paths.
- External pool behavior is repeatedly central to threat reasoning, while deep validation of that boundary is still comparatively limited.
