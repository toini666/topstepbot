import type { HistoricalTrade, AggregatedTrade } from '../types';

export const aggregateTrades = (trades: HistoricalTrade[]): AggregatedTrade[] => {
    // 1. Sort by time ascending (oldest first) to ensure FIFO
    const sortedTrades = [...trades].sort((a, b) =>
        new Date(a.creationTimestamp).getTime() - new Date(b.creationTimestamp).getTime()
    );

    const openPositions: { [key: string]: HistoricalTrade[] } = {};
    const aggregated: AggregatedTrade[] = [];

    // Helper to normalize side (Handles '0', '1', 'Buy', 'Long' etc)
    const getSideStr = (s: any) => {
        const strVal = String(s).toUpperCase().trim();
        // 0 = Buy, 1 = Sell (Standard Topstep API for Orders/Trades)
        if (strVal === '0' || strVal === 'BUY' || strVal === 'LONG') return 'BUY';
        if (strVal === '1' || strVal === '2' || strVal === 'SELL' || strVal === 'SHORT') return 'SELL';
        return 'UNK';
    };

    for (const trade of sortedTrades) {
        const contractId = trade.contractId;
        // const strategy = trade.strategy || 'default';
        // const key = `${contractId}|${strategy}`;
        // REVERT to Contract ID only grouping to better handle SL/TP exits which might lack strategy label
        const key = contractId;

        // Ensure inventory exists
        if (!openPositions[key]) {
            openPositions[key] = [];
        }

        const inventory = openPositions[key];

        // Determine if this trade closes existing inventory
        // A trade is a CLOSE if there is inventory AND the side is opposite
        const firstOpen = inventory[0];
        const isOpposite = firstOpen && (getSideStr(firstOpen.side) !== getSideStr(trade.side));

        if (isOpposite) {
            // Processing CLOSE (Partial or Full)
            let remainingCloseSize = trade.size;
            let collectedFees = trade.fees || 0;

            // We might match multiple opens if strict FIFO
            let totalEntryCost = 0;
            let totalEntrySize = 0;
            let firstEntryTime = new Date().toISOString();
            let entrySideLabel: 'LONG' | 'SHORT' = 'LONG'; // Default
            let entryStrategy = 'default';
            let entryTimeframe = '';
            let matchCount = 0;

            while (remainingCloseSize > 0 && inventory.length > 0) {
                const openTrade = inventory[0]; // Oldest

                // Match Logic
                const matchSize = Math.min(openTrade.size, remainingCloseSize);

                // Capture Entry Details from the FIRST match
                // Logic: If Inventory has Side 'Buy', it was a Long position.
                if (matchCount === 0) {
                    firstEntryTime = openTrade.creationTimestamp;
                    const normalizedSide = getSideStr(openTrade.side);
                    entrySideLabel = normalizedSide === 'BUY' ? 'LONG' : 'SHORT';
                    entryStrategy = openTrade.strategy || 'default';
                    entryTimeframe = openTrade.timeframe || '';
                }

                // Accumulate Cost
                totalEntryCost += openTrade.price * matchSize;
                totalEntrySize += matchSize;

                // Accumulate Fees (Pro-rated)
                // Deduct from openTrade fees to avoid double counting if matched again
                const proRatedFee = (openTrade.fees || 0) * (matchSize / openTrade.size);
                collectedFees += proRatedFee;

                // Mutate Inventory
                openTrade.fees = (openTrade.fees || 0) - proRatedFee;
                openTrade.size -= matchSize;
                remainingCloseSize -= matchSize;
                matchCount++;

                if (openTrade.size <= 0) {
                    inventory.shift(); // Remove fully used
                }
            }

            // Create Aggregated Trade
            if (totalEntrySize > 0) {
                aggregated.push({
                    id: trade.id,
                    symbol: trade.contractId,
                    side: entrySideLabel,
                    size: totalEntrySize,
                    entryTime: firstEntryTime,
                    exitTime: trade.creationTimestamp,
                    entryPrice: totalEntryCost / totalEntrySize,
                    exitPrice: trade.price,
                    pnl: trade.profitAndLoss || 0,
                    fees: collectedFees,
                    strategy: entryStrategy,
                    timeframe: entryTimeframe
                });
            }

        } else {
            // OPEN
            // Add to inventory
            // Clone to avoid mutation issues if reused (though we validly mutate size above)
            inventory.push({ ...trade });
        }
    }

    // Return newest first
    return aggregated.reverse();
};
