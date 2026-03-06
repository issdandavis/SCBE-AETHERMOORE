use scbe_core::poincare_distance;

fn main() {
    let u = vec![0.1, 0.2];
    let v = vec![0.3, 0.4];

    match poincare_distance(&u, &v) {
        Ok(dist) => println!("Distance: {dist}"),
        Err(err) => eprintln!("Error: {err:?}"),
    }
}
