# Efficiency on this PC: neuromorphic hardware, RAM drives, and what was measured (2026-10-17)

Asked by Lawrence: "research neuromorphic hardware and ram drives to increase our productivity affordably". Web reads
went through the project's own door (`covenant_web.py`, every read in `ops/web_reads.jsonl`), not a paid crawler.

## The machine, measured

- **Hardware:** HP 255 G9; AMD Ryzen 5 5625U, 6 cores and 12 threads; integrated Radeon graphics.
- **RAM:** 15.3 GB as 2 × 8 GB DDR4-3200 SO-DIMM, in two slots; the board reports 64 GB maximum.
- **Disk:** NVMe SSD (Samsung MZVL4512HBLU).
- **Free RAM:** about 4.1–4.3 GB with the nodes running (the model keeper's log), and 2.8 GB with a second copy of
  the 3B model loaded for benchmarking.

## What helped, measured: llama-server threads (A360)

llama-bench, Qwen2.5-3B Q4_K_M, generating 128 tokens at a context depth of 3,000, 3 repetitions each:

| threads | flash attention | tokens/s |
|---|---|---|
| 10 (the old rule) | off | 10.84 |
| 6 | off | 12.24 |
| **5 (now)** | off | **13.28 (+22%)** |
| 5 | on | 10.68 |

- Prompt reading is a little slower at 5 threads. On real asks it is a small share: the server reuses the cached
  prefix, and asks read 50–540 new tokens (`ops/model_asks.jsonl`).
- Real asks before the change generated at 12–13 tokens/s.
- A short-context run first suggested flash attention helped. The real-depth run reversed that, so it stays off.

## Neuromorphic hardware: not a win for this project today

- **The chips:**
  - **BrainChip Akida AKD1000:** 1.5 TOPS INT8 at about 1 W. The PCIe board lists at **$289** on BrainChip's shop
    (read 2026-10-17). The M.2 card is for an M.2 2260 B+M slot; its price was not in the page text.
  - **SynSense Xylo and Speck:** development kits, about $199 per a third-party listing, not checked against the
    seller.
  - **Intel Loihi:** access is by research partnership. Intel's Lava software is archived.
- **Why none helps here:**
  - These chips run small spiking or converted networks at microwatts to about a watt. They do not run a language
    model like Tetsu's.
  - The gate's student judges already answer in microseconds on the CPU, so there is nothing for a chip to speed up.
  - Spiking-model energy savings (SpikeGPT, SpikeLM) are measured on neuromorphic hardware. On a CPU, a spiking
    network is no faster.
- **Where it could matter:** a battery-powered judge on a phone-class node. The software path for that is NIR
  (github.com/neuromorphs/nir), Pedersen's format, which this project already credits.

## RAM drives: would make things worse here

- Free RAM is the constraint. A RAM drive takes memory from the model and the nodes.
- The model file is read once from a fast NVMe drive, and Windows then caches it.
- Free options exist: ImDisk and its forks, and Arsenal Image Mounter's free drivers. Installing one is a kernel
  driver, which is the operator's decision. On this evidence it would not help.

## The affordable upgrade that would help: RAM

- Replacing the two 8 GB sticks with 2 × 16 GB DDR4-3200 SO-DIMM gives 32 GB.
- That leaves room for the 7B model the keeper already lists, and for the nodes, without swapping.
- **Price:** RamRadar, read 2026-10-17, says DDR4 is roughly 2–4× its 2025 price. Desktop DDR4-3200 16 GB sticks
  were about $75–80 each. A laptop SO-DIMM kit was not priced. Spending is Lawrence's decision.

## A defect found on the way (A360): Tetsu's web search

- Bing, through the door, answered "RAM disk software Windows" with Ram Trucks and "neuromorphic hardware
  development kit" with Halloween stores, and the search handed those to Tetsu as results.
- Now a Bing result must share at least two query words (one, for a one-word query). DuckDuckGo's lite page is
  asked next, then Wikipedia.
- Wikipedia's parser sometimes returns empty titles. Noted, not fixed.
