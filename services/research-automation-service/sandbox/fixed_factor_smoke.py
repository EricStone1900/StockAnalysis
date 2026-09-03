"""阶段04固定脚本：只读取只读输入目录并输出确定性摘要。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] != "fixed-factor-smoke-v1":
        return 2
    input_root = Path("/input")
    files = tuple(sorted(path.name for path in input_root.iterdir())) if input_root.exists() else ()
    digest = hashlib.sha256("\n".join(files).encode()).hexdigest()
    print(json.dumps({"scriptId": sys.argv[1], "inputFileCount": len(files), "inputListingHash": digest}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
