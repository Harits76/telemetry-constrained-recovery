"""Exact finite-belief MMSE objectives, independent of allocation selectors.

Flow-MSE estimates F(X); Summary-VoI estimates mean monitored capacity.
The latter adapts the summary-statistic MMSE objective in Chiariotti et al.,
IEEE Networking Letters (2022), DOI 10.1109/LNET.2022.3172591. Their Gaussian
Kalman scheduling algorithm is not reproduced here.
"""
import itertools
import numpy as np


def coefficients(values, theta):
    """Orthonormal product-Bernoulli ANOVA, bit 0 varies fastest."""
    out = np.asarray(values, float).copy()
    for i, p in enumerate(theta):
        view = out.reshape(-1, 2, 1 << i)
        a, b = view[:, 0].copy(), view[:, 1].copy()
        view[:, 0] = (1-p)*a+p*b
        view[:, 1] = np.sqrt(p*(1-p))*(b-a)
    return out


def observation_groups(m, k):
    groups = []
    for degree in range(k+1):
        ids = np.array(list(itertools.combinations(range(m), degree)), int).reshape(-1, degree) if degree else np.empty((1, 0), int)
        local = (np.arange(1 << degree)[:, None] >> np.arange(degree)) & 1
        sub = np.sum(local[None, :, :] * (1 << ids[:, None, :]), axis=2, dtype=np.int64)
        groups.append((ids, local, sub))
    return groups


def reduction(coeffs, components, M, groups):
    """Var(E[z|X_R]) for each R in M, for a mixture of product laws.

    Integrates all possible observed values, including posterior component
    reweighting. This is not the mixture of component-wise variances.
    """
    pos = np.full(1 << len(components[0]['probability']), -1, int)
    pos[M] = np.arange(len(M))
    mean = sum(c['weight']*v[0] for c, v in zip(components, coeffs))
    result = np.zeros(len(M))
    for ids, local, sub in groups:
        degree = ids.shape[1]
        mass = np.zeros(sub.shape)
        numerator = np.zeros(sub.shape)
        for c, co in zip(components, coeffs):
            p = np.asarray(c['probability'])
            values = co[sub].copy()
            for j in range(degree):
                view = values.reshape(len(ids), -1, 2, 1 << j)
                a, b = view[:, :, 0].copy(), view[:, :, 1].copy()
                q = p[ids[:, j], None, None]
                view[:, :, 0] = a-np.sqrt(q/(1-q))*b
                view[:, :, 1] = a+np.sqrt((1-q)/q)*b
            likelihood = np.prod(np.where(local[None, :, :], p[ids[:, None, :]], 1-p[ids[:, None, :]]), axis=2)
            weight = c['weight']*likelihood
            mass += weight
            numerator += weight*values
        result[pos[sub[:, -1]]] = np.sum((numerator-mean*mass)**2/mass, axis=1)
    result[0] = 0.
    return result


def criterion_tables(case, values, M, groups, components):
    m = len(case['resource_arcs'])
    arcs = np.array(case['resource_arcs'])
    lo = np.array(case['lower'])[arcs]
    delta = np.array(case['upper'])[arcs]-lo
    flow_coeffs, mean_coeffs = [], []
    for c in components:
        p = np.asarray(c['probability'])
        flow_coeffs.append(coefficients(values, p))
        co = np.zeros(1 << m)
        co[0] = (lo+p*delta).mean()
        co[1 << np.arange(m)] = delta*np.sqrt(p*(1-p))/m
        mean_coeffs.append(co)
    return (reduction(flow_coeffs, components, M, groups),
            reduction(mean_coeffs, components, M, groups))
