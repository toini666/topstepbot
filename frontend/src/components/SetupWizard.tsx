import { useState } from 'react';
import { ChevronRight, ChevronLeft, Check, AlertCircle, Key, MessageCircle, Activity, Rocket, Globe, Copy, ExternalLink, Clock, Bot } from 'lucide-react';
import axios from 'axios';
import { API_BASE } from '../config';
import type { SetupConfig } from '../types';
import { cn } from '../utils/cn';
import { Button, Badge } from './ui';

interface SetupWizardProps {
  onComplete: () => void;
}

const STEPS = ['Welcome', 'TopStep', 'Webhook', 'Preferences', 'Telegram', 'Heartbeat', 'Launch'] as const;

const COMMON_TIMEZONES = [
  'America/New_York', 'America/Chicago', 'America/Denver', 'America/Los_Angeles',
  'America/Toronto', 'America/Sao_Paulo',
  'Europe/London', 'Europe/Brussels', 'Europe/Paris', 'Europe/Berlin',
  'Europe/Amsterdam', 'Europe/Madrid', 'Europe/Rome', 'Europe/Zurich',
  'Europe/Moscow',
  'Asia/Dubai', 'Asia/Kolkata', 'Asia/Singapore', 'Asia/Tokyo',
  'Asia/Hong_Kong', 'Asia/Shanghai',
  'Australia/Sydney', 'Pacific/Auckland',
  'UTC',
];

export function SetupWizard({ onComplete }: SetupWizardProps) {
  const [step, setStep] = useState(0);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const detectedTz = Intl.DateTimeFormat().resolvedOptions().timeZone;
  const [config, setConfig] = useState<SetupConfig>({
    TOPSTEP_USERNAME: '',
    TOPSTEP_APIKEY: '',
    TELEGRAM_BOT_TOKEN: '',
    TELEGRAM_ID: '',
    HEARTBEAT_WEBHOOK_URL: '',
    HEARTBEAT_INTERVAL_SECONDS: '60',
    HEARTBEAT_AUTH_TOKEN: '',
    USER_TIMEZONE: detectedTz,
    BOT_NAME: '',
  });

  const updateField = (key: keyof SetupConfig, value: string) => {
    setConfig(prev => ({ ...prev, [key]: value }));
    setError('');
  };

  const canProceed = () => {
    if (step === 1) {
      return config.TOPSTEP_USERNAME.trim() !== '' && config.TOPSTEP_APIKEY.trim() !== '';
    }
    return true;
  };

  const next = () => {
    if (canProceed()) setStep(s => Math.min(s + 1, STEPS.length - 1));
  };
  const prev = () => setStep(s => Math.max(s - 1, 0));

  const handleSave = async () => {
    setSaving(true);
    setError('');
    try {
      const payload: Record<string, string> = {};
      for (const [key, value] of Object.entries(config)) {
        if (value && value.trim()) {
          payload[key] = value.trim();
        }
      }
      const res = await axios.post(`${API_BASE}/setup/save`, payload);
      if (res.data.connected) {
        onComplete();
      } else if (res.data.error) {
        setError(`Connection failed: ${res.data.error}`);
      } else {
        setError('Credentials saved but could not connect to TopStep. Please verify your credentials.');
      }
    } catch {
      setError('Failed to save configuration. Is the backend running?');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="w-full max-w-lg animate-rise">

        {/* Brand moment */}
        <div className="flex flex-col items-center text-center mb-8">
          <div className="relative w-16 h-16 mb-4">
            <div className="absolute inset-0 rounded-2xl bg-indigo-500/30 blur-xl" aria-hidden="true" />
            <div className="relative w-16 h-16 rounded-2xl overflow-hidden bg-slate-900/80 ring-4 ring-indigo-500/15 border border-indigo-400/30 shadow-[0_0_40px_-8px_rgba(99,102,241,0.55)] flex items-center justify-center">
              <img src="/logo.svg" alt="TopStepBot logo" className="w-full h-full object-cover" />
            </div>
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">TopStepBot</h1>
          <p className="text-slate-500 text-sm mt-1.5 max-w-xs">Your automated trading bot for TopStepX.</p>
        </div>

        {/* Step progress */}
        <div className="flex items-center justify-center gap-1 mb-8" role="list" aria-label="Setup progress">
          {STEPS.map((s, i) => (
            <div key={s} className="flex items-center" role="listitem">
              <div
                title={s}
                className={cn(
                  'w-6 h-6 text-[10px] sm:w-8 sm:h-8 sm:text-xs rounded-full flex items-center justify-center font-bold font-mono transition-all',
                  i < step
                    ? 'bg-emerald-500/90 text-white shadow-[0_0_12px_-2px_rgba(16,185,129,0.5)]'
                    : i === step
                      ? 'bg-indigo-500/90 text-white ring-2 ring-indigo-400/50 ring-offset-2 ring-offset-slate-950 shadow-[0_0_16px_-2px_rgba(99,102,241,0.6)]'
                      : 'bg-slate-800/80 text-slate-500 border border-slate-700/60'
                )}
              >
                {i < step ? <Check className="w-3 h-3 sm:w-4 sm:h-4" /> : i + 1}
              </div>
              {i < STEPS.length - 1 && (
                <div className={cn('w-2.5 sm:w-8 h-0.5 mx-0.5 transition-colors', i < step ? 'bg-emerald-500/60' : 'bg-slate-800')} />
              )}
            </div>
          ))}
        </div>

        {/* Panel */}
        <div className="modal-container p-8">
          <div key={step} className="animate-rise">
            {/* Step: Welcome */}
            {step === 0 && (
              <div className="text-center space-y-6">
                <p className="text-slate-400 text-sm leading-relaxed">
                  This wizard will help you configure the essential settings to get started.
                </p>
                <div className="bg-slate-800/50 rounded-xl p-4 text-left space-y-2">
                  <p className="text-xs text-slate-500 uppercase font-bold tracking-wider mb-3">What you'll need</p>
                  <div className="flex items-center gap-3 text-sm text-slate-300">
                    <Key className="w-4 h-4 text-indigo-400 flex-shrink-0" />
                    <span>TopStep API credentials <span className="text-slate-500">(required)</span></span>
                  </div>
                  <div className="flex items-center gap-3 text-sm text-slate-300">
                    <Globe className="w-4 h-4 text-amber-400 flex-shrink-0" />
                    <span>ngrok for TradingView webhooks <span className="text-slate-500">(required)</span></span>
                  </div>
                  <div className="flex items-center gap-3 text-sm text-slate-300">
                    <MessageCircle className="w-4 h-4 text-slate-500 flex-shrink-0" />
                    <span>Telegram bot token <span className="text-slate-500">(optional)</span></span>
                  </div>
                  <div className="flex items-center gap-3 text-sm text-slate-300">
                    <Activity className="w-4 h-4 text-slate-500 flex-shrink-0" />
                    <span>Heartbeat monitoring URL <span className="text-slate-500">(optional)</span></span>
                  </div>
                </div>
              </div>
            )}

            {/* Step: TopStep Credentials */}
            {step === 1 && (
              <div className="space-y-6">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-indigo-600/20 rounded-xl flex items-center justify-center">
                    <Key className="w-5 h-5 text-indigo-400" />
                  </div>
                  <div>
                    <h2 className="text-lg font-bold text-white">TopStep Credentials</h2>
                    <p className="text-slate-500 text-xs">Required to connect to your TopStepX account</p>
                  </div>
                </div>

                <div className="space-y-4">
                  <div>
                    <label className="label">Username</label>
                    <input
                      type="text"
                      className="input"
                      placeholder="Your TopStep username"
                      value={config.TOPSTEP_USERNAME}
                      onChange={e => updateField('TOPSTEP_USERNAME', e.target.value)}
                      autoFocus
                    />
                  </div>
                  <div>
                    <label className="label">API Key</label>
                    <input
                      type="password"
                      className="input-mono"
                      placeholder="Your TopStep API key"
                      value={config.TOPSTEP_APIKEY}
                      onChange={e => updateField('TOPSTEP_APIKEY', e.target.value)}
                    />
                    <p className="help-text">Found in your TopStepX account settings</p>
                  </div>
                </div>
              </div>
            )}

            {/* Step: Webhook / ngrok */}
            {step === 2 && (
              <div className="space-y-6">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-amber-600/20 rounded-xl flex items-center justify-center">
                    <Globe className="w-5 h-5 text-amber-400" />
                  </div>
                  <div>
                    <h2 className="text-lg font-bold text-white">TradingView Webhook</h2>
                    <p className="text-slate-500 text-xs">Required — connect TradingView alerts to your bot</p>
                  </div>
                </div>

                <div className="bg-slate-800/50 rounded-xl p-4 space-y-4">
                  <p className="text-sm text-slate-300 leading-relaxed">
                    TopStepBot executes trades based on <span className="text-white font-medium">TradingView alert webhooks</span>.
                    To receive these alerts, you need to expose your bot to the internet using <span className="text-white font-medium">ngrok</span>.
                  </p>

                  <div className="space-y-3">
                    <div className="flex items-start gap-3">
                      <span className="w-6 h-6 rounded-full bg-amber-600/20 text-amber-400 flex items-center justify-center text-xs font-bold flex-shrink-0 mt-0.5">1</span>
                      <div>
                        <p className="text-sm text-slate-300">Install ngrok from <a href="https://ngrok.com/download" target="_blank" rel="noopener noreferrer" className="text-amber-400 hover:text-amber-300 underline inline-flex items-center gap-1">ngrok.com <ExternalLink className="w-3 h-3" /></a></p>
                        <p className="text-xs text-slate-500 mt-0.5">Create a free account and follow the install instructions</p>
                      </div>
                    </div>

                    <div className="flex items-start gap-3">
                      <span className="w-6 h-6 rounded-full bg-amber-600/20 text-amber-400 flex items-center justify-center text-xs font-bold flex-shrink-0 mt-0.5">2</span>
                      <div className="flex-1">
                        <p className="text-sm text-slate-300">Run this command on your machine:</p>
                        <div className="well mt-1.5 px-3 py-2 flex items-center justify-between gap-2">
                          <code className="text-xs text-amber-300 font-mono">ngrok http 8080</code>
                          <button
                            onClick={() => {
                              navigator.clipboard.writeText('ngrok http 8080');
                            }}
                            className="text-slate-500 hover:text-white transition-colors flex-shrink-0"
                            title="Copy command"
                          >
                            <Copy className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-start gap-3">
                      <span className="w-6 h-6 rounded-full bg-amber-600/20 text-amber-400 flex items-center justify-center text-xs font-bold flex-shrink-0 mt-0.5">3</span>
                      <div>
                        <p className="text-sm text-slate-300">Copy the <span className="text-white font-medium">Forwarding</span> URL from ngrok</p>
                        <p className="text-xs text-slate-500 mt-0.5">It looks like: <code className="text-amber-400/70 font-mono">https://abc123.ngrok-free.app</code></p>
                      </div>
                    </div>

                    <div className="flex items-start gap-3">
                      <span className="w-6 h-6 rounded-full bg-amber-600/20 text-amber-400 flex items-center justify-center text-xs font-bold flex-shrink-0 mt-0.5">4</span>
                      <div className="flex-1">
                        <p className="text-sm text-slate-300">In TradingView, set your alert webhook URL to:</p>
                        <div className="well mt-1.5 px-3 py-2">
                          <code className="text-xs text-amber-300 font-mono">https://your-url.ngrok-free.app/api/webhook</code>
                        </div>
                        <p className="text-xs text-slate-500 mt-1">Replace <code className="font-mono text-slate-400">your-url</code> with your actual ngrok subdomain</p>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="flex items-start gap-2 bg-amber-500/5 border border-amber-500/10 rounded-xl p-3">
                  <AlertCircle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
                  <p className="text-xs text-slate-400">
                    ngrok must be running on the same machine as the bot whenever you want to receive TradingView alerts.
                    You can set this up later — this step is informational only.
                  </p>
                </div>
              </div>
            )}

            {/* Step: Preferences (Bot Name + Timezone) */}
            {step === 3 && (
              <div className="space-y-6">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-violet-600/20 rounded-xl flex items-center justify-center">
                    <Clock className="w-5 h-5 text-violet-400" />
                  </div>
                  <div>
                    <h2 className="text-lg font-bold text-white">Preferences</h2>
                    <p className="text-slate-500 text-xs">Name your bot and set the timezone it operates in</p>
                  </div>
                </div>

                <div className="space-y-4">
                  <div>
                    <label className="label">Bot Name</label>
                    <input
                      type="text"
                      className="input"
                      placeholder="TopStep Bot"
                      value={config.BOT_NAME || ''}
                      onChange={e => updateField('BOT_NAME', e.target.value)}
                    />
                    <p className="help-text">How your dashboard greets you. You can change it later in Settings.</p>
                  </div>
                  <div>
                    <label className="label">Your Timezone</label>
                    <select
                      className="input"
                      value={config.USER_TIMEZONE || detectedTz}
                      onChange={e => updateField('USER_TIMEZONE', e.target.value)}
                    >
                      {/* Ensure detected TZ is always in the list */}
                      {[...new Set([detectedTz, ...COMMON_TIMEZONES])].map(tz => (
                        <option key={tz} value={tz}>{tz}</option>
                      ))}
                    </select>
                    <p className="help-text">
                      Detected from your browser: <span className="text-slate-400">{detectedTz}</span>
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Step: Telegram */}
            {step === 4 && (
              <div className="space-y-6">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-blue-600/20 rounded-xl flex items-center justify-center">
                    <MessageCircle className="w-5 h-5 text-blue-400" />
                  </div>
                  <div>
                    <h2 className="text-lg font-bold text-white">Telegram Notifications</h2>
                    <p className="text-slate-500 text-xs">Optional — receive trade alerts on Telegram</p>
                  </div>
                </div>

                <div className="space-y-4">
                  <div>
                    <label className="label">Bot Token</label>
                    <input
                      type="password"
                      className="input-mono"
                      placeholder="123456:ABC-DEF..."
                      value={config.TELEGRAM_BOT_TOKEN || ''}
                      onChange={e => updateField('TELEGRAM_BOT_TOKEN', e.target.value)}
                    />
                    <p className="help-text">Get one from @BotFather on Telegram</p>
                  </div>
                  <div>
                    <label className="label">Chat ID</label>
                    <input
                      type="text"
                      className="input-mono"
                      placeholder="Your Telegram user ID"
                      value={config.TELEGRAM_ID || ''}
                      onChange={e => updateField('TELEGRAM_ID', e.target.value)}
                    />
                    <p className="help-text">Get yours from @userinfobot on Telegram</p>
                  </div>
                </div>

                <button
                  onClick={next}
                  className="text-xs text-slate-500 hover:text-slate-300 transition-colors"
                >
                  Skip this step →
                </button>
              </div>
            )}

            {/* Step: Heartbeat */}
            {step === 5 && (
              <div className="space-y-6">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-emerald-600/20 rounded-xl flex items-center justify-center">
                    <Activity className="w-5 h-5 text-emerald-400" />
                  </div>
                  <div>
                    <h2 className="text-lg font-bold text-white">Heartbeat Monitoring</h2>
                    <p className="text-slate-500 text-xs">Optional — monitor bot uptime with an external service</p>
                  </div>
                </div>

                <div className="space-y-4">
                  <div>
                    <label className="label">Webhook URL</label>
                    <input
                      type="url"
                      className="input-mono"
                      placeholder="https://your-monitoring.com/webhook"
                      value={config.HEARTBEAT_WEBHOOK_URL || ''}
                      onChange={e => updateField('HEARTBEAT_WEBHOOK_URL', e.target.value)}
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="label">Interval (seconds)</label>
                      <input
                        type="number"
                        className="input-mono"
                        placeholder="60"
                        value={config.HEARTBEAT_INTERVAL_SECONDS || '60'}
                        onChange={e => updateField('HEARTBEAT_INTERVAL_SECONDS', e.target.value)}
                      />
                    </div>
                    <div>
                      <label className="label">Auth Token</label>
                      <input
                        type="password"
                        className="input-mono"
                        placeholder="Bearer token"
                        value={config.HEARTBEAT_AUTH_TOKEN || ''}
                        onChange={e => updateField('HEARTBEAT_AUTH_TOKEN', e.target.value)}
                      />
                    </div>
                  </div>
                </div>

                <button
                  onClick={next}
                  className="text-xs text-slate-500 hover:text-slate-300 transition-colors"
                >
                  Skip this step →
                </button>
              </div>
            )}

            {/* Step: Confirmation */}
            {step === 6 && (
              <div className="space-y-6">
                <div className="text-center">
                  <div className="relative w-14 h-14 mx-auto mb-3">
                    <div className="absolute inset-0 rounded-full bg-emerald-500/20 blur-lg" aria-hidden="true" />
                    <div className="relative w-14 h-14 rounded-full bg-emerald-500/15 border border-emerald-400/30 flex items-center justify-center animate-scale-in">
                      <Check className="w-7 h-7 text-emerald-400" />
                    </div>
                  </div>
                  <h2 className="text-lg font-bold text-white mb-1">Ready to Launch</h2>
                  <p className="text-slate-500 text-xs">Review your configuration and start the bot</p>
                </div>

                <div className="space-y-3">
                  <div className="flex items-center justify-between bg-slate-800/50 rounded-xl px-4 py-3">
                    <div className="flex items-center gap-3">
                      <Key className="w-4 h-4 text-indigo-400" />
                      <span className="text-sm text-slate-300">TopStep</span>
                    </div>
                    <Badge variant="success">Configured</Badge>
                  </div>

                  <div className="flex items-center justify-between bg-slate-800/50 rounded-xl px-4 py-3">
                    <div className="flex items-center gap-3">
                      <Globe className="w-4 h-4 text-amber-400" />
                      <span className="text-sm text-slate-300">Webhook (ngrok)</span>
                    </div>
                    <Badge variant="info">Setup externally</Badge>
                  </div>

                  <div className="flex items-center justify-between bg-slate-800/50 rounded-xl px-4 py-3">
                    <div className="flex items-center gap-3">
                      <Bot className="w-4 h-4 text-violet-400" />
                      <span className="text-sm text-slate-300">Bot Name</span>
                    </div>
                    <span className="text-xs text-slate-400 font-mono">{config.BOT_NAME?.trim() || 'TopStep Bot'}</span>
                  </div>

                  <div className="flex items-center justify-between bg-slate-800/50 rounded-xl px-4 py-3">
                    <div className="flex items-center gap-3">
                      <Clock className="w-4 h-4 text-violet-400" />
                      <span className="text-sm text-slate-300">Timezone</span>
                    </div>
                    <span className="text-xs text-slate-400 font-mono">{config.USER_TIMEZONE || detectedTz}</span>
                  </div>

                  <div className="flex items-center justify-between bg-slate-800/50 rounded-xl px-4 py-3">
                    <div className="flex items-center gap-3">
                      <MessageCircle className="w-4 h-4 text-blue-400" />
                      <span className="text-sm text-slate-300">Telegram</span>
                    </div>
                    {config.TELEGRAM_BOT_TOKEN && config.TELEGRAM_ID
                      ? <Badge variant="success">Configured</Badge>
                      : <Badge variant="neutral">Skipped</Badge>
                    }
                  </div>

                  <div className="flex items-center justify-between bg-slate-800/50 rounded-xl px-4 py-3">
                    <div className="flex items-center gap-3">
                      <Activity className="w-4 h-4 text-emerald-400" />
                      <span className="text-sm text-slate-300">Heartbeat</span>
                    </div>
                    {config.HEARTBEAT_WEBHOOK_URL
                      ? <Badge variant="success">Configured</Badge>
                      : <Badge variant="neutral">Skipped</Badge>
                    }
                  </div>
                </div>

                {error && (
                  <div className="flex items-start gap-3 bg-red-500/10 border border-red-500/20 rounded-xl p-4">
                    <AlertCircle className="w-4 h-4 text-red-300 flex-shrink-0 mt-0.5" />
                    <p className="text-red-300 text-sm">{error}</p>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Navigation */}
          <div className="flex items-center justify-between mt-8 pt-6 border-t border-slate-800/60">
            {step > 0 ? (
              <Button variant="ghost" icon={ChevronLeft} onClick={prev}>
                Back
              </Button>
            ) : (
              <div />
            )}

            {step < STEPS.length - 1 ? (
              <button onClick={next} disabled={!canProceed()} className="btn-primary">
                Continue
                <ChevronRight className="w-4 h-4" />
              </button>
            ) : (
              <Button variant="primary" onClick={handleSave} loading={saving} icon={Rocket}>
                {saving ? 'Connecting...' : 'Launch Bot'}
              </Button>
            )}
          </div>
        </div>

        <p className="text-center text-slate-600 text-xs mt-6">
          TopStepBot — made with love by toini666
        </p>
      </div>
    </div>
  );
}
