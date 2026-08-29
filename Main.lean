import SpecToProof

def main : IO Unit := do
  IO.println s!"spec-to-proof smoke: {SpecToProof.identity 4}"
