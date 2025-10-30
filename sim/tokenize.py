from __future__ import annotations

import json
from typing import Dict, Any, List

from .model import World


def cip25_like_metadata(world: World) -> Dict[str, Any]:
    """Create a compact CIP-25-like metadata blob for a world.

    This is not a full CIP-25 implementation; it mirrors structure for demonstration.
    """
    return {
        "world_id": world.world_id,
        "name": world.name,
        "description": world.description,
        "arweave_uri": world.arweave_uri,
        "attributes": {
            "necessary": list(world.necessary),
            "possible": list(world.possible),
            "edges": list(world.edges),
        },
        "created_by": world.created_by,
        "created_at": world.created_at,
    }


def write_metadata_json(world: World, outfile: str) -> None:
    data = cip25_like_metadata(world)
    with open(outfile, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)


