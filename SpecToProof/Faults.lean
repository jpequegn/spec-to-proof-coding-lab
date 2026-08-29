import SpecToProof.Arithmetic
import SpecToProof.Parsing

namespace SpecToProof

def faultySaturatingAdd (left right cap : Nat) : Nat :=
  min (left + right) (cap + 1)

theorem faultySaturatingAdd_exceeds_cap :
    faultySaturatingAdd 8 7 10 = 11 ∧ faultySaturatingAdd 8 7 10 > 10 := by
  decide

def faultyClamp (value _lower upper : Nat) : Nat :=
  min value upper

theorem faultyClamp_ignores_lower :
    faultyClamp 2 4 9 = 2 ∧ faultyClamp 2 4 9 < 4 := by
  decide

def faultyParseBit (input : String) : Option Nat :=
  if input = "0" then
    some 0
  else if input = "1" then
    some 1
  else if input = "01" then
    some 1
  else
    none

theorem faultyParseBit_accepts_leading_zero :
    faultyParseBit "01" = some 1 ∧ parseBit "01" = none := by
  decide

end SpecToProof
