module

public import FilterFormalization.Model
public import Mathlib.MeasureTheory.Measure.Decomposition.RadonNikodym
public import Mathlib.Probability.Kernel.CondDistrib

/-!
# 无记忆性引理的一般情形形式化 (`Memorylessness`)

对应论文第 2.2 节**引理 2.1（无记忆性，`cw:lem:markov`）**及附录 A.1 节末尾关于一般情形的完整推广：
> “一般情形对任意可测集合写条件概率，将上述求和替换为对噪声分布的积分，即得相同的条件分布等式；
> 在正文的密度存在假设下，进一步得到几乎处处成立的密度等式。”

本文件分两层推进：
1. **第一层（抽象单步机制无记忆性）**：对任意由独立噪声驱动的可测机制 $Z = g(\pi(W), N)$（其中 $W \perp N$），建立：
   - 联合推前测度与核乘积耦合的精确分解：$\mathbb{P}_{(W, Z)} = \mathbb{P}_W \otimes_m (\kappa_g \circ \pi)$（无需任何拓扑或标准 Borel 假设）；
   - **任意可测空间上的集合条件概率等式**（`condExp` 形式，完全无需 `StandardBorelSpace`）：
     对任意可测集 $B$，$\mathbb{P}(Z \in B \mid \sigma(W)) =^{\text{a.e.}} \kappa_g(\pi(W))(B) =^{\text{a.e.}} \mathbb{P}(Z \in B \mid \sigma(\pi \circ W))$；
   - **标准 Borel 空间上的正则条件分布（Markov 核 `condDistrib`）等式**（兼容零噪声确定性单点质量核与连续模型）；
   - **条件密度等式（`IsCondDensity` 与 `rnDeriv`）**：相对于任意 $\sigma$-有限参考测度（如体积测度 $v_X, v_Y$ 或计数测度），
     在密度存在假设下给出几乎处处成立的条件密度等式。
2. **第二层（非线性滤波状态空间模型实例化，`k ≥ 1` 含 `k = 1` 空历史观测情形）**：
   - 状态单步无记忆性（式 `cw:eq:2` 第一式）：给定 $(X_{0:k-1}, Y_{1:k-1})$ 时 $X_k$ 的条件分布/条件概率/条件密度仅依赖 $X_{k-1}$；
   - 观测条件独立性（式 `cw:eq:2` 第二式及附录式 `cw:eq:18`）：给定 $(X_{0:k}, Y_{1:k-1})$ 或 $(X_k, Y_{1:k-1})$ 时 $Y_k$ 的条件分布/条件概率/条件密度仅依赖 $X_k$。
-/

@[expose] public section

open MeasureTheory ProbabilityTheory MeasurableSpace Set
open scoped ENNReal

namespace FilterFormalization

/-! ## 第一部分：独立噪声驱动机制的一般无记忆性定理 -/

section AbstractMechanism

variable {Ω SW SU SN SZ : Type*}
  [mΩ : MeasurableSpace Ω] [mSW : MeasurableSpace SW] [mSU : MeasurableSpace SU]
  [mSN : MeasurableSpace SN] [mSZ : MeasurableSpace SZ]

/-- **核心耦合分解引理**（无需 `StandardBorelSpace`）：
若历史随机变量 `W` 与噪声 `N` 关于概率测度 `μ` 独立，且 `Z ω = g (π (W ω)) (N ω)`，
则 `(W, Z)` 的联合分布精确等于 `μ.map W` 与拉回转移核 `(mechKernel g (μ.map N)).comap π hπ` 的乘积耦合 `⊗ₘ`。 -/
theorem map_prod_mech_eq_compProd
    {μ : Measure Ω} [IsProbabilityMeasure μ]
    {W : Ω → SW} (hW : Measurable W) {N : Ω → SN} (hN : Measurable N)
    (hWN : W ⟂ᵢ[μ] N) {π : SW → SU} (hπ : Measurable π)
    {g : SU → SN → SZ} (hg : Measurable (Function.uncurry g))
    {Z : Ω → SZ} (hZ : ∀ ω, Z ω = g (π (W ω)) (N ω)) :
    μ.map (fun ω ↦ (W ω, Z ω)) = (μ.map W) ⊗ₘ ((mechKernel g (μ.map N)).comap π hπ) := by
  have : IsProbabilityMeasure (μ.map W) :=
    ⟨by rw [Measure.map_apply hW .univ, preimage_univ, measure_univ]⟩
  have : IsProbabilityMeasure (μ.map N) :=
    ⟨by rw [Measure.map_apply hN .univ, preimage_univ, measure_univ]⟩
  have : IsMarkovKernel (mechKernel g (μ.map N)) := isMarkovKernel_mechKernel hg (μ.map N)
  let Φ : SW × SN → SW × SZ := fun p ↦ (p.1, Function.uncurry g (π p.1, p.2))
  have hΦ : Measurable Φ :=
    measurable_fst.prodMk (hg.comp ((hπ.comp measurable_fst).prodMk measurable_snd))
  have hWZ_eq : (fun ω ↦ (W ω, Z ω)) = Φ ∘ (fun ω ↦ (W ω, N ω)) := by
    ext ω <;> simp [Φ, hZ ω]
  rw [hWZ_eq, ← Measure.map_map hΦ (hW.prodMk hN),
    hWN.map_prod_eq_prod_map_map hW.aemeasurable hN.aemeasurable]
  ext E hE
  rw [Measure.map_apply hΦ hE, Measure.prod_apply (hΦ hE), Measure.compProd_apply hE]
  refine lintegral_congr fun w ↦ ?_
  have hg_w : Measurable (g (π w)) := hg.comp (measurable_const.prodMk measurable_id)
  rw [Kernel.comap_apply, mechKernel_apply hg (μ.map N) (π w),
    Measure.map_apply hg_w (measurable_prodMk_left hE)]
  rfl

/-- 由核心耦合分解导出的截面转移积分恒等式：对任意 `W`-可测集 `W ⁻¹' A` 与可测集 `B ⊆ SZ`，
`Z ∈ B` 与 `W ∈ A` 的联合测度等于转移核在 `W ⁻¹' A` 上的积分。 -/
lemma setLIntegral_mechKernel_eq_measure_inter
    {μ : Measure Ω} [IsProbabilityMeasure μ]
    {W : Ω → SW} (hW : Measurable W) {N : Ω → SN} (hN : Measurable N)
    (hWN : W ⟂ᵢ[μ] N) {π : SW → SU} (hπ : Measurable π)
    {g : SU → SN → SZ} (hg : Measurable (Function.uncurry g))
    {Z : Ω → SZ} (hZ : ∀ ω, Z ω = g (π (W ω)) (N ω))
    {A : Set SW} (hA : MeasurableSet A) {B : Set SZ} (hB : MeasurableSet B) :
    ∫⁻ ω in W ⁻¹' A, mechKernel g (μ.map N) (π (W ω)) B ∂μ = μ (W ⁻¹' A ∩ Z ⁻¹' B) := by
  have : IsProbabilityMeasure (μ.map W) :=
    ⟨by rw [Measure.map_apply hW .univ, preimage_univ, measure_univ]⟩
  have : IsProbabilityMeasure (μ.map N) :=
    ⟨by rw [Measure.map_apply hN .univ, preimage_univ, measure_univ]⟩
  have : IsMarkovKernel (mechKernel g (μ.map N)) := isMarkovKernel_mechKernel hg (μ.map N)
  have hZ_meas : Measurable Z := by
    have : Z = fun ω ↦ Function.uncurry g (π (W ω), N ω) := funext hZ
    rw [this]
    exact hg.comp ((hπ.comp hW).prodMk hN)
  have h_coup := map_prod_mech_eq_compProd hW hN hWN hπ hg hZ
  have h_prod := congrArg (fun m : Measure (SW × SZ) ↦ m (A ×ˢ B)) h_coup
  rw [Measure.map_apply (hW.prodMk hZ_meas) (hA.prod hB), mk_preimage_prod,
    Measure.compProd_apply_prod hA hB] at h_prod
  rw [h_prod, Measure.restrict_map hW hA,
    lintegral_map (Kernel.measurable_coe ((mechKernel g (μ.map N)).comap π hπ) hB) hW]
  rfl

/-- **一般可测空间上的集合条件概率显式核表示**（无需 `StandardBorelSpace`）：
对任意可测集 `B ⊆ SZ`，给定 `σ(W)` 的条件概率 `μ⟦Z ⁻¹' B | σ(W)⟧` 几乎处处等于噪声积分核
`ω ↦ (mechKernel g (μ.map N) (π (W ω))).real B`。 -/
theorem condExp_preimage_mech_ae_eq
    {μ : Measure Ω} [IsProbabilityMeasure μ]
    {W : Ω → SW} (hW : Measurable W) {N : Ω → SN} (hN : Measurable N)
    (hWN : W ⟂ᵢ[μ] N) {π : SW → SU} (hπ : Measurable π)
    {g : SU → SN → SZ} (hg : Measurable (Function.uncurry g))
    {Z : Ω → SZ} (hZ : ∀ ω, Z ω = g (π (W ω)) (N ω))
    {B : Set SZ} (hB : MeasurableSet B) :
    μ⟦Z ⁻¹' B | mSW.comap W⟧ =ᵐ[μ]
      fun ω ↦ (mechKernel g (μ.map N) (π (W ω))).real B := by
  have : IsProbabilityMeasure (μ.map N) :=
    ⟨by rw [Measure.map_apply hN .univ, preimage_univ, measure_univ]⟩
  have : IsMarkovKernel (mechKernel g (μ.map N)) := isMarkovKernel_mechKernel hg (μ.map N)
  have hZ_meas : Measurable Z := by
    have : Z = fun ω ↦ Function.uncurry g (π (W ω), N ω) := funext hZ
    rw [this]
    exact hg.comp ((hπ.comp hW).prodMk hN)
  have h_meas_mW : Measurable[mSW.comap W] (fun ω ↦ mechKernel g (μ.map N) (π (W ω)) B) :=
    ((Kernel.measurable_coe _ hB).comp hπ).comp (Measurable.of_comap_le le_rfl)
  have h_int : Integrable (fun ω ↦ (mechKernel g (μ.map N) (π (W ω))).real B) μ := by
    refine integrable_toReal_of_lintegral_ne_top (h_meas_mW.mono hW.comap_le le_rfl).aemeasurable ?_
    refine ne_of_lt ?_
    calc
      ∫⁻ ω, mechKernel g (μ.map N) (π (W ω)) B ∂μ ≤ ∫⁻ _, 1 ∂μ :=
        lintegral_mono fun _ ↦ prob_le_one
      _ = μ univ := lintegral_one
      _ < ∞ := measure_lt_top _ _
  symm
  refine ae_eq_condExp_of_forall_setIntegral_eq hW.comap_le
    ((integrable_const _).indicator (hZ_meas hB))
    (fun _ _ _ ↦ h_int.integrableOn) ?_ h_meas_mW.ennreal_toReal.aestronglyMeasurable
  rintro t ⟨A, hA, rfl⟩ _
  simp_rw [measureReal_def]
  rw [integral_toReal (h_meas_mW.mono hW.comap_le le_rfl).aemeasurable
    (Filter.Eventually.of_forall fun ω ↦ measure_lt_top (mechKernel g (μ.map N) (π (W ω))) B),
    integral_indicator_const _ (hZ_meas hB), measureReal_restrict_apply (hZ_meas hB),
    smul_eq_mul, mul_one, inter_comm,
    setLIntegral_mechKernel_eq_measure_inter hW hN hWN hπ hg hZ hA hB]
  rfl

/-- **一般可测空间上的无记忆性条件概率恒等式**（对应附录 A.1 节一般情形第一结论，无需 `StandardBorelSpace`）：
对任意可测集 `B ⊆ SZ`，给定完整历史 `W` 的条件概率几乎处处等于仅给定投影状态 `π ∘ W` 的条件概率。 -/
theorem condExp_preimage_memoryless
    {μ : Measure Ω} [IsProbabilityMeasure μ]
    {W : Ω → SW} (hW : Measurable W) {N : Ω → SN} (hN : Measurable N)
    (hWN : W ⟂ᵢ[μ] N) {π : SW → SU} (hπ : Measurable π)
    {g : SU → SN → SZ} (hg : Measurable (Function.uncurry g))
    {Z : Ω → SZ} (hZ : ∀ ω, Z ω = g (π (W ω)) (N ω))
    {B : Set SZ} (hB : MeasurableSet B) :
    μ⟦Z ⁻¹' B | mSW.comap W⟧ =ᵐ[μ] μ⟦Z ⁻¹' B | mSU.comap (π ∘ W)⟧ := by
  have h1 := condExp_preimage_mech_ae_eq hW hN hWN hπ hg hZ hB
  have hWN_proj : (π ∘ W) ⟂ᵢ[μ] N := hWN.comp hπ measurable_id
  have h2 := condExp_preimage_mech_ae_eq (hπ.comp hW) hN hWN_proj measurable_id hg
    (fun ω ↦ by simpa using hZ ω) hB
  exact h1.trans h2.symm

section StandardBorel

variable [StandardBorelSpace SZ] [Nonempty SZ]

/-- **正则条件分布显式核刻画**：在标准 Borel 取值空间上，`condDistrib Z W μ` 几乎处处等于拉回核
`(mechKernel g (μ.map N)).comap π hπ`。 -/
theorem condDistrib_mech_ae_eq
    {μ : Measure Ω} [IsProbabilityMeasure μ]
    {W : Ω → SW} (hW : Measurable W) {N : Ω → SN} (hN : Measurable N)
    (hWN : W ⟂ᵢ[μ] N) {π : SW → SU} (hπ : Measurable π)
    {g : SU → SN → SZ} (hg : Measurable (Function.uncurry g))
    {Z : Ω → SZ} (hZ : ∀ ω, Z ω = g (π (W ω)) (N ω)) :
    condDistrib Z W μ =ᵐ[μ.map W] (mechKernel g (μ.map N)).comap π hπ := by
  have : IsProbabilityMeasure (μ.map N) :=
    ⟨by rw [Measure.map_apply hN .univ, preimage_univ, measure_univ]⟩
  have : IsMarkovKernel (mechKernel g (μ.map N)) := isMarkovKernel_mechKernel hg (μ.map N)
  have hZ_meas : Measurable Z := by
    have : Z = fun ω ↦ Function.uncurry g (π (W ω), N ω) := funext hZ
    rw [this]
    exact hg.comp ((hπ.comp hW).prodMk hN)
  exact condDistrib_ae_eq_of_measure_eq_compProd hW.aemeasurable hZ_meas.aemeasurable
    (map_prod_mech_eq_compProd hW hN hWN hπ hg hZ)

/-- 单步条件分布显式核刻画：`condDistrib Z (π ∘ W) μ` 几乎处处等于转移核 `mechKernel g (μ.map N)`。 -/
theorem condDistrib_proj_mech_ae_eq
    {μ : Measure Ω} [IsProbabilityMeasure μ]
    {W : Ω → SW} (hW : Measurable W) {N : Ω → SN} (hN : Measurable N)
    (hWN : W ⟂ᵢ[μ] N) {π : SW → SU} (hπ : Measurable π)
    {g : SU → SN → SZ} (hg : Measurable (Function.uncurry g))
    {Z : Ω → SZ} (hZ : ∀ ω, Z ω = g (π (W ω)) (N ω)) :
    condDistrib Z (π ∘ W) μ =ᵐ[μ.map (π ∘ W)] mechKernel g (μ.map N) := by
  have hWN_proj : (π ∘ W) ⟂ᵢ[μ] N := hWN.comp hπ measurable_id
  simpa using condDistrib_mech_ae_eq (hπ.comp hW) hN hWN_proj measurable_id hg
    (fun ω ↦ by simpa using hZ ω)

/-- **一般正则条件分布无记忆性定理（Markov 核形式）**：
给定完整历史 `W` 的正则条件分布核关于 `μ.map W` 几乎处处等于仅给定 `π ∘ W` 的正则条件分布核沿 `π` 的拉回。 -/
theorem condDistrib_memoryless
    {μ : Measure Ω} [IsProbabilityMeasure μ]
    {W : Ω → SW} (hW : Measurable W) {N : Ω → SN} (hN : Measurable N)
    (hWN : W ⟂ᵢ[μ] N) {π : SW → SU} (hπ : Measurable π)
    {g : SU → SN → SZ} (hg : Measurable (Function.uncurry g))
    {Z : Ω → SZ} (hZ : ∀ ω, Z ω = g (π (W ω)) (N ω)) :
    condDistrib Z W μ =ᵐ[μ.map W] (condDistrib Z (π ∘ W) μ).comap π hπ := by
  have h_full := condDistrib_mech_ae_eq hW hN hWN hπ hg hZ
  have h_proj := condDistrib_proj_mech_ae_eq hW hN hWN hπ hg hZ
  rw [← Measure.map_map hπ hW] at h_proj
  have h_pull : ∀ᵐ w ∂(μ.map W),
      condDistrib Z (π ∘ W) μ (π w) = mechKernel g (μ.map N) (π w) :=
    ae_of_ae_map hπ.aemeasurable h_proj
  filter_upwards [h_full, h_pull] with w hw1 hw2
  rw [hw1, Kernel.comap_apply, Kernel.comap_apply, hw2]

/-- 样本轨道形式的正则条件分布无记忆性：对 `μ`-几乎处处的样本 `ω`，
`condDistrib Z W μ (W ω) = condDistrib Z (π ∘ W) μ (π (W ω))`。 -/
theorem condDistrib_memoryless_ae_sample
    {μ : Measure Ω} [IsProbabilityMeasure μ]
    {W : Ω → SW} (hW : Measurable W) {N : Ω → SN} (hN : Measurable N)
    (hWN : W ⟂ᵢ[μ] N) {π : SW → SU} (hπ : Measurable π)
    {g : SU → SN → SZ} (hg : Measurable (Function.uncurry g))
    {Z : Ω → SZ} (hZ : ∀ ω, Z ω = g (π (W ω)) (N ω)) :
    ∀ᵐ ω ∂μ, condDistrib Z W μ (W ω) = condDistrib Z (π ∘ W) μ (π (W ω)) :=
  ae_of_ae_map hW.aemeasurable (condDistrib_memoryless hW hN hWN hπ hg hZ)

/-- **条件概率密度谓词**（对应论文第 2.1 节“相应密度存在，以相应空间的体积测度为参考测度”约定）：
`p : SW → SZ → ℝ≥0∞` 是 `Z` 给定 `W` 关于参考测度 `ν`（如体积测度 $v_X, v_Y$ 或计数测度）的条件密度，
若对 `(μ.map W)`-几乎处处的条件取值 `w`，`p w` 关于 `ν` 几乎处处可测且 `ν.withDensity (p w) = condDistrib Z W μ w`。 -/
def IsCondDensity
    (Z : Ω → SZ) (W : Ω → SW) (μ : Measure Ω) [IsFiniteMeasure μ]
    (ν : Measure SZ) (p : SW → SZ → ℝ≥0∞) : Prop :=
  ∀ᵐ w ∂(μ.map W), AEMeasurable (p w) ν ∧ ν.withDensity (p w) = condDistrib Z W μ w

/-- 当 `condDistrib Z W μ w ≪ ν` 几乎处处成立且 `ν` 为 $\sigma$-有限测度时，
典范 Radon-Nikodym 导数 `fun w ↦ (condDistrib Z W μ w).rnDeriv ν` 自动满足 `IsCondDensity`。 -/
lemma isCondDensity_rnDeriv
    {Z : Ω → SZ} {W : Ω → SW} {μ : Measure Ω} [IsFiniteMeasure μ]
    {ν : Measure SZ} [SigmaFinite ν]
    (h_ac : ∀ᵐ w ∂(μ.map W), condDistrib Z W μ w ≪ ν) :
    IsCondDensity Z W μ ν (fun w ↦ (condDistrib Z W μ w).rnDeriv ν) := by
  filter_upwards [h_ac] with w hw
  exact ⟨(Measure.measurable_rnDeriv _ _).aemeasurable, Measure.withDensity_rnDeriv_eq _ _ hw⟩

/-- **典范 Radon-Nikodym 条件密度的无记忆性**：对任意参考测度 `ν`，`(μ.map W)`-几乎处处有
`(condDistrib Z W μ w).rnDeriv ν = (condDistrib Z (π ∘ W) μ (π w)).rnDeriv ν`。 -/
theorem rnDeriv_condDistrib_memoryless
    {μ : Measure Ω} [IsProbabilityMeasure μ]
    {W : Ω → SW} (hW : Measurable W) {N : Ω → SN} (hN : Measurable N)
    (hWN : W ⟂ᵢ[μ] N) {π : SW → SU} (hπ : Measurable π)
    {g : SU → SN → SZ} (hg : Measurable (Function.uncurry g))
    {Z : Ω → SZ} (hZ : ∀ ω, Z ω = g (π (W ω)) (N ω)) (ν : Measure SZ) :
    ∀ᵐ w ∂(μ.map W),
      (condDistrib Z W μ w).rnDeriv ν = (condDistrib Z (π ∘ W) μ (π w)).rnDeriv ν := by
  filter_upwards [condDistrib_memoryless hW hN hWN hπ hg hZ] with w hw
  rw [hw, Kernel.comap_apply]

/-- **任意版本条件密度函数的几乎处处无记忆性等式**（对应附录 A.1 节末尾“在正文的密度存在假设下，进一步得到几乎处处成立的密度等式”）：
设 `ν` 为 $\sigma$-有限参考测度（如体积测度 $v_X$ 或计数测度），`pFull` 为 `Z | W` 的任意条件密度，
`pStep` 为 `Z | (π ∘ W)` 的任意条件密度，则对 `(μ.map W)`-几乎处处的 `w`，`pFull w =ᵐ[ν] pStep (π w)`。 -/
theorem isCondDensity_memoryless
    {μ : Measure Ω} [IsProbabilityMeasure μ]
    {W : Ω → SW} (hW : Measurable W) {N : Ω → SN} (hN : Measurable N)
    (hWN : W ⟂ᵢ[μ] N) {π : SW → SU} (hπ : Measurable π)
    {g : SU → SN → SZ} (hg : Measurable (Function.uncurry g))
    {Z : Ω → SZ} (hZ : ∀ ω, Z ω = g (π (W ω)) (N ω))
    {ν : Measure SZ} [SigmaFinite ν]
    {pFull : SW → SZ → ℝ≥0∞} {pStep : SU → SZ → ℝ≥0∞}
    (hpFull : IsCondDensity Z W μ ν pFull)
    (hpStep : IsCondDensity Z (π ∘ W) μ ν pStep) :
    ∀ᵐ w ∂(μ.map W), pFull w =ᵐ[ν] pStep (π w) := by
  have hpStep' : ∀ᵐ u ∂((μ.map W).map π),
      AEMeasurable (pStep u) ν ∧ ν.withDensity (pStep u) = condDistrib Z (π ∘ W) μ u := by
    rwa [Measure.map_map hπ hW]
  have hpStep_pull := ae_of_ae_map hπ.aemeasurable hpStep'
  filter_upwards [hpFull, hpStep_pull, condDistrib_memoryless hW hN hWN hπ hg hZ] with
    w ⟨hm1, hd1⟩ ⟨hm2, hd2⟩ hmem
  have h_wd : ν.withDensity (pFull w) = ν.withDensity (pStep (π w)) := by
    rw [hd1, hmem, Kernel.comap_apply, ← hd2]
  have h1 := Measure.rnDeriv_withDensity₀ ν hm1
  have h2 := Measure.rnDeriv_withDensity₀ ν hm2
  rw [h_wd] at h1
  exact h1.symm.trans h2

end StandardBorel

end AbstractMechanism

/-! ## 第二部分：非线性滤波状态空间模型的无记忆性引理（论文引理 `cw:lem:markov`） -/

namespace StateSpaceModel

universe u v

variable {Ω : Type v} {SX SY SNx SNy : Type u}
  [mΩ : MeasurableSpace Ω] [mSX : MeasurableSpace SX] [mSY : MeasurableSpace SY]
  [mSNx : MeasurableSpace SNx] [mSNy : MeasurableSpace SNy]
  {P : Measure Ω} [IsProbabilityMeasure P]
  (M : StateSpaceModel Ω SX SY SNx SNy P)

/-! ### 2.1 一般可测空间上的集合条件概率形式（无需 `StandardBorelSpace`） -/

/-- **状态单步无记忆性（集合条件概率形式）**：对任意 $k \ge 1$ 及可测集 $B \subseteq \mathcal{S}_X$，
$\mathbb{P}(X_k \in B \mid \sigma(X_{0:k-1}, Y_{1:k-1})) =^{\text{a.e.}} \mathbb{P}(X_k \in B \mid \sigma(X_{k-1}))$。
当 $k = 1$ 时，$Y_{1:0}$ 自动为空元组 `Fin 0 → SY`。 -/
theorem state_memoryless_condExp {k : ℕ} (hk : 1 ≤ k) {B : Set SX} (hB : MeasurableSet B) :
    P⟦M.X k ⁻¹' B | MeasurableSpace.comap (stateObsHist M.X M.Y (k - 1)) inferInstance⟧ =ᵐ[P]
      P⟦M.X k ⁻¹' B | mSX.comap (M.X (k - 1))⟧ := by
  simpa only [lastStateProj_comp_stateObsHist] using
    condExp_preimage_memoryless (M.measurable_stateObsHist (k - 1)) (M.measurable_Nx k hk)
      (M.indepFun_stateObsHist_procNoise hk) measurable_lastStateProj M.measurable_f
      (M.state_eq k hk) hB

/-- **观测条件独立性（集合条件概率形式）**：对任意 $k \ge 1$ 及可测集 $B \subseteq \mathcal{S}_Y$，
$\mathbb{P}(Y_k \in B \mid \sigma(X_{0:k}, Y_{1:k-1})) =^{\text{a.e.}} \mathbb{P}(Y_k \in B \mid \sigma(X_k))$。 -/
theorem obs_condIndep_condExp {k : ℕ} (hk : 1 ≤ k) {B : Set SY} (hB : MeasurableSet B) :
    P⟦M.Y k ⁻¹' B | MeasurableSpace.comap (stateCurrObsHist M.X M.Y k) inferInstance⟧ =ᵐ[P]
      P⟦M.Y k ⁻¹' B | mSX.comap (M.X k)⟧ := by
  simpa only [lastStateProj_comp_stateCurrObsHist] using
    condExp_preimage_memoryless (M.measurable_stateCurrObsHist k) (M.measurable_Ny k hk)
      (M.indepFun_stateCurrObsHist_obsNoise hk) measurable_lastStateProj M.measurable_h
      (M.obs_eq k hk) hB

/-! ### 2.2 标准 Borel 状态/观测空间上的正则条件分布（Markov 核）与条件密度形式 -/

section StateStandardBorel

variable [StandardBorelSpace SX] [Nonempty SX]

/-- 状态单步条件分布等于显式状态转移核 `M.stateKernel k`：
$\mathbb{P}_{X_k \mid X_{k-1}} =^{\text{a.e.}} \kappa_{f,k}$。 -/
theorem state_condDistrib_step_eq_kernel {k : ℕ} (hk : 1 ≤ k) :
    condDistrib (M.X k) (M.X (k - 1)) P =ᵐ[P.map (M.X (k - 1))] M.stateKernel k := by
  simpa only [lastStateProj_comp_stateObsHist, stateKernel] using
    condDistrib_proj_mech_ae_eq (M.measurable_stateObsHist (k - 1)) (M.measurable_Nx k hk)
      (M.indepFun_stateObsHist_procNoise hk) measurable_lastStateProj M.measurable_f
      (M.state_eq k hk)

/-- **状态单步无记忆性（引理 `cw:lem:markov` 第一式，正则条件分布核形式）**：
对任意 $k \ge 1$，给定 $(X_{0:k-1}, Y_{1:k-1})$ 的 $X_k$ 正则条件分布核几乎处处等于仅给定 $X_{k-1}$ 的正则条件分布核。 -/
theorem state_memoryless_condDistrib {k : ℕ} (hk : 1 ≤ k) :
    condDistrib (M.X k) (stateObsHist M.X M.Y (k - 1)) P =ᵐ[P.map (stateObsHist M.X M.Y (k - 1))]
      (condDistrib (M.X k) (M.X (k - 1)) P).comap lastStateProj measurable_lastStateProj := by
  simpa only [lastStateProj_comp_stateObsHist] using
    condDistrib_memoryless (M.measurable_stateObsHist (k - 1)) (M.measurable_Nx k hk)
      (M.indepFun_stateObsHist_procNoise hk) measurable_lastStateProj M.measurable_f
      (M.state_eq k hk)

/-- **状态单步无记忆性（引理 `cw:lem:markov` 第一式，条件概率密度形式）**：
设 $v_X$ 为状态空间上的 $\sigma$-有限参考测度（如体积测度或离散计数测度），
$p_{X_k \mid X_{0:k-1}, Y_{1:k-1}}$ 与 $p_{X_k \mid X_{k-1}}$ 分别为对应条件密度，则几乎处处有
$p_{X_k \mid X_{0:k-1}, Y_{1:k-1}}(\cdot \mid x_{0:k-1}, y_{1:k-1}) =^{\text{a.e.}}_{v_X} p_{X_k \mid X_{k-1}}(\cdot \mid x_{k-1})$。 -/
theorem state_memoryless_density {k : ℕ} (hk : 1 ≤ k)
    (vX : Measure SX) [SigmaFinite vX]
    {pFull : ((Fin (k - 1 + 1) → SX) × (Fin (k - 1) → SY)) → SX → ℝ≥0∞}
    {pStep : SX → SX → ℝ≥0∞}
    (hpFull : IsCondDensity (M.X k) (stateObsHist M.X M.Y (k - 1)) P vX pFull)
    (hpStep : IsCondDensity (M.X k) (M.X (k - 1)) P vX pStep) :
    ∀ᵐ h ∂(P.map (stateObsHist M.X M.Y (k - 1))),
      pFull h =ᵐ[vX] pStep (lastStateProj h) := by
  exact isCondDensity_memoryless (M.measurable_stateObsHist (k - 1)) (M.measurable_Nx k hk)
    (M.indepFun_stateObsHist_procNoise hk) measurable_lastStateProj M.measurable_f
    (M.state_eq k hk) hpFull (by simpa only [lastStateProj_comp_stateObsHist] using hpStep)

end StateStandardBorel

section ObsStandardBorel

variable [StandardBorelSpace SY] [Nonempty SY]

/-- 观测单步条件分布等于显式观测似然核 `M.obsKernel k`：
$\mathbb{P}_{Y_k \mid X_k} =^{\text{a.e.}} \kappa_{h,k}$。 -/
theorem obs_condDistrib_step_eq_kernel {k : ℕ} (hk : 1 ≤ k) :
    condDistrib (M.Y k) (M.X k) P =ᵐ[P.map (M.X k)] M.obsKernel k := by
  simpa only [lastStateProj_comp_stateCurrObsHist, obsKernel] using
    condDistrib_proj_mech_ae_eq (M.measurable_stateCurrObsHist k) (M.measurable_Ny k hk)
      (M.indepFun_stateCurrObsHist_obsNoise hk) measurable_lastStateProj M.measurable_h
      (M.obs_eq k hk)

/-- **观测条件独立性（引理 `cw:lem:markov` 第二式，正则条件分布核形式）**：
对任意 $k \ge 1$，给定 $(X_{0:k}, Y_{1:k-1})$ 的 $Y_k$ 正则条件分布核几乎处处等于仅给定 $X_k$ 的正则条件分布核。 -/
theorem obs_condIndep_condDistrib {k : ℕ} (hk : 1 ≤ k) :
    condDistrib (M.Y k) (stateCurrObsHist M.X M.Y k) P =ᵐ[P.map (stateCurrObsHist M.X M.Y k)]
      (condDistrib (M.Y k) (M.X k) P).comap lastStateProj measurable_lastStateProj := by
  simpa only [lastStateProj_comp_stateCurrObsHist] using
    condDistrib_memoryless (M.measurable_stateCurrObsHist k) (M.measurable_Ny k hk)
      (M.indepFun_stateCurrObsHist_obsNoise hk) measurable_lastStateProj M.measurable_h
      (M.obs_eq k hk)

/-- **观测条件独立性推论（对应附录 Bayes 更新证明式 `cw:eq:18`，正则条件分布核形式）**：
给定当前状态与历史观测 $(X_k, Y_{1:k-1})$ 时，$Y_k$ 的正则条件分布核几乎处处等于仅给定 $X_k$ 的正则条件分布核。 -/
theorem obs_condIndep_given_currStateObsHist_condDistrib {k : ℕ} (hk : 1 ≤ k) :
    condDistrib (M.Y k) (currStateObsHist M.X M.Y k) P =ᵐ[P.map (currStateObsHist M.X M.Y k)]
      Kernel.comap (mγ := inferInstance) (condDistrib (M.Y k) (M.X k) P) Prod.fst measurable_fst := by
  simpa only [fst_comp_currStateObsHist] using
    condDistrib_memoryless (mSW := inferInstance)
      (M.measurable_currStateObsHist k) (M.measurable_Ny k hk)
      (M.indepFun_currStateObsHist_obsNoise hk) measurable_fst M.measurable_h
      (M.obs_eq k hk)

/-- **观测条件独立性（引理 `cw:lem:markov` 第二式，条件概率密度形式）**：
设 $v_Y$ 为观测空间上的 $\sigma$-有限参考测度，$p_{Y_k \mid X_{0:k}, Y_{1:k-1}}$ 与 $p_{Y_k \mid X_k}$ 分别为对应条件密度，
则几乎处处有 $p_{Y_k \mid X_{0:k}, Y_{1:k-1}}(\cdot \mid x_{0:k}, y_{1:k-1}) =^{\text{a.e.}}_{v_Y} p_{Y_k \mid X_k}(\cdot \mid x_k)$。 -/
theorem obs_condIndep_density {k : ℕ} (hk : 1 ≤ k)
    (vY : Measure SY) [SigmaFinite vY]
    {pFull : ((Fin (k + 1) → SX) × (Fin (k - 1) → SY)) → SY → ℝ≥0∞}
    {pStep : SX → SY → ℝ≥0∞}
    (hpFull : IsCondDensity (M.Y k) (stateCurrObsHist M.X M.Y k) P vY pFull)
    (hpStep : IsCondDensity (M.Y k) (M.X k) P vY pStep) :
    ∀ᵐ h ∂(P.map (stateCurrObsHist M.X M.Y k)),
      pFull h =ᵐ[vY] pStep (lastStateProj h) := by
  exact isCondDensity_memoryless (M.measurable_stateCurrObsHist k) (M.measurable_Ny k hk)
    (M.indepFun_stateCurrObsHist_obsNoise hk) measurable_lastStateProj M.measurable_h
    (M.obs_eq k hk) hpFull (by simpa only [lastStateProj_comp_stateCurrObsHist] using hpStep)

/-- **观测条件独立性推论（对应附录式 `cw:eq:18`，条件概率密度形式）**：
$p_{Y_k \mid X_k, Y_{1:k-1}}(\cdot \mid x_k, y_{1:k-1}) =^{\text{a.e.}}_{v_Y} p_{Y_k \mid X_k}(\cdot \mid x_k)$。 -/
theorem obs_condIndep_given_currStateObsHist_density {k : ℕ} (hk : 1 ≤ k)
    (vY : Measure SY) [SigmaFinite vY]
    {pFull : (SX × (Fin (k - 1) → SY)) → SY → ℝ≥0∞}
    {pStep : SX → SY → ℝ≥0∞}
    (hpFull : IsCondDensity (M.Y k) (currStateObsHist M.X M.Y k) P vY pFull)
    (hpStep : IsCondDensity (M.Y k) (M.X k) P vY pStep) :
    ∀ᵐ h ∂(P.map (currStateObsHist M.X M.Y k)),
      pFull h =ᵐ[vY] pStep h.1 := by
  exact isCondDensity_memoryless (M.measurable_currStateObsHist k) (M.measurable_Ny k hk)
    (M.indepFun_currStateObsHist_obsNoise hk) measurable_fst M.measurable_h
    (M.obs_eq k hk) hpFull (by simpa only [fst_comp_currStateObsHist] using hpStep)

end ObsStandardBorel

end StateSpaceModel

end FilterFormalization

end
