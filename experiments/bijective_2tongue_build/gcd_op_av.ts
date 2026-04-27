function gcd(a: bigint, b: bigint): bigint {
  while (b !== 0n) { [a, b] = [b, a % b]; }
  return a;
}
console.log(gcd(462n, 1071n).toString());
