from collections import defaultdict, deque
from typing import Dict, List
from .config import HISTO_MAX, DEFAULT_SYSTEM

# --- Memory per instance
memory: Dict[int, deque]   = defaultdict(lambda: deque(maxlen=HISTO_MAX))
facts: Dict[int, List[str]] = defaultdict(list)
personas: Dict[int, str]    = defaultdict(lambda: DEFAULT_SYSTEM)

# --- Instance map
user_instances: Dict[int, List[int]] = defaultdict(list)  # user.id -> [channel.id...]
instance_owner: Dict[int, int]       = {}                 # channel.id -> user.id
instance_tags: Dict[int, List[str]]  = defaultdict(list)  # channel.id -> ["joyeuse", ...]

def is_instance_channel_id(channel_id: int) -> bool:
    return channel_id in instance_owner