# gpu-port · HackiOS GPU 驱动 → 小米9 (a640/SM8150) 适配工作区

> 上游：oosexgang/hakios-xnu-kernel @ 63fc2b4（浅克隆，/tmp/hakios-research/，可随时重取）
> 适配脚本：`adapt_a640.py`（唯一入口，可重放；`*_a640.*` 为产物，`a640-constants.diff` 为与上游的全部差异）
> 方法论：**只做常量层适配，不动 22 步 bring-up 流程骨架**。每处替换带权威出处。

## 文件

| 文件 | 来源 | 状态 |
|------|------|------|
| `hakios_adreno_a640.c` | drivers/gpu/hakios.adreno.c（3852 行） | **a640 已适配**（24 处替换，见 diff） |
| `hakios_gpu.cpp` | drivers/gpu/hakios.gpu.cpp | 原样（GPU 无关：msm DRM ABI 的 IOKit 网关） |
| `a6xx_a640.hpp` | hakios-metal/include/hakios-metal/a6xx.hpp | **a640 已适配**（用户态芯片事实） |
| `a640-constants.diff` | — | 与上游的全部差异（280 行，逐条带出处注释） |
| `adapt_a640.py` | — | 重放入口：`python3 adapt_a640.py <hackios-clone> .` |

## 642L → 640 映射表（全部已应用）

| 项 | 642L 原值 | **a640 新值** | 出处 |
|----|-----------|--------------|------|
| GPU chip id | 0x06030500 | **0x06040001** | kernel a6xx_catalog.c:1028 |
| GMU chipid | 0x06035000 | **0x06040000** | a6xx_gmu.c:1022-1024 公式代入 |
| SQE/GMU/zap 固件 | a660_sqe.fw / a660_gmu.bin / a660_zap.mdt | **a630_sqe.fw / a640_gmu.bin / a640_zap.mdt** | a6xx_catalog.c:1032-1039 |
| GMEM | 512K | **1M** | a6xx_catalog.c:1034 |
| HIGHEST_BANK_BIT | 14 | **15** | fd_devices.py A640 (hbb=15) |
| UBWC_SWIZZLE / MACROTILE | 6 / 1 | **0 / 0** | sm8150 = ubwc_3_0_hbb15（ubwc_config.c:45-48,172） |
| RB/TPL1/SP/UCHE/RBBM NC_MODE_CNTL | 642L 值 | **0x1004 / 0x44 / 0x1004 / 0x400000 / 0** | a6xx_gpu.c:769-805 公式 × sm8150 cfg |
| PC_DBG_ECO_CNTL | 0x00200200 | **0x00180000** | a6xx_catalog.c:1041（a640 prim_fifo_threshold） |
| CP_LPAC_PROG_FIFO_SIZE | 有 | **删除**（gen2 无 LPAC） | a6xx_gpu.c:1318 仅 a660_family |
| CP_APRIV_CNTL | 有 | **删除**（gen2 无 HW_APRIV） | a6xx_catalog.c:1035-1036 quirks |
| 基址 gpu/gmu/gpucc/smmu | 0x03d00000/0x03d6a000/0x03d90000/0x03da0000 | **0x02c00000/0x02c6a000/0x02c90000/0x02ca0000** | sm8150.dtsi:2252/2316/2355/2369 |
| qfprom | 0x00780000, bin@corrected+0x1e9 | **0x00784000, bin@0x133 bits5-7（3bit）** | sm8150.dtsi:969-978 |
| pdc | 0x0b290000 | **不变**（sm8150 gmu 节点 gmu_pdc 同址） | sm8150.dtsi:2320 |
| 频率表 | 315/450/550（3 档） | **257/345/427/499.2/585/675（6 档，RPMh 16/48/112/192/224/256）** | sm8150.dtsi gpu_opp_table |
| a6xx.hpp | kChipId/kHasLpac=true/kInstrCache=127/kFibers=128*2*16 | **0x06040001/false/64/128*4*16** | fd_devices.py A640+a6xx_gen2 |

不变项：gcc 基址 0x00100000、CP_ROQ_THRESHOLDS（0x02000140/0x8040362c，a640_family 同组）、RB_DBG_ECO_CNTL 0x04100000、UCHE/GBIF/QSB 序列、SMMU 页表逻辑、cmd-db 资源名（gfx.lvl/cx.lvl/mx.lvl 通用）。

## 接线 TODO（C5.2c，进 fork 补丁系列前必读）

1. **conf/files**：`bsd/dev/hakios_adreno.c optional hakios_adreno` + `iokit/Kernel/hakios_gpu.cpp optional hakios_adreno iokitcpp`（对齐 hackios xnu/hakios.patch:149/1915 的做法）；文件需改名进树（`hakios.adreno.c`→`hakios_adreno.c`）
2. **boot-arg 闸门**：上游 `adreno=N` 分步纪律原样保留；默认 **`adreno=0`（全关）**，首次真机从 `adreno=1` 逐级放行
3. **电源钩子**：hakios.patch:2403-2413 的 `hakios_adreno_stop()` 挂接点要复刻进我们树
4. **固件打包**：`fw/a640_{zap,gmu,sqe}` 三件随 payload/bootimg 携带（zap 必须本机 TWRP 提取的签名版 → C5.1）
5. **sweet surface 对接**：hakios_gpu.cpp 的 `kHakiosSurface 0x7e`（IOSurface 注册）要改挂我们 0046 补丁的 `SweetSurface` 对象（用户态 iOS 16.7.16 已在与 SweetSurface 对话，这是与 hackios Darwin 16.5 语境的最大结构差异）
6. **MetalPlugin 出口**：0046 的 IOMobileFramebuffer stand-in 上补 `MetalPluginName/MetalPluginClassName` 属性（hackios MiniIOMobileFramebuffer.cpp:2014-2033 的机制通用）
7. **RSCC 基址 0x02cde000 为 UNVERIFIED**（sm8150 无独立 RSCC 节点，仅调试读；bring-up 时若 trap 即跳过）
8. **hwcg 表**：a640_hwcg（a6xx_catalog.c:293，48 项）上游未写入（GMU 托管时钟），bring-up 若遇时钟挂死再补
9. **CP_PROTECT**：上游有意省略（driver-review G1）；a640 对应 a630_protect 32 项表（a6xx_catalog.c:507-541，已留档 /tmp/hakios/），bring-up 通过后作为加固项补

## 下一步

- **C5.1**（等设备）：TWRP 提取本机 `/vendor/firmware` 的 a640_zap.mdt/bXX、a630_sqe.fw、a640_gmu.bin → 本目录 `fw/`，SHA256 入档
- **C5.2 收尾**：以上接线做成 `0110-gpu-a640-port.patch` 系列（对 post-0081+0071 树生成；树从 CI buildtree artifact 重取），推 tag 触发 CI 编译
- **C5.3**：真机 `adreno=1..22` 分步 bring-up → 三色带 = GPU 硬件首帧
