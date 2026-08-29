import Std

namespace SpecToProof

def parseBit (input : String) : Option Nat :=
  if input = "0" then
    some 0
  else if input = "1" then
    some 1
  else
    none

theorem parseBit_zero : parseBit "0" = some 0 := by
  simp [parseBit]

theorem parseBit_one : parseBit "1" = some 1 := by
  simp [parseBit]

theorem parseBit_other (input : String) (not_zero : input ≠ "0")
    (not_one : input ≠ "1") : parseBit input = none := by
  simp [parseBit, not_zero, not_one]

theorem parseBit_sound (input : String) (value : Nat)
    (parsed : parseBit input = some value) : value ≤ 1 := by
  simp only [parseBit] at parsed
  split at parsed
  · cases parsed
    omega
  · split at parsed
    · cases parsed
      omega
    · contradiction

end SpecToProof
