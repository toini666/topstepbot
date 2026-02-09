import { useState, useEffect, useMemo } from 'react';
import { useTopStep } from './hooks/useTopStep';
import { Activity, FileText, Layers, Terminal, Settings, Calendar as CalendarIcon } from 'lucide-react';
import axios from 'axios';
import { Toaster, toast } from 'sonner';
import { ConfirmationModal } from './components/ConfirmationModal';
import { ConfigModal } from './components/ConfigModal';
import { MockWebhookModal } from './components/MockWebhookModal';
import { StrategiesManager } from './components/StrategiesManager';
import { Calendar } from './components/Calendar';
import ReconciliationModal from './components/ReconciliationModal';
import { aggregateTrades } from './utils/tradeAggregator';
import { API_BASE } from './config';
import { SetupWizard } from './components/SetupWizard';

// Dashboard Components
import {
  Header,
  PositionsTable,
  AccountDetails,
  TradesHistory,
  OrdersTable,
  LogsPanel,
  OrphanedOrdersWarning,
} from './components/dashboard';

function App() {
  const [isConfigured, setIsConfigured] = useState<boolean | null>(null);

  const checkSetup = () => {
    axios.get(`${API_BASE}/setup/status`)
      .then(res => setIsConfigured(res.data.configured))
      .catch(() => setIsConfigured(false));
  };

  useEffect(() => { checkSetup(); }, []);

  // Loading state — checking configuration
  if (isConfigured === null) {
    return (
      <div className="h-screen flex items-center justify-center bg-slate-950 text-white">
        <div className="flex flex-col items-center gap-4">
          <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-slate-400 text-sm">Checking configuration...</span>
        </div>
      </div>
    );
  }

  // Setup wizard — credentials not configured
  if (!isConfigured) {
    return <SetupWizard onComplete={checkSetup} />;
  }

  // Configured — render dashboard
  return <Dashboard />;
}

function Dashboard() {
  const {
    trades,
    logs,
    accounts,
    positions,
    orders,
    historicalTrades,
    selectedAccountId,
    setSelectedAccountId,
    connect,
    logout,
    loadMoreLogs,
    isConnected,
    loading,
    selectedAccountSettings,
    toggleAccountTrading,
    config,
    updateConfig,
    historyFilter,
    setHistoryFilter,
    marketStatus,
    strategies,
    updateAccountSettings,
    accountSettings,
    ordersByAccount,
    positionsByAccount,
    previewReconciliation,
    applyReconciliation
  } = useTopStep();

  const [activeTab, setActiveTab] = useState<'trading' | 'logs' | 'strategies' | 'calendar'>('trading');

  // Reconciliation Modal State
  const [reconcileModalOpen, setReconcileModalOpen] = useState(false);
  const [reconcileLoading, setReconcileLoading] = useState(false);
  const [reconcileChanges, setReconcileChanges] = useState<any[]>([]);
  const [reconcileSummary, setReconcileSummary] = useState({ trades_to_close: 0, pnl_updates: 0, total_pnl_change: 0 });

  // Modal State
  const [modalOpen, setModalOpen] = useState(false);
  const [configModalOpen, setConfigModalOpen] = useState(false);
  const [mockModalOpen, setMockModalOpen] = useState(false);

  const [modalConfig, setModalConfig] = useState<{
    title: string;
    message: string;
    type: 'danger' | 'info';
    action: () => void;
    confirmText?: string;
  }>({ title: '', message: '', type: 'info', action: () => { } });

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

  // Enrich Historical Trades with Strategy + Timeframe
  const enrichedHistory = useMemo(() => {
    return historicalTrades.map(ht => {
      if ((ht as any).isAggregated) {
        return ht;
      }
      const info = tradeInfoMap.get(String(ht.orderId));
      return {
        ...ht,
        strategy: info?.strategy || 'RobReversal',
        timeframe: info?.timeframe
      };
    });
  }, [historicalTrades, tradeInfoMap]);

  // Aggregate Trades for display
  const aggregatedTrades = useMemo(() => {
    const firstTrade = enrichedHistory[0];
    if (firstTrade && (firstTrade as any).isAggregated) {
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
    return aggregateTrades(enrichedHistory);
  }, [enrichedHistory]);

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

  const currentAccount = accounts.find(a => a.id === selectedAccountId);

  // === Event Handlers ===

  const handleClosePosition = async (contractId: string) => {
    setModalConfig({
      title: 'Close Position',
      message: 'Are you sure you want to close this position manually?',
      type: 'danger',
      confirmText: 'Close Position',
      action: async () => {
        try {
          if (!selectedAccountId) return;
          const res = await axios.post(`${API_BASE}/dashboard/positions/${selectedAccountId}/close`, { contract_id: contractId });
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

  const handleToggleTrading = () => {
    if (selectedAccountId) {
      toggleAccountTrading(selectedAccountId);
    }
  };

  const handleUpdateAccountSettings = (settings: any) => {
    if (selectedAccountId) {
      updateAccountSettings(selectedAccountId, settings);
    }
  };

  // Loading state
  if (loading && trades.length === 0 && accounts.length === 0) {
    return (
      <div className="h-screen flex items-center justify-center bg-slate-950 text-white" role="status" aria-busy="true">
        <div className="flex flex-col items-center gap-4">
          <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-slate-400 text-sm">Loading...</span>
        </div>
      </div>
    );
  }

  const tabs = [
    { key: 'trading' as const, label: 'Trading', icon: Activity },
    { key: 'logs' as const, label: 'Logs', icon: FileText },
    { key: 'strategies' as const, label: 'Strategies', icon: Layers },
  ];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-4 md:p-8 font-sans">

      {/* HEADER */}
      <Header
        isConnected={isConnected}
        loading={loading}
        connect={connect}
        logout={logout}
        accounts={accounts}
        selectedAccountId={selectedAccountId}
        setSelectedAccountId={setSelectedAccountId}
        accountSettings={accountSettings}
        currentAccount={currentAccount}
        marketStatus={marketStatus}
        dailyPnl={calculatedDailyPnl}
        activePositions={positions.length}
        onDisconnect={handleDisconnect}
      />

      {/* ORPHANED ORDERS WARNING */}
      <OrphanedOrdersWarning
        accounts={accounts}
        ordersByAccount={ordersByAccount}
        positionsByAccount={positionsByAccount}
      />

      {/* MENU BAR */}
      <nav className="max-w-7xl mx-auto mb-6 flex gap-2 md:gap-4 flex-wrap" role="tablist" aria-label="Main navigation">
        {tabs.map(tab => (
          <button
            key={tab.key}
            role="tab"
            aria-selected={activeTab === tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={activeTab === tab.key ? 'tab-btn-active' : 'tab-btn-inactive'}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}

        <div className="ml-auto flex gap-2 md:gap-4">
          <button
            onClick={() => setMockModalOpen(true)}
            className="tab-btn-inactive"
          >
            <Terminal className="w-4 h-4" />
            <span className="hidden sm:inline">Mock API</span>
          </button>

          <button
            role="tab"
            aria-selected={activeTab === 'calendar'}
            onClick={() => setActiveTab('calendar')}
            className={activeTab === 'calendar' ? 'tab-btn-active' : 'tab-btn-inactive'}
          >
            <CalendarIcon className="w-4 h-4" />
            <span className="hidden sm:inline">Calendar</span>
          </button>

          <button
            onClick={() => setConfigModalOpen(true)}
            className="tab-btn-inactive"
            aria-label="Open settings"
          >
            <Settings className="w-4 h-4" />
            <span className="hidden sm:inline">Settings</span>
          </button>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto space-y-8" role="tabpanel">

        {/* TRADING TAB */}
        {activeTab === 'trading' && (
          <div className="space-y-8 animate-fade-in">
            {/* Top Row: Positions & Account Details */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
              <PositionsTable
                positions={positions}
                trades={trades}
                strategies={strategies}
                onClosePosition={handleClosePosition}
                onFlattenAll={handlePanic}
              />

              <AccountDetails
                currentAccount={currentAccount}
                accountSettings={selectedAccountSettings ?? undefined}
                isConnected={isConnected}
                onToggleTrading={handleToggleTrading}
                onUpdateSettings={handleUpdateAccountSettings}
              />
            </div>

            {/* Closed Trades */}
            <TradesHistory
              trades={aggregatedTrades}
              strategies={strategies}
              historyFilter={historyFilter}
              setHistoryFilter={setHistoryFilter}
              onReconcile={handleReconcile}
              isReconcileDisabled={!selectedAccountId || !isConnected || positions.length > 0}
              reconcileTitle={positions.length > 0 ? "Close all positions before reconciling" : "Sync with TopStep"}
            />

            {/* Order History */}
            <OrdersTable
              orders={orders}
              historyFilter={historyFilter}
              setHistoryFilter={setHistoryFilter}
            />
          </div>
        )}

        {/* LOGS TAB */}
        {activeTab === 'logs' && (
          <LogsPanel logs={logs} loadMoreLogs={loadMoreLogs} />
        )}

        {/* STRATEGIES TAB */}
        {activeTab === 'strategies' && (
          <StrategiesManager
            selectedAccountId={selectedAccountId}
            selectedAccountName={currentAccount?.name}
          />
        )}

        {/* CALENDAR TAB */}
        {activeTab === 'calendar' && <Calendar />}

        {/* Modals */}
        <ConfirmationModal
          isOpen={modalOpen}
          onClose={() => setModalOpen(false)}
          onConfirm={modalConfig.action}
          title={modalConfig.title}
          message={modalConfig.message}
          type={modalConfig.type}
          confirmText={modalConfig.confirmText}
        />

        <ConfigModal
          isOpen={configModalOpen}
          onClose={() => setConfigModalOpen(false)}
          config={config}
          onSave={updateConfig}
        />

        <MockWebhookModal
          isOpen={mockModalOpen}
          onClose={() => setMockModalOpen(false)}
        />

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
