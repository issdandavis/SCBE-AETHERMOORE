package io.aethermoor.context;

import java.io.ByteArrayOutputStream;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.zip.CRC32;

/** Dependency-free portable codec for HeldContextPacket v1. */
public final class HeldContextPacket {
    public static final int HEADER_LEN = 64;
    public static final int LANE_HEADER_LEN = 96;
    public static final int Q_SCALE = 1_000_000;
    public static final long NO_EXPIRY = -1L; // Unsigned u64::MAX on the wire.
    public static final int MAX_BODY_LEN = 16 * 1024 * 1024;
    public static final int MAX_LANES = 4096;
    private static final int MAX_ROUTE_DIM = 256;
    private static final int MAX_TOKEN_COUNT = 1_048_576;
    private static final int MAX_PAYLOAD_LEN = 8 * 1024 * 1024;
    private static final int KNOWN_FLAGS = 7;

    public enum LaneKind {
        ROOT(0), LINGUISTIC(1), ROUTE(2), TOOL(3), SPEECH(4), GEOMETRY(5), RECEIPT(6), CUSTOM(7);

        private final int code;

        LaneKind(int code) {
            this.code = code;
        }

        static LaneKind fromCode(int code) {
            for (LaneKind value : values()) {
                if (value.code == code) return value;
            }
            throw new IllegalArgumentException("unknown lane kind");
        }
    }

    public enum EvidenceState {
        PRESENT(0), MISSING(1), NEUTRAL(2), SILENCE(3), ABSTAIN(4);

        private final int code;

        EvidenceState(int code) {
            this.code = code;
        }

        static EvidenceState fromCode(int code) {
            for (EvidenceState value : values()) {
                if (value.code == code) return value;
            }
            throw new IllegalArgumentException("unknown evidence state");
        }
    }

    public enum LaneRole {
        INDEPENDENT(0), DERIVED(1), CONTROL(2), OBSERVED(3), COMPUTED(4), PROVENANCE(5);

        private final int code;

        LaneRole(int code) {
            this.code = code;
        }

        static LaneRole fromCode(int code) {
            for (LaneRole value : values()) {
                if (value.code == code) return value;
            }
            throw new IllegalArgumentException("unknown lane role");
        }
    }

    public static final class Lane {
        public final int laneId;
        public final LaneKind kind;
        public final EvidenceState evidence;
        public final LaneRole role;
        public final int flags;
        public final int[] routeQ1e6;
        public final long[] tokenIds;
        public final byte[] payload;
        public final long expirySequence;
        public final byte[] canonicalValueId;
        public final byte[] sourceHash;

        public Lane(
                int laneId,
                LaneKind kind,
                EvidenceState evidence,
                LaneRole role,
                int flags,
                int[] routeQ1e6,
                long[] tokenIds,
                byte[] payload,
                long expirySequence,
                byte[] canonicalValueId,
                byte[] sourceHash) {
            this.laneId = laneId;
            this.kind = kind;
            this.evidence = evidence;
            this.role = role;
            this.flags = flags;
            this.routeQ1e6 = routeQ1e6.clone();
            this.tokenIds = tokenIds.clone();
            this.payload = payload.clone();
            this.expirySequence = expirySequence;
            this.canonicalValueId = canonicalValueId.clone();
            this.sourceHash = sourceHash.clone();
            validate();
        }

        private void validate() {
            require(laneId >= 0 && laneId <= 0xffff, "laneId must fit u16");
            require(kind != null && evidence != null && role != null, "lane enums are required");
            require((flags & ~KNOWN_FLAGS) == 0, "unknown lane flag bit");
            require(routeQ1e6.length <= MAX_ROUTE_DIM, "route dimension exceeds v1 limit");
            require(tokenIds.length <= MAX_TOKEN_COUNT, "token count exceeds v1 limit");
            require(payload.length <= MAX_PAYLOAD_LEN, "payload exceeds v1 limit");
            for (long tokenId : tokenIds) {
                require(tokenId >= 0 && tokenId <= 0xffff_ffffL, "token ID must fit u32");
            }
            require(canonicalValueId.length == 32, "canonicalValueId must be 32 bytes");
            require(sourceHash.length == 32, "sourceHash must be 32 bytes");
        }

        private byte[] encode() {
            validate();
            long variableLength = (long) routeQ1e6.length * 4L + (long) tokenIds.length * 4L + payload.length;
            require(variableLength <= Integer.MAX_VALUE, "lane length overflow");
            ByteBuffer variable = littleBuffer((int) variableLength);
            for (int value : routeQ1e6) variable.putInt(value);
            for (long value : tokenIds) variable.putInt((int) value);
            variable.put(payload);

            byte[] output = new byte[LANE_HEADER_LEN + (int) variableLength];
            ByteBuffer header = ByteBuffer.wrap(output).order(ByteOrder.LITTLE_ENDIAN);
            header.putShort((short) laneId);
            header.put((byte) kind.code);
            header.put((byte) evidence.code);
            header.put((byte) role.code);
            header.put((byte) flags);
            header.putShort((short) routeQ1e6.length);
            header.putInt(tokenIds.length);
            header.putInt(payload.length);
            header.putLong(expirySequence);
            header.put(canonicalValueId);
            header.put(sourceHash);
            byte[] variableBytes = variable.array();
            CRC32 crc = new CRC32();
            crc.update(output, 0, 88);
            crc.update(variableBytes);
            header.putInt(88, (int) crc.getValue());
            System.arraycopy(variableBytes, 0, output, LANE_HEADER_LEN, variableBytes.length);
            return output;
        }
    }

    public final byte[] packetId;
    public final long generation;
    public final long sequenceCutoff;
    public final long tokenBudget;
    public final int breathQ1e6;
    public final int radiusQ1e6;
    public final int flags;
    public final List<Lane> lanes;

    public HeldContextPacket(
            byte[] packetId,
            long generation,
            long sequenceCutoff,
            long tokenBudget,
            int breathQ1e6,
            int radiusQ1e6,
            int flags,
            List<Lane> lanes) {
        this.packetId = packetId.clone();
        this.generation = generation;
        this.sequenceCutoff = sequenceCutoff;
        this.tokenBudget = tokenBudget;
        this.breathQ1e6 = breathQ1e6;
        this.radiusQ1e6 = radiusQ1e6;
        this.flags = flags;
        this.lanes = Collections.unmodifiableList(new ArrayList<>(lanes));
        validate();
    }

    private void validate() {
        require(packetId.length == 16, "packetId must be 16 bytes");
        require(generation >= 0 && generation <= 0xffff_ffffL, "generation must fit u32");
        require(tokenBudget >= 0 && tokenBudget <= 0xffff_ffffL, "tokenBudget must fit u32");
        require(flags >= 0 && flags <= 0xff, "packet flags must fit u8");
        require(radiusQ1e6 >= 0 && radiusQ1e6 < Q_SCALE, "radius must remain inside unit ball");
        require(lanes.size() <= MAX_LANES, "lane count exceeds v1 limit");
        int previous = -1;
        for (Lane lane : lanes) {
            lane.validate();
            require(lane.laneId > previous, "lanes must have unique ascending lane IDs");
            if (lane.expirySequence != NO_EXPIRY) {
                require(Long.compareUnsigned(lane.expirySequence, sequenceCutoff) >= 0,
                        "packet contains a lane expired before sequence cutoff");
            }
            previous = lane.laneId;
        }
    }

    public byte[] encode() {
        validate();
        ByteArrayOutputStream body = new ByteArrayOutputStream();
        for (Lane lane : lanes) body.writeBytes(lane.encode());
        byte[] bodyBytes = body.toByteArray();
        require(bodyBytes.length <= MAX_BODY_LEN, "packet body exceeds v1 limit");
        byte[] output = new byte[HEADER_LEN + bodyBytes.length];
        ByteBuffer header = ByteBuffer.wrap(output).order(ByteOrder.LITTLE_ENDIAN);
        header.put(new byte[] {'H', 'C', 'T', 'X'});
        header.put((byte) 1);
        header.put((byte) flags);
        header.putShort((short) HEADER_LEN);
        header.putInt(bodyBytes.length);
        header.putShort((short) lanes.size());
        header.putShort((short) 0);
        header.putLong(sequenceCutoff);
        header.putInt((int) tokenBudget);
        header.putInt(breathQ1e6);
        header.putInt(radiusQ1e6);
        header.put(packetId);
        header.putInt((int) generation);
        header.putInt((int) crc32(bodyBytes, 0, bodyBytes.length));
        header.putInt((int) crc32(output, 0, 60));
        System.arraycopy(bodyBytes, 0, output, HEADER_LEN, bodyBytes.length);
        return output;
    }

    public static HeldContextPacket decode(byte[] raw) {
        require(raw != null && raw.length >= HEADER_LEN, "truncated packet header");
        ByteBuffer header = ByteBuffer.wrap(raw).order(ByteOrder.LITTLE_ENDIAN);
        byte[] magic = new byte[4];
        header.get(magic);
        int version = Byte.toUnsignedInt(header.get());
        int flags = Byte.toUnsignedInt(header.get());
        int headerLength = Short.toUnsignedInt(header.getShort());
        long bodyLengthLong = Integer.toUnsignedLong(header.getInt());
        int laneCount = Short.toUnsignedInt(header.getShort());
        int reserved = Short.toUnsignedInt(header.getShort());
        require(Arrays.equals(magic, new byte[] {'H', 'C', 'T', 'X'}) && version == 1 && headerLength == HEADER_LEN,
                "unsupported packet magic, version, or header length");
        require(reserved == 0, "packet reserved field must be zero");
        require(bodyLengthLong <= MAX_BODY_LEN && laneCount <= MAX_LANES, "declared dimensions exceed v1 limits");
        int bodyLength = (int) bodyLengthLong;
        require(raw.length == HEADER_LEN + bodyLength, "packet length does not match body length");
        long sequenceCutoff = header.getLong();
        long tokenBudget = Integer.toUnsignedLong(header.getInt());
        int breathQ1e6 = header.getInt();
        int radiusQ1e6 = header.getInt();
        byte[] packetId = new byte[16];
        header.get(packetId);
        long generation = Integer.toUnsignedLong(header.getInt());
        long bodyCrc = Integer.toUnsignedLong(header.getInt());
        long headerCrc = Integer.toUnsignedLong(header.getInt());
        require(crc32(raw, 0, 60) == headerCrc, "header CRC mismatch");
        require(crc32(raw, HEADER_LEN, bodyLength) == bodyCrc, "body CRC mismatch");

        List<Lane> lanes = new ArrayList<>(laneCount);
        int offset = HEADER_LEN;
        for (int index = 0; index < laneCount; index++) {
            require(raw.length - offset >= LANE_HEADER_LEN, "truncated lane header");
            ByteBuffer laneHeader = ByteBuffer.wrap(raw, offset, LANE_HEADER_LEN).order(ByteOrder.LITTLE_ENDIAN);
            int laneId = Short.toUnsignedInt(laneHeader.getShort());
            LaneKind kind = LaneKind.fromCode(Byte.toUnsignedInt(laneHeader.get()));
            EvidenceState evidence = EvidenceState.fromCode(Byte.toUnsignedInt(laneHeader.get()));
            LaneRole role = LaneRole.fromCode(Byte.toUnsignedInt(laneHeader.get()));
            int laneFlags = Byte.toUnsignedInt(laneHeader.get());
            int routeDim = Short.toUnsignedInt(laneHeader.getShort());
            long tokenCountLong = Integer.toUnsignedLong(laneHeader.getInt());
            long payloadLengthLong = Integer.toUnsignedLong(laneHeader.getInt());
            long expirySequence = laneHeader.getLong();
            byte[] canonical = new byte[32];
            byte[] source = new byte[32];
            laneHeader.get(canonical);
            laneHeader.get(source);
            long laneCrc = Integer.toUnsignedLong(laneHeader.getInt());
            int laneReserved = laneHeader.getInt();
            require(laneReserved == 0, "lane reserved field must be zero");
            require(routeDim <= MAX_ROUTE_DIM && tokenCountLong <= MAX_TOKEN_COUNT && payloadLengthLong <= MAX_PAYLOAD_LEN,
                    "declared lane dimensions exceed v1 limits");
            int tokenCount = (int) tokenCountLong;
            int payloadLength = (int) payloadLengthLong;
            long variableLengthLong = (long) routeDim * 4L + (long) tokenCount * 4L + payloadLength;
            require(variableLengthLong <= Integer.MAX_VALUE, "lane length overflow");
            int variableLength = (int) variableLengthLong;
            require(raw.length - offset - LANE_HEADER_LEN >= variableLength, "truncated lane variable data");
            CRC32 laneChecksum = new CRC32();
            laneChecksum.update(raw, offset, 88);
            laneChecksum.update(raw, offset + LANE_HEADER_LEN, variableLength);
            require(laneChecksum.getValue() == laneCrc, "lane CRC mismatch");
            ByteBuffer variable = ByteBuffer.wrap(raw, offset + LANE_HEADER_LEN, variableLength).order(ByteOrder.LITTLE_ENDIAN);
            int[] route = new int[routeDim];
            for (int routeIndex = 0; routeIndex < routeDim; routeIndex++) route[routeIndex] = variable.getInt();
            long[] tokens = new long[tokenCount];
            for (int tokenIndex = 0; tokenIndex < tokenCount; tokenIndex++) {
                tokens[tokenIndex] = Integer.toUnsignedLong(variable.getInt());
            }
            byte[] payload = new byte[payloadLength];
            variable.get(payload);
            lanes.add(new Lane(laneId, kind, evidence, role, laneFlags, route, tokens, payload, expirySequence,
                    canonical, source));
            offset += LANE_HEADER_LEN + variableLength;
        }
        require(offset == raw.length, "unclaimed bytes remain after final lane");
        return new HeldContextPacket(packetId, generation, sequenceCutoff, tokenBudget, breathQ1e6, radiusQ1e6, flags,
                lanes);
    }

    private static ByteBuffer littleBuffer(int size) {
        return ByteBuffer.allocate(size).order(ByteOrder.LITTLE_ENDIAN);
    }

    private static long crc32(byte[] bytes, int offset, int length) {
        CRC32 crc = new CRC32();
        crc.update(bytes, offset, length);
        return crc.getValue();
    }

    private static void require(boolean condition, String message) {
        if (!condition) throw new IllegalArgumentException(message);
    }
}
