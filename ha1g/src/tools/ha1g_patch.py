#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tempitor. Part of Tempest, see LICENSE and NOTICE at the repository root.
"""
ha1g_patch.py - make or apply an HA1G mod patch, so a mod can be shared without
shipping any Retevis/Ailunce firmware.

A patch holds only the bytes our build changed or added, compared with the stock
V1.01.14.002 image. Whoever applies it supplies their own stock file; its sha256
must match, and the result must match the build's sha256, or nothing is written.

  make:   ha1g_patch.py make STOCK.bin BUILD.bin --name D006 [-o D006.ha1gpatch.json]
                                                  [--html tool/ha1g_flasher.html]
          --html writes the patch into the flasher page (between the
          HA1G-PATCH-BEGIN / HA1G-PATCH-END markers), so the page you share
          carries the latest build.
  apply:  ha1g_patch.py apply STOCK.bin PATCH.json OUT.bin
  public: ha1g_patch.py public tool/ha1g_flasher.html OUT/index.html
          writes the public flasher page: the same page with every DEV{ ... }DEV
          block removed (no Full .bin tab, no Save patched .bin, no image override).

Patch format (JSON):
  {"format": "ha1g-patch-1", "name": "D006",
   "stock_len": 455396, "stock_sha256": "...",
   "out_len": 464832,   "out_sha256": "...",
   "edits": [[offset, "hexbytes"], ...]}
Output = stock bytes, extended with zeros to out_len, then each edit written at
its offset. Edits are runs of bytes that differ from stock; bytes past the end of
stock are our appended code.
"""
import argparse, hashlib, json, re, sys

FORMAT = "ha1g-patch-1"
BEGIN, END = "<!--HA1G-PATCH-BEGIN-->", "<!--HA1G-PATCH-END-->"


def sha(b):
    return hashlib.sha256(b).hexdigest()


def make(stock, build, name):
    edits, i = [], 0
    while i < len(build):
        if i < len(stock) and build[i] == stock[i]:
            i += 1
            continue
        j = i
        while j < len(build) and (j >= len(stock) or build[j] != stock[j]):
            j += 1
        edits.append([i, build[i:j].hex()])
        i = j
    return {"format": FORMAT, "name": name,
            "stock_len": len(stock), "stock_sha256": sha(stock),
            "out_len": len(build), "out_sha256": sha(build), "edits": edits}


def apply(stock, p):
    if p.get("format") != FORMAT:
        raise ValueError("not an %s patch" % FORMAT)
    if len(stock) != p["stock_len"] or sha(stock) != p["stock_sha256"]:
        raise ValueError("this is not the stock file the patch was made for "
                         "(need sha256 %s, %d bytes)" % (p["stock_sha256"], p["stock_len"]))
    out = bytearray(stock) + bytes(max(0, p["out_len"] - len(stock)))
    del out[p["out_len"]:]
    for off, h in p["edits"]:
        b = bytes.fromhex(h)
        if off + len(b) > len(out):
            raise ValueError("edit at %#x runs past the end" % off)
        out[off:off + len(b)] = b
    if sha(out) != p["out_sha256"]:
        raise ValueError("patched image hash mismatch")
    return bytes(out)


def embed(html_path, p):
    s = open(html_path, encoding="utf-8").read()
    blob = json.dumps(p, separators=(",", ":"))
    if "</" in blob:
        raise ValueError("unexpected '</' in patch JSON")
    new = (BEGIN + '\n<script type="application/json" id="patchdata">' + blob + '</script>\n' + END)
    s2, n = re.subn(re.escape(BEGIN) + ".*?" + re.escape(END), lambda m: new, s, flags=re.S)
    if n != 1:
        raise ValueError("%s: expected one %s ... %s block, found %d" % (html_path, BEGIN, END, n))
    open(html_path, "w", encoding="utf-8", newline="\n").write(s2)


def public(src, dst):
    s = open(src, encoding="utf-8").read()
    n0 = s.count("/*DEV{*/") + s.count("<!--DEV{-->")
    if n0 == 0 or n0 != s.count("/*}DEV*/") + s.count("<!--}DEV-->"):
        raise ValueError("unbalanced or missing DEV markers in " + src)
    s = re.sub(r"[ \t]*/\*DEV\{\*/.*?/\*\}DEV\*/[ \t]*\n?", "", s, flags=re.S)
    s = re.sub(r"[ \t]*<!--DEV\{-->.*?<!--\}DEV-->[ \t]*\n?", "", s, flags=re.S)
    for left in ("DEV{", "}DEV", 'id="tabfull"', 'id="savepatched"', 'id="file"', 'id="force"', "checkImage"):
        if left in s:
            raise ValueError("public page still contains " + left)
    if 'id="patchdata"' not in s:
        raise ValueError("no patch embedded in " + src)
    open(dst, "w", encoding="utf-8", newline="\n").write(s)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    m = sp.add_parser("make")
    m.add_argument("stock"); m.add_argument("build")
    m.add_argument("--name", required=True, help="build name shown to users, e.g. D006")
    m.add_argument("-o", "--out", help="write the patch as JSON")
    m.add_argument("--html", help="write the patch into this flasher page")
    a = sp.add_parser("apply")
    a.add_argument("stock"); a.add_argument("patch"); a.add_argument("out")
    pb = sp.add_parser("public")
    pb.add_argument("page"); pb.add_argument("out")
    args = ap.parse_args()

    if args.cmd == "make":
        stock, build = open(args.stock, "rb").read(), open(args.build, "rb").read()
        p = make(stock, build, args.name)
        assert apply(stock, p) == build          # round trip
        changed = sum(len(h) // 2 for _, h in p["edits"])
        print("%s: %d edits, %d bytes of mod data, output %d bytes sha256 %s"
              % (args.name, len(p["edits"]), changed, p["out_len"], p["out_sha256"]))
        if args.out:
            open(args.out, "w").write(json.dumps(p, indent=0) + "\n")
            print("wrote", args.out)
        if args.html:
            embed(args.html, p)
            print("embedded into", args.html)
        if not (args.out or args.html):
            print("(nothing written: give -o and/or --html)")
    elif args.cmd == "public":
        try:
            public(args.page, args.out)
        except ValueError as e:
            sys.exit("error: %s" % e)
        print("wrote public page", args.out)
    else:
        p = json.load(open(args.patch))
        try:
            out = apply(open(args.stock, "rb").read(), p)
        except ValueError as e:
            sys.exit("error: %s" % e)
        open(args.out, "wb").write(out)
        print("wrote %s (%s, %d bytes, sha256 %s)" % (args.out, p["name"], len(out), p["out_sha256"]))


if __name__ == "__main__":
    main()
