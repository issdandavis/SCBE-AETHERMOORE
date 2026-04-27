fn gcd(mut a: u64, mut b: u64) -> u64 {
    while b != 0 {
        let t = b; b = a % b; a = t;
    }
    a
}
fn main() { println!("{}", gcd(462, 1071)); }
