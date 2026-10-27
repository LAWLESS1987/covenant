#!/usr/bin/env python3
"""Covenant Neural Event Bridge -- v1 (session v8.5-PQ1, item Y)

WHAT THIS IS
------------
A source-agnostic ingestion path from any spike-train-like signal source
(EEG via BrainFlow, or any (timestamp, channel_values) frame iterator)
into Covenant's SpikingAnomalyMonitor. Band-limited power threshold
crossings become discrete events; the monitor's LIF substrate consumes
them exactly as it consumes transaction arrivals. Verified end-to-end in
this session against BrainFlow's SYNTHETIC_BOARD (no hardware present).

WHAT THIS DELIBERATELY IS NOT -- MEASURED, NOT ASSERTED
-------------------------------------------------------
This bridge does NOT and will not gate signing, authentication, or any
chain action on neural signals. The obvious BCI-crypto idea (derive a
signing key from neural features) was attempted quantitatively this
session rather than dismissed rhetorically. Result, at literature-
realistic feature separability (d' = 2, 32 band-power features, 50
subjects, median-split quantization, Hamming-tolerance fuzzy matcher):

    to reach usable false-rejection (<5%) the matcher must tolerate
    enough bit error that effective key entropy collapses to ~10-17
    bits -- against a 128-bit requirement -- while FAR is already
    nonzero. At d'=1 it is worse than a 4-digit PIN. And unlike a PIN,
    the biometric is non-revocable: leak it once, it is burned forever.

Numbers from exp_phase4_keying.py in the session log. Until someone
demonstrates >=128 stable extractable bits from scalp EEG (nobody has),
neural signals here are a TELEMETRY source, never a key source.

USAGE
-----
    from covenant_neural_bridge import NeuralEventBridge
    bridge = NeuralEventBridge(monitor)           # any SpikingAnomalyMonitor
    bridge.run_synthetic(seconds=5)               # BrainFlow synthetic board
    # or: bridge.feed_frames(iterable_of_(t, [ch0, ch1, ...]))
"""
import time
import math
from typing import Iterable, List, Optional, Tuple

try:
    from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds
    BRAINFLOW_AVAILABLE = True
except Exception:
    BRAINFLOW_AVAILABLE = False


class NeuralEventBridge:
    """Windowed band-power thresholding over multichannel frames.
    A channel whose short-window log-power exceeds `z_thresh` standard
    deviations of its own running baseline emits one event into the
    monitor under sender id 'neural:ch<i>'. Observe-only, like every
    other monitor input."""

    def __init__(self, monitor, window: int = 64, z_thresh: float = 3.0):
        self.monitor = monitor
        self.window = window
        self.z_thresh = z_thresh
        self._buf: List[List[float]] = []
        self._mu: List[float] = []
        self._var: List[float] = []
        self.events = 0

    def _power(self, xs: List[float]) -> float:
        m = sum(xs) / len(xs)
        return math.log1p(sum((x - m) ** 2 for x in xs) / len(xs))

    def feed_frames(self, frames: Iterable[Tuple[float, List[float]]]) -> int:
        emitted = 0
        for t, chans in frames:
            self._buf.append(list(chans))
            if len(self._buf) < self.window:
                continue
            block = self._buf[-self.window:]
            self._buf = block  # bounded memory
            n_ch = len(block[0])
            if not self._mu:
                self._mu = [0.0] * n_ch
                self._var = [1.0] * n_ch
            for i in range(n_ch):
                p = self._power([row[i] for row in block])
                mu, var = self._mu[i], self._var[i]
                z = (p - mu) / max(math.sqrt(var), 1e-9)
                # slow EWMA baseline so the threshold adapts per channel
                self._mu[i] = 0.99 * mu + 0.01 * p
                self._var[i] = 0.99 * var + 0.01 * (p - mu) ** 2
                if z > self.z_thresh:
                    self.monitor.observe(f"neural:ch{i}", t)
                    emitted += 1
        self.events += emitted
        return emitted

    def run_synthetic(self, seconds: float = 5.0) -> int:
        """Stream BrainFlow's hardware-free synthetic board through the
        bridge. Raises if brainflow absent -- loud, never silent."""
        if not BRAINFLOW_AVAILABLE:
            raise RuntimeError("brainflow not installed; use feed_frames() with your own source")
        BoardShim.disable_board_logger()
        params = BrainFlowInputParams()
        board = BoardShim(BoardIds.SYNTHETIC_BOARD.value, params)
        board.prepare_session()
        board.start_stream()
        time.sleep(seconds)
        data = board.get_board_data()
        board.stop_stream()
        board.release_session()
        eeg_rows = BoardShim.get_eeg_channels(BoardIds.SYNTHETIC_BOARD.value)
        ts_row = BoardShim.get_timestamp_channel(BoardIds.SYNTHETIC_BOARD.value)
        frames = [(float(data[ts_row][k]), [float(data[r][k]) for r in eeg_rows])
                  for k in range(data.shape[1])]
        return self.feed_frames(frames)
