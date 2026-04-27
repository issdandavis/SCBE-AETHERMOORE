function mygcd(a::Integer, b::Integer)
    while b != 0
        a, b = b, mod(a, b)
    end
    return a
end
println(mygcd(462, 1071))
