from __future__ import annotations

import hashlib
import json
from typing import Any, Dict


class MockArchiver:
    """Deterministic mock Arweave uploader.

    Returns a placeholder arweave-like URI based on sha256 hash of the JSON content.
    """

    def upload_json(self, data: Dict[str, Any]) -> str:
        payload = json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
        digest = hashlib.sha256(payload).hexdigest()[:16]
        return f"ar://placeholder-{digest}"


# Real client hook (example, commented):
#
# from arweave import Wallet, Transaction
# class ArweaveClient:
#     def __init__(self, jwk_path: str):
#         self.wallet = Wallet(jwk_path)
#
#     def upload_json(self, data: Dict[str, Any]) -> str:
#         payload = json.dumps(data).encode("utf-8")
#         tx = Transaction(self.wallet, data=payload)
#         tx.sign()
#         tx.send()
#         return f"ar://{tx.id}"


