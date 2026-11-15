#include "held_context.h"

#include <limits.h>
#include <string.h>

#define HCTX_HEADER_LEN 64u
#define HCTX_LANE_HEADER_LEN 96u
#define HCTX_MAX_BODY_LEN (16u * 1024u * 1024u)
#define HCTX_MAX_LANES 4096u
#define HCTX_MAX_ROUTE_DIM 256u
#define HCTX_MAX_TOKEN_COUNT 1048576u
#define HCTX_MAX_PAYLOAD_LEN (8u * 1024u * 1024u)
#define HCTX_Q_SCALE 1000000
#define HCTX_KNOWN_FLAGS 7u

static uint16_t read_u16(const uint8_t *p) {
    return (uint16_t)((uint16_t)p[0] | ((uint16_t)p[1] << 8));
}

static uint32_t read_u32(const uint8_t *p) {
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static uint64_t read_u64(const uint8_t *p) {
    return (uint64_t)read_u32(p) | ((uint64_t)read_u32(p + 4) << 32);
}

static uint32_t crc32_update(uint32_t crc, const uint8_t *data, size_t len) {
    size_t i;
    unsigned bit;
    for (i = 0; i < len; ++i) {
        crc ^= (uint32_t)data[i];
        for (bit = 0; bit < 8; ++bit) {
            uint32_t mask = (uint32_t)(0u - (crc & 1u));
            crc = (crc >> 1) ^ (0xEDB88320u & mask);
        }
    }
    return crc;
}

uint32_t hctx_crc32(const uint8_t *data, size_t len) {
    if (data == NULL && len != 0u) {
        return 0u;
    }
    return ~crc32_update(0xFFFFFFFFu, data, len);
}

static int valid_enums(const uint8_t *header) {
    return header[2] <= 7u && header[3] <= 4u && header[4] <= 5u && (header[5] & ~HCTX_KNOWN_FLAGS) == 0u;
}

int hctx_validate(const uint8_t *data, size_t len, hctx_summary *summary) {
    uint32_t body_len_u32;
    size_t body_len;
    uint16_t lane_count;
    uint64_t sequence_cutoff;
    const uint8_t *body;
    size_t offset = 0u;
    uint16_t previous_lane_id = 0u;
    int have_previous = 0;
    size_t all_tokens = 0u;
    size_t all_payload = 0u;
    uint16_t lane_index;

    if (data == NULL || len < HCTX_HEADER_LEN) {
        return HCTX_ERR_TRUNCATED;
    }
    if (memcmp(data, "HCTX", 4u) != 0 || data[4] != 1u || read_u16(data + 6) != HCTX_HEADER_LEN ||
        read_u16(data + 14) != 0u) {
        return HCTX_ERR_HEADER;
    }
    body_len_u32 = read_u32(data + 8);
    lane_count = read_u16(data + 12);
    if (body_len_u32 > HCTX_MAX_BODY_LEN || lane_count > HCTX_MAX_LANES) {
        return HCTX_ERR_LIMIT;
    }
    body_len = (size_t)body_len_u32;
    if (body_len > SIZE_MAX - HCTX_HEADER_LEN || len != HCTX_HEADER_LEN + body_len) {
        return HCTX_ERR_TRAILING;
    }
    if (hctx_crc32(data, 60u) != read_u32(data + 60)) {
        return HCTX_ERR_CRC;
    }
    body = data + HCTX_HEADER_LEN;
    if (hctx_crc32(body, body_len) != read_u32(data + 56)) {
        return HCTX_ERR_CRC;
    }
    if ((int32_t)read_u32(data + 32) < 0 || (int32_t)read_u32(data + 32) >= HCTX_Q_SCALE) {
        return HCTX_ERR_HEADER;
    }
    sequence_cutoff = read_u64(data + 16);

    for (lane_index = 0u; lane_index < lane_count; ++lane_index) {
        const uint8_t *lane;
        uint16_t lane_id;
        uint16_t route_dim;
        uint32_t token_count;
        uint32_t payload_len;
        uint64_t expiry;
        size_t route_bytes;
        size_t token_bytes;
        size_t variable_len;
        size_t lane_len;
        uint32_t crc;

        if (offset > body_len || body_len - offset < HCTX_LANE_HEADER_LEN) {
            return HCTX_ERR_TRUNCATED;
        }
        lane = body + offset;
        if (!valid_enums(lane) || read_u32(lane + 92) != 0u) {
            return HCTX_ERR_LANE;
        }
        lane_id = read_u16(lane);
        if (have_previous && lane_id <= previous_lane_id) {
            return HCTX_ERR_ORDER;
        }
        previous_lane_id = lane_id;
        have_previous = 1;
        route_dim = read_u16(lane + 6);
        token_count = read_u32(lane + 8);
        payload_len = read_u32(lane + 12);
        expiry = read_u64(lane + 16);
        if (route_dim > HCTX_MAX_ROUTE_DIM || token_count > HCTX_MAX_TOKEN_COUNT ||
            payload_len > HCTX_MAX_PAYLOAD_LEN) {
            return HCTX_ERR_LIMIT;
        }
        if (expiry != UINT64_MAX && expiry < sequence_cutoff) {
            return HCTX_ERR_LANE;
        }
        route_bytes = (size_t)route_dim * 4u;
        token_bytes = (size_t)token_count * 4u;
        if (route_bytes > SIZE_MAX - token_bytes || route_bytes + token_bytes > SIZE_MAX - (size_t)payload_len) {
            return HCTX_ERR_LIMIT;
        }
        variable_len = route_bytes + token_bytes + (size_t)payload_len;
        if (variable_len > SIZE_MAX - HCTX_LANE_HEADER_LEN) {
            return HCTX_ERR_LIMIT;
        }
        lane_len = HCTX_LANE_HEADER_LEN + variable_len;
        if (lane_len > body_len - offset) {
            return HCTX_ERR_TRUNCATED;
        }
        crc = crc32_update(0xFFFFFFFFu, lane, 88u);
        crc = ~crc32_update(crc, lane + HCTX_LANE_HEADER_LEN, variable_len);
        if (crc != read_u32(lane + 88)) {
            return HCTX_ERR_CRC;
        }
        if (all_tokens > SIZE_MAX - (size_t)token_count || all_payload > SIZE_MAX - (size_t)payload_len) {
            return HCTX_ERR_LIMIT;
        }
        all_tokens += (size_t)token_count;
        all_payload += (size_t)payload_len;
        offset += lane_len;
    }
    if (offset != body_len) {
        return HCTX_ERR_TRAILING;
    }
    if (summary != NULL) {
        summary->generation = read_u32(data + 52);
        summary->sequence_cutoff = sequence_cutoff;
        summary->token_budget = read_u32(data + 24);
        summary->breath_q1e6 = (int32_t)read_u32(data + 28);
        summary->radius_q1e6 = (int32_t)read_u32(data + 32);
        summary->lane_count = lane_count;
        summary->body_len = body_len;
        summary->token_count = all_tokens;
        summary->payload_bytes = all_payload;
    }
    return HCTX_OK;
}

const char *hctx_error_string(int code) {
    switch (code) {
        case HCTX_OK:
            return "ok";
        case HCTX_ERR_TRUNCATED:
            return "truncated input";
        case HCTX_ERR_HEADER:
            return "invalid header";
        case HCTX_ERR_LIMIT:
            return "declared limit exceeded";
        case HCTX_ERR_CRC:
            return "CRC mismatch";
        case HCTX_ERR_LANE:
            return "invalid lane";
        case HCTX_ERR_ORDER:
            return "lane IDs are not strictly ascending";
        case HCTX_ERR_TRAILING:
            return "length mismatch or trailing bytes";
        default:
            return "unknown error";
    }
}
