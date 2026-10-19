# GitHub / Hugging Face, searched for potential improvements (2026-10-19)

**His ask:** *"Search github and hugging face for potential improvements."* Searched for work bearing on the three
things in flight: the spiking redundant-witness monitoring layer (A375), the self-healing highway (A377), and the
wake-word SNN lab. These are SEARCH HITS, pointers only -- none has been opened and read yet (rule 7: a grep/search
hit is not a citation), and nothing is adopted. Listed so the leads are not lost.

## The top find: NAB answers Amendment 2's missing piece

The five-model review (A375 Amendment 2) said our keep-bar tests only sensitivity, never specificity, with "no
held-out set of negatives." The **Numenta Anomaly Benchmark (NAB)** is exactly that, as a published standard:
- labelled anomaly WINDOWS; a scoring system where every FALSE POSITIVE lowers the score; only the earliest true
  positive in a window scores; "low-FP"/"low-FN" application profiles; 58 labelled real-world streams.
- Source: arXiv 1510.03336 (the paper), github numenta/NAB (to verify). This is the evaluation harness Amendment 2
  needs -- adopt its scoring philosophy rather than invent our own. HIGHEST VALUE.

## Spiking witness / monitoring layer
- **OeSNN-UAD** (github AI-for-Space/outlier-spiking-neural-network; Maciag et al., Neural Networks 2021, vol. 139):
  an Online evolving Spiking Neural Network for unsupervised STREAM anomaly detection -- our exact use case, with a
  real evaluation method. A principled reference/baseline for the twins.
- **Fast_BOCPD / ocpdet** (Bayesian online change-point detection) and **ALACPD** (github zahraatashgahi/ALACPD, an
  LSTM-autoencoder online CPD): the plain baselines Amendment 2 requires a spiking twin to BEAT. Concrete controls.
- **Balanced SNN for online vibration anomaly detection** (arXiv 2106.00687); **low-power neuromorphic acoustic
  anomaly detection** (arXiv 2608.18341): efficiency-focused SNN detectors over streams.

## Wake-word SNN lab (efficiency -- the one place the review said spiking genuinely cuts compute)
- **ED-sKWS** (arXiv 2406.12726, Song et al.): early-decision SNN keyword spotting -- stops before the utterance
  ends; a Cumulative Temporal loss; the SC-100 dataset with start/end timestamps; reports ~61% fewer timesteps and
  ~52% lower energy than late-decision SNN KWS. A direct extension of our Amendment 5/9/10 efficiency line. Code
  availability unconfirmed (SOTAVerified lists it as code-available; verify).
- **Adaptive Speech-to-Spike Encoding for SNNs** (arXiv 2606.19039).
- Hugging Face: no snnTorch KWS model hosted; the KWS models there are Wav2Vec2 / DistilHuBERT
  (anton-l/distilhubert-ft-keyword-spotting, ~97% on SUPERB) -- non-spiking, useful only as accuracy baselines.

## Self-healing highway -- mostly CORROBORATION (our design matches the field)
- RenderSREAgent (github kishh20/RenderSREAgent): restart cap + alert only on state change -- our A367.
- Self-Healing-Data-Pipeline (github bgukhan204-tech): quarantine + exponential backoff + recovery cooldown -- our
  A377 (quarantine, 2/4/8/16h backoff, the noise cooldown).
- Autonomous-DevOps-Monitoring-Agent (github HIBAMAHROUG): stop auto-restart after repeated failures, escalate to a
  human -- our break_stall (declines what it cannot safely retry, tells him).
- Nothing here is new to adopt; it validates that the highway's quarantine/backoff/escalate pattern is the field's.

## The order to act, if he wants (each under the Amendment 2 bar, review before build)
1. Adopt NAB-style scoring for the witness keep-bar (specificity + a held-out negative set). This is the one that
   turns Amendment 2 from a rule into a measurement.
2. Build Fast_BOCPD/CUSUM as the explicit baselines a twin must beat.
3. For the lab: try ED-sKWS's early-decision idea for the phone wake word's efficiency.
- Verify each repo/paper by opening it first (rule 7); none is adopted on a search hit alone.
