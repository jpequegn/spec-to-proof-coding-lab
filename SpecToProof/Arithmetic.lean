import Std

namespace SpecToProof

def saturatingAdd (left right cap : Nat) : Nat :=
  min (left + right) cap

theorem saturatingAdd_eq_min (left right cap : Nat) :
    saturatingAdd left right cap = min (left + right) cap := by
  rfl

theorem saturatingAdd_le_cap (left right cap : Nat) :
    saturatingAdd left right cap ≤ cap := by
  exact Nat.min_le_right _ _

def clamp (value lower upper : Nat) : Nat :=
  max lower (min value upper)

theorem clamp_lower (value lower upper : Nat) :
    lower ≤ clamp value lower upper := by
  exact Nat.le_max_left _ _

theorem clamp_upper (value lower upper : Nat) (bounds : lower ≤ upper) :
    clamp value lower upper ≤ upper := by
  unfold clamp
  exact Nat.max_le.mpr ⟨bounds, Nat.min_le_right _ _⟩

theorem clamp_eq_self (value lower upper : Nat)
    (lower_bound : lower ≤ value) (upper_bound : value ≤ upper) :
    clamp value lower upper = value := by
  unfold clamp
  rw [Nat.min_eq_left upper_bound, Nat.max_eq_right lower_bound]

end SpecToProof
