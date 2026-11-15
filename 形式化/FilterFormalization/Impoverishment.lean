module

public import Mathlib.Algebra.Order.Chebyshev
public import Mathlib.Analysis.SpecificLimits.Basic
public import Mathlib.Data.Set.Card
public import Mathlib.Probability.ProbabilityMassFunction.Constructions

/-!
# 零过程噪声下的粒子贫化

对应论文定理 `cw:thm:bpf-impoverishment`。粒子数为 $N$，预测为确定性映射，
每步按归一化权重独立抽取 $N$ 个祖先下标（多项重采样）。记 $D_k$ 为第 $k$ 步重采样后互不相同的粒子位置数，则
$1\le\mathbb E[D_k]\le1+(N-1)(1-N^{1-N})^k$，且 $\mathbb E[D_k]\to1$。

粒子组的分布用离散概率分布 `PMF` 表示，期望为加权和，取值于 $[0,\infty]$。
论文要求 $N\ge2$；这里只需 $N\ge1$。固定的观测记录体现为权重只依赖时刻与预测粒子。
-/

@[expose] public section

open Filter Topology Finset
open scoped ENNReal NNReal

namespace FilterFormalization

variable {α β S : Type*} {N : ℕ}

/-! ## 离散分布下的期望 -/

/-- 非负函数 $F$ 在离散分布 $p$ 下的期望。 -/
noncomputable def expect (p : PMF α) (F : α → ℝ≥0∞) : ℝ≥0∞ := ∑' x, p x * F x

lemma expect_mono {p : PMF α} {F G : α → ℝ≥0∞} (h : ∀ x, F x ≤ G x) : expect p F ≤ expect p G :=
  tsum_le_tsum fun x ↦ by gcongr; exact h x

lemma expect_const (p : PMF α) (c : ℝ≥0∞) : expect p (fun _ ↦ c) = c := by
  rw [expect, ENNReal.tsum_mul_right, p.tsum_coe, one_mul]

lemma expect_const_add_mul (p : PMF α) (a b : ℝ≥0∞) (F : α → ℝ≥0∞) :
    expect p (fun x ↦ a + b * F x) = a + b * expect p F := by
  simp_rw [expect, mul_add, tsum_add, mul_left_comm _ b, ENNReal.tsum_mul_left,
    ENNReal.tsum_mul_right, p.tsum_coe, one_mul]

lemma expect_bind (p : PMF α) (f : α → PMF β) (F : β → ℝ≥0∞) :
    expect (p.bind f) F = expect p fun x ↦ expect (f x) F := by
  simp_rw [expect, PMF.bind_apply, ← ENNReal.tsum_mul_right, ← ENNReal.tsum_mul_left]
  rw [tsum_comm]
  simp_rw [mul_assoc]

lemma expect_map (p : PMF α) (g : α → β) (F : β → ℝ≥0∞) : expect (p.map g) F = expect p (F ∘ g) := by
  rw [← PMF.bind_pure_comp, expect_bind]
  simp [expect, PMF.pure_apply, ite_mul]

/-! ## 模型 -/

/-- 粒子组 $x$ 中互不相同的位置数 $D$。 -/
noncomputable def distinct (x : Fin N → S) : ℕ := (Set.range x).ncard

lemma distinct_comp_le (x : Fin N → S) (a : Fin N → Fin N) : distinct (x ∘ a) ≤ distinct x :=
  Set.ncard_le_ncard (Set.range_comp_subset_range a x) (Set.finite_range x)

lemma distinct_map_le (φ : S → S) (x : Fin N → S) : distinct (φ ∘ x) ≤ distinct x := by
  rw [distinct, Set.range_comp]
  exact Set.ncard_image_le (Set.finite_range x)

lemma distinct_le (x : Fin N → S) : distinct x ≤ N := by
  rw [distinct, ← Set.image_univ]
  exact (Set.ncard_image_le Set.finite_univ).trans (by simp [Set.ncard_univ])

/-- 粒子组尚未合并为单点的示性函数 $\mathbb I_{\{D>1\}}$。 -/
noncomputable def multi (x : Fin N → S) : ℝ≥0∞ := if 1 < distinct x then 1 else 0

lemma multi_le_one (x : Fin N → S) : multi x ≤ 1 := by
  unfold multi
  split_ifs <;> simp

lemma multi_eq_zero {x : Fin N → S} (h : distinct x ≤ 1) : multi x = 0 := by
  simp [multi, h.not_gt]

variable [NeZero N]

lemma one_le_distinct (x : Fin N → S) : 1 ≤ distinct x :=
  (Set.ncard_pos (Set.finite_range x)).2 (Set.range_nonempty x)

lemma distinct_comp_const (x : Fin N → S) (i : Fin N) : distinct (x ∘ fun _ : Fin N ↦ i) = 1 := by
  rw [distinct, show (x ∘ fun _ : Fin N ↦ i) = fun _ ↦ x i from rfl, Set.range_const,
    Set.ncard_singleton]

/-- 一步之内全部粒子选中同一祖先的概率下界 $N^{1-N}$。 -/
noncomputable def coal (N : ℕ) : ℝ≥0 := (N : ℝ≥0)⁻¹ ^ (N - 1)

lemma coal_le_sum_pow {p : Fin N → ℝ≥0} (hp : ∑ i, p i = 1) : coal N ≤ ∑ i, p i ^ N := by
  have h := pow_sum_div_card_le_sum_pow (s := univ) (f := p) (fun _ _ ↦ zero_le) (N - 1)
  rw [hp, one_pow, card_univ, Fintype.card_fin, Nat.sub_add_cancel (NeZero.one_le)] at h
  simpa [coal, one_div, inv_pow] using h

/-- 零过程噪声的自举粒子滤波：确定性预测，加权，多项重采样。 -/
structure ZeroNoiseBPF (S : Type*) (N : ℕ) where
  /-- 初始粒子组的分布。 -/
  init : PMF (Fin N → S)
  /-- 第 $k$ 步的确定性预测映射。 -/
  pred : ℕ → S → S
  /-- 第 $k$ 步的归一化权重，由预测粒子组决定；观测记录固定，故不作为自变量。 -/
  weight : ℕ → (Fin N → S) → Fin N → ℝ≥0
  weight_sum : ∀ k x, ∑ i, weight k x i = 1

namespace ZeroNoiseBPF

variable (B : ZeroNoiseBPF S N)

/-- 祖先下标 $(A_1,\dots,A_N)$ 的分布：各分量独立，$\mathbb P(A_j=i)=w^{(i)}$。 -/
noncomputable def ancestors (k : ℕ) (x : Fin N → S) : PMF (Fin N → Fin N) :=
  PMF.ofFintype (fun a ↦ ∏ j, (B.weight k x (a j) : ℝ≥0∞)) <| by
    have h := prod_univ_sum (fun _ : Fin N ↦ (univ : Finset (Fin N)))
      fun _ i ↦ (B.weight k x i : ℝ≥0∞)
    have hw : ∑ j, (B.weight k x j : ℝ≥0∞) = 1 := by exact_mod_cast B.weight_sum k x
    rw [Fintype.piFinset_univ] at h
    simp [← h, hw]

/-- 一步更新：先预测，再重采样，$x_k^{+,(j)}=x_k^{-,(A_j)}$。 -/
noncomputable def step (k : ℕ) (x : Fin N → S) : PMF (Fin N → S) :=
  (B.ancestors k (B.pred k ∘ x)).map fun a ↦ B.pred k ∘ x ∘ a

/-- 第 $k$ 步重采样后粒子组的分布。 -/
noncomputable def law : ℕ → PMF (Fin N → S)
  | 0 => B.init
  | k + 1 => (law k).bind (B.step k)

/-- 单步估计：$\mathbb P(D_{k+1}>1\mid x_k^+)\le(1-N^{1-N})\,\mathbb I_{\{D_k>1\}}$。 -/
lemma expect_step_multi_le (k : ℕ) (x : Fin N → S) :
    expect (B.step k x) multi ≤ (1 - coal N) * multi x := by
  rw [step, expect_map, expect, tsum_fintype]
  set y := B.pred k ∘ x
  have hy (a : Fin N → Fin N) : distinct (y ∘ a) ≤ distinct x :=
    (distinct_comp_le y a).trans (distinct_map_le _ x)
  by_cases h : 1 < distinct x
  · -- 祖先全部相同的下标组成集合 `T`，其上 `multi` 为零，其概率不小于 `coal N`
    classical
    let T : Finset (Fin N → Fin N) := univ.image fun i _ ↦ i
    have hT : (coal N : ℝ≥0∞) ≤ ∑ a ∈ T, B.ancestors k y a := by
      rw [sum_image fun i _ j _ hij ↦ congrFun hij 0]
      simpa [ancestors] using ENNReal.coe_le_coe.2 (coal_le_sum_pow (B.weight_sum k y))
    have hQ : ∑ a, B.ancestors k y a * (multi ∘ fun a ↦ y ∘ a) a ≤ ∑ a ∈ Tᶜ, B.ancestors k y a := by
      rw [← sum_add_sum_compl T, sum_eq_zero, zero_add]
      · exact sum_le_sum fun a _ ↦ mul_le_of_le_one_right' (multi_le_one _)
      · intro a ha
        obtain ⟨i, -, rfl⟩ := mem_image.1 ha
        simp [multi_eq_zero (distinct_comp_const y i).le]
    rw [show multi x = 1 by simp [multi, h], mul_one]
    refine ENNReal.le_sub_of_add_le_right ENNReal.coe_ne_top ((add_le_add hQ hT).trans_eq ?_)
    rw [sum_compl_add_sum]
    simpa [tsum_fintype] using (B.ancestors k y).tsum_coe
  · exact (sum_eq_zero fun a _ ↦ mul_eq_zero_of_right _
      (multi_eq_zero ((hy a).trans (not_lt.1 h)))).le.trans zero_le

/-- $\mathbb P(D_k>1)\le(1-N^{1-N})^k$。 -/
theorem expect_multi_le (k : ℕ) : expect (B.law k) multi ≤ (1 - coal N : ℝ≥0∞) ^ k := by
  induction k with
  | zero =>
    simpa [expect_const] using expect_mono (p := B.law 0) multi_le_one
  | succ k ih =>
    rw [law, expect_bind, pow_succ']
    calc _ ≤ expect (B.law k) fun x ↦ 0 + (1 - coal N) * multi x :=
          expect_mono fun x ↦ by simpa using B.expect_step_multi_le k x
      _ = (1 - coal N) * expect (B.law k) multi := by rw [expect_const_add_mul, zero_add]
      _ ≤ _ := by gcongr

/-- 论文式 `cw:eq:particle-count-decay` 的上下界：$1\le\mathbb E[D_k]\le1+(N-1)(1-N^{1-N})^k$。 -/
theorem one_le_expect_distinct (k : ℕ) : 1 ≤ expect (B.law k) fun x ↦ (distinct x : ℝ≥0∞) :=
  (expect_const _ 1).ge.trans (expect_mono fun x ↦ by exact_mod_cast one_le_distinct x)

@[inherit_doc one_le_expect_distinct]
theorem expect_distinct_le (k : ℕ) :
    expect (B.law k) (fun x ↦ (distinct x : ℝ≥0∞)) ≤ 1 + (N - 1) * (1 - coal N : ℝ≥0∞) ^ k :=
  calc _ ≤ expect (B.law k) fun x ↦ 1 + (N - 1) * multi x := expect_mono fun x ↦ by
        unfold multi
        split_ifs with h
        · rw [mul_one, add_tsub_cancel_of_le (by exact_mod_cast NeZero.one_le)]
          exact_mod_cast distinct_le x
        · simpa using not_lt.1 h
    _ = 1 + (N - 1) * expect (B.law k) multi := expect_const_add_mul ..
    _ ≤ _ := by gcongr; exact B.expect_multi_le k

/-- 论文式 `cw:eq:particle-count-decay` 的极限：$\lim_{k\to\infty}\mathbb E[D_k]=1$。 -/
theorem tendsto_expect_distinct :
    Tendsto (fun k ↦ expect (B.law k) fun x ↦ (distinct x : ℝ≥0∞)) atTop (𝓝 1) := by
  have h0 : Tendsto (fun k ↦ (1 - coal N : ℝ≥0∞) ^ k) atTop (𝓝 0) :=
    ENNReal.tendsto_pow_atTop_nhds_zero_of_lt_one <|
      ENNReal.sub_lt_self ENNReal.one_ne_top one_ne_zero (by simp [coal, NeZero.ne])
  have h1 := (ENNReal.Tendsto.const_mul (a := (N - 1 : ℝ≥0∞)) h0 (.inr (by simp))).const_add 1
  rw [mul_zero, add_zero] at h1
  exact tendsto_of_tendsto_of_tendsto_of_le_of_le tendsto_const_nhds h1 B.one_le_expect_distinct
    B.expect_distinct_le

end ZeroNoiseBPF

end FilterFormalization

end
