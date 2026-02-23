# Non-Binary Kernel Spec (Triadic / Quaternary)

Use a K-ary simplex kernel to avoid binary-only governance.

## State
- `E_t`: exposure accumulator
- `J_t`: intent accumulator
- `q_t = E_t / (|J_t| + eps)`

## Dynamics
- `E_t = (1-lambdaE)*E_(t-1) + v_t*P_t*D_t*dt`
- `J_t = (1-lambdaJ)*J_(t-1) + I_t*dt`

## K=4 Logits
- `z_care = 1.8J - 1.2E`
- `z_neutral = 0.8 - |J| - 0.2E`
- `z_harm = -1.5J + 1.8E`
- `z_repair = 1.2J + 1.2E - 0.5`
- `p = softmax(z / tau)`

## Tiering
- `R = p . r`
- `T1 if R < theta1`
- `T2 if theta1 <= R < theta2`
- `T3 otherwise`

## Demo
```powershell
python scripts/system/nonbinary_kernel_demo.py --k 4 --steps 40
```
