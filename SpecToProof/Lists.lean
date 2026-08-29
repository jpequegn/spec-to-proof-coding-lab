import Std

namespace SpecToProof

def incrementAll (values : List Nat) : List Nat :=
  values.map (fun value => value + 1)

theorem incrementAll_eq_map (values : List Nat) :
    incrementAll values = values.map (fun value => value + 1) := by
  rfl

theorem incrementAll_length (values : List Nat) :
    (incrementAll values).length = values.length := by
  simp [incrementAll]

end SpecToProof
