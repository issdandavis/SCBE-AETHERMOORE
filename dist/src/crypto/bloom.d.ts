export declare class BloomFilter {
    private bits;
    private k;
    constructor(sizeBits?: number, hashes?: number);
    private hN;
    add(s: string): void;
    mightHave(s: string): boolean;
}
//# sourceMappingURL=bloom.d.ts.map