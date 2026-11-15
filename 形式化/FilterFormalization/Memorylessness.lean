module

public import FilterFormalization.Model
public import Mathlib.MeasureTheory.Measure.Decomposition.RadonNikodym
public import Mathlib.Probability.Kernel.CondDistrib

/-!
# 无记忆性引理

对应论文引理 `cw:lem:markov` 及附录 A.1 的一般情形。

第一部分讨论抽象机制 $Z=g(\pi(W),N)$，其中历史 $W$ 与噪声 $N$ 独立：给定 $W$ 时 $Z$ 的条件分布
是机制核在 $\pi(W)$ 处的值，因而只依赖 $\pi(W)$；密度存在时得到几乎处处成立的密度等式。
第二部分把它用于状态方程（$W=(X_{0:k},Y_{1:k})$，$\pi$ 取末尾状态）与观测方程（$W=(X_{0:k+1},Y_{1:k})$）。
-/

@[expose] public section

open MeasureTheory ProbabilityTheory
open scoped ENNReal

namespace FilterFormalization

section Mechanism

variable {Ω SW SU SN SZ : Type*} [MeasurableSpace Ω] [MeasurableSpace SW] [MeasurableSpace SU]
  [MeasurableSpace SN] [MeasurableSpace SZ] {μ : Measure Ω} [IsProbabilityMeasure μ]
  {W : Ω → SW} {N : Ω → SN} {Z : Ω → SZ} {π : SW → SU} {g : SU × SN → SZ}
  (hW : Measurable W) (hN : Measurable N) (hWN : W ⟂ᵢ[μ] N) (hπ : Measurable π)
  (hg : Measurable g) (hZ : Z = fun ω ↦ g (π (W ω), N ω))

variable [StandardBorelSpace SZ] [Nonempty SZ]

/-- $p$ 是给定 $W$ 时 $Z$ 关于参考测度 $\nu$ 的条件密度。 -/
def IsCondDensity (Z : Ω → SZ) (W : Ω → SW) (μ : Measure Ω) [IsFiniteMeasure μ] (ν : Measure SZ)
    (p : SW → SZ → ℝ≥0∞) : Prop :=
  ∀ᵐ w ∂μ.map W, AEMeasurable (p w) ν ∧ ν.withDensity (p w) = condDistrib Z W μ w

include hW hN hWN hg hZ

/-- 给定 $W$ 时 $Z$ 的条件分布等于机制核沿 $\pi$ 的拉回，即 $\mathbb P_{(W,Z)}=\mathbb P_W\otimes_m(\kappa_g\circ\pi)$。 -/
theorem condDistrib_eq_mechKernel :
    condDistrib Z W μ =ᵐ[μ.map W] (mechKernel g (μ.map N)).comap π hπ := by
  subst hZ
  have := isMarkovKernel_mechKernel hg (μ.map N)
  have hΦ : Measurable fun p : SW × SN ↦ (p.1, g (π p.1, p.2)) := by fun_prop
  refine condDistrib_ae_eq_of_measure_eq_compProd hW.aemeasurable (by fun_prop) ?_
  change μ.map ((fun p : SW × SN ↦ (p.1, g (π p.1, p.2))) ∘ fun ω ↦ (W ω, N ω)) = _
  rw [← Measure.map_map hΦ (hW.prodMk hN),
    hWN.map_prod_eq_prod_map_map hW.aemeasurable hN.aemeasurable]
  ext E hE
  rw [Measure.map_apply hΦ hE, Measure.prod_apply (hΦ hE), Measure.compProd_apply hE]
  refine lintegral_congr fun w ↦ ?_
  rw [Kernel.comap_apply, mechKernel_apply hg, Measure.map_apply (by fun_prop)
    (measurable_prodMk_left hE)]
  rfl

/-- 无记忆性（核形式）：给定 $W$ 的条件分布等于仅给定 $\pi(W)$ 的条件分布。 -/
theorem condDistrib_memoryless :
    condDistrib Z W μ =ᵐ[μ.map W] (condDistrib Z (π ∘ W) μ).comap π hπ := by
  have h := condDistrib_eq_mechKernel (hπ.comp hW) hN (hWN.comp hπ measurable_id) measurable_id hg hZ
  rw [← Measure.map_map hπ hW] at h
  filter_upwards [condDistrib_eq_mechKernel hW hN hWN hπ hg hZ, ae_of_ae_map hπ.aemeasurable h]
    with w h₁ h₂
  rw [h₁, Kernel.comap_apply, Kernel.comap_apply, h₂]
  rfl

include hπ in
/-- 无记忆性（密度形式）：两个条件密度几乎处处相等。 -/
theorem condDensity_memoryless {ν : Measure SZ} [SigmaFinite ν] {p : SW → SZ → ℝ≥0∞}
    {q : SU → SZ → ℝ≥0∞} (hp : IsCondDensity Z W μ ν p) (hq : IsCondDensity Z (π ∘ W) μ ν q) :
    ∀ᵐ w ∂μ.map W, p w =ᵐ[ν] q (π w) := by
  rw [IsCondDensity, ← Measure.map_map hπ hW] at hq
  filter_upwards [hp, ae_of_ae_map hπ.aemeasurable hq, condDistrib_memoryless hW hN hWN hπ hg hZ]
    with w ⟨hp₁, hp₂⟩ ⟨hq₁, hq₂⟩ h
  have := Measure.rnDeriv_withDensity₀ ν hp₁
  rw [hp₂, h, Kernel.comap_apply, ← hq₂] at this
  exact this.symm.trans (Measure.rnDeriv_withDensity₀ ν hq₁)

end Mechanism

namespace StateSpaceModel

variable {Ω SX SY SNx SNy : Type*} [MeasurableSpace Ω] [MeasurableSpace SX] [MeasurableSpace SY]
  [MeasurableSpace SNx] [MeasurableSpace SNy] {P : Measure Ω} [IsProbabilityMeasure P]
  (M : StateSpaceModel Ω SX SY SNx SNy P) (k : ℕ)

section State

variable [StandardBorelSpace SX] [Nonempty SX]

/-- 引理 `cw:lem:markov` 第一式（核形式）：给定 $(X_{0:k},Y_{1:k})$ 时 $X_{k+1}$ 的条件分布只依赖 $X_k$。 -/
theorem state_memoryless :
    condDistrib (M.X (k + 1)) (M.hist k k) P =ᵐ[P.map (M.hist k k)]
      (condDistrib (M.X (k + 1)) (M.X k) P).comap last measurable_last :=
  condDistrib_memoryless (M.measurable_hist le_rfl) (M.measurable_Nx _) (M.indepFun_hist_Nx k)
    measurable_last M.measurable_f (M.state_eq k)

/-- 引理 `cw:lem:markov` 第一式（密度形式）。 -/
theorem state_memoryless_density {v : Measure SX} [SigmaFinite v]
    {p : (Fin (k + 1) → SX) × (Fin k → SY) → SX → ℝ≥0∞} {q : SX → SX → ℝ≥0∞}
    (hp : IsCondDensity (M.X (k + 1)) (M.hist k k) P v p)
    (hq : IsCondDensity (M.X (k + 1)) (M.X k) P v q) :
    ∀ᵐ w ∂P.map (M.hist k k), p w =ᵐ[v] q (last w) :=
  condDensity_memoryless (M.measurable_hist le_rfl) (M.measurable_Nx _) (M.indepFun_hist_Nx k)
    measurable_last M.measurable_f (M.state_eq k) hp hq

end State

section Obs

variable [StandardBorelSpace SY] [Nonempty SY]

/-- 引理 `cw:lem:markov` 第二式（核形式）：给定 $(X_{0:k+1},Y_{1:k})$ 时 $Y_{k+1}$ 的条件分布只依赖 $X_{k+1}$。 -/
theorem obs_memoryless :
    condDistrib (M.Y (k + 1)) (M.hist (k + 1) k) P =ᵐ[P.map (M.hist (k + 1) k)]
      (condDistrib (M.Y (k + 1)) (M.X (k + 1)) P).comap last measurable_last :=
  condDistrib_memoryless (M.measurable_hist (by omega)) (M.measurable_Ny _) (M.indepFun_hist_Ny k)
    measurable_last M.measurable_h (M.obs_eq k)

/-- 引理 `cw:lem:markov` 第二式（密度形式）。 -/
theorem obs_memoryless_density {v : Measure SY} [SigmaFinite v]
    {p : (Fin (k + 1 + 1) → SX) × (Fin k → SY) → SY → ℝ≥0∞} {q : SX → SY → ℝ≥0∞}
    (hp : IsCondDensity (M.Y (k + 1)) (M.hist (k + 1) k) P v p)
    (hq : IsCondDensity (M.Y (k + 1)) (M.X (k + 1)) P v q) :
    ∀ᵐ w ∂P.map (M.hist (k + 1) k), p w =ᵐ[v] q (last w) :=
  condDensity_memoryless (M.measurable_hist (by omega)) (M.measurable_Ny _) (M.indepFun_hist_Ny k)
    measurable_last M.measurable_h (M.obs_eq k) hp hq

end Obs

end StateSpaceModel

end FilterFormalization

end
