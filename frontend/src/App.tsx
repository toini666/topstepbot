import { useState, useEffect, useMemo } from 'react';
import type { Order } from './types';
import { useTopStep } from './hooks/useTopStep';
import { Activity, CheckCircle, TrendingUp, DollarSign, Settings, AlertTriangle, X, Terminal, ChevronDown, ChevronRight, FileText, Copy, Layers, Power, RefreshCw, Calendar as CalendarIcon } from 'lucide-react';
import axios from 'axios';
import { format } from 'date-fns';
import { Toaster, toast } from 'sonner';
import { ConfirmationModal } from './components/ConfirmationModal';
import { ConfigModal } from './components/ConfigModal';
import { MockWebhookModal } from './components/MockWebhookModal';
import { StrategiesManager } from './components/StrategiesManager';
import { Calendar } from './components/Calendar';
import { RiskInput } from './components/RiskInput';
import ReconciliationModal from './components/ReconciliationModal';
import { aggregateTrades } from './utils/tradeAggregator';
import { API_BASE } from './config';

function App() {
  const { trades, logs, accounts, positions, orders, historicalTrades, selectedAccountId, setSelectedAccountId, connect, logout, loadMoreLogs, isConnected, loading, selectedAccountSettings, toggleAccountTrading, config, updateConfig, historyFilter, setHistoryFilter, marketStatus, strategies, updateAccountSettings, accountSettings, ordersByAccount, positionsByAccount, previewReconciliation, applyReconciliation } = useTopStep();
  const [activeTab, setActiveTab] = useState<'trading' | 'logs' | 'strategies' | 'calendar'>('trading');
  const [expandedLogs, setExpandedLogs] = useState<Set<number>>(new Set());
  const [selectedStrategyFilter, setSelectedStrategyFilter] = useState<string>('ALL');
  const [strategyDropdownOpen, setStrategyDropdownOpen] = useState(false);

  // Reconciliation Modal State
  const [reconcileModalOpen, setReconcileModalOpen] = useState(false);
  const [reconcileLoading, setReconcileLoading] = useState(false);
  const [reconcileChanges, setReconcileChanges] = useState<any[]>([]);
  const [reconcileSummary, setReconcileSummary] = useState({ trades_to_close: 0, pnl_updates: 0, total_pnl_change: 0 });

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as HTMLElement;
      if (strategyDropdownOpen && !target.closest('.group-strategy-selector')) {
        setStrategyDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [strategyDropdownOpen]);

  const toggleLog = (id: number) => {
    const newSet = new Set(expandedLogs);
    if (newSet.has(id)) {
      newSet.delete(id);
    } else {
      newSet.add(id);
    }
    setExpandedLogs(newSet);
  };



  // Map Strategy + Timeframe from Local Trades
  const tradeInfoMap = useMemo(() => {
    const map = new Map<string, { strategy: string; timeframe?: string }>();
    trades.forEach(t => {
      if (t.topstep_order_id && t.strategy) {
        map.set(String(t.topstep_order_id), {
          strategy: t.strategy,
          timeframe: t.timeframe
        });
      }
    });
    return map;
  }, [trades]);

  // Enrich Historical Trades with Strategy + Timeframe (if from TopStep API)
  // Note: When using internal Trade table, data is already complete
  const enrichedHistory = useMemo(() => {
    return historicalTrades.map(ht => {
      // If already aggregated from internal table, use as-is
      if ((ht as any).isAggregated) {
        return ht;
      }
      // Otherwise enrich from tradeInfoMap (legacy TopStep API path)
      const info = tradeInfoMap.get(String(ht.orderId));
      return {
        ...ht,
        strategy: info?.strategy || 'RobReversal',
        timeframe: info?.timeframe
      };
    });
  }, [historicalTrades, tradeInfoMap]);

  // Aggregate Trades for display
  // - If data is from internal Trade table (isAggregated=true), map directly
  // - If data is from TopStep API, use aggregateTrades() to combine
  const aggregatedTrades = useMemo(() => {
    const firstTrade = enrichedHistory[0];
    if (firstTrade && (firstTrade as any).isAggregated) {
      // Data from internal Trade table - already aggregated, just map to display format
      return enrichedHistory.map(t => ({
        id: t.id,
        symbol: t.contractId,
        side: (String(t.side) === '0' || String(t.side).toUpperCase() === 'BUY' || String(t.side).toUpperCase() === 'LONG') ? 'LONG' : 'SHORT' as 'LONG' | 'SHORT',
        size: t.size,
        entryTime: t.creationTimestamp,
        exitTime: (t as any).exitTime || t.creationTimestamp,
        entryPrice: (t as any).entryPrice || t.price,
        exitPrice: (t as any).exitPrice || t.price,
        pnl: t.profitAndLoss || 0,
        fees: t.fees || 0,
        strategy: t.strategy,
        timeframe: t.timeframe
      }));
    }
    // Fallback to legacy aggregation for TopStep API data
    return aggregateTrades(enrichedHistory);
  }, [enrichedHistory]);

  const isMarketOpen = marketStatus.is_open;
  // Optional: We can also show marketStatus.reason if needed in UI

  // Calculate Daily PnL
  const calculatedDailyPnl = historicalTrades
    .filter(trade => {
      const tradeDate = new Date(trade.creationTimestamp);
      const today = new Date();
      return tradeDate.getDate() === today.getDate() &&
        tradeDate.getMonth() === today.getMonth() &&
        tradeDate.getFullYear() === today.getFullYear();
    })
    .reduce((acc, trade) => acc + (trade.profitAndLoss || 0) - (trade.fees || 0), 0);

  // Modal State
  const [modalOpen, setModalOpen] = useState(false);
  const [configModalOpen, setConfigModalOpen] = useState(false);
  const [mockModalOpen, setMockModalOpen] = useState(false);
  const [accountDropdownOpen, setAccountDropdownOpen] = useState(false);

  const [modalConfig, setModalConfig] = useState<{
    title: string;
    message: string;
    type: 'danger' | 'info';
    action: () => void;
    confirmText?: string;
  }>({ title: '', message: '', type: 'info', action: () => { } });

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as HTMLElement;
      if (accountDropdownOpen && !target.closest('.group-account-selector')) {
        setAccountDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [accountDropdownOpen]);



  const handleClosePosition = async (contractId: string) => {
    setModalConfig({
      title: 'Close Position',
      message: 'Are you sure you want to close this position manually?',
      type: 'danger',
      confirmText: 'Close Position',
      action: async () => {
        try {
          if (!selectedAccountId) return;
          const res = await axios.post(`${API_BASE}/dashboard/positions/close`, { contract_id: contractId });
          if (!res.data.success) {
            toast.error("Failed: " + res.data.message);
          } else {
            toast.success("Position Closed Successfully");
          }
        } catch (e) {
          console.error(e);
          toast.error("Error closing position");
        }
      }
    });
    setModalOpen(true);
  };

  const handlePanic = async () => {
    setModalConfig({
      title: 'FLATTEN & CANCEL ALL',
      message: 'WARNING: This will immediately CLOSE all open positions and CANCEL all pending orders for this account. Are you absolutely sure?',
      type: 'danger',
      confirmText: 'FLATTEN ACCOUNT',
      action: async () => {
        try {
          if (!selectedAccountId) return;
          const res = await axios.post(`${API_BASE}/dashboard/account/${selectedAccountId}/flatten`);
          if (!res.data.success) {
            toast.error("Failed: " + res.data.message);
          } else {
            toast.success("Account Flattened Successfully");
          }
        } catch (e) {
          console.error(e);
          toast.error("Error flattening account");
        }
      }
    });
    setModalOpen(true);
  };

  const handleReconcile = async () => {
    if (!selectedAccountId) return;
    setReconcileLoading(true);
    setReconcileModalOpen(true);

    const result = await previewReconciliation(selectedAccountId);
    if (result.success) {
      setReconcileChanges(result.proposed_changes || []);
      setReconcileSummary(result.summary || { trades_to_close: 0, pnl_updates: 0, total_pnl_change: 0 });
    }
    setReconcileLoading(false);
  };

  const handleApplyReconcile = async () => {
    if (!selectedAccountId) return;
    await applyReconciliation(selectedAccountId, reconcileChanges);
    setReconcileModalOpen(false);
    setReconcileChanges([]);
  };

  const handleDisconnect = () => {
    setModalConfig({
      title: 'Disconnect',
      message: 'Are you sure you want to disconnect?',
      type: 'info',
      confirmText: 'Disconnect',
      action: logout
    });
    setModalOpen(true);
  };

  if (loading && trades.length === 0 && accounts.length === 0) return <div className="h-screen flex items-center justify-center bg-slate-950 text-white">Loading...</div>;

  const currentAccount = accounts.find(a => a.id === selectedAccountId);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-8 font-sans">

      {/* HEADER */}
      <header className="max-w-7xl mx-auto mb-6 flex justify-between items-center bg-slate-900/50 p-6 rounded-2xl border border-slate-800">
        <div className="flex items-center gap-4">
          <img src="/robot_favicon.png" alt="Bot Logo" className="w-12 h-12 rounded-xl" />
          <div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-indigo-400 bg-clip-text text-transparent">TopStep Bot Toini666</h1>
            <div className="flex items-center gap-2 mt-2 flex-wrap">
              <div className="flex items-center gap-2 bg-slate-800/50 px-3 py-1 rounded-full border border-slate-700/50 text-xs text-slate-400">
                <span>Status:</span>
                <span className={`font-mono font-bold ${isConnected ? 'text-green-400' : 'text-orange-400'}`}>{isConnected ? 'ONLINE' : 'DISCONNECTED'}</span>
              </div>
              <div className="flex items-center gap-2 bg-slate-800/50 px-3 py-1 rounded-full border border-slate-700/50 text-xs text-slate-400">
                <span>Market:</span>
                <span className={`font-mono font-bold ${isMarketOpen ? 'text-blue-400' : 'text-slate-500'}`}>{isMarketOpen ? 'OPEN' : 'CLOSED'}</span>
              </div>
              {isMarketOpen && marketStatus.current_session && (
                <div className="flex items-center gap-2 bg-slate-800/50 px-3 py-1 rounded-full border border-slate-700/50 text-xs text-slate-400">
                  <span>Session:</span>
                  <span className="font-mono font-bold text-amber-400">{marketStatus.current_session}</span>
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-8">
          {!isConnected && (
            <button
              onClick={connect}
              disabled={loading}
              className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-6 rounded-xl transition-all flex items-center gap-2 shadow-lg shadow-blue-900/20"
            >
              {loading ? "Connecting..." : "Connect TopStep"}
            </button>
          )}

          {isConnected && (
            <div className="flex items-center gap-2">
              <div className="bg-slate-900 border border-slate-800 p-2 rounded-xl min-w-[200px] flex flex-col justify-center relative group-account-selector">
                <p className="text-slate-400 text-xs uppercase tracking-wider mb-1 ml-1">Connected Account</p>
                <button
                  onClick={() => accounts.length > 0 && setAccountDropdownOpen(!accountDropdownOpen)}
                  className="w-full flex items-center justify-between text-left px-1 focus:outline-none"
                  disabled={accounts.length === 0}
                >
                  <span className="text-white font-mono text-sm truncate mr-2">
                    {currentAccount ? `${currentAccount.name} (${currentAccount.id})` : 'Select Account'}
                  </span>
                  <ChevronDown className={`w-4 h-4 text-slate-500 transition-transform duration-200 ${accountDropdownOpen ? 'rotate-180' : ''}`} />
                </button>
                {accountDropdownOpen && accounts.length > 0 && (
                  <div className="absolute top-full left-0 mt-2 w-full bg-slate-800 border border-slate-700 rounded-xl shadow-xl overflow-hidden z-20">
                    <div className="max-h-60 overflow-y-auto custom-scrollbar">
                      {accounts.map((acc) => (
                        <button
                          key={acc.id}
                          onClick={() => {
                            setSelectedAccountId(acc.id);
                            setAccountDropdownOpen(false);
                          }}
                          className={`w-full text-left px-4 py-2 flex items-center justify-between transition-colors hover:bg-slate-700/50 ${acc.id === selectedAccountId
                            ? 'bg-indigo-500/10 text-indigo-400'
                            : 'text-slate-300'
                            }`}
                        >
                          <div className="flex items-center gap-2 truncate">
                            {/* Trading Status Icon */}
                            <div className={`p-0.5 rounded-full ${accountSettings[acc.id]?.trading_enabled ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-500'}`} title={accountSettings[acc.id]?.trading_enabled ? "Trading ON" : "Trading OFF"}>
                              <Power className="w-3 h-3" />
                            </div>
                            <span className="font-mono text-xs truncate">{acc.name} ({acc.id})</span>
                          </div>
                          {acc.id === selectedAccountId && <CheckCircle className="w-3 h-3 flex-shrink-0" />}
                        </button>
                      ))}
                    </div>

                    {/* Disconnect Option */}
                    <div className="border-t border-slate-700 mt-1 pt-1 bg-slate-900/50">
                      <button
                        onClick={() => {
                          setAccountDropdownOpen(false);
                          handleDisconnect();
                        }}
                        className="w-full text-left px-4 py-2 flex items-center gap-2 text-red-400 hover:text-red-300 hover:bg-red-500/10 transition-colors"
                      >
                        <div className="p-0.5 rounded-full bg-red-500/10">
                          <Power className="w-3 h-3" />
                        </div>
                        <span className="font-bold text-xs">Disconnect</span>
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          <div className="h-8 w-px bg-slate-800" />

          {/* Stats */}
          <div className="flex gap-8">
            <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl min-w-[150px] flex flex-col justify-between">
              <p className="text-slate-400 text-xs uppercase tracking-wider mb-1">Daily P&L (Realized)</p>
              <div className="flex items-center gap-2">
                <DollarSign className={`w-5 h-5 ${calculatedDailyPnl >= 0 ? 'text-green-400' : 'text-red-400'}`} />
                <span className={`text-2xl font-mono font-bold ${calculatedDailyPnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {calculatedDailyPnl.toFixed(2)}
                </span>
              </div>
            </div>
            <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl min-w-[150px] flex flex-col justify-between">
              <p className="text-slate-400 text-xs uppercase tracking-wider mb-1">Active Trades</p>
              <div className="flex items-center gap-2">
                <Activity className="w-5 h-5 text-blue-400" />
                <span className="text-2xl font-mono font-bold text-white">
                  {positions.length}
                </span>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* WARNING: ORPHANED ORDERS (ALL ACCOUNTS) */}
      {(() => {
        // Detect orphaned orders across ALL accounts
        const orphanedOrders: Array<Order & { accountName: string }> = [];

        for (const account of accounts) {
          const accountOrders = ordersByAccount[account.id] || [];
          const accountPositions = positionsByAccount[account.id] || [];

          for (const order of accountOrders) {
            if ((order.status === 1 || order.status === 6) &&
              !accountPositions.some(p => p.contractId === order.contractId)) {
              orphanedOrders.push({ ...order, accountName: account.name });
            }
          }
        }

        if (orphanedOrders.length > 0) {
          return (
            <div className="max-w-7xl mx-auto mb-6 bg-yellow-500/10 border border-yellow-500/20 rounded-xl p-4 flex items-center gap-4 animate-fade-in">
              <div className="bg-yellow-500/20 p-2 rounded-lg shrink-0">
                <AlertTriangle className="w-6 h-6 text-yellow-500" />
              </div>
              <div className="flex-1">
                <h3 className="text-yellow-500 font-bold mb-1">Warning: Active Orders without Position</h3>
                <p className="text-yellow-200/80 text-sm">
                  You have <strong>{orphanedOrders.length}</strong> working order(s) for contracts where you have no open position.
                  These orders may execute unexpectedly.
                </p>
                <div className="flex flex-wrap gap-2 mt-2">
                  {orphanedOrders.map(o => (
                    <span key={`${o.accountId}-${o.id}`} className="text-xs bg-yellow-900/50 text-yellow-200 px-2 py-1 rounded font-mono border border-yellow-700/50">
                      {o.symbolId} ({o.side === 0 ? 'BUY' : 'SELL'}) <span className="text-yellow-400">@{o.accountName}</span>
                    </span>
                  ))}
                </div>
              </div>
            </div>
          );
        }
        return null;
      })()}

      {/* MENU BAR */}
      <nav className="max-w-7xl mx-auto mb-6 flex gap-4">
        <button
          onClick={() => setActiveTab('trading')}
          className={`px-6 py-3 rounded-xl font-bold text-sm flex items-center gap-2 transition-all ${activeTab === 'trading'
            ? 'bg-blue-600 text-white shadow-lg shadow-blue-900/20'
            : 'bg-slate-900/50 text-slate-400 hover:text-white hover:bg-slate-800'
            }`}
        >
          <Activity className="w-4 h-4" />
          Trading
        </button>
        <button
          onClick={() => setActiveTab('logs')}
          className={`px-6 py-3 rounded-xl font-bold text-sm flex items-center gap-2 transition-all ${activeTab === 'logs'
            ? 'bg-blue-600 text-white shadow-lg shadow-blue-900/20'
            : 'bg-slate-900/50 text-slate-400 hover:text-white hover:bg-slate-800'
            }`}
        >
          <FileText className="w-4 h-4" />
          Logs
        </button>
        <button
          onClick={() => setActiveTab('strategies')}
          className={`px-6 py-3 rounded-xl font-bold text-sm flex items-center gap-2 transition-all ${activeTab === 'strategies'
            ? 'bg-blue-600 text-white shadow-lg shadow-blue-900/20'
            : 'bg-slate-900/50 text-slate-400 hover:text-white hover:bg-slate-800'
            }`}
        >
          <Layers className="w-4 h-4" />
          Strategies
        </button>

        <div className="ml-auto flex gap-4">
          <button
            onClick={() => setMockModalOpen(true)}
            className="px-6 py-3 rounded-xl font-bold text-sm flex items-center gap-2 transition-all bg-indigo-500/10 text-indigo-400 hover:bg-indigo-500/20 hover:text-indigo-300 border border-indigo-500/20"
          >
            <Terminal className="w-4 h-4" />
            Mock API
          </button>

          <button
            onClick={() => setActiveTab('calendar')}
            className={`px-6 py-3 rounded-xl font-bold text-sm flex items-center gap-2 transition-all ${activeTab === 'calendar'
              ? 'bg-blue-600 text-white shadow-lg shadow-blue-900/20'
              : 'bg-slate-900/50 text-slate-400 hover:text-white hover:bg-slate-800'
              }`}
          >
            <CalendarIcon className="w-4 h-4" />
            Calendar
          </button>

          <button
            onClick={() => setConfigModalOpen(true)}
            className="px-6 py-3 rounded-xl font-bold text-sm flex items-center gap-2 transition-all bg-slate-900/50 text-slate-400 hover:text-white hover:bg-slate-800"
          >
            <Settings className="w-4 h-4" />
            Settings
          </button>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto space-y-8">

        {/* TRADING TAB */}
        {activeTab === 'trading' && (
          <div className="space-y-8 animate-fade-in">
            {/* Top Row: Positions & Account Details */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">

              {/* Open Positions */}
              <section className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6 flex flex-col lg:col-span-2">
                <div className="flex justify-between items-start mb-6">
                  <h2 className="text-xl font-semibold flex items-center gap-2">
                    <Activity className="w-5 h-5 text-indigo-400" />
                    Open Positions
                  </h2>
                  <button
                    onClick={handlePanic}
                    className="flex items-center gap-2 bg-red-500/10 hover:bg-red-500/20 text-red-500 font-bold py-2 px-4 rounded-lg transition-all border border-red-500/20 text-xs"
                    title="Flatten & Cancel All"
                  >
                    <AlertTriangle className="w-4 h-4" />
                    Flatten & Cancel All
                  </button>
                </div>

                <div className="overflow-x-auto flex-1">
                  <table className="w-full text-sm text-left">
                    <thead className="text-slate-500 border-b border-slate-800 uppercase text-xs">
                      <tr>
                        <th className="py-3 px-4">Contract</th>
                        <th className="py-3 px-4">Strategy</th>
                        <th className="py-3 px-4 text-center">Side</th>
                        <th className="py-3 px-4 text-center">Qty</th>
                        <th className="py-3 px-4 text-right">Entry</th>
                        <th className="py-3 px-4 text-right">Current</th>
                        <th className="py-3 px-4 text-right">PnL</th>
                        <th className="py-3 px-4 text-center">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/50">
                      {positions.map((pos) => {
                        // Find matching trade for strategy info
                        const matchingTrade = trades.find(t =>
                          t.ticker && pos.contractId &&
                          pos.contractId.toUpperCase().includes(t.ticker.replace('1!', '').replace('2!', '').toUpperCase()) &&
                          t.status === 'OPEN'
                        );
                        const strat = matchingTrade ? strategies.find(s => s.tv_id === matchingTrade.strategy) : null;
                        const stratDisplay = strat?.name || matchingTrade?.strategy || '-';
                        const tf = matchingTrade?.timeframe;

                        return (
                          <tr key={pos.id} className="hover:bg-slate-800/30 transition-colors">
                            <td className="py-3 px-4 font-bold text-white">{pos.contractId}</td>
                            <td className="py-3 px-4 text-violet-300 font-mono text-xs">
                              {tf ? `${stratDisplay} (${tf})` : stratDisplay}
                            </td>
                            <td className="py-3 px-4 text-center">
                              <span className={`px-2 py-1 rounded-md text-xs font-bold ${pos.type === 1 ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                                {pos.type === 1 ? 'LONG' : 'SHORT'}
                              </span>
                            </td>
                            <td className="py-3 px-4 text-center font-mono">{pos.size}</td>
                            <td className="py-3 px-4 text-right font-mono">{pos.averagePrice.toFixed(2)}</td>
                            <td className="py-3 px-4 text-right font-mono text-slate-400">
                              {pos.currentPrice ? pos.currentPrice.toFixed(2) : '-'}
                            </td>
                            <td className={`py-3 px-4 text-right font-mono font-bold ${pos.unrealizedPnl === undefined || pos.unrealizedPnl === null
                              ? 'text-slate-500'
                              : pos.unrealizedPnl >= 0
                                ? 'text-green-400'
                                : 'text-red-400'
                              }`}>
                              {pos.unrealizedPnl !== undefined && pos.unrealizedPnl !== null
                                ? `$${pos.unrealizedPnl.toFixed(2)}`
                                : '-'}
                            </td>
                            <td className="py-3 px-4 text-center">
                              <button
                                onClick={() => handleClosePosition(pos.contractId)}
                                className="p-1 hover:bg-red-500/20 text-red-400 rounded transition-colors"
                                title="Close Position"
                              >
                                <X className="w-4 h-4" />
                              </button>
                            </td>
                          </tr>
                        );
                      })}
                      {positions.length === 0 && (
                        <tr>
                          <td colSpan={8} className="py-8 text-center text-slate-500 italic">No open positions.</td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </section>

              {/* Account Details */}
              <section className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6 flex flex-col h-full lg:col-span-1">
                <div className="flex justify-between items-center mb-6">
                  <h3 className="text-xl font-semibold text-slate-300 flex items-center gap-2">
                    <CheckCircle className="w-5 h-5 text-green-400" />
                    Account Details
                  </h3>
                  <div className="flex gap-2">
                    <button
                      onClick={() => selectedAccountId && toggleAccountTrading(selectedAccountId)}
                      disabled={!isConnected}
                      className={`text-xs font-bold px-3 py-1.5 rounded-lg transition-all ${!isConnected ? 'bg-slate-800 text-slate-500 cursor-not-allowed' :
                        selectedAccountSettings?.trading_enabled ? 'bg-green-500/20 text-green-400 hover:bg-green-500/30' : 'bg-red-500/20 text-red-400 hover:bg-red-500/30'
                        }`}
                    >
                      {selectedAccountSettings?.trading_enabled ? 'TRADING ON' : 'TRADING PAUSED'}
                    </button>
                  </div>
                </div>

                {currentAccount ? (
                  <div className="space-y-4 flex-1">
                    <div className="flex justify-between items-center">
                      <span className="text-slate-400 text-sm">Name</span>
                      <span className="font-mono text-white text-right">{currentAccount.name}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-slate-400 text-sm">ID</span>
                      <span className="font-mono text-slate-500">{currentAccount.id}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-slate-400 text-sm">Status</span>
                      <span className={`text-xs font-bold px-2 py-0.5 rounded ${currentAccount.simulated ? 'bg-orange-500/20 text-orange-400' : 'bg-blue-500/20 text-blue-400'}`}>
                        {currentAccount.simulated ? 'SIMULATED' : 'LIVE'}
                      </span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-slate-400 text-sm">Trading</span>
                      <span className={`text-xs font-bold px-2 py-0.5 rounded ${currentAccount.canTrade ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                        {currentAccount.canTrade ? 'ENABLED' : 'DISABLED'}
                      </span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-slate-400 text-sm">Risk / Trade</span>
                      <RiskInput
                        currentValue={selectedAccountSettings?.risk_per_trade ?? 200}
                        onSave={(val) => {
                          if (selectedAccountId) {
                            updateAccountSettings(selectedAccountId, { risk_per_trade: val });
                          }
                        }}
                      />
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-slate-400 text-sm">Max Contracts</span>
                      <RiskInput
                        currentValue={selectedAccountSettings?.max_contracts ?? 50}
                        onSave={(val) => {
                          if (selectedAccountId) {
                            updateAccountSettings(selectedAccountId, { max_contracts: Math.round(val) });
                          }
                        }}
                        prefix=""
                      />
                    </div>
                    <div className="flex justify-between items-center border-t border-slate-800 pt-4 mt-auto">
                      <span className="text-slate-400 text-sm">Balance</span>
                      <span className="font-mono text-white text-2xl font-bold">
                        ${currentAccount.balance?.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) ?? "0.00"}
                      </span>
                    </div>
                  </div>
                ) : (
                  <div className="text-slate-500 italic text-center py-10">No account selected</div>
                )}
              </section>

            </div>

            {/* Closed Trades */}
            <section className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6">
              <h2 className="text-xl font-semibold mb-6 flex items-center gap-2">
                <DollarSign className="w-5 h-5 text-emerald-400" />
                Closed Trades (History)
                <div className="ml-auto flex items-center gap-2">
                  {/* Reconcile Button */}
                  <button
                    onClick={handleReconcile}
                    disabled={!selectedAccountId || !isConnected || positions.length > 0}
                    className="p-2 rounded-lg text-slate-400 hover:text-indigo-400 hover:bg-indigo-500/10 transition-colors disabled:opacity-50 disabled:cursor-not-allowed border border-slate-700 hover:border-indigo-500/30 disabled:hover:text-slate-400 disabled:hover:bg-transparent disabled:hover:border-slate-700"
                    title={positions.length > 0 ? "Close all positions before reconciling" : "Sync with TopStep"}
                  >
                    <RefreshCw className="w-4 h-4" />
                  </button>

                  <div className="flex bg-slate-800 rounded-lg p-1 text-xs font-medium">
                    <button
                      onClick={() => setHistoryFilter('today')}
                      className={`px-3 py-1 rounded-md transition-all ${historyFilter === 'today' ? 'bg-indigo-500 text-white shadow' : 'text-slate-400 hover:text-slate-200'}`}
                    >
                      Today
                    </button>
                    <button
                      onClick={() => setHistoryFilter('week')}
                      className={`px-3 py-1 rounded-md transition-all ${historyFilter === 'week' ? 'bg-indigo-500 text-white shadow' : 'text-slate-400 hover:text-slate-200'}`}
                    >
                      7 Days
                    </button>

                    <div className="w-px h-4 bg-slate-700 mx-2 self-center"></div>

                    <div className="relative group-strategy-selector">
                      <button
                        onClick={() => setStrategyDropdownOpen(!strategyDropdownOpen)}
                        className="flex items-center gap-2 bg-slate-800 text-slate-300 text-xs font-medium px-3 py-1.5 rounded-md border border-slate-700 hover:bg-slate-700 hover:text-white transition-colors"
                      >
                        <span>{selectedStrategyFilter === 'ALL' ? 'All Strategies' : (strategies.find(s => s.tv_id === selectedStrategyFilter)?.name || selectedStrategyFilter)}</span>
                        <ChevronDown className={`w-3 h-3 transition-transform duration-200 ${strategyDropdownOpen ? 'rotate-180' : ''}`} />
                      </button>

                      {strategyDropdownOpen && (
                        <div className="absolute top-full right-0 mt-2 w-48 bg-slate-800 border border-slate-700 rounded-xl shadow-xl overflow-hidden z-20 animate-fade-in-down">
                          <div className="max-h-60 overflow-y-auto custom-scrollbar p-1">
                            <button
                              onClick={() => {
                                setSelectedStrategyFilter('ALL');
                                setStrategyDropdownOpen(false);
                              }}
                              className={`w-full text-left px-3 py-2 rounded-lg flex items-center justify-between transition-colors text-xs ${selectedStrategyFilter === 'ALL'
                                ? 'bg-indigo-500/10 text-indigo-400'
                                : 'text-slate-300 hover:bg-slate-700/50'
                                }`}
                            >
                              <span>All Strategies</span>
                              {selectedStrategyFilter === 'ALL' && <CheckCircle className="w-3 h-3" />}
                            </button>
                            {[...new Set(aggregatedTrades.map(t => t.strategy).filter(Boolean))].map(strat => {
                              const stratInfo = strategies.find(s => s.tv_id === strat);
                              const displayName = stratInfo?.name || strat;
                              return (
                                <button
                                  key={strat}
                                  onClick={() => {
                                    setSelectedStrategyFilter(strat || '');
                                    setStrategyDropdownOpen(false);
                                  }}
                                  className={`w-full text-left px-3 py-2 rounded-lg flex items-center justify-between transition-colors text-xs ${selectedStrategyFilter === strat
                                    ? 'bg-indigo-500/10 text-indigo-400'
                                    : 'text-slate-300 hover:bg-slate-700/50'
                                    }`}
                                >
                                  <span>{displayName}</span>
                                  {selectedStrategyFilter === strat && <CheckCircle className="w-3 h-3" />}
                                </button>
                              );
                            })}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </h2>
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left">
                  <thead className="text-slate-500 border-b border-slate-800 uppercase text-xs">
                    <tr>
                      <th className="py-3 px-4">Entry Time</th>
                      <th className="py-3 px-4">Exit Time</th>
                      <th className="py-3 px-4">Strategy</th>
                      <th className="py-3 px-4">Symbol</th>
                      <th className="py-3 px-4 text-center">Side</th>
                      <th className="py-3 px-4 text-center">Qty</th>
                      <th className="py-3 px-4 text-right">Entry Price</th>
                      <th className="py-3 px-4 text-right">Exit Price</th>
                      <th className="py-3 px-4 text-right">Fees</th>
                      <th className="py-3 px-4 text-right">PnL</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/50">
                    {aggregatedTrades
                      .filter(t => selectedStrategyFilter === 'ALL' || t.strategy === selectedStrategyFilter)
                      .map((trade) => (
                        <tr key={trade.id} className="hover:bg-slate-800/30 transition-colors">
                          <td className="py-3 px-4 text-slate-500 font-mono text-xs">
                            {format(new Date(trade.entryTime), 'MM/dd HH:mm:ss')}
                          </td>
                          <td className="py-3 px-4 text-slate-500 font-mono text-xs">
                            {format(new Date(trade.exitTime), 'HH:mm:ss')}
                          </td>
                          <td className="py-3 px-4 text-violet-300 font-mono text-xs">
                            {(() => {
                              const strat = strategies.find(s => s.tv_id === trade.strategy);
                              const displayName = strat?.name || trade.strategy || '-';
                              const tf = (trade as any).timeframe;
                              return tf ? `${displayName} (${tf})` : displayName;
                            })()}
                          </td>
                          <td className="py-3 px-4 font-bold text-white">{trade.symbol}</td>
                          <td className="py-3 px-4 text-center">
                            <span className={`px-2 py-1 rounded-md text-xs font-bold ${trade.side === 'LONG' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                              {trade.side}
                            </span>
                          </td>
                          <td className="py-3 px-4 text-center font-mono">{trade.size}</td>
                          <td className="py-3 px-4 text-right font-mono">{trade.entryPrice.toFixed(2)}</td>
                          <td className="py-3 px-4 text-right font-mono">{trade.exitPrice.toFixed(2)}</td>
                          <td className="py-3 px-4 text-right font-mono text-slate-400">
                            {trade.fees ? `$${trade.fees.toFixed(2)}` : '-'}
                          </td>
                          <td className={`py-3 px-4 text-right font-mono font-bold ${trade.pnl > 0 ? 'text-green-400' :
                            trade.pnl < 0 ? 'text-red-400' : 'text-slate-500'
                            }`}>
                            {trade.pnl !== undefined && trade.pnl !== null ? `$${trade.pnl.toFixed(2)}` : '-'}
                          </td>
                        </tr>
                      ))}
                    {aggregatedTrades.length === 0 && (
                      <tr>
                        <td colSpan={9} className="py-8 text-center text-slate-500 italic">No closed trades found.</td>
                      </tr>
                    )}
                  </tbody>
                </table>

              </div>
            </section>

            {/* Order History */}
            <section className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6">
              <h2 className="text-xl font-semibold mb-6 flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-indigo-400" />
                Order History
                <div className="ml-auto flex bg-slate-800 rounded-lg p-1 text-xs font-medium">
                  <button
                    onClick={() => setHistoryFilter('today')}
                    className={`px-3 py-1 rounded-md transition-all ${historyFilter === 'today' ? 'bg-indigo-500 text-white shadow' : 'text-slate-400 hover:text-slate-200'}`}
                  >
                    Today
                  </button>
                  <button
                    onClick={() => setHistoryFilter('week')}
                    className={`px-3 py-1 rounded-md transition-all ${historyFilter === 'week' ? 'bg-indigo-500 text-white shadow' : 'text-slate-400 hover:text-slate-200'}`}
                  >
                    7 Days
                  </button>
                </div>
              </h2>
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left">
                  <thead className="text-slate-500 border-b border-slate-800 uppercase text-xs">
                    <tr>
                      <th className="py-3 px-4">Time</th>
                      <th className="py-3 px-4">Symbol</th>
                      <th className="py-3 px-4 text-center">Side</th>
                      <th className="py-3 px-4 text-center">Qty</th>
                      <th className="py-3 px-4 text-center">Type</th>
                      <th className="py-3 px-4 text-right">Stop</th>
                      <th className="py-3 px-4 text-right">Limit</th>
                      <th className="py-3 px-4 text-right">Filled</th>
                      <th className="py-3 px-4 text-center">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/50">
                    {[...orders].sort((a, b) => new Date(b.creationTimestamp).getTime() - new Date(a.creationTimestamp).getTime()).map((order) => (
                      <tr key={order.id} className="hover:bg-slate-800/30 transition-colors">
                        <td className="py-3 px-4 text-slate-500 font-mono text-xs">
                          {format(new Date(order.creationTimestamp), 'MM/dd HH:mm:ss')}
                        </td>
                        <td className="py-3 px-4 font-bold text-white">{order.symbolId}</td>
                        <td className="py-3 px-4 text-center">
                          <span className={`px-2 py-1 rounded-md text-xs font-bold ${order.side === 0 ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                            {order.side === 0 ? 'BUY' : 'SELL'}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-center font-mono">{order.size}</td>
                        <td className="py-3 px-4 text-center font-mono text-xs text-slate-400">
                          {['UNK', 'LMT', 'MKT', 'STL', 'STP', 'TRL'][order.type] || order.type}
                        </td>
                        <td className="py-3 px-4 text-right font-mono text-slate-400">
                          {order.stopPrice ? order.stopPrice.toFixed(2) : '-'}
                        </td>
                        <td className="py-3 px-4 text-right font-mono text-slate-400">
                          {order.limitPrice ? order.limitPrice.toFixed(2) : '-'}
                        </td>
                        <td className="py-3 px-4 text-right font-mono text-slate-400">
                          {order.filledPrice ? order.filledPrice.toFixed(2) : '-'}
                        </td>
                        <td className="py-3 px-4 text-center">
                          <span className={`px-2 py-1 rounded-md text-xs font-bold ${order.status === 2 ? 'bg-blue-500/20 text-blue-400' :
                            order.status === 3 ? 'bg-slate-700 text-slate-400' :
                              order.status === 1 ? 'bg-yellow-500/20 text-yellow-400' :
                                'bg-slate-800 text-slate-500'
                            }`}>
                            {['NONE', 'OPEN', 'FILLED', 'CXLD', 'EXP', 'REJ', 'PEND'][order.status] || order.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                    {orders.length === 0 && (
                      <tr>
                        <td colSpan={9} className="py-8 text-center text-slate-500 italic">No orders found.</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </section>
          </div >
        )
        }

        {/* LOGS TAB */}
        {
          activeTab === 'logs' && (
            <div className="animate-fade-in h-[calc(100vh-250px)] min-h-[500px]">
              <section className="bg-black/40 border border-slate-800 rounded-2xl overflow-hidden flex flex-col h-full">
                <div className="bg-slate-900 p-4 border-b border-slate-800 flex justify-between items-center">
                  <h3 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
                    <Terminal className="w-4 h-4" />
                    System Logs
                  </h3>
                  <div className="flex gap-2 items-center">
                    <div className="flex gap-2">
                      <span className="w-2.5 h-2.5 rounded-full bg-red-500"></span>
                      <span className="w-2.5 h-2.5 rounded-full bg-yellow-500"></span>
                      <span className="w-2.5 h-2.5 rounded-full bg-green-500"></span>
                    </div>
                  </div>
                </div>
                <div className="flex-1 overflow-y-auto p-4 font-mono text-xs space-y-2 custom-scrollbar font-medium">
                  {logs.map((log) => {
                    const isExpanded = expandedLogs.has(log.id);
                    const hasDetails = !!log.details;

                    return (
                      <div key={log.id} className={`flex flex-col hover:bg-slate-800/30 rounded px-2 -mx-2 transition-colors ${hasDetails ? 'cursor-pointer' : ''}`} onClick={() => hasDetails && toggleLog(log.id)}>
                        <div className="flex gap-3 p-0.5">
                          <span className={`text-slate-500 shrink-0 flex items-center gap-1 w-32`}>
                            {hasDetails && (
                              isExpanded ? <ChevronDown className="w-3 h-3 text-slate-400" /> : <ChevronRight className="w-3 h-3 text-slate-400" />
                            )}
                            {!hasDetails && <div className="w-3" />}
                            {format(new Date(log.timestamp), 'dd/MM HH:mm:ss')}
                          </span>
                          <span className={`shrink-0 w-16 ${log.level === 'ERROR' ? 'text-red-400' :
                            log.level === 'WARNING' ? 'text-yellow-400' :
                              'text-blue-300'
                            }`}>
                            [{log.level}]
                          </span>
                          <span className="text-slate-300 break-words flex-1">{log.message}</span>
                        </div>

                        {isExpanded && hasDetails && (
                          <div className="ml-10 mt-1 mb-2 relative group">
                            <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  const content = (() => {
                                    try {
                                      return JSON.stringify(JSON.parse(log.details || "{}"), null, 2);
                                    } catch (e) {
                                      return log.details;
                                    }
                                  })();
                                  if (content) {
                                    navigator.clipboard.writeText(content);
                                    toast.success("Log details copied!");
                                  }
                                }}
                                className="p-1 bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white rounded border border-slate-700 shadow-lg"
                                title="Copy to clipboard"
                              >
                                <Copy className="w-3 h-3" />
                              </button>
                            </div>
                            <div className="p-3 bg-slate-950/50 rounded-lg border border-slate-800/50 overflow-x-auto">
                              <pre className="text-[10px] text-slate-400 font-mono whitespace-pre-wrap">
                                {(() => {
                                  try {
                                    // Attempt to parse if stringified JSON
                                    return JSON.stringify(JSON.parse(log.details || "{}"), null, 2);
                                  } catch (e) {
                                    return log.details;
                                  }
                                })()}
                              </pre>
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                  {logs.length === 0 && <span className="text-slate-600">Waiting for logs...</span>}

                  <div className="pt-2 flex justify-center">
                    <button
                      className="text-slate-500 hover:text-white text-xs underline"
                      onClick={loadMoreLogs}
                    >
                      Load More Logs
                    </button>
                  </div>
                </div>
              </section>
            </div>
          )
        }

        {/* STRATEGIES TAB */}
        {activeTab === 'strategies' && <StrategiesManager selectedAccountId={selectedAccountId} selectedAccountName={currentAccount?.name} />}

        {/* CALENDAR TAB */}
        {activeTab === 'calendar' && <Calendar />}

        {/* Confirmation Modal */}
        <ConfirmationModal
          isOpen={modalOpen}
          onClose={() => setModalOpen(false)}
          onConfirm={modalConfig.action}
          title={modalConfig.title}
          message={modalConfig.message}
          type={modalConfig.type}
          confirmText={modalConfig.confirmText}
        />

        {/* Config Modal */}
        <ConfigModal
          isOpen={configModalOpen}
          onClose={() => setConfigModalOpen(false)}
          config={config}
          onSave={updateConfig}
        />

        {/* Mock Webhook Modal */}
        <MockWebhookModal
          isOpen={mockModalOpen}
          onClose={() => setMockModalOpen(false)}
        />

        {/* Reconciliation Modal */}
        <ReconciliationModal
          isOpen={reconcileModalOpen}
          onClose={() => {
            setReconcileModalOpen(false);
            setReconcileChanges([]);
          }}
          changes={reconcileChanges}
          summary={reconcileSummary}
          onApply={handleApplyReconcile}
          isLoading={reconcileLoading}
        />

        <Toaster theme="dark" position="top-right" richColors />
      </main>

      <footer className="max-w-7xl mx-auto mt-12 mb-8 text-center text-slate-500 text-sm font-mono opacity-50 hover:opacity-100 transition-opacity">
        top step trading bot made with love by toini666
      </footer>
    </div>
  );
}

export default App;
