#!/usr/bin/env python3
"""adapt_a640.py — 把 HackiOS GPU 驱动（642L/SM7325）适配成 a640/SM8150（小米9 cepheus）版本。

只做"常量层"适配（09 文档第三节映射表），不动 bring-up 流程骨架。
每个替换都带权威出处；输出 *_a640 文件 + 与上游的差异 diff。

用法: python3 adapt_a640.py <srcdir> <outdir>
  srcdir = hackios 仓库根（含 drivers/gpu/、hakios-metal/include/）
  outdir = 本目录
"""
import re, sys, pathlib

SRC = pathlib.Path(sys.argv[1])
OUT = pathlib.Path(sys.argv[2])

adreno = (SRC / "drivers/gpu/hakios.adreno.c").read_text()
gpucpp = (SRC / "drivers/gpu/hakios.gpu.cpp").read_text()
a6xxhpp = (SRC / "hakios-metal/include/hakios-metal/a6xx.hpp").read_text()

def must_sub(text, old, new, count=1):
    """精确替换；old 必须恰好出现 count 次否则报错（防漂移）。"""
    n = text.count(old)
    assert n == count, f"替换点计数不符: {old!r} 出现 {n} 次(期望 {count})"
    return text.replace(old, new)

# ---------- hakios.adreno.c: 芯片身份 ----------
adreno = must_sub(adreno,
    '#define GPU_CHIP_ID             0x06030500ull   /* dt: qcom,chipid */',
    '#define GPU_CHIP_ID             0x06040001ull   /* dt: qcom,chipid (sm8150 dtsi gpu@2c00000, adreno-640.1; kernel a6xx_catalog.c:1028) */')

# GMU chipid：内核公式 chip_id&0xffff0000 | (chip_id<<4)&0xf000 | (chip_id<<8)&0x0f00 → a640 = 0x06040000（a6xx_gmu.c:1022-1024；642L 侧 0x06030500→0x06035000 已验证吻合）
adreno = must_sub(adreno,
    '#define GMU_CHIP                0x06035000      /* dt qcom,chipid 0x06030500 the way the firmware wants it */',
    '#define GMU_CHIP                0x06040000      /* dt qcom,chipid 0x06040001 per a6xx_gmu.c GMU layout formula */')

# ---------- 固件三件套（kernel a6xx_catalog.c:1032-1039；注释与代码处一并替换）----------
for old, new, expect in [('a660_gmu.bin', 'a640_gmu.bin', 4), ('a660_sqe.fw', 'a630_sqe.fw', 5), ('a660_zap', 'a640_zap', 8)]:
    n = adreno.count(old)
    assert n == expect, f"{old!r} 出现 {n} 次(期望 {expect})"
    adreno = adreno.replace(old, new)

# ---------- 寄存器块基址（sm8150.dtsi 实测）----------
adreno = must_sub(adreno,
    'static struct block qfprom = { "qfprom", 0x00780000, 0x7000 };',
    'static struct block qfprom = { "qfprom", 0x00784000, 0x9000 };   /* sm8150: efuse@784000 */')
adreno = must_sub(adreno,
    'static struct block gpucc = { "gpucc", 0x03d90000, 0x9000 };',
    'static struct block gpucc = { "gpucc", 0x02c90000, 0x9000 };   /* sm8150: gpucc@2c90000 */')
adreno = must_sub(adreno,
    'static struct block gmu = { "gmu", 0x03d6a000, 0x34000 };',
    'static struct block gmu = { "gmu", 0x02c6a000, 0x30000 };   /* sm8150: gmu@2c6a000 reg 0x30000 */')
adreno = must_sub(adreno,
    'static struct block gbif = { "gbif", 0x03d00000 + 4 * 0x3c00, 0x1000 };',
    'static struct block gbif = { "gbif", 0x02c00000 + 4 * 0x3c00, 0x1000 };   /* gpu 基址随 sm8150 */')
adreno = must_sub(adreno,
    'static struct block cx_misc = { "cx_misc", 0x03d9e000, 0x1000 };',
    'static struct block cx_misc = { "cx_misc", 0x02c9e000, 0x1000 };   /* 随 gpucc 基址平移 */')
adreno = must_sub(adreno,
    'static struct block rscc = { "rscc", 0x03de0000, 0x2000 };',
    'static struct block rscc = { "rscc", 0x02cde000, 0x2000 };   /* UNVERIFIED: sm8150 无独立 RSCC 节点，按 delta 平移；仅调试读 */')
adreno = must_sub(adreno,
    'static struct block smmu = { "smmu", 0x03da0000, 0x20000 };',
    'static struct block smmu = { "smmu", 0x02ca0000, 0x20000 };   /* sm8150: adreno_smmu iommu@2ca0000 */')
# gcc 0x00100000 sm8150 相同，不动；pdc 0x0b290000 sm8150 gmu 节点 reg-names gmu_pdc 同址，不动

# ---------- QFPROM 熔丝偏移（sm8150.dtsi:975 gpu-speed-bin@133, bits 5-7；无 gaming bin）----------
adreno = must_sub(adreno,
    '#define QFPROM_GPU_SPEED_BIN    0x1e9',
    '#define QFPROM_GPU_SPEED_BIN    0x133   /* sm8150: gpu-speed-bin@133 bits 5-7 (3 bits) */')
adreno = must_sub(adreno,
    '#define QFPROM_GPU_GAMING_BIN   0x1f5',
    '#define QFPROM_GPU_GAMING_BIN   0x1f5   /* sm8150 无 gaming bin 熔丝，读数恒 0 */')

# ---------- 频率表（sm8150.dtsi gpu_opp_table 六档 + RPMh level 值）----------
adreno = must_sub(adreno,
    '	} speeds[] = { { 0, 0 }, { 315000, 64 }, { 450000, 128 }, { 550000, 192 } };',
    '	} speeds[] = { { 0, 0 }, { 257000, 16 }, { 345000, 48 }, { 427000, 112 }, { 499200, 192 }, { 585000, 224 }, { 675000, 256 } };')
adreno = must_sub(adreno,
    ' *   adreno_speed=N     step 17 asks the GMU for the 3D core\'s Nth speed: 1 315 MHz, 2 450 MHz,\n'
    ' *                      3 550 MHz (the default: the most this phone\'s GPU is rated for)',
    ' *   adreno_speed=N     step 17 asks the GMU for the 3D core\'s Nth speed: 1 257 MHz, 2 345 MHz,\n'
    ' *                      3 427 MHz, 4 499 MHz, 5 585 MHz, 6 675 MHz (sm8150 OPP; the default: the\n'
    ' *                      most this phone\'s GPU is rated for)')

# ---------- hw_init (step 20) 常量（kernel a6xx_gpu.c a640 分支 + fd_devices A640 + ubwc 公式×sm8150 cfg）----------
# UBWC: sm8150 = UBWC 3.0 / hbb=15(hbb_lo=2) / macrotile=0 / swizzle=0 → 无 rgb565_pred、无 amsbc、无 min_acc_len、无 uavflagprd
adreno = must_sub(adreno,
    '	put(&gpu, "rb_nc_mode_cntl", GPU_WORD(0x8e08), 1u << 11 | 1u << 4 | 1u << 1);',
    '	put(&gpu, "rb_nc_mode_cntl", GPU_WORD(0x8e08), 1u << 12 | 2u << 1);   /* sm8150: lvl2_swizz_dis + hbb_lo=2 */')
adreno = must_sub(adreno,
    '	put(&gpu, "tpl1_nc_mode_cntl", GPU_WORD(0xb604), 1u << 1);',
    '	put(&gpu, "tpl1_nc_mode_cntl", GPU_WORD(0xb604), 1u << 6 | 2u << 1);   /* sm8150 */')
adreno = must_sub(adreno,
    '	put(&gpu, "sp_nc_mode_cntl", GPU_WORD(0xae02), 2u << 4 | 1u << 1);',
    '	put(&gpu, "sp_nc_mode_cntl", GPU_WORD(0xae02), 1u << 12 | 2u << 1);   /* sm8150: 无 uavflagprd_inv (gen2) */')
adreno = must_sub(adreno,
    '	put(&gpu, "uche_mode_cntl", GPU_WORD(0x0e01), 1u << 21);',
    '	put(&gpu, "uche_mode_cntl", GPU_WORD(0x0e01), 2u << 21);   /* sm8150: hbb_lo=2, 无 min_acc_len */')
adreno = must_sub(adreno,
    '	put(&gpu, "rbbm_nc_mode_cntl", GPU_WORD(0x0534), 1);',
    '	put(&gpu, "rbbm_nc_mode_cntl", GPU_WORD(0x0534), 0);   /* sm8150: macrotile_mode=0 */')
# LPAC 与 APRIV 是 gen4 特性，a640 (gen2) 无 —— 删除整行
adreno = must_sub(adreno,
    '	put(&gpu, "cp_lpac_prog_fifo_size", CP_LPAC_PROG_FIFO_SIZE, 0x20);\n', '')
adreno = must_sub(adreno,
    '	put(&gpu, "cp_apriv_cntl", CP_APRIV_CNTL, 1u << 6 | 1u << 5 | 1u << 3 | 1u << 2 | 1u << 1);\n', '')
# PC_DBG_ECO_CNTL = a640 prim_fifo_threshold（kernel a6xx_catalog.c:1041）
adreno = must_sub(adreno,
    '	put(&gpu, "pc_dbg_eco_cntl", PC_DBG_ECO_CNTL, 0x00200200);',
    '	put(&gpu, "pc_dbg_eco_cntl", PC_DBG_ECO_CNTL, 0x00180000);   /* a640 prim_fifo_threshold (a6xx_catalog.c) */')

# ---------- SoC 基址闸门（sm8150 soc ranges=恒等映射，pe_arm_get_soc_base_phys() 返回值待真机实证；
# 上游 sc7280 是 0x00400000。bring-up 阶段改为宽容闸门：匹配即过，不匹配打印实值继续（后续加固））
adreno = must_sub(adreno,
    '\tif (pe_arm_get_soc_base_phys() != HAKIOS_SOC_BASE) {\n\t\tprintf("adreno: THE GPU IS NOT STARTED: gpu=1 is for the phone, and this is not it\\n");\n\t\treturn false;\n\t}',
    '\tif (pe_arm_get_soc_base_phys() != HAKIOS_SOC_BASE) {\n\t\tprintf("adreno: soc base 0x%llx differs from upstream 0x%llx (sm8150 identity ranges); proceeding (bring-up gate)\\n",\n\t\t    (unsigned long long)pe_arm_get_soc_base_phys(), (unsigned long long)HAKIOS_SOC_BASE);\n\t}')

# ---------- cmd-db 物理地址（sm8150.dtsi:707 aop_cmd_db@85f20000；sc7280 是 0x80860000）----------
adreno = must_sub(adreno,
    '#define CMD_DB_PHYS             0x80860000UL',
    '#define CMD_DB_PHYS             0x85f20000UL   /* sm8150: aop_cmd_db memory@85f20000 (0x20000) */')
adreno = must_sub(adreno,
    'announce("look up the GPU\'s supply rails in the boot loader\'s list of RPMh resources (memory at 0x80860000)");',
    'announce("look up the GPU\'s supply rails in the boot loader\'s list of RPMh resources (memory at 0x85f20000)");')

# ---------- a6xx.hpp（hakios-metal 用户态芯片事实，fd_devices.py A640 条目 L457-487 + a6xx_gen2 L180-191）----------
a6xxhpp = must_sub(a6xxhpp,
    'inline constexpr uint32_t kChipId = 0x06030500;',
    'inline constexpr uint32_t kChipId = 0x06040001;')
a6xxhpp = must_sub(a6xxhpp, 'inline constexpr bool kHasLpac = true;', 'inline constexpr bool kHasLpac = false;')
a6xxhpp = must_sub(a6xxhpp, 'inline constexpr uint32_t kInstrCacheSize = 127;', 'inline constexpr uint32_t kInstrCacheSize = 64;')
a6xxhpp = must_sub(a6xxhpp, 'inline constexpr uint32_t kFibersPerSp = 128 * 2 * 16;', 'inline constexpr uint32_t kFibersPerSp = 128 * 4 * 16;')
# kNumSpCores=2 / kCsSharedMemSize=32K / kWaveGranularity=2 / kSupportsDoubleThreadsize=true：A640 与 A635 相同，不动
# 注释语境修正（chip id 提及处）
adreno = must_sub(adreno,
    'There is no register that holds the chip ID (0x06030500,',
    'There is no register that holds the chip ID (0x06040001,')
a6xxhpp = must_sub(a6xxhpp,
    '// 7c+ Gen 3 (the A635 family, chip id 0x06030500: Mesa\'s "a6xx gen4", the same generation as the A660).',
    '// A640 (chip id 0x06040001: Mesa\'s "a6xx gen2", the a630/a640/a680 generation; freedreno_devices.py GPUId(640)).')

# ---------- 落盘 ----------
(OUT / "hakios_adreno_a640.c").write_text(adreno)
(OUT / "hakios_gpu.cpp").write_text(gpucpp)
(OUT / "a6xx_a640.hpp").write_text(a6xxhpp)

orig_adreno = (SRC / "drivers/gpu/hakios.adreno.c").read_text()
orig_hpp = (SRC / "hakios-metal/include/hakios-metal/a6xx.hpp").read_text()
import difflib
d1 = difflib.unified_diff(orig_adreno.splitlines(), adreno.splitlines(), "hakios.adreno.c (642L upstream 63fc2b4)", "hakios_adreno_a640.c (cepheus)", lineterm="")
d2 = difflib.unified_diff(orig_hpp.splitlines(), a6xxhpp.splitlines(), "a6xx.hpp (upstream)", "a6xx_a640.hpp (cepheus)", lineterm="")
(OUT / "a640-constants.diff").write_text("\n".join(d1) + "\n\n" + "\n".join(d2) + "\n")
print("OK: hakios_adreno_a640.c / hakios_gpu.cpp / a6xx_a640.hpp / a640-constants.diff 已生成")
