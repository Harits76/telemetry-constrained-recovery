# Telemetry Constrained Recovery Allocation

Code, data, and reproducible experiments for **Telemetry-Constrained Recovery Allocation on Shared-Capacity Logistics Networks**. The controller selects capacity reports before allocating flow through shared routes. It maximizes expected flow certified by timely reports.

## Main experiments

- Nine selection rules at 20 resources: cut ranking, random, static gain, greedy gain, exchange, singleton knapsack, cut knapsack, Flow-MSE and Summary-VoI.
- Earlier and newly sampled 24-scenario cohorts, with three priors, two reception laws and budgets 0.42/0.70 s; 0.28 s is a predefined sensitivity.
- All 50,331,648 full capacity states checked with integer primal/cut certificates. The allocation reference uses 60,460 short batches per graph.
- 124,416 ns-3 packet dispatches across deadlines, duty fractions, background loads and simulated radii, plus a service-adapted exact reference.

The allocation design was recorded before generating the new test scenarios. The earlier scenarios were previously examined. The new cohort reuses the same graph families and communication corpus; it is not a set of measured deployments. Read the frozen designs in `protocol/`. The folder `cases/original` denotes the earlier 20-resource cohort and `cases/test` denotes the new 20-resource cohort; both use this repository’s model.

## Quick numerical replay

Python 3.12 and a C++17 compiler are required. The recorded environment uses NumPy 2.3.5, SciPy 1.17.0 and GCC 14.2.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python tests/test_information.py
.venv/bin/python src/restore_tables.py
.venv/bin/python src/run_study.py --workers 2
.venv/bin/python src/structure.py
.venv/bin/python src/supporting.py
.venv/bin/python src/transport_replay.py
.venv/bin/python src/communication_audit.py
.venv/bin/python src/validate.py
.venv/bin/python src/summarize.py
```

Restoration verifies SHA-256 hashes of the published integer tables. Replaying recomputes all selection objectives, optima and policy scores; it does not rebuild those restored flows. For a full integer-flow rebuild, omit restoration and start with no `work/*.bin` files. Use `--cohort original` or `--cohort test` for a single cohort. `src/supporting.py --rebuild-reduced` also rebuilds every terminal flow in the reduced eight-resource data.

The full-scale information checks independently group all capacity states for 1,152 conditional variances. Separate decimal integration checks 864 optimum witnesses. Per-case times are audit records with concurrent computation, not isolated latency benchmarks.

[Open the CPU notebook in Google Colab](https://colab.research.google.com/github/Harits76/telemetry-constrained-recovery/blob/v1.1.0/notebooks/Recovery_Allocation.ipynb). The notebook is prepared for Colab; the reported study and reproduction checks ran in the documented Linux workspace. No live Colab execution is claimed.

## Packet simulation

```bash
.venv/bin/python -m pip install -r ns3/requirements-build.txt
PATH="$PWD/.venv/bin:$PATH" .venv/bin/python ns3/setup.py --jobs 2
.venv/bin/python tests/test_packets.py work/ns-3/build/scratch/ns3.48-telemetry-packets
work/ns-3/build/utils/ns3.48-test-runner --suite=lorawan --verbose
.venv/bin/python src/packet_experiment.py prepare
work/ns-3/build/scratch/ns3.48-telemetry-packets --input=work/packets/trials.txt --output=work/packets/Packet_Outputs.csv
.venv/bin/python src/packet_experiment.py analyze
.venv/bin/python src/service_reference.py
```

The setup pins ns-3.48 and Padova LoRa module revisions. This stage requires a compatible C++23 toolchain; GCC 14.2 was tested. Native LoRa PHY propagation, interference, sensitivity, receive paths and gateway half duplex are used with an application query/reply scheduler and explicit duty accounting. Gapless rearmed single-receive operations model continuous listening. Join, ADR, security processing and full Class-C MAC behavior are outside this abstraction. There are no hardware measurements.

Nominal batches are held fixed for the packet transport test. `Service_Optima.csv` separately adapts the batch to timing/duty under perfect reception; it is not an optimum over the physical MAC. Communication loss compares actual flow with perfect timely delivery of the same batch. Bootstrap intervals are conditional Monte Carlo intervals for the fixed scenarios. All profiles and losses are retained.

## PureChain audit

The allocation runner and packet analysis use the local PureChain audit by default. This is an adaptation of the original RARCA notebook’s hash-linked ledger. The collector logs completed decisions and results. The original canonical JSON structure and SHA-256 payload, block and previous-hash fields are retained. Ledger timestamps give replay order. Coverage counts verified experiment records against the declared experiment IDs and excludes the genesis record.

```bash
.venv/bin/python tests/test_purechain.py
.venv/bin/python src/verify_audit.py --kind allocation --anchor protocol/PureChain_Checkpoints.json
# After the packet simulation commands above regenerate the trial and packet files:
.venv/bin/python src/verify_audit.py --kind packet --anchor protocol/PureChain_Checkpoints.json
```

Use a checkpoint obtained independently of the copy being checked. The adjacent checkpoints are convenient for local replay. The verifier also checks the input and code commitments and compares experiment payloads with the CSV records. For a fresh run on another toolchain, verify against that run’s checkpoint and compare the scientific output separately if floating-point or compression differences prevent byte equality. The ledger supplies record integrity relative to the checkpoint. Sensor authenticity and distributed consensus are outside the audit model.

The released runs verified 7,776 policy records and 124,416 packet dispatches, with one separate genesis block in each chain. `--audit off` is available on both runners for the comparison. `results/purechain/` contains the chains, verification results, and paired on/off checks. Measured host recording times cover serialization, hashing, compression and buffered writes after evaluation. They do not enter the simulated radio deadline.

## Figures and manuscript

```bash
.venv/bin/python -m pip install -r requirements-figures.txt
.venv/bin/python src/plot_figures.py
.venv/bin/python src/plot_packets.py
```

Figure sources use 18-point bold labels and vector PDF output. The scripts write regenerated figures to `paper/figures/`. The manuscript and minimal HiTeX package are delivered separately; this public repository releases the experiment code and data. The four historical supporting analyses have explicit inputs and standalone replay scripts; private reviews and reading-copy PDFs are excluded.

Flow-MSE targets full-state maximum flow. Summary-VoI targets mean monitored capacity, adapting the statistic-specific MMSE objective in Chiariotti et al., IEEE Networking Letters (2022), DOI [10.1109/LNET.2022.3172591](https://doi.org/10.1109/LNET.2022.3172591). This finite binary-belief control does not reproduce their Gaussian/Kalman algorithm.

## Data and licenses

Historical research graphs and generated structures supply topology. Environmental LoRaWAN metadata supply derived communication summaries, not measured logistics capacities. Read [data terms](licenses/DATA_TERMS.md) and upstream README files. Own standalone code is MIT; `ns3/` is GPL-2.0-only; upstream data retain their original conditions. The code license excludes manuscript text and figures.
