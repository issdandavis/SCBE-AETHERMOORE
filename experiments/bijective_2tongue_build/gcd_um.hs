-- UM tongue: pure-functional
myGcd :: Integer -> Integer -> Integer
myGcd a 0 = a
myGcd a b = myGcd b (a `mod` b)
main :: IO ()
main = print (myGcd 462 1071)
