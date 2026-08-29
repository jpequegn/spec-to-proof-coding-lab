import Std

namespace SpecToProof

def sortPair (left right : Nat) : Nat × Nat :=
  if left ≤ right then (left, right) else (right, left)

theorem sortPair_ordered (left right : Nat) :
    (sortPair left right).1 ≤ (sortPair left right).2 := by
  simp only [sortPair]
  split
  · assumption
  · omega

theorem sortPair_sum (left right : Nat) :
    (sortPair left right).1 + (sortPair left right).2 = left + right := by
  simp only [sortPair]
  split
  · rfl
  · exact Nat.add_comm right left

end SpecToProof
