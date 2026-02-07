export declare class Feistel {
    private rounds;
    constructor(rounds?: number);
    private roundFunction;
    private xorBuffers;
    encrypt(data: Buffer, key: string): Buffer;
    decrypt(data: Buffer, key: string): Buffer;
}
//# sourceMappingURL=Feistel.d.ts.map