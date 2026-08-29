namespace SpecToProof

def identity (value : Nat) : Nat := value

theorem identity_spec (value : Nat) : identity value = value := by
  rfl

end SpecToProof
