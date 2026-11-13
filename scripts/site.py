#!/usr/bin/env python3
"""Đọc deploy.toml cho các script shell.
  site.py upstream <trạm>   địa chỉ host:port mà container campus_a / toxiproxy dùng để tới trạm đó
                            (host là localhost => cùng máy, dùng tên dịch vụ compose; ngược lại dùng IP:cổng thật)
  site.py machine <trạm>    máy A hay B
  site.py sites             danh sách trạm
"""
import sys, tomllib
from pathlib import Path

cfg = tomllib.loads((Path(__file__).resolve().parent.parent / "deploy.toml").read_text(encoding="utf-8"))
st = cfg["stations"]
cmd = sys.argv[1]
if cmd == "sites":
    print(" ".join(st))
else:
    s = st[sys.argv[2]]
    if cmd == "upstream":
        print(f"{sys.argv[2]}:5432" if s["host"] in ("localhost", "127.0.0.1") else f"{s['host']}:{s['port']}")
    elif cmd == "machine":
        print(s["machine"])
