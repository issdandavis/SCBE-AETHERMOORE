import Mathlib.Logic.Equiv.List

namespace SCBE

abbrev ByteSymbol := Fin 256
abbrev Tongue := Fin 6

/-- Token t is the valid vocabulary of tongue t, not every possible string. -/
abbrev TongueCodecs (Token : Tongue → Type) := (t : Tongue) → (ByteSymbol ≃ Token t)

variable {Token : Tongue → Type}

def encode (codecs : TongueCodecs Token) (t : Tongue) (xs : List ByteSymbol) : List (Token t) :=
  xs.map (codecs t)

def decode (codecs : TongueCodecs Token) (t : Tongue) (xs : List (Token t)) : List ByteSymbol :=
  xs.map (codecs t).symm

theorem codec_roundtrip (codecs : TongueCodecs Token) (t : Tongue) (xs : List ByteSymbol) :
    decode codecs t (encode codecs t xs) = xs := by simp [encode, decode, List.map_map]

def translate (codecs : TongueCodecs Token) (source target : Tongue) (xs : List (Token source)) :
    List (Token target) := encode codecs target (decode codecs source xs)

theorem translation_composes (codecs : TongueCodecs Token) (a b c : Tongue) (xs : List (Token a)) :
    translate codecs b c (translate codecs a b xs) = translate codecs a c xs := by
  simp [translate, codec_roundtrip]

theorem translation_back (codecs : TongueCodecs Token) (a b : Tongue) (xs : List (Token a)) :
    translate codecs b a (translate codecs a b xs) = xs := by
  rw [translation_composes]
  simp only [translate, encode, decode, List.map_map]
  have h : (codecs a) ∘ (codecs a).symm = id := by funext x; simp
  simp [h]

theorem codec_preserves_length (codecs : TongueCodecs Token) (t : Tongue) (xs : List ByteSymbol) :
    (encode codecs t xs).length = xs.length := by simp [encode]

end SCBE
