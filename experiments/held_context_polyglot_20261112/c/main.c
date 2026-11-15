#include "held_context.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_FILE_BYTES (16u * 1024u * 1024u + 64u)

static int read_file(const char *path, uint8_t **out, size_t *out_len) {
    FILE *file = fopen(path, "rb");
    long length;
    uint8_t *buffer;
    size_t read_count;
    if (file == NULL) {
        return 0;
    }
    if (fseek(file, 0, SEEK_END) != 0 || (length = ftell(file)) < 0 || (unsigned long)length > MAX_FILE_BYTES ||
        fseek(file, 0, SEEK_SET) != 0) {
        fclose(file);
        return 0;
    }
    buffer = (uint8_t *)malloc((size_t)length == 0u ? 1u : (size_t)length);
    if (buffer == NULL) {
        fclose(file);
        return 0;
    }
    read_count = fread(buffer, 1u, (size_t)length, file);
    if (fclose(file) != 0 || read_count != (size_t)length) {
        free(buffer);
        return 0;
    }
    *out = buffer;
    *out_len = (size_t)length;
    return 1;
}

static int write_file(const char *path, const uint8_t *data, size_t len) {
    FILE *file = fopen(path, "wb");
    size_t written;
    int close_result;
    int ok;
    if (file == NULL) {
        return 0;
    }
    written = fwrite(data, 1u, len, file);
    close_result = fclose(file);
    ok = written == len && close_result == 0;
    return ok;
}

int main(int argc, char **argv) {
    uint8_t *raw = NULL;
    size_t raw_len = 0u;
    hctx_summary summary;
    int result;
    if (!((argc == 3 && strcmp(argv[1], "validate") == 0) ||
          (argc == 4 && strcmp(argv[1], "roundtrip") == 0))) {
        fprintf(stderr, "usage: held-context-c validate INPUT | roundtrip INPUT OUTPUT\n");
        return 2;
    }
    if (!read_file(argv[2], &raw, &raw_len)) {
        fprintf(stderr, "ERROR: cannot read input\n");
        return 1;
    }
    result = hctx_validate(raw, raw_len, &summary);
    if (result != HCTX_OK) {
        fprintf(stderr, "ERROR: %s\n", hctx_error_string(result));
        free(raw);
        return 1;
    }
    if (argc == 4 && !write_file(argv[3], raw, raw_len)) {
        fprintf(stderr, "ERROR: cannot write output\n");
        free(raw);
        return 1;
    }
    if (argc == 3) {
        printf("VALID bytes=%zu generation=%u lanes=%u tokens=%zu payload=%zu\n", raw_len, summary.generation,
               (unsigned)summary.lane_count, summary.token_count, summary.payload_bytes);
    }
    free(raw);
    return 0;
}
