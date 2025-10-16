# bench.py — ultra-light metrics with near-zero hot-path overhead
from __future__ import annotations
import os, time, json, threading, queue, math
from dataclasses import dataclass, asdict

BENCH_ENABLED = os.getenv("BENCH", "1") not in ("0", "false", "False", "")

@dataclass
class Point:
    t_ns: int
    name: str
    kind: str          # "span","mark","value"
    value: float|None  # seconds for spans/marks, arbitrary for values
    extra: dict

class Bench:
    def __init__(self, flush_path="/tmp/buttontalk_metrics.jsonl", flush_interval=2.0, max_queue=5000):
        self.enabled = BENCH_ENABLED
        self.q = queue.SimpleQueue() if self.enabled else None
        self.flush_path = flush_path
        self.flush_interval = flush_interval
        self._stop = False
        self._thread = None
        # cache monotonic to avoid attribute lookup in hot path
        self._now = time.perf_counter_ns

    # ---------- Hot-path API (all branch-predicted no-ops when disabled) ----------
    def mark(self, name: str, **extra):
        if not self.enabled: return
        self.q.put(Point(self._now(), name, "mark", None, extra))

    def value(self, name: str, v: float, **extra):
        if not self.enabled: return
        self.q.put(Point(self._now(), name, "value", float(v), extra))

    def span(self, name: str, **extra):
        """Usage: with bench.span('stt.record'): ..."""
        if not self.enabled:
            class _Null: 
                def __enter__(self): return None
                def __exit__(self, *a): return False
            return _Null()
        start_ns = self._now()
        def _exit(exc_type, exc, tb):
            dur_s = (self._now() - start_ns) / 1e9
            self.q.put(Point(self._now(), name, "span", dur_s, extra))
            return False
        class _Ctx:
            def __enter__(self): return None
            def __exit__(self, *a): return _exit(*a)
        return _Ctx()

    # ---------- Background flush ----------
    def start(self):
        if not self.enabled or self._thread: return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop = True
        if self._thread: self._thread.join(timeout=1.0)

    def _run(self):
        buf = []
        last = time.time()
        while not self._stop:
            try:
                p = self.q.get(timeout=0.2)
                buf.append(p)
            except Exception:
                pass
            now = time.time()
            if buf and (now - last) >= self.flush_interval:
                # write once per interval to minimise I/O
                with open(self.flush_path, "a") as f:
                    for pt in buf:
                        rec = asdict(pt)
                        # convert ns timestamp + keep as seconds too
                        rec["t"] = pt.t_ns / 1e9
                        rec["t_ns"] = pt.t_ns
                        f.write(json.dumps(rec, separators=(",",":")) + "\n")
                buf.clear()
                last = now

bench = Bench()
