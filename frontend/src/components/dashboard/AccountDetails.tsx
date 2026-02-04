/**
 * Account Details Panel Component
 * 
 * Displays account information, trading status, and risk settings.
 */

import { CheckCircle } from 'lucide-react';
import type { Account, AccountSettings as AccountSettingsType } from '../../types';
import { RiskInput } from '../RiskInput';

interface AccountDetailsProps {
    currentAccount: Account | undefined;
    accountSettings: AccountSettingsType | undefined;
    isConnected: boolean;
    onToggleTrading: () => void;
    onUpdateSettings: (settings: Partial<AccountSettingsType>) => void;
}

export function AccountDetails({
    currentAccount,
    accountSettings,
    isConnected,
    onToggleTrading,
    onUpdateSettings,
}: AccountDetailsProps) {
    return (
        <section className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6 flex flex-col h-full lg:col-span-1">
            <div className="flex justify-between items-center mb-6">
                <h3 className="text-xl font-semibold text-slate-300 flex items-center gap-2">
                    <CheckCircle className="w-5 h-5 text-green-400" />
                    Account Details
                </h3>
                <div className="flex gap-2">
                    <button
                        onClick={onToggleTrading}
                        disabled={!isConnected}
                        className={`text-xs font-bold px-3 py-1.5 rounded-lg transition-all ${!isConnected
                            ? 'bg-slate-800 text-slate-500 cursor-not-allowed'
                            : accountSettings?.trading_enabled
                                ? 'bg-green-500/20 text-green-400 hover:bg-green-500/30'
                                : 'bg-red-500/20 text-red-400 hover:bg-red-500/30'
                            }`}
                    >
                        {accountSettings?.trading_enabled ? 'TRADING ON' : 'TRADING PAUSED'}
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
                        <span className={`text-xs font-bold px-2 py-0.5 rounded ${currentAccount.simulated ? 'bg-orange-500/20 text-orange-400' : 'bg-blue-500/20 text-blue-400'
                            }`}>
                            {currentAccount.simulated ? 'SIMULATED' : 'LIVE'}
                        </span>
                    </div>
                    <div className="flex justify-between items-center">
                        <span className="text-slate-400 text-sm">Trading</span>
                        <span className={`text-xs font-bold px-2 py-0.5 rounded ${currentAccount.canTrade ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
                            }`}>
                            {currentAccount.canTrade ? 'ENABLED' : 'DISABLED'}
                        </span>
                    </div>
                    <div className="flex justify-between items-center">
                        <span className="text-slate-400 text-sm">Risk / Trade</span>
                        <RiskInput
                            currentValue={accountSettings?.risk_per_trade ?? 200}
                            onSave={(val) => onUpdateSettings({ risk_per_trade: val })}
                        />
                    </div>
                    <div className="flex justify-between items-center">
                        <span className="text-slate-400 text-sm">Max Contracts</span>
                        <RiskInput
                            currentValue={accountSettings?.max_contracts ?? 50}
                            onSave={(val) => onUpdateSettings({ max_contracts: Math.round(val) })}
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
    );
}
