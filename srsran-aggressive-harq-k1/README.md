# srsran-aggressive-harq-k1-lab

Aggressive HARQ-ACK timing (k1) experiment for srsRAN (ZMQ PHY) with RTT comparison.

This repo contains:
- a minimal scheduler patch (k1 prioritization)
- baseline + aggressive run artifacts (ping + logs)
- step-by-step instructions to reproduce from scratch

---

## 0. What you will achieve

You will:
1) Clone **srsRAN_Project** twice (baseline + aggressive)
2) Build both
3) Run the same Core + UE setup
4) Run `ping -c 200` from UE namespace
5) Compare RTT statistics
6) Verify scheduler behavior via logs (“BASELINE-HARQ” vs “AGGRESSIVE-HARQ”)

---

## 1. Prerequisites (Ubuntu)

You need:
- git
- cmake + ninja
- g++ / build-essential
- docker + docker compose
- iproute2


## 2. Configuration files

The directory `configs/` contains reference ZMQ configurations used in this lab:

- `gnb_zmq.yaml` – gNB ZMQ PHY configuration
- `ue_zmq.conf` – UE ZMQ configuration

You may adapt IP addresses or ports to your local setup, but
scheduler behavior and HARQ results are validated using these files.



Example install (Ubuntu):
```bash
sudo apt update
sudo apt install -y git cmake ninja-build build-essential iproute2 ccache \
  pkg-config libfftw3-dev libmbedtls-dev libyaml-cpp-dev libsctp-dev \
  libzmq3-dev libczmq-dev cppzmq-dev
```

Docker (if not already installed):

```bash
sudo apt install -y docker.io docker-compose-plugin
sudo usermod -aG docker $USER
newgrp docker
```

⚠️ Important version note

This lab is validated against:
- srsRAN_Project commit: 9d5dd742a
- srsRAN_4G commit: ec29b0c1f

Using different commits may:
- fail to build
- change scheduler behavior
- invalidate RTT comparisons


## 3. Directory layout (recommended)

Create a clean workspace:

```
mkdir -p ~/srs_harq_lab
cd ~/srs_harq_lab
```

You will have:

```
~/srs_harq_lab/
  srsRAN_Project_baseline/      (commit 9d5dd742a)
  srsRAN_Project_aggressive/    (same commit + patch)
  srsRAN_4G_UE/                 (commit ec29b0c1f)
  harq_results/
```

Create results directory:
```
mkdir -p ~/srs_harq_lab/harq_results
```

## 4. Clone and checkout srsRAN gNB (baseline)

```
cd ~/srs_harq_lab
git clone https://github.com/srsran/srsRAN_Project srsRAN_Project_baseline
cd srsRAN_Project_baseline
git checkout 9d5dd742a
```

Build baseline:

```
rm -rf build
cmake -S . -B build -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DENABLE_PLUGINS=ON \
  -DENABLE_ZEROMQ=ON
cmake --build build -j 2
```

## 5. Clone and checkout srsRAN gNB (aggressive)

```
cd ~/srs_harq_lab
git clone https://github.com/srsran/srsRAN_Project srsRAN_Project_aggressive
cd srsRAN_Project_aggressive
git checkout 9d5dd742a
```

Apply the patch from this repo:

Assuming you cloned this lab repo as ~/srsran-aggressive-harq-k1-lab:

```
git apply ~/srsran-aggressive-harq-k1-lab/patches/aggressive-harq-k1.patch
```

### Alternative to patch application (manual copy)

If `git apply patches/aggressive-harq-k1.patch` fails on your system,
you can manually apply the change by copying the provided modified file:

```bash
cp \
modified_files/lib/scheduler/uci_scheduling/uci_allocator_impl.cpp \
<srsRAN_Project_root>/lib/scheduler/uci_scheduling/
```


Build aggressive again for the scheduling changes to get effective:

```
rm -rf build
cmake -S . -B build -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DENABLE_PLUGINS=ON \
  -DENABLE_ZEROMQ=ON
cmake --build build -j 2
```

## 6. Clone and checkout UE project (srsRAN_4G)

```
cd ~/srs_harq_lab
git clone https://github.com/srsran/srsRAN_4G srsRAN_4G_UE
cd srsRAN_4G_UE
git checkout ec29b0c1f
```

Build UE (example steps — depending on your environment/config):

```
mkdir -p build
cd build
sudo apt update
sudo apt install -y gcc-11 g++-11
cmake .. -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_C_COMPILER=gcc-11 -DCMAKE_CXX_COMPILER=g++-11
cmake --build . -j 2
```

Note: Your UE runtime YAML and ZMQ parameters must match your lab setup.

## 7. Start 5G Core (Docker)

Go to the core directory you use (example: `~/srs_harq_lab/srsRAN_Project/docker`):

```
cd <your_core_docker_folder>
sudo docker compose up -d 5gc
sudo docker ps
```

## 8. Run procedure: baseline measurement

#### 8.1 Start baseline gNB

```
sudo stdbuf -oL -eL \
  ~/srs_harq_lab/srsRAN_Project_baseline/build/apps/gnb/gnb \
  -c <your_gnb_yaml> \
  log --filename /tmp/gnb_baseline.log \
      --mac_level debug \
      --fapi_level debug \
      --phy_level info \
      --radio_level info \
      --all_level warning
```

#### 8.2 Start UE + create namespace

Example namespace approach:

```
sudo ip netns add ue1
sudo ip netns list
```

Start UE inside namespace (example):

```
sudo ip netns exec ue1 <your_ue_command>
```

#### 8.3 Add routes (example)

```
sudo ip route add 10.45.0.0/16 via 10.53.1.2
sudo ip netns exec ue1 ip route add default via 10.45.1.1 dev tun_srsue
```

#### 8.4 Run 200 pings (baseline)

```
sudo ip netns exec ue1 ping 10.45.1.1 -c 200 | tee ~/srs_harq_lab/harq_results/ping_baseline_200.txt
```

Save logs:

```
sudo cp /tmp/gnb_baseline.log ~/srs_harq_lab/harq_results/gnb_baseline.log
```

## 9. Run procedure: aggressive measurement

#### 9.1 Start aggressive gNB

```
sudo stdbuf -oL -eL \
  ~/srs_harq_lab/srsRAN_Project_aggressive/build/apps/gnb/gnb \
  -c <your_gnb_yaml> \
  log --filename /tmp/gnb_aggressive.log \
      --mac_level debug \
      --fapi_level debug \
      --phy_level info \
      --radio_level info \
      --all_level warning
```

#### 9.2 Run 200 pings (aggressive)

```
sudo ip netns exec ue1 ping 10.45.1.1 -c 200 | tee ~/srs_harq_lab/harq_results/ping_aggressive_200.txt
```

Save logs:

```
sudo cp /tmp/gnb_aggressive.log ~/srs_harq_lab/harq_results/gnb_aggressive.log
```

## 10. Compare RTT results (one-liners)

```
echo "BASELINE:"
grep "rtt min/avg/max/mdev" ~/srs_harq_lab/harq_results/ping_baseline_200.txt
echo
echo "AGGRESSIVE:"
grep "rtt min/avg/max/mdev" ~/srs_harq_lab/harq_results/ping_aggressive_200.txt
```

## 11. Verify k1 logging evidence

Baseline:

```
sudo grep -F "BASELINE-HARQ" /tmp/gnb_baseline.log | head
```

Aggressive:

```
sudo grep -F "AGGRESSIVE-HARQ" /tmp/gnb_aggressive.log | head
```

It should be mentioned here that the above "BASELINE-HARQ" logging will return values only if a logger has been inserted in the baseline uci_allocator_impl.cpp like in the aggressive scenario.

```
lib/scheduler/uci_scheduling/uci_allocator_impl.cpp
```
Add the following log immediately before returning the UCI allocation and build again the gNB like in paragraph 4.

```
logger.warning(
  "BASELINE-HARQ: rnti={} k0={} k1_candidate={} uci_slot={}",
  crnti, k0, k1_candidate, uci_slot
);
```

Count k1 candidates:

```
sudo grep -F "BASELINE-HARQ" /tmp/gnb_baseline.log \
| sed -n 's/.*k1_candidate=\([0-9]\+\).*/\1/p' | sort -n | uniq -c | sort -nr | head

sudo grep -F "AGGRESSIVE-HARQ" /tmp/gnb_aggressive.log \
| sed -n 's/.*k1_candidate=\([0-9]\+\).*/\1/p' | sort -n | uniq -c | sort -nr | head
```

## 12. Aggressive HARQ Modification

#### 12.1 Design Rationale

The objective is to reduce HARQ feedback latency by:

* Preferring smaller k1 values

* Preserving all existing validity checks

* Avoiding behavioral changes outside k1 selection order

This corresponds to an aggressive HARQ strategy, prioritizing earlier ACK/NACK transmission opportunities.

#### 12.2 Code Modification

File modified:

```
lib/scheduler/uci_scheduling/uci_allocator_impl.cpp
```

Key change:

* Copy k1_list (span) into a mutable container

* Sort ascending

* Iterate over sorted k1 candidates

Minimal patch:

```
+#include <algorithm>
+#include <vector>

- for (const uint8_t k1_candidate : k1_list) {
+ std::vector<uint8_t> k1_candidates_sorted(k1_list.begin(), k1_list.end());
+ std::sort(k1_candidates_sorted.begin(), k1_candidates_sorted.end());
+ k1_candidates_sorted.erase(
+     std::unique(k1_candidates_sorted.begin(), k1_candidates_sorted.end()),
+     k1_candidates_sorted.end());
+
+ for (const uint8_t k1_candidate : k1_candidates_sorted) {


A diagnostic log was added to verify runtime behavior:

logger.warning(
  "AGGRESSIVE-HARQ: rnti={} k0={} k1_candidate={} uci_slot={}",
  crnti, k0, k1_candidate, uci_slot);
```

The full patch is available in:

```
patches/aggressive-harq-k1.patch
```

## 13) Results

#### 13.1 RTT Comparison

| Metric         | Baseline        | Aggressive HARQ |
|----------------|-----------------|-----------------|
| Min RTT        | 30.184 ms       | 26.111 ms       |
| Avg RTT        | 60.292 ms       | 46.747 ms       |
| Max RTT        | 224.340 ms      | 131.366 ms      |
| Jitter (mdev)  | 21.769 ms       | 15.849 ms       |



#### 13.2 HARQ Logging Evidence

Aggressive HARQ runtime logs:

```
grep "AGGRESSIVE-HARQ" /tmp/gnb_mac_fapi_debug.log
```

Example:

AGGRESSIVE-HARQ: rnti=0x4601 k0=0 k1_candidate=4 uci_slot=39.7


## 14) Notes on Interpretation

* k1 value may remain the same (e.g., k1=4)

* Improvement comes from earlier evaluation and selection

* Reduced deferrals lead to:

    * lower average RTT

    * reduced RTT variance

    * shorter tail latency

* Baseline results were validated using both:

    * a representative unmodified run

    * a clean clone baseline


## 15) Graphs

#### 15.1 RTT Histogram (graphs/rtt_histogram.png)

Compares the frequency distribution of RTT samples. A left-shift and narrower spread indicate lower delay and reduced variability under the aggressive HARQ configuration.

#### 15.2 RTT Boxplot (graphs/rtt_boxplot.png)

Summarizes RTT dispersion via median, interquartile range, and outliers. The aggressive scenario shows a lower median and fewer/lower outliers, highlighting improved stability.

#### 15.3 RTT per Packet / Time Series (graphs/rtt_timeseries.png)

Plots RTT for each ICMP sequence. It reveals transient spikes and bursty behavior; the aggressive scenario exhibits fewer and smaller spikes, reducing tail events.

#### 15.4 RTT CDF (graphs/rtt_cdf.png)

The cumulative distribution function shows the fraction of packets below a given RTT threshold. A curve closer to the left and rising faster indicates consistently lower RTT across the whole distribution.

#### 15.5 Tail Percentiles (p95/p99) (graphs/rtt_percentiles_p95_p99.png)

Compares high-percentile RTT (tail latency). Lower p95/p99 values in the aggressive scenario confirm significant reduction of worst-case delays.

#### 15.6 Jitter Over Time (Rolling STD) (graphs/rtt_jitter_rolling_std.png)

Estimates jitter as rolling standard deviation of RTT (windowed). Lower rolling STD indicates more stable latency and reduced short-term variability.

The graphs can be produced with the python framework matplotlib through a script (python_scripts/make_graphs.py):

```
# From repo root
python3 -m pip install --user numpy matplotlib

python3 python_scripts/make_graphs.py \
  --baseline results/ping_baseline_200.txt \
  --aggressive results/ping_aggressive_200.txt \
  --outdir graphs
 ```


### Notes on RF Conditions and SNR Limitations

It should be noted that this experimental setup is based on a ZMQ PHY emulation, which provides an almost ideal RF environment.

Despite extensive testing with reduced transmit and receive gain values on both the gNB and UE sides, no significant degradation of the Signal-to-Noise Ratio (SNR) was observed. As a result, the radio link remained highly stable, with very limited or no HARQ retransmissions triggered by channel errors.

This behavior is inherent to the ZMQ-based PHY, which does not model realistic channel impairments such as fading, interference, or thermal noise. Consequently, the experiment does not aim to study HARQ behavior under varying SNR conditions or error-prone radio links.

Instead, the focus of this work is on the **scheduler-level HARQ-ACK timing behavior**, isolating the impact of aggressive k1 prioritization on end-to-end latency and jitter. The observed performance improvements are therefore attributed to scheduling decisions rather than changes in link quality.

Future work could extend this study by incorporating more realistic channel models or over-the-air experiments, where SNR variations and retransmissions would play a more prominent role in HARQ dynamics.
