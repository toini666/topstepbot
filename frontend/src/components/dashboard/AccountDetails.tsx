/**
 * Account Details Panel Component
 *
 * Displays account information, trading status, and risk settings.
 */

import { CheckCircle, ShieldOff } from 'lucide-react';
import type { Account, AccountSettings as AccountSettingsType } from '../../types';
import { RiskInput } from '../RiskInput';
import { Card, CardHeader, Badge, Toggle, EmptyState } from '../ui';

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
    const tradingEnabled = accountSettings?.trading_enabled ?? false;
    const overrideEnabled = accountSettings?.allow_min_contract_over_risk ?? false;

    return (
        <Card className="flex flex-col h-full lg:col-span-1">
            <CardHeader icon={CheckCircle} title="Account Details" />

            {currentAccount ? (
                <div className="flex flex-col flex-1">
                    {/* Trading-enabled hero control */}
                    <div className="flex items-center justify-between rounded-xl px-4 py-3 mb-5 bg-slate-900/60 border border-slate-800/60">
                        <div>
                            <p className="micro-label mb-1.5">Bot Trading</p>
                            <Badge variant={!isConnected ? 'neutral' : tradingEnabled ? 'success' : 'danger'}>
                                {tradingEnabled ? 'TRADING ON' : 'TRADING PAUSED'}
                            </Badge>
                        </div>
                        <Toggle
                            checked={tradingEnabled}
                            onChange={onToggleTrading}
                            disabled={!isConnected}
                            activeColor="emerald"
                            label="Toggle bot trading"
                        />
                    </div>

                    <div className="space-y-4 flex-1">
                        <div className="flex justify-between items-center">
                            <span className="micro-label">Name</span>
                            <span className="font-mono text-white text-sm text-right">{currentAccount.name}</span>
                        </div>
                        <div className="flex justify-between items-center">
                            <span className="micro-label">ID</span>
                            <span className="font-mono text-slate-500 text-sm">{currentAccount.id}</span>
                        </div>
                        <div className="flex justify-between items-center">
                            <span className="micro-label">Status</span>
                            <Badge variant={currentAccount.simulated ? 'warning' : 'info'}>
                                {currentAccount.simulated ? 'SIMULATED' : 'LIVE'}
                            </Badge>
                        </div>
                        <div className="flex justify-between items-center">
                            <span className="micro-label">Trading</span>
                            <Badge variant={currentAccount.canTrade ? 'success' : 'danger'}>
                                {currentAccount.canTrade ? 'ENABLED' : 'DISABLED'}
                            </Badge>
                        </div>
                        <div className="flex justify-between items-center">
                            <span className="micro-label">Risk / Trade</span>
                            <RiskInput
                                currentValue={accountSettings?.risk_per_trade ?? 200}
                                onSave={(val) => onUpdateSettings({ risk_per_trade: val })}
                            />
                        </div>
                        <div className="flex justify-between items-center">
                            <span className="micro-label">Max Contracts</span>
                            <RiskInput
                                currentValue={accountSettings?.max_contracts ?? 50}
                                onSave={(val) => onUpdateSettings({ max_contracts: Math.round(val) })}
                                prefix=""
                            />
                        </div>
                        <div>
                            <div className="flex justify-between items-center">
                                <span
                                    className="micro-label"
                                    title="If enabled, take 1 contract even when the SL distance would exceed the configured risk per trade. The bot logs a warning and notifies Telegram on every override."
                                >
                                    Force 1 contract over risk
                                </span>
                                <button
                                    type="button"
                                    role="switch"
                                    aria-checked={overrideEnabled}
                                    onClick={() =>
                                        onUpdateSettings({ allow_min_contract_over_risk: !overrideEnabled })
                                    }
                                    className={`toggle-sm ${overrideEnabled
                                        ? 'bg-amber-500/80 border-amber-400/50 shadow-[0_0_12px_-2px_rgba(251,191,36,0.5)]'
                                        : 'bg-slate-700/80'
                                        }`}
                                >
                                    <span
                                        className={`toggle-dot-sm ${overrideEnabled ? 'translate-x-[1.15rem]' : 'translate-x-0.5'}`}
                                    />
                                </button>
                            </div>
                            <p className="help-text">
                                Takes 1 contract even if the stop-loss distance exceeds risk/trade. Logs a warning and notifies Telegram on every override.
                            </p>
                        </div>
                    </div>

                    <div className="flex justify-between items-center border-t border-slate-800/60 pt-4 mt-4">
                        <span className="micro-label">Balance</span>
                        <span className="font-mono text-white text-2xl font-bold">
                            ${currentAccount.balance?.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) ?? "0.00"}
                        </span>
                    </div>
                </div>
            ) : (
                <EmptyState
                    icon={ShieldOff}
                    title="No account selected"
                    hint="Choose an account from the header to see its details."
                    className="flex-1"
                />
            )}
        </Card>
    );
}
