(* CA tongue: symbolic *)
gcd[a_, b_] := If[b == 0, a, gcd[b, Mod[a, b]]];
Print[gcd[462, 1071]];
