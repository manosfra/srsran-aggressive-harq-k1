import re
import argparse
import numpy as np
import matplotlib.pyplot as plt

def parse_ping_file(path: str):
    """
    Parse RTT values (ms) from a Linux ping output file.
    Extracts the number after 'time=' in lines like:
    '64 bytes from ... icmp_seq=1 ttl=... time=46.7 ms'
    """
    rtts = []
    pattern = re.compile(r'time=([0-9]+(?:\.[0-9]+)?)\s*ms')
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            m = pattern.search(line)
            if m:
                rtts.append(float(m.group(1)))
    return np.array(rtts, dtype=float)

def rolling_std(x: np.ndarray, window: int):
    if len(x) < window:
        return np.array([])
    out = []
    for i in range(len(x)):
        if i < window - 1:
            out.append(np.nan)
        else:
            out.append(np.std(x[i-window+1:i+1], ddof=0))
    return np.array(out, dtype=float)

def ensure_dir(path: str):
    import os
    os.makedirs(path, exist_ok=True)

def savefig(path: str):
    plt.tight_layout()
    plt.savefig(path, dpi=200)
    plt.close()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", required=True, help="Path to baseline ping output txt")
    ap.add_argument("--aggressive", required=True, help="Path to aggressive ping output txt")
    ap.add_argument("--outdir", default="graphs", help="Output folder for PNGs")
    ap.add_argument("--bins", type=int, default=25, help="Histogram bins")
    ap.add_argument("--jitter_window", type=int, default=10, help="Rolling STD window")
    args = ap.parse_args()

    ensure_dir(args.outdir)

    baseline = parse_ping_file(args.baseline)
    aggressive = parse_ping_file(args.aggressive)

    if baseline.size == 0 or aggressive.size == 0:
        raise SystemExit("ERROR: No RTT samples parsed. Check ping files format.")

    # 1) Histogram
    plt.figure()
    plt.hist(baseline, bins=args.bins, alpha=0.6, label="Baseline")
    plt.hist(aggressive, bins=args.bins, alpha=0.6, label="Aggressive")
    plt.title("RTT Histogram")
    plt.xlabel("RTT (ms)")
    plt.ylabel("Count")
    plt.legend()
    savefig(f"{args.outdir}/rtt_histogram.png")

    # 2) Boxplot
    plt.figure()
    plt.boxplot([baseline, aggressive], labels=["Baseline", "Aggressive"])
    plt.title("RTT Distribution Comparison")
    plt.ylabel("RTT (ms)")
    savefig(f"{args.outdir}/rtt_boxplot.png")

    # 3) RTT per packet (timeseries)
    plt.figure()
    plt.plot(np.arange(1, len(baseline)+1), baseline, label="Baseline")
    plt.plot(np.arange(1, len(aggressive)+1), aggressive, label="Aggressive HARQ")
    plt.title("RTT per packet")
    plt.xlabel("ICMP Sequence")
    plt.ylabel("RTT (ms)")
    plt.legend()
    savefig(f"{args.outdir}/rtt_timeseries.png")

    # 4) CDF
    def cdf(x):
        xs = np.sort(x)
        ys = np.arange(1, len(xs)+1) / len(xs)
        return xs, ys

    xb, yb = cdf(baseline)
    xa, ya = cdf(aggressive)

    plt.figure()
    plt.plot(xb, yb, label="Baseline")
    plt.plot(xa, ya, label="Aggressive")
    plt.title("RTT CDF")
    plt.xlabel("RTT (ms)")
    plt.ylabel("CDF")
    plt.legend()
    savefig(f"{args.outdir}/rtt_cdf.png")

    # 5) Percentiles (p95/p99)
    pcts = [95, 99]
    bvals = np.percentile(baseline, pcts)
    avals = np.percentile(aggressive, pcts)

    x = np.arange(len(pcts))
    width = 0.35

    plt.figure()
    plt.bar(x - width/2, bvals, width, label="Baseline")
    plt.bar(x + width/2, avals, width, label="Aggressive")
    plt.xticks(x, [f"p{p}" for p in pcts])
    plt.title("Tail RTT Comparison (Percentiles)")
    plt.ylabel("RTT (ms)")
    plt.legend()
    savefig(f"{args.outdir}/rtt_percentiles_p95_p99.png")

    # 6) Jitter over time (rolling std)
    jb = rolling_std(baseline, args.jitter_window)
    ja = rolling_std(aggressive, args.jitter_window)

    plt.figure()
    plt.plot(jb, label=f"Baseline (rolling std, w={args.jitter_window})")
    plt.plot(ja, label=f"Aggressive (rolling std, w={args.jitter_window})")
    plt.title("Jitter Over Time (Rolling STD of RTT)")
    plt.xlabel("ICMP sequence index")
    plt.ylabel("Rolling std of RTT (ms)")
    plt.legend()
    savefig(f"{args.outdir}/rtt_jitter_rolling_std.png")

    # Console summary
    def summary(name, x):
        print(f"{name}: n={len(x)}  min={np.min(x):.3f}  avg={np.mean(x):.3f}  max={np.max(x):.3f}  std={np.std(x):.3f}")
        print(f"  p95={np.percentile(x,95):.3f}  p99={np.percentile(x,99):.3f}")

    summary("Baseline", baseline)
    summary("Aggressive", aggressive)

if __name__ == "__main__":
    main()
