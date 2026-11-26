"""Direct posterior integration checks the transformed implementation."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
from information import coefficients, reduction, observation_groups

def literal(f, components, R, m):
    X = (np.arange(1 << m)[:, None] >> np.arange(m)) & 1
    prob = sum(c['weight']*np.prod(np.where(X, c['probability'], 1-np.asarray(c['probability'])), axis=1) for c in components)
    mu = prob@f
    return sum((prob[((np.arange(1 << m)^r)&R)==0]@(f[((np.arange(1 << m)^r)&R)==0]-mu))**2/prob[((np.arange(1 << m)^r)&R)==0].sum() for r in range(1 << m) if r&~R==0)

rng = np.random.default_rng(42)
checks = 0
for m in [1, 3, 6]:
    M = np.arange(1 << m)
    for components in [
        [dict(weight=1., probability=rng.uniform(.1,.9,m).tolist())],
        [dict(weight=.3, probability=rng.uniform(.1,.9,m).tolist()), dict(weight=.7, probability=rng.uniform(.1,.9,m).tolist())]]:
        f = rng.integers(0, 50, 1 << m)
        co = [coefficients(f,c['probability']) for c in components]
        got = reduction(co,components,M,observation_groups(m,m))
        expected = np.array([literal(f,components,int(R),m) for R in M])
        np.testing.assert_allclose(got,expected,atol=2e-10,rtol=2e-12)
        for R in M:
            for i in range(m):
                assert got[R|(1<<i)] >= got[R]-1e-10
        checks += len(M)
print(f'PASS: {checks} posterior-variance values against literal full-state integration')
