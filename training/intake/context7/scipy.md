# SciPy

SciPy is a Python library for scientific and technical computing that builds on NumPy. It provides efficient algorithms for optimization, integration, interpolation, eigenvalue problems, algebraic equations, differential equations, statistics, and signal processing.

## Subpackages Overview

SciPy is organized into domain-specific subpackages:

```python
import scipy

# Key subpackages:
# scipy.sparse       - Sparse matrices and sparse linear algebra
# scipy.linalg       - Dense linear algebra (extends numpy.linalg)
# scipy.signal       - Signal processing (filtering, spectral analysis)
# scipy.fft          - Fast Fourier transforms
# scipy.optimize     - Optimization and root finding
# scipy.integrate    - Numerical integration and ODE solvers
# scipy.interpolate  - Interpolation (splines, RBF)
# scipy.stats        - Statistical distributions and tests
# scipy.spatial      - Spatial data structures (KDTree, convex hull)
# scipy.special      - Special mathematical functions
# scipy.ndimage      - N-dimensional image processing
# scipy.io           - Data input/output (MATLAB, WAV, NetCDF)
# scipy.cluster      - Clustering algorithms (hierarchical, k-means)

# Check version
print(scipy.__version__)
```

## Sparse Linear Algebra

Solve sparse linear systems and compute eigenvalues/singular values for large sparse matrices:

```python
import numpy as np
from scipy import sparse
from scipy.sparse.linalg import spsolve, eigs, svds

# Create a sparse matrix (CSR format)
row = np.array([0, 0, 1, 1, 2, 2, 3, 3])
col = np.array([0, 1, 0, 1, 2, 3, 2, 3])
data = np.array([4.0, -1.0, -1.0, 4.0, 4.0, -1.0, -1.0, 4.0])
A = sparse.csr_matrix((data, (row, col)), shape=(4, 4))

print(f"Shape: {A.shape}")
print(f"Non-zeros: {A.nnz}")
print(f"Density: {A.nnz / (A.shape[0] * A.shape[1]):.2%}")

# Solve sparse linear system: Ax = b
b = np.array([1.0, 2.0, 3.0, 4.0])
x = spsolve(A, b)
print(f"Solution: {x}")

# Verify: A @ x should equal b
residual = np.linalg.norm(A @ x - b)
print(f"Residual: {residual:.2e}")

# Compute largest eigenvalues of a sparse matrix
# Create a large sparse matrix (tridiagonal)
n = 1000
diag_main = 2.0 * np.ones(n)
diag_off = -1.0 * np.ones(n - 1)
A_large = sparse.diags([diag_off, diag_main, diag_off], [-1, 0, 1], format='csr')

# Find 6 largest eigenvalues
eigenvalues, eigenvectors = eigs(A_large, k=6, which='LM')
print(f"Largest eigenvalues: {eigenvalues.real}")

# Find 6 smallest eigenvalues
eigenvalues_sm, eigenvectors_sm = eigs(A_large, k=6, which='SM')
print(f"Smallest eigenvalues: {eigenvalues_sm.real}")

# Compute truncated SVD of a sparse matrix
# Useful for dimensionality reduction and latent semantic analysis
m, n_cols = 500, 200
A_rect = sparse.random(m, n_cols, density=0.05, format='csr')

# Find 10 largest singular values
U, sigma, Vt = svds(A_rect, k=10)
print(f"Singular values: {sigma}")
print(f"U shape: {U.shape}")       # (500, 10)
print(f"Vt shape: {Vt.shape}")     # (10, 200)

# Reconstruct low-rank approximation
A_approx = U @ np.diag(sigma) @ Vt
error = sparse.linalg.norm(A_rect - sparse.csr_matrix(A_approx))
print(f"Reconstruction error: {error:.4f}")
```

## Signal Detrending with FFT

Remove trends from signals and analyze frequency content:

```python
import numpy as np
from scipy import signal, fft

# Generate a signal with trend + periodic components + noise
t = np.linspace(0, 10, 1000)
trend = 0.5 * t + 2.0              # Linear trend
periodic = 3.0 * np.sin(2 * np.pi * 5 * t) + 1.5 * np.sin(2 * np.pi * 12 * t)
noise = 0.5 * np.random.randn(len(t))
raw_signal = trend + periodic + noise

# Detrend: remove linear trend
detrended = signal.detrend(raw_signal, type='linear')

# Detrend: remove constant (mean)
demeaned = signal.detrend(raw_signal, type='constant')

# Detrend with breakpoints (piecewise linear)
detrended_pw = signal.detrend(raw_signal, type='linear', bp=[250, 500, 750])

# FFT analysis of the detrended signal
N = len(detrended)
dt = t[1] - t[0]
freqs = fft.fftfreq(N, d=dt)
spectrum = fft.fft(detrended)
magnitude = np.abs(spectrum[:N // 2]) * 2 / N

# Find dominant frequencies
positive_freqs = freqs[:N // 2]
peak_indices = np.argsort(magnitude)[-5:]  # Top 5 peaks
for idx in peak_indices:
    print(f"Frequency: {positive_freqs[idx]:.2f} Hz, Magnitude: {magnitude[idx]:.4f}")

# Bandpass filter to isolate specific frequency range
sos = signal.butter(4, [3, 8], btype='bandpass', fs=1/dt, output='sos')
filtered = signal.sosfilt(sos, detrended)

# Welch power spectral density
freqs_psd, psd = signal.welch(detrended, fs=1/dt, nperseg=256)
print(f"PSD peak at: {freqs_psd[np.argmax(psd)]:.2f} Hz")

# Spectrogram (time-frequency analysis)
freqs_spec, times_spec, Sxx = signal.spectrogram(detrended, fs=1/dt, nperseg=128)
print(f"Spectrogram shape: {Sxx.shape}")
```
