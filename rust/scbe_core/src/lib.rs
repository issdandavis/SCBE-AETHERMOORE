//! SCBE Rust core math primitives.
//!
//! This crate starts with the canonical Poincare-ball distance function used
//! for polyglot parity checks across Python, TypeScript, and Rust.

/// Error variants for Poincare distance calculations.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum PoincareError {
    DimensionMismatch,
    NonFiniteCoordinate,
    OutsideUnitBall,
    InvalidAcoshArgument,
}

/// Computes the Poincare-ball distance between two points `u` and `v`.
///
/// Formula:
/// `d = acosh(1 + 2 * ||u - v||^2 / ((1 - ||u||^2) * (1 - ||v||^2)))`
///
/// Both points must lie strictly inside the unit ball.
pub fn poincare_distance(u: &[f64], v: &[f64]) -> Result<f64, PoincareError> {
    if u.len() != v.len() {
        return Err(PoincareError::DimensionMismatch);
    }

    let mut norm_u_sq = 0.0_f64;
    let mut norm_v_sq = 0.0_f64;
    let mut diff_sq = 0.0_f64;

    for i in 0..u.len() {
        let ui = u[i];
        let vi = v[i];

        if !ui.is_finite() || !vi.is_finite() {
            return Err(PoincareError::NonFiniteCoordinate);
        }

        norm_u_sq += ui * ui;
        norm_v_sq += vi * vi;

        let diff = ui - vi;
        diff_sq += diff * diff;
    }

    if norm_u_sq >= 1.0 || norm_v_sq >= 1.0 {
        return Err(PoincareError::OutsideUnitBall);
    }

    let denominator = (1.0 - norm_u_sq) * (1.0 - norm_v_sq);
    if !denominator.is_finite() || denominator <= 0.0 {
        return Err(PoincareError::InvalidAcoshArgument);
    }

    let arg = 1.0 + (2.0 * diff_sq) / denominator;
    if !arg.is_finite() {
        return Err(PoincareError::InvalidAcoshArgument);
    }

    // Numerical safety near 1.0 where tiny negative roundoff could happen.
    if arg < 1.0 {
        let eps = 1e-12;
        if 1.0 - arg > eps {
            return Err(PoincareError::InvalidAcoshArgument);
        }
        return Ok(1.0_f64.acosh());
    }

    Ok(arg.acosh())
}

#[cfg(test)]
mod tests {
    use super::{poincare_distance, PoincareError};

    fn assert_close(a: f64, b: f64, tol: f64) {
        assert!((a - b).abs() <= tol, "expected {a} ~= {b} (tol={tol})");
    }

    #[test]
    fn returns_zero_for_identical_points() {
        let u = [0.1, 0.2, 0.3];
        let d = poincare_distance(&u, &u).expect("distance should compute");
        assert_close(d, 0.0, 1e-12);
    }

    #[test]
    fn symmetric_distance() {
        let u = [0.1, 0.2];
        let v = [0.3, 0.4];
        let d_uv = poincare_distance(&u, &v).expect("distance should compute");
        let d_vu = poincare_distance(&v, &u).expect("distance should compute");
        assert_close(d_uv, d_vu, 1e-12);
    }

    #[test]
    fn matches_known_vector() {
        let u = [0.1, 0.2];
        let v = [0.3, 0.4];
        let d = poincare_distance(&u, &v).expect("distance should compute");
        assert_close(d, 0.658_219_427_369_333_1, 1e-12);
    }

    #[test]
    fn dimension_mismatch_rejected() {
        let u = [0.1, 0.2];
        let v = [0.1, 0.2, 0.3];
        let err = poincare_distance(&u, &v).expect_err("should reject mismatch");
        assert_eq!(err, PoincareError::DimensionMismatch);
    }

    #[test]
    fn non_finite_input_rejected() {
        let u = [f64::NAN, 0.2];
        let v = [0.1, 0.2];
        let err = poincare_distance(&u, &v).expect_err("should reject non-finite");
        assert_eq!(err, PoincareError::NonFiniteCoordinate);
    }

    #[test]
    fn outside_ball_rejected() {
        let u = [1.0, 0.0];
        let v = [0.1, 0.2];
        let err = poincare_distance(&u, &v).expect_err("should reject boundary/outside");
        assert_eq!(err, PoincareError::OutsideUnitBall);
    }

    #[test]
    fn near_boundary_distance_is_larger() {
        let origin = [0.0, 0.0];
        let near = [0.3, 0.0];
        let far = [0.9, 0.0];
        let d_near = poincare_distance(&origin, &near).expect("distance should compute");
        let d_far = poincare_distance(&origin, &far).expect("distance should compute");
        assert!(d_far > d_near);
    }
}
