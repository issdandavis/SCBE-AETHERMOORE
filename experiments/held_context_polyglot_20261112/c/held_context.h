#ifndef HELD_CONTEXT_V1_H
#define HELD_CONTEXT_V1_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

enum {
    HCTX_OK = 0,
    HCTX_ERR_TRUNCATED = 1,
    HCTX_ERR_HEADER = 2,
    HCTX_ERR_LIMIT = 3,
    HCTX_ERR_CRC = 4,
    HCTX_ERR_LANE = 5,
    HCTX_ERR_ORDER = 6,
    HCTX_ERR_TRAILING = 7
};

typedef struct hctx_summary {
    uint32_t generation;
    uint64_t sequence_cutoff;
    uint32_t token_budget;
    int32_t breath_q1e6;
    int32_t radius_q1e6;
    uint16_t lane_count;
    size_t body_len;
    size_t token_count;
    size_t payload_bytes;
} hctx_summary;

uint32_t hctx_crc32(const uint8_t *data, size_t len);
int hctx_validate(const uint8_t *data, size_t len, hctx_summary *summary);
const char *hctx_error_string(int code);

#ifdef __cplusplus
}
#endif

#endif
