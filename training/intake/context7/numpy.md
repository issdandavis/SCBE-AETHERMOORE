# NumPy

NumPy is the fundamental package for scientific computing with Python. It provides a powerful N-dimensional array object, broadcasting functions, tools for integrating C/C++ code, linear algebra, Fourier transforms, and random number capabilities.

## Broadcasting with Scalars and Arrays

Broadcasting allows arithmetic operations between arrays of different shapes:

```python
import numpy as np

# Scalar broadcast: operates on every element
a = np.array([1, 2, 3, 4])
result = a * 2          # array([2, 4, 6, 8])
result = a + 10         # array([11, 12, 13, 14])

# 1D + 2D broadcasting
matrix = np.array([[1, 2, 3],
                   [4, 5, 6],
                   [7, 8, 9]])
row = np.array([10, 20, 30])

# row broadcasts across each row of the matrix
result = matrix + row
# array([[11, 22, 33],
#        [14, 25, 36],
#        [17, 28, 39]])

# Column vector broadcasting
col = np.array([[100], [200], [300]])
result = matrix + col
# array([[101, 102, 103],
#        [204, 205, 206],
#        [307, 308, 309]])

# Broadcasting rules:
# 1. Arrays are compared from trailing dimensions
# 2. Dimensions are compatible if equal or one of them is 1
# 3. Arrays with fewer dimensions are padded with 1s on the left

# Normalize columns (subtract column means)
data = np.random.randn(100, 5)
col_means = data.mean(axis=0)       # shape (5,)
normalized = data - col_means        # (100,5) - (5,) broadcasts

# Normalize rows (subtract row means)
row_means = data.mean(axis=1, keepdims=True)  # shape (100, 1)
normalized = data - row_means                  # (100,5) - (100,1) broadcasts
```

## newaxis for Outer Operations

Use `np.newaxis` (or `None`) to add dimensions for outer products and cross-array operations:

```python
import numpy as np

# Outer product using newaxis
a = np.array([1, 2, 3])
b = np.array([10, 20, 30, 40])

# a[:, np.newaxis] has shape (3, 1), b has shape (4,)
# Result shape: (3, 4)
outer = a[:, np.newaxis] * b
# array([[ 10,  20,  30,  40],
#        [ 20,  40,  60,  80],
#        [ 30,  60,  90, 120]])

# Equivalent to np.outer(a, b)
assert np.array_equal(outer, np.outer(a, b))

# Pairwise distances using newaxis
points = np.array([1.0, 3.0, 5.0, 7.0])
# |points[i] - points[j]| for all i, j
distances = np.abs(points[:, np.newaxis] - points[np.newaxis, :])
# shape: (4, 4)

# 2D pairwise Euclidean distance
X = np.random.randn(100, 3)  # 100 points in 3D
# X[:, np.newaxis, :] has shape (100, 1, 3)
# X[np.newaxis, :, :] has shape (1, 100, 3)
diff = X[:, np.newaxis, :] - X[np.newaxis, :, :]   # (100, 100, 3)
dist_matrix = np.sqrt((diff ** 2).sum(axis=-1))      # (100, 100)

# Meshgrid alternative using newaxis
x = np.linspace(0, 1, 50)
y = np.linspace(0, 1, 30)
# Create 2D grid values
z = np.sin(x[:, np.newaxis] * np.pi) * np.cos(y[np.newaxis, :] * np.pi)
print(z.shape)  # (50, 30)
```

## Linear Algebra on Stacked Arrays

NumPy's linear algebra functions operate on batches of matrices (stacked in higher dimensions):

```python
import numpy as np

# Stack of 3x3 matrices
A = np.random.randn(10, 3, 3)  # 10 matrices, each 3x3

# Batch matrix inverse
A_inv = np.linalg.inv(A)           # shape (10, 3, 3)

# Verify: A @ A_inv should be identity
identity = A @ A_inv                # batched matrix multiply
print(np.allclose(identity, np.eye(3)))  # True

# Batch determinant
dets = np.linalg.det(A)            # shape (10,)

# Batch eigenvalues
eigenvalues, eigenvectors = np.linalg.eig(A)  # (10, 3), (10, 3, 3)

# Batch SVD
U, S, Vh = np.linalg.svd(A)        # U: (10,3,3), S: (10,3), Vh: (10,3,3)

# Batch linear solve: Ax = b for each matrix
b = np.random.randn(10, 3)         # 10 right-hand sides
x = np.linalg.solve(A, b)          # shape (10, 3)

# Verify
residual = A @ x[..., np.newaxis] - b[..., np.newaxis]
print(np.allclose(residual, 0))     # True

# Batch matrix multiply with @ operator
B = np.random.randn(10, 3, 4)
C = A @ B                           # shape (10, 3, 4)

# Matrix norm (batch)
norms = np.linalg.norm(A, axis=(1, 2))  # Frobenius norm per matrix
```

## Advanced Indexing

NumPy supports integer array indexing, boolean indexing, and fancy indexing:

```python
import numpy as np

# Integer array indexing
a = np.array([10, 20, 30, 40, 50])
indices = np.array([0, 3, 4])
result = a[indices]                 # array([10, 40, 50])

# 2D integer indexing
matrix = np.arange(12).reshape(3, 4)
rows = np.array([0, 1, 2])
cols = np.array([1, 3, 0])
result = matrix[rows, cols]         # array([1, 7, 8]) - elements at (0,1), (1,3), (2,0)

# Boolean (mask) indexing
data = np.array([1, -2, 3, -4, 5, -6])
mask = data > 0
positives = data[mask]              # array([1, 3, 5])

# Conditional assignment
data[data < 0] = 0                  # Replace negatives with 0

# np.where for conditional selection
x = np.array([1, -2, 3, -4])
result = np.where(x > 0, x, 0)     # array([1, 0, 3, 0])

# Fancy indexing to reorder/duplicate
a = np.array([10, 20, 30, 40, 50])
result = a[[4, 2, 0, 2]]           # array([50, 30, 10, 30])

# Indexing with np.ix_ for cross-product selection
matrix = np.arange(20).reshape(4, 5)
rows = np.array([0, 2, 3])
cols = np.array([1, 3])
submatrix = matrix[np.ix_(rows, cols)]
# Selects rows 0,2,3 and columns 1,3
# shape: (3, 2)

# np.take and np.put
values = np.array([100, 200, 300, 400, 500])
result = np.take(values, [0, 2, 4])  # array([100, 300, 500])

# Argmax/argsort for indirect indexing
scores = np.array([0.3, 0.8, 0.1, 0.9, 0.5])
top_k = np.argsort(scores)[-3:][::-1]  # Indices of top 3: [3, 1, 4]
print(scores[top_k])                    # array([0.9, 0.8, 0.5])
```
