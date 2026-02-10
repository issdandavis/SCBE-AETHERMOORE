export declare class HealingCoordinator {
    private quick;
    private deep;
    handleFailure(failure: any): Promise<{
        quick: {
            success: boolean;
            actions: string[];
            branch: string;
        };
        deep: {
            plan: string[];
            branch: string;
        };
        decision: string;
    }>;
}
//# sourceMappingURL=coordinator.d.ts.map