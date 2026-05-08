# Audit Report

**Total findings:** 6

## Critical (1)

### F-001: `proxyDeposit` can be farmed with zero amount to drain reward treasury

**Confidence:** high | **Locations:** `AaveBoost.sol:48, AaveBoost.sol:49, AaveBoost.sol:50`

The reward branch is gated only by `aave.balanceOf(address(this)) >= REWARD` and does not enforce `amount > 0` or any per-user rate/accounting. Calling `proxyDeposit` with `amount = 0` still reaches `pool.deposit(..., amount + REWARD, ...)`, allowing repeated extraction of `REWARD` from contract-held AAVE.

**Impact:** Any account can repeatedly consume the subsidy and redirect deposits to itself, draining the contract's reward inventory and breaking incentive distribution.

**Paths:**

- Attacker calls `proxyDeposit(aave, attacker, 0)` while contract AAVE balance is at least `REWARD`.

- `aave.safeTransferFrom(msg.sender, address(this), 0)` succeeds with no economic cost.

- `pool.deposit(aave, attacker, REWARD, false)` spends reward inventory.

- Repeat until AAVE balance falls below `REWARD`.

*Round 1 | Agents: codex_1, opencode_1*

---

## High (3)

### F-002: Historical pools retain unlimited AAVE allowance after `setPool`

**Confidence:** high | **Locations:** `AaveBoost.sol:27, AaveBoost.sol:28, AaveBoost.sol:34, AaveBoost.sol:37`

The contract grants `type(uint256).max` allowance to each configured pool via `safeIncreaseAllowance` but never revokes allowance from prior pools when rotating `pool`. Every previously configured pool keeps perpetual transfer rights over this contract’s AAVE.

**Impact:** If any previous pool address is compromised/malicious, it can drain all current and future AAVE held by this contract through `transferFrom`.

**Paths:**

- Deploy with pool P1, giving P1 max allowance on AAVE.

- Owner calls `setPool(P2, ...)`; P2 also receives max allowance.

- P1 allowance remains nonzero forever.

- Compromised P1 transfers AAVE out of AaveBoost via `transferFrom`.

*Round 1 | Agents: codex_1, opencode_1*

---

### F-003: `proxyDeposit` does not source the deposited `asset` from user, causing broken deposits and DoS paths

**Confidence:** medium | **Locations:** `AaveBoost.sol:44, AaveBoost.sol:49, AaveBoost.sol:50, AaveBoost.sol:53`

`proxyDeposit` pulls only `aave` (and only in the reward branch) and never transfers the user-selected `asset` into this contract. For pool implementations where `deposit` pulls `asset` from `msg.sender` (AaveBoost), deposits for non-AAVE assets or unfunded states revert.

**Impact:** Proxy deposits can fail systematically (especially for `asset != aave` and after rewards deplete), creating permissionless availability failure for intended user deposits.

**Paths:**

- User calls `proxyDeposit(asset, recipient, amount)` with `asset != aave`; reward branch still pulls AAVE (or pulls nothing in fallback).

- `pool.deposit(asset, ...)` attempts to source `asset` from AaveBoost, which is typically unfunded/unapproved for that token.

- Call reverts; users cannot complete deposits via this proxy path.

- After contract AAVE drops below `REWARD`, fallback branch often remains non-functional for assets not already funded in AaveBoost.

*Round 1 | Agents: codex_1, opencode_1*

---

### F-006: Fallback branch can drain remaining AAVE from the contract when rewards are below threshold

**Confidence:** medium | **Locations:** `AaveBoost.sol:28, AaveBoost.sol:37, AaveBoost.sol:53`

When `aave.balanceOf(address(this)) < REWARD`, `proxyDeposit` skips any transfer from caller and still executes `pool.deposit(asset, recipient, amount, false)`. For pool implementations that pull `asset` from `msg.sender`, calling with `asset = aave` lets callers spend AaveBoost-held AAVE into their own recipient position at no cost.

**Impact:** Residual AAVE inventory below `REWARD` can be permissionlessly stolen, causing direct protocol treasury loss.

**Paths:**

- Precondition: `0 < aave.balanceOf(AaveBoost) < REWARD`.

- Attacker calls `proxyDeposit(aave, attackerRecipient, amount)` with `amount` up to contract-held AAVE.

- Fallback branch runs and does not pull tokens from attacker.

- Pool pulls AAVE from AaveBoost (via prior allowance) and credits attacker recipient.

*Round 2 | Agents: codex_1*

---

## Medium (1)

### F-004: `setPool` cannot update reward on same pool due max-allowance overflow in `safeIncreaseAllowance`

**Confidence:** high | **Locations:** `AaveBoost.sol:34, AaveBoost.sol:37, AaveBoost.sol:39`

`setPool` always calls `aave.safeIncreaseAllowance(address(pool), maxUint)`. If current allowance is already max (constructor/previous call), adding max overflows and reverts under Solidity 0.8 checked arithmetic.

**Impact:** Owner cannot adjust `REWARD` while keeping the same pool address, reducing ability to operate/tune incentives and potentially blocking maintenance actions.

**Paths:**

- Pool already has max allowance from constructor or prior `setPool`.

- Owner calls `setPool(existingPool, newReward)`.

- Allowance increment `oldAllowance + maxUint` overflows and transaction reverts.

*Round 1 | Agents: opencode_1*

---

## Low (1)

### F-005: `setPool` lacks zero/non-contract validation and can brick deposits if misconfigured

**Confidence:** medium | **Locations:** `AaveBoost.sol:34, AaveBoost.sol:35, AaveBoost.sol:50, AaveBoost.sol:53`

Unlike constructor checks, `setPool` does not validate `pool_ != address(0)` or contract code presence. Misconfiguration to an invalid target can make subsequent `proxyDeposit` calls revert when invoking `pool.deposit`.

**Impact:** A mistaken governance/operator action can halt all proxy deposits until corrected, causing service outage.

**Paths:**

- Owner sets `pool` to zero/non-contract via `setPool`.

- Users call `proxyDeposit`.

- External call to `pool.deposit` fails, reverting deposits globally.

*Round 1 | Agents: codex_1, opencode_1*

---
