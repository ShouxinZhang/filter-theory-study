module

public import Mathlib.Probability.Independence.Basic
public import Mathlib.Probability.Kernel.Composition.MapComap
public import Mathlib.Probability.Kernel.Composition.Prod

/-!
# 非线性滤波状态空间模型 (`StateSpaceModel`)

对应论文第 2.1 节式 `(cw:eq:1)` 的一般可测空间非线性状态空间模型：
- 状态递推：$X_k = f(X_{k-1}, N_{x,k})$（$k \ge 1$）
- 观测方程：$Y_k = h(X_k, N_{y,k})$（$k \ge 1$）
- 噪声独立性：$X_0$ 与全体 $\{N_{x,k}\}_{k \ge 1}$、$\{N_{y,k}\}_{k \ge 1}$ 相互独立

不对状态空间 `SX`、观测空间 `SY` 或样本空间 `Ω` 预设有限离散或欧氏维数限制，离散情形与连续欧氏空间均为特例。
-/

@[expose] public section

open MeasureTheory ProbabilityTheory MeasurableSpace

namespace FilterFormalization

universe u v

/-- 状态空间模型的原始随机源索引：初始状态 $X_0$、过程噪声 $N_{x,k}$ ($k \ge 1$) 与观测噪声 $N_{y,k}$ ($k \ge 1$)。 -/
inductive PrimSource : Type
  | initState : PrimSource
  | procNoise : {k : ℕ // 1 ≤ k} → PrimSource
  | obsNoise : {k : ℕ // 1 ≤ k} → PrimSource
  deriving DecidableEq

/-- 各原始随机源对应的取值空间。 -/
def PrimSpace (SX SNx SNy : Type u) : PrimSource → Type u
  | .initState => SX
  | .procNoise _ => SNx
  | .obsNoise _ => SNy

instance instMeasurableSpacePrimSpace {SX SNx SNy : Type u}
    [MeasurableSpace SX] [MeasurableSpace SNx] [MeasurableSpace SNy] (s : PrimSource) :
    MeasurableSpace (PrimSpace SX SNx SNy s) := by
  cases s <;> assumption

/-- 将 $X_0$、$\{N_{x,k}\}_{k \ge 1}$、$\{N_{y,k}\}_{k \ge 1}$ 打包为依赖索引族，用于刻画联合相互独立性 `iIndepFun`。 -/
def primRV {Ω : Type v} {SX SNx SNy : Type u}
    (X : ℕ → Ω → SX) (Nx : ℕ → Ω → SNx) (Ny : ℕ → Ω → SNy) :
    (s : PrimSource) → Ω → PrimSpace SX SNx SNy s
  | .initState => X 0
  | .procNoise k => Nx k.1
  | .obsNoise k => Ny k.1

/-- 状态历史序列 $X_{0:m} = (X_0, \dots, X_m)$。 -/
def stateHist {Ω SX : Type*} (X : ℕ → Ω → SX) (m : ℕ) : Ω → (Fin (m + 1) → SX) :=
  fun ω i ↦ X i.1 ω

/-- 观测历史序列 $Y_{1:m} = (Y_1, \dots, Y_m)$。当 $m = 0$（对应 $k = 1$ 时的 $Y_{1:k-1}$）时为空元组 `Fin 0 → SY`。 -/
def obsHist {Ω SY : Type*} (Y : ℕ → Ω → SY) (m : ℕ) : Ω → (Fin m → SY) :=
  fun ω i ↦ Y (i.1 + 1) ω

/-- 状态与观测联合历史 $(X_{0:m}, Y_{1:m})$；当 $m = k - 1$ 时即 $(X_{0:k-1}, Y_{1:k-1})$。 -/
def stateObsHist {Ω SX SY : Type*} (X : ℕ → Ω → SX) (Y : ℕ → Ω → SY) (m : ℕ) :
    Ω → (Fin (m + 1) → SX) × (Fin m → SY) :=
  fun ω ↦ (stateHist X m ω, obsHist Y m ω)

/-- 含当前状态的联合历史 $(X_{0:k}, Y_{1:k-1})$，用于观测条件独立性引理。 -/
def stateCurrObsHist {Ω SX SY : Type*} (X : ℕ → Ω → SX) (Y : ℕ → Ω → SY) (k : ℕ) :
    Ω → (Fin (k + 1) → SX) × (Fin (k - 1) → SY) :=
  fun ω ↦ (stateHist X k ω, obsHist Y (k - 1) ω)

/-- 当前状态与历史观测对 $(X_k, Y_{1:k-1})$，直接对应 Bayes 更新公式证明式 `(cw:eq:18)` 的条件变量。 -/
def currStateObsHist {Ω SX SY : Type*} (X : ℕ → Ω → SX) (Y : ℕ → Ω → SY) (k : ℕ) :
    Ω → SX × (Fin (k - 1) → SY) :=
  fun ω ↦ (X k ω, obsHist Y (k - 1) ω)

/-- 从形如 `(Fin (m + 1) → SX) × α` 的历史对中投影出末尾状态 $X_m$。 -/
def lastStateProj {SX α : Type*} {m : ℕ} (p : (Fin (m + 1) → SX) × α) : SX :=
  p.1 (Fin.last m)

@[simp]
lemma lastStateProj_comp_stateObsHist {Ω SX SY : Type*}
    (X : ℕ → Ω → SX) (Y : ℕ → Ω → SY) (m : ℕ) :
    lastStateProj ∘ stateObsHist X Y m = X m :=
  rfl

@[simp]
lemma lastStateProj_comp_stateCurrObsHist {Ω SX SY : Type*}
    (X : ℕ → Ω → SX) (Y : ℕ → Ω → SY) (k : ℕ) :
    lastStateProj ∘ stateCurrObsHist X Y k = X k :=
  rfl

@[simp]
lemma fst_comp_currStateObsHist {Ω SX SY : Type*}
    (X : ℕ → Ω → SX) (Y : ℕ → Ω → SY) (k : ℕ) :
    Prod.fst ∘ currStateObsHist X Y k = X k :=
  rfl

lemma measurable_lastStateProj {SX α : Type*} [MeasurableSpace SX] [MeasurableSpace α] {m : ℕ} :
    Measurable (lastStateProj (SX := SX) (α := α) (m := m)) :=
  (measurable_pi_apply (Fin.last m)).comp measurable_fst

/-- 由双元可测机制 `g : SU → SN → SZ` 与噪声分布 `ν : Measure SN` 诱导的 Markov 转移核
`u ↦ ν.map (g u)`。 -/
noncomputable def mechKernel {SU SN SZ : Type*}
    [MeasurableSpace SU] [MeasurableSpace SN] [MeasurableSpace SZ]
    (g : SU → SN → SZ) (ν : Measure SN) : Kernel SU SZ :=
  (Kernel.id ×ₖ Kernel.const SU ν).map (Function.uncurry g)

lemma isMarkovKernel_mechKernel {SU SN SZ : Type*}
    [MeasurableSpace SU] [MeasurableSpace SN] [MeasurableSpace SZ]
    {g : SU → SN → SZ} (hg : Measurable (Function.uncurry g))
    (ν : Measure SN) [IsProbabilityMeasure ν] :
    IsMarkovKernel (mechKernel g ν) :=
  Kernel.IsMarkovKernel.map _ hg

lemma mechKernel_apply {SU SN SZ : Type*}
    [MeasurableSpace SU] [MeasurableSpace SN] [MeasurableSpace SZ]
    {g : SU → SN → SZ} (hg : Measurable (Function.uncurry g))
    (ν : Measure SN) [SFinite ν] (u : SU) :
    mechKernel g ν u = ν.map (g u) := by
  ext s hs
  rw [mechKernel, Kernel.map_apply' _ hg u hs, Kernel.prod_apply' _ _ _ (hg hs)]
  simp only [Kernel.id_apply, Kernel.const_apply]
  rw [lintegral_dirac' _ (measurable_measure_prodMk_left (hg hs)), Measure.map_apply _ hs]
  · rfl
  · exact hg.comp (measurable_const.prodMk measurable_id)

/-- 一般非线性状态空间模型（对应论文第 2.1 节式 `(cw:eq:1)` 及噪声独立性条件）。 -/
structure StateSpaceModel (Ω : Type v) (SX SY SNx SNy : Type u)
    [mΩ : MeasurableSpace Ω] [MeasurableSpace SX] [MeasurableSpace SY]
    [MeasurableSpace SNx] [MeasurableSpace SNy] (ℙ : Measure Ω) where
  /-- 状态随机过程 $X_k : \Omega \to \mathcal{S}_X$（$k \ge 0$） -/
  X : ℕ → Ω → SX
  /-- 观测随机过程 $Y_k : \Omega \to \mathcal{S}_Y$（$k \ge 1$） -/
  Y : ℕ → Ω → SY
  /-- 过程噪声序列 $N_{x,k} : \Omega \to \mathcal{S}_{N_x}$（$k \ge 1$） -/
  Nx : ℕ → Ω → SNx
  /-- 观测噪声序列 $N_{y,k} : \Omega \to \mathcal{S}_{N_y}$（$k \ge 1$） -/
  Ny : ℕ → Ω → SNy
  /-- 状态转移函数 $f : \mathcal{S}_X \times \mathcal{S}_{N_x} \to \mathcal{S}_X$ -/
  f : SX → SNx → SX
  /-- 观测函数 $h : \mathcal{S}_X \times \mathcal{S}_{N_y} \to \mathcal{S}_Y$ -/
  h : SX → SNy → SY
  /-- 初始状态可测 -/
  measurable_X0 : Measurable (X 0)
  /-- 各拍过程噪声可测（$k \ge 1$） -/
  measurable_Nx : ∀ k, 1 ≤ k → Measurable (Nx k)
  /-- 各拍观测噪声可测（$k \ge 1$） -/
  measurable_Ny : ∀ k, 1 ≤ k → Measurable (Ny k)
  /-- 状态转移映射联合可测 -/
  measurable_f : Measurable (Function.uncurry f)
  /-- 观测映射联合可测 -/
  measurable_h : Measurable (Function.uncurry h)
  /-- 状态递推方程：$X_k = f(X_{k-1}, N_{x,k})$（$k \ge 1$） -/
  state_eq : ∀ k, 1 ≤ k → ∀ ω, X k ω = f (X (k - 1) ω) (Nx k ω)
  /-- 观测方程：$Y_k = h(X_k, N_{y,k})$（$k \ge 1$） -/
  obs_eq : ∀ k, 1 ≤ k → ∀ ω, Y k ω = h (X k ω) (Ny k ω)
  /-- 初始状态与所有时刻的过程噪声、观测噪声相互独立 -/
  indep_sources : iIndepFun (primRV X Nx Ny) ℙ

namespace StateSpaceModel

variable {Ω : Type v} {SX SY SNx SNy : Type u}
  [mΩ : MeasurableSpace Ω] [mSX : MeasurableSpace SX] [mSY : MeasurableSpace SY]
  [mSNx : MeasurableSpace SNx] [mSNy : MeasurableSpace SNy] {ℙ : Measure Ω}
  (M : StateSpaceModel Ω SX SY SNx SNy ℙ)

lemma isProbabilityMeasure (M : StateSpaceModel Ω SX SY SNx SNy ℙ) :
    IsProbabilityMeasure ℙ :=
  M.indep_sources.isProbabilityMeasure

/-- 第 $k$ 拍状态转移核 $\kappa_{f,k}(x) = (N_{x,k})_*\mathbb{P} \circ (f(x, \cdot))^{-1}$。 -/
noncomputable def stateKernel (k : ℕ) : Kernel SX SX :=
  mechKernel M.f (ℙ.map (M.Nx k))

/-- 第 $k$ 拍观测似然核 $\kappa_{h,k}(x) = (N_{y,k})_*\mathbb{P} \circ (h(x, \cdot))^{-1}$。 -/
noncomputable def obsKernel (k : ℕ) : Kernel SX SY :=
  mechKernel M.h (ℙ.map (M.Ny k))

lemma isMarkovKernel_stateKernel {k : ℕ} (hk : 1 ≤ k) :
    IsMarkovKernel (M.stateKernel k) := by
  have := M.isProbabilityMeasure
  have : IsProbabilityMeasure (ℙ.map (M.Nx k)) :=
    ⟨by rw [Measure.map_apply (M.measurable_Nx k hk) .univ, Set.preimage_univ, measure_univ]⟩
  exact isMarkovKernel_mechKernel M.measurable_f _

lemma isMarkovKernel_obsKernel {k : ℕ} (hk : 1 ≤ k) :
    IsMarkovKernel (M.obsKernel k) := by
  have := M.isProbabilityMeasure
  have : IsProbabilityMeasure (ℙ.map (M.Ny k)) :=
    ⟨by rw [Measure.map_apply (M.measurable_Ny k hk) .univ, Set.preimage_univ, measure_univ]⟩
  exact isMarkovKernel_mechKernel M.measurable_h _

/-- 每个原始随机源生成的子 $\sigma$-代数。 -/
@[reducible]
def srcSigma (s : PrimSource) : MeasurableSpace Ω :=
  MeasurableSpace.comap (primRV M.X M.Nx M.Ny s) inferInstance

lemma srcSigma_le (s : PrimSource) : M.srcSigma s ≤ mΩ := by
  cases s with
  | initState => exact M.measurable_X0.comap_le
  | procNoise k => exact (M.measurable_Nx k.1 k.2).comap_le
  | obsNoise k => exact (M.measurable_Ny k.1 k.2).comap_le

lemma measurable_primRV_of_mem {S : Set PrimSource} {s : PrimSource} (hs : s ∈ S) :
    Measurable[⨆ t ∈ S, M.srcSigma t] (primRV M.X M.Nx M.Ny s) :=
  Measurable.of_comap_le (le_biSup M.srcSigma hs)

/-- 若集合 `S` 包含 `.initState` 以及所有 `1 ≤ j ≤ m` 的过程噪声源，则对任意 `i ≤ m`，
状态 $X_i$ 关于 `⨆ t ∈ S, M.srcSigma t` 可测。 -/
lemma measurable_X_of_subset_sources {S : Set PrimSource} {m : ℕ}
    (h0 : PrimSource.initState ∈ S)
    (hNx : ∀ (j : {k : ℕ // 1 ≤ k}), j.1 ≤ m → PrimSource.procNoise j ∈ S) :
    ∀ i ≤ m, @Measurable Ω SX (⨆ t ∈ S, M.srcSigma t) mSX (M.X i) := by
  intro i hi
  induction i with
  | zero =>
    exact M.measurable_primRV_of_mem h0
  | succ n ih =>
    have hn1 : 1 ≤ n + 1 := Nat.succ_pos n
    have h_eq : M.X (n + 1) = fun ω ↦ Function.uncurry M.f (M.X n ω, M.Nx (n + 1) ω) := by
      ext ω
      simpa using M.state_eq (n + 1) hn1 ω
    rw [h_eq]
    have hXn := ih (Nat.le_of_succ_le hi)
    have hN : @Measurable Ω SNx (⨆ t ∈ S, M.srcSigma t) mSNx (M.Nx (n + 1)) :=
      M.measurable_primRV_of_mem (hNx ⟨n + 1, hn1⟩ hi)
    exact M.measurable_f.comp (hXn.prodMk hN)

/-- 若集合 `S` 同时包含所有 `1 ≤ j ≤ m_y`（其中 `m_y ≤ m_x`）的观测噪声源，
则对任意 `1 ≤ j ≤ m_y`，观测 $Y_j$ 关于 `⨆ t ∈ S, M.srcSigma t` 可测。 -/
lemma measurable_Y_of_subset_sources {S : Set PrimSource} {mx my : ℕ} (hmyx : my ≤ mx)
    (h0 : PrimSource.initState ∈ S)
    (hNx : ∀ (j : {k : ℕ // 1 ≤ k}), j.1 ≤ mx → PrimSource.procNoise j ∈ S)
    (hNy : ∀ (j : {k : ℕ // 1 ≤ k}), j.1 ≤ my → PrimSource.obsNoise j ∈ S) :
    ∀ j, 1 ≤ j → j ≤ my → @Measurable Ω SY (⨆ t ∈ S, M.srcSigma t) mSY (M.Y j) := by
  intro j hj1 hjmy
  have h_eq : M.Y j = fun ω ↦ Function.uncurry M.h (M.X j ω, M.Ny j ω) := by
    ext ω
    simpa using M.obs_eq j hj1 ω
  rw [h_eq]
  have hXj := M.measurable_X_of_subset_sources h0 hNx j (le_trans hjmy hmyx)
  have hNj : @Measurable Ω SNy (⨆ t ∈ S, M.srcSigma t) mSNy (M.Ny j) :=
    M.measurable_primRV_of_mem (hNy ⟨j, hj1⟩ hjmy)
  exact M.measurable_h.comp (hXj.prodMk hNj)

/-- 对任意 $k \ge 0$，状态 $X_k$ 关于样本空间 $\mathcal{F}$ 可测。 -/
lemma measurable_X (k : ℕ) : Measurable (M.X k) := by
  have h := M.measurable_X_of_subset_sources (S := Set.univ) (m := k)
    (Set.mem_univ _) (fun _ _ ↦ Set.mem_univ _) k le_rfl
  exact h.mono (iSup₂_le fun s _ ↦ M.srcSigma_le s) le_rfl

/-- 对任意 $k \ge 1$，观测 $Y_k$ 关于样本空间 $\mathcal{F}$ 可测。 -/
lemma measurable_Y {k : ℕ} (hk : 1 ≤ k) : Measurable (M.Y k) := by
  have h := M.measurable_Y_of_subset_sources (S := Set.univ) (mx := k) (my := k) le_rfl
    (Set.mem_univ _) (fun _ _ ↦ Set.mem_univ _) (fun _ _ ↦ Set.mem_univ _) k hk le_rfl
  exact h.mono (iSup₂_le fun s _ ↦ M.srcSigma_le s) le_rfl

lemma measurable_stateHist (m : ℕ) : Measurable (stateHist M.X m) :=
  measurable_pi_iff.mpr fun i ↦ M.measurable_X i.1

lemma measurable_obsHist (m : ℕ) : Measurable (obsHist M.Y m) :=
  measurable_pi_iff.mpr fun i ↦ M.measurable_Y (Nat.succ_pos i.1)

lemma measurable_stateObsHist (m : ℕ) : Measurable (stateObsHist M.X M.Y m) :=
  (M.measurable_stateHist m).prodMk (M.measurable_obsHist m)

lemma measurable_stateCurrObsHist (k : ℕ) : Measurable (stateCurrObsHist M.X M.Y k) :=
  (M.measurable_stateHist k).prodMk (M.measurable_obsHist (k - 1))

lemma measurable_currStateObsHist (k : ℕ) : Measurable (currStateObsHist M.X M.Y k) :=
  (M.measurable_X k).prodMk (M.measurable_obsHist (k - 1))

/-- 通用工具：若随机变量 `W` 关于原始随机源子集 `S` 生成的 $\sigma$-代数可测，且 `s₀ ∉ S`，
则 `W` 与 `primRV s₀` 关于 `ℙ` 独立。 -/
lemma indepFun_of_measurable_sources {SW : Type*} [mSW : MeasurableSpace SW]
    {S : Set PrimSource} {s₀ : PrimSource} (hs₀ : s₀ ∉ S)
    {W : Ω → SW} (hW : @Measurable Ω SW (⨆ t ∈ S, M.srcSigma t) mSW W) :
    W ⟂ᵢ[ℙ] primRV M.X M.Nx M.Ny s₀ := by
  have h_disj : Disjoint S ({s₀} : Set PrimSource) := Set.disjoint_singleton_right.mpr hs₀
  have h_indep : Indep (⨆ t ∈ S, M.srcSigma t) (⨆ t ∈ ({s₀} : Set PrimSource), M.srcSigma t) ℙ :=
    indep_iSup_of_disjoint M.srcSigma_le M.indep_sources.iIndep h_disj
  rw [IndepFun_iff_Indep]
  exact indep_of_indep_of_le h_indep hW.comap_le (le_biSup M.srcSigma (Set.mem_singleton s₀))

/-- 构造生成 $(X_{0:m_x}, Y_{1:m_y})$ 所需的原始随机源集合。 -/
def histSourceSet (mx my : ℕ) : Set PrimSource :=
  { s | match s with
    | .initState => True
    | .procNoise j => j.1 ≤ mx
    | .obsNoise j => j.1 ≤ my }

private lemma measurable_prod_pi {α β γ : Type*} {n₁ n₂ : ℕ}
    (m : MeasurableSpace α) [MeasurableSpace β] [MeasurableSpace γ]
    {u : Fin n₁ → α → β} {v : Fin n₂ → α → γ}
    (hu : ∀ i, @Measurable α β m _ (u i)) (hv : ∀ j, @Measurable α γ m _ (v j)) :
    @Measurable α ((Fin n₁ → β) × (Fin n₂ → γ)) m _ (fun ω ↦ (fun i ↦ u i ω, fun j ↦ v j ω)) := by
  let _ : MeasurableSpace α := m
  exact (measurable_pi_iff.mpr hu).prodMk (measurable_pi_iff.mpr hv)

/-- 联合历史 $(X_{0:k-1}, Y_{1:k-1})$ 与当前拍过程噪声 $N_{x,k}$ 独立（对应附录 `markov.tex` 第一段关键断言）。 -/
theorem indepFun_stateObsHist_procNoise {k : ℕ} (hk : 1 ≤ k) :
    stateObsHist M.X M.Y (k - 1) ⟂ᵢ[ℙ] M.Nx k := by
  let S := histSourceSet (k - 1) (k - 1)
  have hs₀ : PrimSource.procNoise ⟨k, hk⟩ ∉ S := by
    simp [S, histSourceSet]
    omega
  have hX_meas := M.measurable_X_of_subset_sources (S := S) (m := k - 1)
    (by simp [S, histSourceSet]) (fun j hj ↦ by simp [S, histSourceSet, hj])
  have hY_meas := M.measurable_Y_of_subset_sources (S := S) (mx := k - 1) (my := k - 1) le_rfl
    (by simp [S, histSourceSet]) (fun j hj ↦ by simp [S, histSourceSet, hj])
    (fun j hj ↦ by simp [S, histSourceSet, hj])
  have hW := measurable_prod_pi (⨆ t ∈ S, M.srcSigma t)
    (u := fun (i : Fin (k - 1 + 1)) ↦ M.X i.1)
    (v := fun (j : Fin (k - 1)) ↦ M.Y (j.1 + 1))
    (fun i ↦ hX_meas i.1 (Nat.le_of_lt_succ i.2))
    (fun j ↦ hY_meas (j.1 + 1) (Nat.succ_pos j.1) (Nat.succ_le_of_lt j.2))
  exact M.indepFun_of_measurable_sources hs₀ hW

/-- 联合历史 $(X_{0:k}, Y_{1:k-1})$ 与当前拍观测噪声 $N_{y,k}$ 独立（对应附录 `markov.tex` 第二段关键断言）。 -/
theorem indepFun_stateCurrObsHist_obsNoise {k : ℕ} (hk : 1 ≤ k) :
    stateCurrObsHist M.X M.Y k ⟂ᵢ[ℙ] M.Ny k := by
  let S := histSourceSet k (k - 1)
  have hs₀ : PrimSource.obsNoise ⟨k, hk⟩ ∉ S := by
    simp [S, histSourceSet]
    omega
  have hX_meas := M.measurable_X_of_subset_sources (S := S) (m := k)
    (by simp [S, histSourceSet]) (fun j hj ↦ by simp [S, histSourceSet, hj])
  have hY_meas := M.measurable_Y_of_subset_sources (S := S) (mx := k) (my := k - 1) (Nat.sub_le k 1)
    (by simp [S, histSourceSet]) (fun j hj ↦ by simp [S, histSourceSet, hj])
    (fun j hj ↦ by simp [S, histSourceSet, hj])
  have hW := measurable_prod_pi (⨆ t ∈ S, M.srcSigma t)
    (u := fun (i : Fin (k + 1)) ↦ M.X i.1)
    (v := fun (j : Fin (k - 1)) ↦ M.Y (j.1 + 1))
    (fun i ↦ hX_meas i.1 (Nat.le_of_lt_succ i.2))
    (fun j ↦ hY_meas (j.1 + 1) (Nat.succ_pos j.1) (Nat.succ_le_of_lt j.2))
  exact M.indepFun_of_measurable_sources hs₀ hW

/-- $(X_k, Y_{1:k-1})$ 与当前拍观测噪声 $N_{y,k}$ 独立（用于 Bayes 更新式 `(cw:eq:18)`）。 -/
theorem indepFun_currStateObsHist_obsNoise {k : ℕ} (hk : 1 ≤ k) :
    currStateObsHist M.X M.Y k ⟂ᵢ[ℙ] M.Ny k := by
  have h := (M.indepFun_stateCurrObsHist_obsNoise hk).comp
    (measurable_lastStateProj.prodMk measurable_snd) measurable_id
  exact h

end StateSpaceModel

end FilterFormalization

end
