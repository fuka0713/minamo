"""ID を作る（例：itm_1a2b3c…）。前の文字で、何の ID かが分かる。"""

import uuid


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"
