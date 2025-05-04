# Oppie.xyz — Your reliable Cursor Remote Control Product-Market-Fit Canvas (v0.4)

> TL;DR — **Ship a mobile-first _Remote Cursor Control_ layer that executes development & research tasks reliably from your phone, then upsell Guard-Rails and the Raft vector store.**

---

## 1  Unique Assets (Recap)
| Edge | Why it Matters |
| :-- | :-- |
| **Remote Planner ⇄ Executor loop** | Turns Cursor into a remotely steerable agent that can be paused, resumed, or re-prompted from any device. |
| **Self-Recovery & Tight Loop** | Guarantees progress even after hitting Cursor's 25-tool-call limit; lifts trust for unattended runs. |
| **Mobile PWA + Sidecar Daemon** | Removes the "laptop tether" — queue tasks on the train, let the desktop work at home. |
| **Guard-Rails SDK** | Enterprise teams can inject security & compliance policies into every remote command. |
| **Raft-backed Vector Store** | Stores logs, embeddings, and diff history with durability beyond local disk failures. |

---

## 2  Market Pulse & Gaps (May 2025)
* **Remote-first dev need:** Engineers increasingly travel light (iPad/phone) yet still own heavy CI/CD duties.
* **Tool-chain fragmentation:** Few agent frameworks integrate tightly with IDEs; none expose a robust remote surface.
* **Cursor ubiquity:** 100 k paying Cursor users already "live" in the IDE — we piggyback instead of replacing workflows.
* **Benchmarks plateau:** SWE-Bench success stalled at ≈35 %; improving autonomy & recovery directly unlocks higher pass-rate.
* **Pricing vacuum:** Cursor $20 < **PRICE GAP** < Fully-managed agents $500 — room for a mid-tier SaaS.

---

## 3  Beach-head Wedge — **Oppie Remote Cursor Control**
| Dimension | Choice |
| --- | --- |
| **Early adopter** | Indie maintainers, bootstrapped SaaS teams, digital nomads. |
| **Job-to-be-done** | "Kick off, monitor, and merge a green PR (or run a research report) from my phone while away from keyboard." |
| **North-Star Metric** | **Cost-per-successful remote task ≤ $15** at ≥ 40 % success on SWE-Bench-Lite. |
| **Monetisation** | *Starter* – $9 / mo includes 20 remote tasks • *Pro* – $49 / seat / mo unlimited • *Cloud Runner* compute add-on. |
| **Why Oppie wins** | Proven self-recovery + tight template loop ⇒ fewer stalls, higher trust, cheaper GPU minutes. |

---

## 4  Expansion Lanes
| Wedge | Trigger Condition | Revenue Mode |
| :-- | :-- | :-- |
| **Guard-Rails SDK** | Teams demand SOC-2 / HIPAA audit trail | Annual licence + compliance bundle |
| **Code-Atlas** | Repos > 1 M LOC & search latency > 400 ms | Managed cluster ($/GiB-mo) |
| **Edge-VM Runner** | Users want disposable sandboxes | Per-minute VM billing |

---

## 5  Validation Roadmap (next 60 days)
1. **Dog-food**: run 200 remote SWE-Bench-Lite tasks — hit ≥ 40 % success by 2025-06-30.  
2. **Private beta**: onboard 5 OSS maintainers; measure cost-per-merged-PR.  
3. **Retention probe**: track repeat PWA usage & "Run again" clicks.  
4. **Pricing test**: $9 vs $49 tiers.  
5. Publish transparent blog + collect mobile demo videos.

---

## 6  TAM → SAM → SOM snapshot
| Tier | Definition | 2025 $ (est.) |
| --- | --- | --- |
| **TAM** | All GitHub repos with active CI (28 M) | $8 B |
| **SAM** | Cursor & Copilot paying users (≈ 2 M) | $1.6 B |
| **SOM (2-yr)** | 1 % of SAM at $49/seat (3 seats avg) | $24 M ARR |

---

## 7  Risk Register
| Risk | Impact | Likelihood | Mitigation |
| :-- | :-- | :-- | :-- |
| Mobile network flakiness interrupts tasks | Medium | Medium | Offline queue + Sidecar retry buffer |
| Cursor UI changes break automation | Medium | Medium | Dual-path fallback (hidden command ✚ GUI automation) |
| Agents introduce silent bugs | High | Medium | OTP gating for high-risk commands; diff approval via PWA |
| GPU cost overrun | Medium | Medium | Default to o4-mini; auto-kill loops after 15 min |
| Cheaper competitor undercuts price | High | Low | Double-down on Guard-Rails & Vector Store moat |

---