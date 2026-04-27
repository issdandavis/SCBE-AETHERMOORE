# Euclid's Algorithm — Narrative Form (DR tongue)

Given two numbers, the larger holds the secret.
Subtract the smaller from the larger as remainders, repeatedly,
until nothing remains to subtract. What stands is the **GCD**.

    gcd(462, 1071)
    -> gcd(1071, 462)
    -> gcd(462, 147)
    -> gcd(147, 21)
    -> gcd(21, 0)
    => **21**
