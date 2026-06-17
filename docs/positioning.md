# Positioning

`dp-release-card` is not trying to be a general-purpose differential privacy
framework.

The project is a narrow release workflow:

```text
public policy + CSV column -> DP histogram -> signed receipt -> release card
```

That narrowness is the point. The repository is meant to make one privacy
release flow easy to inspect, test, verify, and discuss.

## Why It Exists

Many DP libraries focus on mechanisms, accounting, or analytics APIs. Those are
important, but they do not always answer the operational question:

> What exactly did we release, under which public policy, and can someone verify
> the artifact later?

`dp-release-card` answers that narrower question for v1 CSV histograms.

## Who It Is For

- Developers who want a minimal DP release demo they can run locally.
- Data teams that need a concrete example of public-policy release artifacts.
- Privacy engineers who want explicit public bounds, bins, epsilon, sensitivity,
  and proof scope in one bundle.
- Auditors and reviewers who care about tamper-evident output packages.

## Differentiators

| Project type | What it optimizes for | Where `dp-release-card` is different |
|---|---|---|
| DP frameworks | Many mechanisms and analytics APIs | One small release flow with signed artifacts |
| DP tutorials | Teaching concepts | A CLI that emits verifiable files |
| Data clean rooms | Hosted workflows and governance | Local, dependency-free artifact generation |
| Synthetic data tools | New records and utility metrics | No synthetic data; only a noisy histogram release |

## Intentional Boundaries

The public repository does not include production TaupT engine internals:

- AutoBound
- AC-PQ
- fairness calibration
- internal planners or routers
- benchmark regime maps
- service workflow code
- private metadata derivation

The result is a clean open-source slice that demonstrates discipline without
publishing the full production engine.
