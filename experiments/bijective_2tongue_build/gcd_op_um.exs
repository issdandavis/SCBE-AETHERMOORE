defmodule G do
  def gcd(a, 0), do: a
  def gcd(a, b), do: gcd(b, rem(a, b))
end
IO.puts(G.gcd(462, 1071))
