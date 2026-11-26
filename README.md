# Telemetry Constrained Recovery Allocation

Code, constructed case inputs, and reproducible experiments for **Telemetry-Constrained Recovery Allocation on Shared-Capacity Logistics Networks**. The controller chooses capacity reports before allocating flow through shared road capacities. The objective is expected feasible flow certified by the received reports.

## Experiments

The allocation study compares nine selection rules on 20 resources, including Flow-MSE and summary-statistic VoI controls. All admissible batches contain at most six reports. Integer flow and cut checks cover all 2^20 capacity states per case for the estimation objectives. The new test seeds and analysis rules are recorded in `protocol/Allocation_Design_Frozen.json`. Original cases were previously examined; the new test cohort uses the same graph families with new sampled scenarios.

The ns-3 companion experiment uses the LoRa PHY model with a query/reply scheduler, explicit airtime, gateway half duplex, interference, duty spacing, and deadlines. Continuous listening uses gapless rearmed receive operations. This is a declared protocol abstraction, not a LoRaWAN MAC conformance test or hardware measurement. Production outcomes will be added after their checks complete.

## Run the allocation comparison

Python 3.12 and a C++17 compiler are required.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python tests/test_information.py
.venv/bin/python src/run_study.py --workers 2
```

Use `--cohort original` or `--cohort test` for a single cohort. The run rebuilds full integer flow tables in `work/` and writes CSVs and compact short-batch tables to `results/`. Checkpoints are saved after each case. Full binary truth tables are regenerated rather than committed.

Flow-MSE minimizes uncertainty about full-state maximum flow. Summary-VoI minimizes uncertainty about mean monitored capacity, adapting the summary-statistic MMSE objective in Chiariotti et al., IEEE Networking Letters (2022), DOI [10.1109/LNET.2022.3172591](https://doi.org/10.1109/LNET.2022.3172591). The finite binary-belief implementation does not reproduce their Gaussian/Kalman algorithm.

## Data and licenses

The graph inputs are historical research benchmarks and generated structures. The reception summaries derive from environmental LoRaWAN metadata, not a logistics deployment. Read [data terms](licenses/DATA_TERMS.md) before reuse. Own standalone code is MIT; `ns3/` is GPL-2.0-only; upstream data retain their original conditions. Private manuscript reviews and copyrighted reading copies are excluded.
