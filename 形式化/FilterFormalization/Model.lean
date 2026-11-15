module

public import Mathlib.Probability.Independence.Basic
public import Mathlib.Probability.Kernel.Composition.MapComap
public import Mathlib.Probability.Kernel.Composition.Prod

/-!
# 非线性状态空间模型

对应论文式 `(cw:eq:1)`：$X_k=f(X_{k-1},N_{x,k})$，$Y_k=h(X_k,N_{y,k})$，$k\ge1$，
其中 $X_0$，$\{N_{x,k}\}$，$\{N_{y,k}\}$ 相互独立。状态与观测空间为任意可测空间。
为免去 $k\ge1$ 的附带假设，方程统一写在 $k+1$ 处；下标为 $0$ 的噪声不出现在方程中。
-/

@[expose] public section

open MeasureTheory ProbabilityTheory

namespace FilterFormalization

variable {Ω SX SY SNx SNy SU SN SZ : Type*} [mΩ : MeasurableSpace Ω] [MeasurableSpace SX]
  [MeasurableSpace SY] [MeasurableSpace SNx] [MeasurableSpace SNy] [MeasurableSpace SU]
  [MeasurableSpace SN] [MeasurableSpace SZ]

/-- 由机制 $g$ 与噪声分布 $\nu$ 诱导的转移核 $u\mapsto(g(u,\cdot))_*\nu$。 -/
noncomputable def mechKernel (g : SU × SN → SZ) (ν : Measure SN) : Kernel SU SZ :=
  (Kernel.id ×ₖ Kernel.const SU ν).map g

lemma isMarkovKernel_mechKernel {g : SU × SN → SZ} (hg : Measurable g) (ν : Measure SN)
    [IsProbabilityMeasure ν] : IsMarkovKernel (mechKernel g ν) :=
  Kernel.IsMarkovKernel.map _ hg

lemma mechKernel_apply {g : SU × SN → SZ} (hg : Measurable g) (ν : Measure SN) [SFinite ν]
    (u : SU) : mechKernel g ν u = ν.map fun n ↦ g (u, n) := by
  rw [mechKernel, Kernel.map_apply _ hg, Kernel.prod_apply, Kernel.id_apply, Kernel.const_apply,
    Measure.dirac_prod, Measure.map_map hg measurable_prodMk_left]
  rfl

/-- 噪声源的索引：`none` 为 $X_0$，`inl k` 为 $N_{x,k}$，`inr k` 为 $N_{y,k}$。 -/
abbrev Src := Option (ℕ ⊕ ℕ)

/-- 各噪声源生成的 $\sigma$-代数。 -/
@[reducible] def srcSigma (X0 : Ω → SX) (Nx : ℕ → Ω → SNx) (Ny : ℕ → Ω → SNy) : Src → MeasurableSpace Ω
  | none => .comap X0 inferInstance
  | some (.inl k) => .comap (Nx k) inferInstance
  | some (.inr k) => .comap (Ny k) inferInstance

/-- 一般非线性状态空间模型。 -/
structure StateSpaceModel (Ω SX SY SNx SNy : Type*) [MeasurableSpace Ω] [MeasurableSpace SX]
    [MeasurableSpace SY] [MeasurableSpace SNx] [MeasurableSpace SNy] (P : Measure Ω) where
  /-- 状态 $X_k$，观测 $Y_k$，过程噪声 $N_{x,k}$，观测噪声 $N_{y,k}$。 -/
  (X : ℕ → Ω → SX) (Y : ℕ → Ω → SY) (Nx : ℕ → Ω → SNx) (Ny : ℕ → Ω → SNy)
  /-- 状态转移函数 $f$ 与观测函数 $h$。 -/
  (f : SX × SNx → SX) (h : SX × SNy → SY)
  measurable_X0 : Measurable (X 0)
  measurable_Nx : ∀ k, Measurable (Nx k)
  measurable_Ny : ∀ k, Measurable (Ny k)
  measurable_f : Measurable f
  measurable_h : Measurable h
  /-- $X_{k+1}=f(X_k,N_{x,k+1})$。 -/
  state_eq : ∀ k, X (k + 1) = fun ω ↦ f (X k ω, Nx (k + 1) ω)
  /-- $Y_{k+1}=h(X_{k+1},N_{y,k+1})$。 -/
  obs_eq : ∀ k, Y (k + 1) = fun ω ↦ h (X (k + 1) ω, Ny (k + 1) ω)
  /-- 初始状态与全体噪声相互独立。 -/
  indep : iIndep (srcSigma (X 0) Nx Ny) P

namespace StateSpaceModel

variable {P : Measure Ω} (M : StateSpaceModel Ω SX SY SNx SNy P) {a b : ℕ}

/-- 第 `s` 个噪声源生成的 $\sigma$-代数。 -/
abbrev src : Src → MeasurableSpace Ω := srcSigma (M.X 0) M.Nx M.Ny

lemma src_le (s : Src) : M.src s ≤ mΩ := by
  rcases s with _ | _ | _
  exacts [M.measurable_X0.comap_le, (M.measurable_Nx _).comap_le, (M.measurable_Ny _).comap_le]

/-- 生成 $(X_{0:a},Y_{1:b})$ 所用的噪声源：$X_0$，$N_{x,j}$（$j\le a$），$N_{y,j}$（$j\le b$）。 -/
def srcs (a b : ℕ) : Set Src := {s | ∀ j, (s = some (.inl j) → j ≤ a) ∧ (s = some (.inr j) → j ≤ b)}

/-- `srcs a b` 中噪声源生成的 $\sigma$-代数。 -/
abbrev histSigma (a b : ℕ) : MeasurableSpace Ω := ⨆ s ∈ srcs a b, M.src s

lemma measurable_src {s : Src} (hs : s ∈ srcs a b) {β : Type*} [MeasurableSpace β] {V : Ω → β}
    (hV : MeasurableSpace.comap V inferInstance = M.src s) : Measurable[M.histSigma a b] V :=
  Measurable.of_comap_le (hV ▸ le_biSup M.src hs)

lemma measurable_X_hist {i : ℕ} (hi : i ≤ a) : Measurable[M.histSigma a b] (M.X i) := by
  induction i with
  | zero => exact M.measurable_src (s := none) (by simp [srcs]) rfl
  | succ n ih =>
    rw [M.state_eq]
    exact M.measurable_f.comp ((ih (by omega)).prodMk
      (M.measurable_src (s := some (.inl (n + 1))) (by simpa [srcs]) rfl))

lemma measurable_Y_hist {j : ℕ} (ha : j + 1 ≤ a) (hb : j + 1 ≤ b) :
    Measurable[M.histSigma a b] (M.Y (j + 1)) := by
  rw [M.obs_eq]
  exact M.measurable_h.comp ((M.measurable_X_hist ha).prodMk
    (M.measurable_src (s := some (.inr (j + 1))) (by simpa [srcs]) rfl))

/-- 联合历史 $(X_{0:a},Y_{1:b})$。 -/
def hist (a b : ℕ) : Ω → (Fin (a + 1) → SX) × (Fin b → SY) :=
  fun ω ↦ (fun i ↦ M.X i ω, fun j ↦ M.Y (j + 1) ω)

/-- 从历史中取出末尾状态。 -/
def last {β : Type*} (p : (Fin (a + 1) → SX) × β) : SX := p.1 (Fin.last a)

lemma measurable_last {β : Type*} [MeasurableSpace β] :
    Measurable (last (SX := SX) (a := a) (β := β)) :=
  (measurable_pi_apply _).comp measurable_fst

lemma measurable_hist_sigma (hba : b ≤ a) : Measurable[M.histSigma a b] (M.hist a b) := by
  let _ := M.histSigma a b
  exact (measurable_pi_iff.2 fun i ↦ M.measurable_X_hist (mΩ := mΩ) (Nat.le_of_lt_succ i.2)).prodMk
    (measurable_pi_iff.2 fun j ↦ M.measurable_Y_hist (mΩ := mΩ) (by omega) (by omega))

lemma measurable_hist (hba : b ≤ a) : Measurable (M.hist a b) :=
  (M.measurable_hist_sigma hba).mono (iSup₂_le fun s _ ↦ M.src_le s) le_rfl

/-- 历史与未参与生成它的噪声源独立。 -/
lemma indep_hist_src (hba : b ≤ a) {s : Src} (hs : s ∉ srcs a b) :
    Indep (.comap (M.hist a b) inferInstance) (M.src s) P :=
  indep_of_indep_of_le_left (indep_of_indep_of_le_right
    (indep_iSup_of_disjoint M.src_le M.indep (Set.disjoint_singleton_right.mpr hs))
    (le_biSup M.src (Set.mem_singleton s))) (M.measurable_hist_sigma hba).comap_le

/-- $(X_{0:k},Y_{1:k})$ 与 $N_{x,k+1}$ 独立。 -/
theorem indepFun_hist_Nx (k : ℕ) : M.hist k k ⟂ᵢ[P] M.Nx (k + 1) :=
  (IndepFun_iff_Indep ..).2 (M.indep_hist_src (s := some (.inl (k + 1))) le_rfl (by simp [srcs]))

/-- $(X_{0:k+1},Y_{1:k})$ 与 $N_{y,k+1}$ 独立。 -/
theorem indepFun_hist_Ny (k : ℕ) : M.hist (k + 1) k ⟂ᵢ[P] M.Ny (k + 1) :=
  (IndepFun_iff_Indep ..).2 (M.indep_hist_src (s := some (.inr (k + 1))) (by omega) (by simp [srcs]))

end StateSpaceModel

end FilterFormalization

end
