# Elastic residual edge

The rendered path may stretch, curve, branch, merge, and recoil. Its endpoint
identities and its carried receipt remain fixed. This separates visible or
learned motion from value conservation.

For edge `e=(i,j)`, let `q_e(s,t)` be a bounded curve with fixed endpoints

`q_e(0,t)=p_i` and `q_e(1,t)=p_j`.

Its deformation energy is

`E_e = k_e/2 (L_e-L0_e)^2 + kappa_e/2 integral ||d2q/ds2||^2 ds`.

A damped update can render or summarize the path:

`m q_tt + c_e q_t = T_e q_ss + f_e`,

subject to `L_e/L0_e <= phi`. The workbook uses `c_e=0.70 sqrt(k_e)`,
`kappa_e=1/phi`, and a maximum stretch ratio of `phi` as explicit defaults.
Those constants are presentation/routing hypotheses, not established neural
advantages.

The payload is a residual or receipt. At a split, payload coefficients must sum
to one. At a merge, each incoming receipt remains separately addressable. A
deformation may change curvature, tension, and travel time; it may not rename a
node, change a discrete token value, or erase provenance. The lattice snap is
therefore the node rule, while the elastic edge is the between-node rule.
