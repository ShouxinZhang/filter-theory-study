module

public import Mathlib.MeasureTheory.Measure.Map
public import Mathlib.MeasureTheory.Integral.Lebesgue.Map
public import Mathlib.Probability.Kernel.Basic
public import Mathlib.Probability.Kernel.Posterior

/-!
# FilterFormalization 基础入口

滤波理论形式化的公共入口与最小冒烟验证模块，确认 `Mathlib` 测度论与转移核（`κ ∘ₘ μ`、`μ ⊗ₘ κ`、后验核 `κ†μ`）预编译缓存工作正常。
-/

@[expose] public section

namespace FilterFormalization

open MeasureTheory ProbabilityTheory

/-- 推前测度与拉回函数的非负积分对偶性（对应仓库符号习惯 `⟨f, T_* μ⟩ = ⟨T^* f, μ⟩`）。 -/
theorem pushforward_pullback_lintegral_duality
    {SX SY : Type*} [MeasurableSpace SX] [MeasurableSpace SY]
    (μ : Measure SX) {T : SX → SY} (hT : Measurable T)
    {f : SY → ENNReal} (hf : Measurable f) :
    ∫⁻ y, f y ∂(μ.map T) = ∫⁻ x, f (T x) ∂μ :=
  lintegral_map hf hT

end FilterFormalization

end
