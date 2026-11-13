/*
 * hakios_fw.h —— 内嵌 a640 固件 blob 的共享描述（hakios_fw_blob.c 数据 / hakios_glue.c 查表）
 */
#ifndef _SYS_HAKIOS_FW_H_
#define _SYS_HAKIOS_FW_H_

#include <stdint.h>
#include <sys/types.h>

struct hakios_fw_file {
	const char *dir;
	const char *name;
	const uint8_t *data;
	uint64_t size;
};

extern const struct hakios_fw_file *const hakios_fw_table[];

#endif /* _SYS_HAKIOS_FW_H_ */
