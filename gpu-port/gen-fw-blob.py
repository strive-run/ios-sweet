#!/usr/bin/env python3
"""gen-fw-blob.py — 把 gpu-port/fw/ 的四件固件生成为 C 内嵌数组（hakios_fw_blob.c）。
再生成：python3 gen-fw-blob.py （在 gpu-port/ 目录内运行）
"""
import pathlib
fwdir = pathlib.Path(__file__).parent / "fw"
files = [("fw", "a630_sqe.fw", fwdir / "vendor-a630_sqe.fw"),
         ("fw", "a640_gmu.bin", fwdir / "vendor-a640_gmu.bin"),
         ("fw", "a640_zap.mdt", fwdir / "a640_zap.mdt"),
         ("fw", "a640_zap.b02", fwdir / "a640_zap.b02")]
out = pathlib.Path(__file__).parent / "hakios_fw_blob.c"
lines = ["""/*
 * hakios_fw_blob.c —— a640 固件内嵌（cepheus 第一批 bring-up 专用）
 *
 * 上游经 hakios_image_file() 从其 "small image" 读固件；本机 shim 引导无该通道，
 * 第一批 bring-up 把四件固件直接编进内核（合计 ~79KB）。来源与校验见 gpu-port/fw/：
 *   a640_zap.mdt/.b02 —— 小米9 本机 vendor 签名版（TrustZone 只认本机签名，无可替代）
 *   a630_sqe.fw        —— Mi 9 /vendor/firmware 版（与上游 linux-firmware 不同，配套集用 vendor 版）
 *   a640_gmu.bin       —— Mi 9 vendor 版，与上游 linux-firmware 逐字节一致
 * 再生成：python3 gen-fw-blob.py（gpu-port/）
 */""",
"#include <sys/types.h>",
"#include <stdint.h>",
"#include <sys/hakios_fw.h>",
""]
for d, n, p in files:
    data = p.read_bytes()
    arr = ",\n\t".join(",".join(f"0x{b:02x}" for b in data[i:i+16]) for i in range(0, len(data), 16))
    sym = "hakios_fw_" + n.replace(".", "_").replace("-", "_")
    lines.append(f"static const uint8_t {sym}[] = {{\n\t{arr}\n}};")
    lines.append(f"static const struct hakios_fw_file {sym}_entry = {{ \"{d}\", \"{n}\", {sym}, {len(data)} }};")
    lines.append("")
lines.append("const struct hakios_fw_file *const hakios_fw_table[] = {")
for d, n, p in files:
    sym = "hakios_fw_" + n.replace(".", "_").replace("-", "_")
    lines.append(f"\t&{sym}_entry,")
lines.append("\t0,")
lines.append("};")
out.write_text("\n".join(lines) + "\n")
print(f"blob written: {out} ({out.stat().st_size} bytes, {len(files)} files)")
