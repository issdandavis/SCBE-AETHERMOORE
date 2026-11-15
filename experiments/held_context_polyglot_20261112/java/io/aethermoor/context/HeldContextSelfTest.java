package io.aethermoor.context;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Arrays;

/** Small command surface used by the cross-language golden-vector verifier. */
public final class HeldContextSelfTest {
    private static final long MAX_FILE_BYTES = HeldContextPacket.MAX_BODY_LEN + HeldContextPacket.HEADER_LEN;

    private HeldContextSelfTest() {}

    public static void main(String[] args) throws Exception {
        if (!((args.length == 2 && args[0].equals("validate")) ||
                (args.length == 3 && args[0].equals("roundtrip")))) {
            System.err.println("usage: HeldContextSelfTest validate INPUT | roundtrip INPUT OUTPUT");
            System.exit(2);
        }
        Path input = Path.of(args[1]);
        if (Files.size(input) > MAX_FILE_BYTES) throw new IllegalArgumentException("input exceeds v1 limit");
        byte[] raw = Files.readAllBytes(input);
        HeldContextPacket packet = HeldContextPacket.decode(raw);
        byte[] encoded = packet.encode();
        if (!Arrays.equals(raw, encoded)) throw new IllegalStateException("Java round trip changed canonical bytes");
        if (args.length == 3) {
            Files.write(Path.of(args[2]), encoded);
        } else {
            System.out.printf("VALID bytes=%d generation=%d lanes=%d%n", raw.length, packet.generation,
                    packet.lanes.size());
        }
    }
}
