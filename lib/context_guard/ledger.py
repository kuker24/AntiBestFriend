"""Per-stream image epoch and new-payload budgets.

Stream key = session_id + SHA256(transcript_path) [+ agent id].
Parent ≠ subagent. UserPromptSubmit resets turn totals and leftover
image slot (aborted loops may skip PostToolBatch). One image per
batch is still enforced by advance_epoch.
A drip TURN_HARD (small batch, turn meter over cap) relieves turn
meters and continues; fat batches still halt.
Image slot is reserve → commit | release so a denied raw Read
does not permanently consume the model-visible claim.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

from .policy import estimate_tokens


def stream_id(session_id: str, transcript_path: str, agent_id: str | None = None) -> str:
    raw = f"{session_id or ''}\n{transcript_path or ''}"
    if agent_id:
        raw += f"\n{agent_id}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class Ledger:
    def __init__(self, cache_root: Path, stream: str) -> None:
        self.stream = stream
        self.dir = Path(cache_root) / stream
        self.dir.mkdir(parents=True, exist_ok=True)
        os.chmod(self.dir, 0o700)
        self.path = self.dir / "ledger.json"
        self.lock_path = self.dir / "image.lock"
        self.log_path = self.dir / "guard.log"
        self._state = self._load()

    def _default(self) -> dict[str, Any]:
        return {
            "stream": self.stream,
            "epoch": 0,
            "imageReserved": False,
            "imageClaimed": False,
            "imageClaimsThisEpoch": 0,
            "imageDeniedThisEpoch": 0,
            "batchTokens": 0,
            "turnTokens": 0,
            "turnObservedTokens": 0,
            "trip": False,
            "tripReason": "",
            "updatedAt": _now(),
        }

    def _load(self) -> dict[str, Any]:
        if not self.path.is_file():
            return self._default()
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return self._default()
        if not isinstance(data, dict):
            return self._default()
        state = self._default()
        state.update({k: data[k] for k in state if k in data})
        return state

    def _write(self) -> None:
        self._state["updatedAt"] = _now()
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._state, indent=2) + "\n", encoding="utf-8")
        os.chmod(tmp, 0o600)
        os.replace(tmp, self.path)
        os.chmod(self.path, 0o600)

    def _flock(self):
        import fcntl

        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        handle = open(self.lock_path, "a+", encoding="utf-8")
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        os.chmod(self.lock_path, 0o600)
        return handle

    def log(self, message: str) -> None:
        line = f"{_now()} {message}\n"
        try:
            with open(self.log_path, "a", encoding="utf-8") as handle:
                handle.write(line)
            os.chmod(self.log_path, 0o600)
        except OSError:
            pass

    def reserve_image(self) -> bool:
        """Hold the epoch slot without making it model-visible yet."""
        handle = self._flock()
        try:
            self._state = self._load()
            if self._state.get("imageClaimed") or self._state.get("imageReserved"):
                denied = int(self._state.get("imageDeniedThisEpoch") or 0) + 1
                self._state["imageDeniedThisEpoch"] = denied
                self._write()
                self.log("IMAGE_RESERVE deny epoch=%s denied=%s" % (self._state.get("epoch"), denied))
                return False
            self._state["imageReserved"] = True
            self._write()
            self.log("IMAGE_RESERVE allow epoch=%s" % self._state.get("epoch"))
            return True
        finally:
            handle.close()

    def commit_image(self) -> None:
        """Reservation becomes the one model-visible claim for this epoch."""
        handle = self._flock()
        try:
            self._state = self._load()
            self._state["imageReserved"] = False
            self._state["imageClaimed"] = True
            self._state["imageClaimsThisEpoch"] = 1
            self._write()
            self.log("IMAGE_COMMIT epoch=%s" % self._state.get("epoch"))
        finally:
            handle.close()

    def release_image(self) -> None:
        """Drop a reservation that will not enter the model (raw deny / derive)."""
        handle = self._flock()
        try:
            self._state = self._load()
            if self._state.get("imageClaimed"):
                return
            self._state["imageReserved"] = False
            self._write()
            self.log("IMAGE_RELEASE epoch=%s" % self._state.get("epoch"))
        finally:
            handle.close()

    def claim_image(self) -> bool:
        """Atomic reserve+commit. True if this caller won the model-visible slot."""
        if not self.reserve_image():
            return False
        self.commit_image()
        return True

    def add_tokens(self, tokens: int) -> dict[str, int]:
        handle = self._flock()
        try:
            self._state = self._load()
            tokens = max(0, int(tokens))
            self._state["batchTokens"] = int(self._state.get("batchTokens") or 0) + tokens
            self._state["turnTokens"] = int(self._state.get("turnTokens") or 0) + tokens
            self._write()
            return {
                "batchTokens": int(self._state["batchTokens"]),
                "turnTokens": int(self._state["turnTokens"]),
                "turnObservedTokens": int(self._state.get("turnObservedTokens") or 0),
            }
        finally:
            handle.close()

    def add_observed_tokens(self, tokens: int) -> dict[str, int]:
        """Accumulate actual PostToolBatch size. Independent of reduced ledger turnTokens."""
        handle = self._flock()
        try:
            self._state = self._load()
            tokens = max(0, int(tokens))
            self._state["turnObservedTokens"] = int(self._state.get("turnObservedTokens") or 0) + tokens
            self._write()
            return {
                "turnObservedTokens": int(self._state["turnObservedTokens"]),
                "turnTokens": int(self._state.get("turnTokens") or 0),
            }
        finally:
            handle.close()

    def add_bytes(self, size_bytes: int) -> dict[str, int]:
        return self.add_tokens(estimate_tokens(size_bytes))

    def trip(self, reason: str) -> None:
        handle = self._flock()
        try:
            self._state = self._load()
            self._state["trip"] = True
            self._state["tripReason"] = reason
            self._write()
            self.log("TRIP %s" % reason)
        finally:
            handle.close()

    def consume_trip(self) -> str | None:
        """Atomically read and clear a trip so later batches are not poisoned."""
        handle = self._flock()
        try:
            self._state = self._load()
            if not self._state.get("trip"):
                return None
            reason = str(self._state.get("tripReason") or "circuit")
            self._state["trip"] = False
            self._state["tripReason"] = ""
            self._write()
            self.log("TRIP_CONSUMED %s" % reason)
            return reason
        finally:
            handle.close()

    def advance_epoch(self) -> int:
        handle = self._flock()
        try:
            self._state = self._load()
            self._state["epoch"] = int(self._state.get("epoch") or 0) + 1
            self._state["imageReserved"] = False
            self._state["imageClaimed"] = False
            self._state["imageClaimsThisEpoch"] = 0
            self._state["imageDeniedThisEpoch"] = 0
            self._state["batchTokens"] = 0
            # Never resurrect a trip that consume_trip already cleared.
            # A leftover unconsumed trip is also dropped here: the batch
            # that should have acted on it has already ended.
            self._state["trip"] = False
            self._state["tripReason"] = ""
            self._write()
            self.log("EPOCH %s" % self._state["epoch"])
            return int(self._state["epoch"])
        finally:
            handle.close()

    def reset_turn(self) -> None:
        handle = self._flock()
        try:
            self._state = self._load()
            self._state["turnTokens"] = 0
            self._state["turnObservedTokens"] = 0
            # An aborted previous loop may never have reached PostToolBatch.
            # Drop leftover batch pressure and image slot so the next turn
            # is not poisoned (IMAGE_SECOND_IN_BATCH / leftover trip).
            # One-image-per-batch stays on advance_epoch.
            self._state["batchTokens"] = 0
            self._state["trip"] = False
            self._state["tripReason"] = ""
            self._state["imageReserved"] = False
            self._state["imageClaimed"] = False
            self._state["imageClaimsThisEpoch"] = 0
            self._state["imageDeniedThisEpoch"] = 0
            self._write()
            self.log("TURN_RESET")
        finally:
            handle.close()

    def relieve_turn(self) -> None:
        """Zero turn meters after a drip TURN_HARD warning. Image slot stays."""
        handle = self._flock()
        try:
            self._state = self._load()
            self._state["turnTokens"] = 0
            self._state["turnObservedTokens"] = 0
            self._write()
            self.log("TURN_RELIEF")
        finally:
            handle.close()

    def reset_pressure(self) -> None:
        handle = self._flock()
        try:
            self._state = self._load()
            self._state["batchTokens"] = 0
            self._state["turnTokens"] = 0
            self._state["turnObservedTokens"] = 0
            self._write()
            self.log("PRESSURE_RESET")
        finally:
            handle.close()

    @property
    def state(self) -> dict[str, Any]:
        return dict(self._state)

    def snapshot(self) -> dict[str, Any]:
        handle = self._flock()
        try:
            self._state = self._load()
            return dict(self._state)
        finally:
            handle.close()
