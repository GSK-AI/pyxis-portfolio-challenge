# Environment Security Analysis: Preventing Gaming of Stochastic Outcomes

## Background

The Pyxis Portfolio Challenge is a competitive multi-agent reinforcement learning environment where agents manage pharmaceutical R&D portfolios. Agents make sequential investment decisions under uncertainty, with drug assets progressing through clinical trial phases that have stochastic success/failure outcomes determined by each trial's Probability of Technical and Regulatory Success (PTRS).

A reviewer raised concerns that the environment could be exploited by a malicious competitor:

> "The environment is still a bit too easy for a malicious competitor to:
> a) fully search the game space with a rule-based agent
> b) reverse engineer the environment and figure out the seed (which means they'd know every secret in the whole game from localized testing on the environment).
>
> We envision someone submitting an agent that is 99% a seed lookup table based on the initial state which wins every game that hits this table."

This document analyses each concern against the actual codebase, evaluates what mitigations were considered, and describes the chosen solution.

---

## Concern A: Exhaustive Game Space Search with Rule-Based Agents

### Assessment: Not feasible

The game tree is astronomically large:

- **Action space per step**: 2^40 binary investment choices (40 asset slots) + 11^3 BD bid combinations (3 slots, 11 levels each) = ~10^12 actions per step
- **Horizon**: 100 steps
- **Game tree**: ~(10^12)^100 possible paths

Even with aggressive action masking reducing feasible actions to ~100-1000 per step, the tree remains intractable (~100^100 nodes). Full minimax search or exhaustive enumeration is impossible.

However, the concern has partial merit: strong rule-based heuristics (such as the included knapsack baseline agent) can perform competitively by solving a greedy optimisation at each step. This is expected behaviour and represents legitimate strategic play, not environment exploitation.

### Verdict: The game space cannot be fully searched. Rule-based heuristics are competitive but represent valid strategies, not gaming.

---

## Concern B: Seed Reverse-Engineering

### Assessment: Valid concern, but mitigated by operational and structural measures

The environment uses Python's `random.Random` (Mersenne Twister) for all stochastic elements. The seed deterministically controls asset generation, trial outcomes, TA quality modifiers, BD asset arrivals, and pipeline leak events. Competitors receive the environment source code, so they know the exact RNG algorithm and seeding mechanism.

#### How seeding worked (before fix)

```
MultiAgentGame.initialise(seed)
  +-- game._rng = random.Random(seed)              # multi-agent orchestrator
  +-- shared_market._rng = random.Random(seed)      # market state
  +-- Agent 0: GameState._rng = random.Random(seed + 0)
  +-- Agent 1: GameState._rng = random.Random(seed + 1)
```

Within each agent's `GameState`, trial outcomes were determined by per-trial RNGs seeded as `random.Random(f"{seed}_{asset_id}_{phase_key}")`. This independent seeding was the root cause of the most critical vulnerability (see Concern C below). It has since been replaced with a single shared RNG (see Chosen Solution).

#### Mersenne Twister state recovery

Mersenne Twister's internal state consists of 624 × 32-bit words (19,968 bits). The standard "untwisting" attack recovers this state from 624 consecutive **raw 32-bit outputs** — and when those outputs are available, recovery is near-instantaneous (it is a linear algebra problem over GF(2), not brute force).

However, the agent never observes raw RNG outputs. They only observe **binary outcomes**: trial pass/fail, asset arrived/didn't, leak occurred/didn't. Each binary observation yields at most ~1 bit of information about the internal state (and often less, depending on the threshold). A typical game produces ~100–200 such observations — roughly two orders of magnitude short of the ~19,968 bits needed to constrain the full MT state. This information-theoretic gap is the primary defence against state recovery, not computation time.

#### Brute-force seed recovery

With a 64-bit seed space (~1.8 × 10^19 candidates), direct brute-force enumeration is computationally infeasible regardless of time budget. The agent would need to validate each candidate against observed outcomes, and the search space is far too large.

#### Post-bankruptcy scenario

A specific scenario was considered: if the opponent goes bankrupt early, the remaining agent controls all actions and knows the full RNG call sequence from that point forward. Could they recover the RNG state from post-bankruptcy observations?

This is not feasible because:
1. The opponent's prior actions (even a single step) consumed unknown RNG draws, corrupting any seed-based reconstruction
2. Post-bankruptcy observations (~20–60 binary outcomes) still provide far fewer bits than needed for MT state recovery (~19,968 bits). The information-theoretic gap remains the binding constraint
3. Even with a fully known call sequence, the agent still only observes thresholded binary outcomes, not raw 32-bit outputs — the standard untwisting attack does not apply

Note: the per-action timeout provides an additional operational constraint but is **not** the primary defence here. Even with unlimited time, the agent cannot recover the MT state from ~200 binary observations.

### Verdict: Seed recovery is theoretically possible but practically infeasible given the 64-bit seed space, the information-theoretic gap between observable binary outcomes (~200 bits) and MT state size (~19,968 bits), and opponent action corruption of the RNG chain.

---

## Concern C: Predetermined Outcomes via Independent Per-Trial RNGs

### Assessment: Valid and critical

This is the most serious vulnerability identified. Each trial phase receives its own independent RNG:

```python
# trial.py:796
current_trial._rng = random.Random(f"{seed}_{asset_id}_{key}")

# trial.py:762
approval_rng = random.Random(f"{seed}_{asset_id}_approval")
```

Because each trial's RNG is seeded independently from the global seed and asset ID, **trial outcomes are completely predetermined at episode creation, regardless of what actions the agent takes**. The order in which assets are invested in, the timing of investments, and the opponent's actions have no effect on whether a given trial succeeds or fails.

#### Exploitation

A competitor with the environment source code can exploit this by:

1. Identifying the seed (from the initial game state or by other means)
2. Creating each trial's independent RNG locally: `random.Random(f"{seed}_{asset_id}_{phase_key}")`
3. Calling `_rng.random()` to pre-reveal every trial outcome
4. Investing only in assets guaranteed to succeed through all phases

This reduces the game from a stochastic optimisation problem to a **deterministic selection problem**: pick the winners, skip the losers. The knapsack baseline agent already solves selection well; combined with perfect foresight, it would be unbeatable.

#### Impact on game complexity

Independent per-trial RNGs fundamentally reduce the combinatorial complexity of the game. Instead of managing risk under genuine uncertainty (where the decision to invest in Asset A vs Asset B at a given step could lead to different outcomes), the agent faces a fully knowable payoff matrix. This undermines the core design goal of creating an environment that rewards robust decision-making under uncertainty.

### Verdict: This is the primary vulnerability. Independent RNGs make outcomes predictable and action-independent, enabling a trivial exploit strategy.

---

## Concern D: Lookup Table Attacks

### Assessment: Valid but addressed operationally

The codebase contained a `CUSTOM_SEEDS` dictionary in `constants.py` with only 33 hardcoded seeds (3 per asset count, 11 asset counts). Additionally, the evaluation seed was hardcoded in `config.yaml` as `eval_initial_seed: 891024889` with sequential incrementing per episode.

If competitors knew the evaluation seeds, they could precompute optimal play for every possible game offline, then look up the correct policy at competition time.

#### Operational mitigation

- Final evaluation uses **held-out seeds** not present in the source code
- Final evaluation uses a **held-out asset library** different from the training set
- `CUSTOM_SEEDS` is not used in the competition game flow

These two held-out elements together prevent the lookup table attack: the agent can't precompute the RNG chain without the seed, and can't brute-force the seed without the asset library to validate against. The action timeout prevents doing this work during the game.

#### Cleanup

Despite being unused, `CUSTOM_SEEDS` and its associated API endpoint (`/game/custom_seeds`) should be removed from the codebase to avoid confusion and eliminate a potential attack surface if the operational controls ever lapse.

### Verdict: Mitigated operationally by held-out seeds and assets. Residual code should be cleaned up.

---

## Solutions Considered

### Option 1: Action-Dependent Shared RNG (Selected)

Thread a single stateful RNG through each agent's game state. All trial outcomes, asset arrivals, and stochastic events consume from the same RNG stream. Since the order of consumption depends on agent actions, outcomes become path-dependent.

**Pros:**
- Structurally eliminates the predetermined outcome vulnerability
- Outcomes depend on the full action history of all agents
- A competitor can't precompute outcomes without knowing all future actions (which is the strategic problem itself)
- Minimal API surface change; `random.Random` interface stays the same
- Preserves reproducibility (same seed + same actions = same outcomes)

**Cons:**
- Changes all numerical outputs (tests checking specific values need updating)
- Must be done atomically (can't be rolled out incrementally)

### Option 2: Cryptographic RNG (HMAC-SHA256)

Replace `random.Random` (Mersenne Twister) with a custom `CryptoRNG` class using HMAC-SHA256 in counter mode. Outputs are deterministic given the seed but cryptographically unpredictable from observed outputs.

**Pros:**
- Closes the theoretical gap where an attacker could recover MT state from observations
- Defence-in-depth against sophisticated statistical attacks

**Cons:**
- ~10x slower per RNG call (negligible in practice given ~dozens of calls per step)
- Additional code complexity (new class to maintain and test)
- The threat it addresses (MT state recovery) is already practically infeasible given:
  - Only ~100-200 binary observations available (vs ~19,968 bits needed for state recovery)
  - The agent never observes raw 32-bit outputs, only thresholded binary outcomes — the standard untwisting attack does not apply
  - Opponent actions corrupt the RNG chain before any recovery attempt

**Decision:** Not selected. The shared RNG combined with held-out seeds/assets and action timeouts makes the cryptographic upgrade unnecessary. The attack it defends against requires conditions that don't hold in the competition setting.

### Option 3: Held-Out Test Seeds and Assets Only

Rely purely on operational security: keep the evaluation seeds and asset library secret.

**Pros:**
- Zero code changes required
- Simple to implement

**Cons:**
- Does not fix the structural vulnerability (independent RNGs still make outcomes predetermined)
- If seeds or assets ever leak (through a bug, accidental commit, or social engineering), the environment becomes fully exploitable
- Security depends on operational discipline rather than system design

**Decision:** Used as a complementary layer alongside the shared RNG, not as the sole defence.

### Option 4: Remove CUSTOM_SEEDS

Delete the hardcoded seed dictionary and associated API endpoint.

**Pros:**
- Removes a confusing artefact that suggests a small seed space
- Eliminates a potential attack surface

**Cons:**
- None (it is unused in competition)

**Decision:** Selected as a cleanup task alongside the shared RNG change.

---

## Chosen Solution

### Defence-in-depth with two layers:

**Layer 1 (Structural): Shared action-dependent RNG**

Convert all per-asset/per-trial independent RNGs to share a single RNG instance per agent. Trial outcomes consume from this shared stream in action-dependent order, making results unpredictable without knowing the full action sequence. This eliminates the core vulnerability regardless of whether seeds or assets are secret.

**Layer 2 (Operational): Held-out evaluation seeds and assets**

Final competition evaluation uses seeds and an asset library that are not included in the distributed source code. This prevents any precomputation-based attacks and ensures agents cannot train directly on evaluation scenarios. Combined with the per-action timeout, this makes online seed recovery infeasible.

**Cleanup: Remove CUSTOM_SEEDS**

Delete the unused hardcoded seed dictionary and its API endpoint to avoid confusion.

### RNG flow after changes

```
MultiAgentGame.initialise(seed)
  +-- init_game_rng(seed)                         # single game-wide RNG (contextvars)
  |
  +-- All components call get_game_rng():
        +-- Agent 0: trial outcomes, asset arrivals, TA quality sampling
        +-- Agent 1: trial outcomes, asset arrivals, TA quality sampling
        +-- SharedMarketState: leaks, BD spawning, market events
        +-- BD auctions: tie-breaking
        +-- All consume from the SAME RNG instance  <-- PATH DEPENDENT
```

Because agents step sequentially and all share one RNG, Agent 0's actions determine how many draws are consumed before Agent 1's trials resolve — and vice versa. Every action by any agent shifts the RNG state for all subsequent draws.

### Why this is sufficient

| Attack Vector | Shared RNG | Held-Out Seeds/Assets | Action Timeout |
|---------------|:----------:|:---------------------:|:--------------:|
| Predetermined trial outcomes | Blocked | - | - |
| Seed lookup table | Blocked | Blocked | - |
| Online seed brute-force | - | Blocked | Blocked |
| MT state recovery | Impractical* | - | - |
| Pre-training on eval scenarios | - | Blocked | - |

*Information-theoretically infeasible: requires ~19,968 bits of state; only ~100-200 binary observations available. Opponent's unknown actions further corrupt the RNG chain. The standard untwisting attack requires raw 32-bit outputs, which are never observable.

---

## Verification Plan

1. **Path-dependence test**: Same seed, different action order produces different trial outcomes
2. **Determinism test**: Same seed + same action sequence produces identical outcomes
3. **CUSTOM_SEEDS removal**: Verify no references remain via grep
4. **Full test suite**: Update any hardcoded expected values, run `pytest`
