/**
 * Credentials Settings Tab Component
 *
 * View and update API credentials (TopStep, Telegram, Heartbeat).
 * Values are masked by the backend — only updated when the user
 * explicitly types a new value.
 */

import { useState, useEffect } from 'react';
import axios from 'axios';
import { Key, MessageCircle, Activity, Save, Loader2, AlertCircle } from 'lucide-react';
import { toast } from 'sonner';
import { API_BASE } from '../../config';

interface FieldInfo {
  value: string;
  is_set: boolean;
  source: 'env' | 'db' | 'none';
}

interface CurrentConfig {
  TOPSTEP_USERNAME: FieldInfo;
  TOPSTEP_APIKEY: FieldInfo;
  TELEGRAM_BOT_TOKEN: FieldInfo;
  TELEGRAM_ID: FieldInfo;
  HEARTBEAT_WEBHOOK_URL: FieldInfo;
  HEARTBEAT_INTERVAL_SECONDS: FieldInfo;
  HEARTBEAT_AUTH_TOKEN: FieldInfo;
}

export function CredentialsTab() {
  const [current, setCurrent] = useState<CurrentConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // Editable fields — only non-empty values get saved
  const [fields, setFields] = useState({
    TOPSTEP_USERNAME: '',
    TOPSTEP_APIKEY: '',
    TELEGRAM_BOT_TOKEN: '',
    TELEGRAM_ID: '',
    HEARTBEAT_WEBHOOK_URL: '',
    HEARTBEAT_INTERVAL_SECONDS: '',
    HEARTBEAT_AUTH_TOKEN: '',
  });

  const fetchCurrent = async () => {
    try {
      const res = await axios.get(`${API_BASE}/setup/current`);
      setCurrent(res.data);
    } catch {
      toast.error('Failed to load credentials');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchCurrent(); }, []);

  const updateField = (key: string, value: string) => {
    setFields(prev => ({ ...prev, [key]: value }));
  };

  const handleSave = async () => {
    // Only send non-empty fields
    const payload: Record<string, string> = {};
    for (const [key, value] of Object.entries(fields)) {
      if (value.trim()) {
        payload[key] = value.trim();
      }
    }

    if (Object.keys(payload).length === 0) {
      toast.info('No changes to save');
      return;
    }

    setSaving(true);
    try {
      const res = await axios.post(`${API_BASE}/setup/save`, payload);
      if (res.data.success) {
        toast.success(`Saved ${res.data.saved_keys.length} setting(s)`);
        if (res.data.connected) {
          toast.success('TopStep connected');
        } else if (res.data.error) {
          toast.error(`TopStep: ${res.data.error}`);
        }
        // Clear fields and reload current values
        setFields({
          TOPSTEP_USERNAME: '',
          TOPSTEP_APIKEY: '',
          TELEGRAM_BOT_TOKEN: '',
          TELEGRAM_ID: '',
          HEARTBEAT_WEBHOOK_URL: '',
          HEARTBEAT_INTERVAL_SECONDS: '',
          HEARTBEAT_AUTH_TOKEN: '',
        });
        await fetchCurrent();
      }
    } catch {
      toast.error('Failed to save');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12 text-slate-500">
        <Loader2 className="w-5 h-5 animate-spin" />
      </div>
    );
  }

  const StatusBadge = ({ info }: { info: FieldInfo }) => {
    if (!info.is_set) return <span className="badge-danger">Not set</span>;
    if (info.source === 'env') return <span className="badge-info">ENV</span>;
    return <span className="badge-success">Configured</span>;
  };

  return (
    <div className="space-y-6">
      {/* TopStep */}
      <div className="space-y-3">
        <div className="flex items-center gap-2 text-sm font-bold text-white">
          <Key className="w-4 h-4 text-indigo-400" />
          TopStep Credentials
        </div>

        <div className="space-y-2">
          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="label mb-0">Username</label>
              {current && <StatusBadge info={current.TOPSTEP_USERNAME} />}
            </div>
            <input
              type="text"
              className="input"
              placeholder={current?.TOPSTEP_USERNAME.is_set ? current.TOPSTEP_USERNAME.value : 'Enter username'}
              value={fields.TOPSTEP_USERNAME}
              onChange={e => updateField('TOPSTEP_USERNAME', e.target.value)}
            />
          </div>
          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="label mb-0">API Key</label>
              {current && <StatusBadge info={current.TOPSTEP_APIKEY} />}
            </div>
            <input
              type="password"
              className="input-mono"
              placeholder={current?.TOPSTEP_APIKEY.is_set ? current.TOPSTEP_APIKEY.value : 'Enter API key'}
              value={fields.TOPSTEP_APIKEY}
              onChange={e => updateField('TOPSTEP_APIKEY', e.target.value)}
            />
          </div>
        </div>
      </div>

      <div className="border-t border-slate-800/60" />

      {/* Telegram */}
      <div className="space-y-3">
        <div className="flex items-center gap-2 text-sm font-bold text-white">
          <MessageCircle className="w-4 h-4 text-blue-400" />
          Telegram
          <span className="text-slate-500 font-normal text-xs">optional</span>
        </div>

        <div className="space-y-2">
          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="label mb-0">Bot Token</label>
              {current && <StatusBadge info={current.TELEGRAM_BOT_TOKEN} />}
            </div>
            <input
              type="password"
              className="input-mono"
              placeholder={current?.TELEGRAM_BOT_TOKEN.is_set ? current.TELEGRAM_BOT_TOKEN.value : '123456:ABC-DEF...'}
              value={fields.TELEGRAM_BOT_TOKEN}
              onChange={e => updateField('TELEGRAM_BOT_TOKEN', e.target.value)}
            />
          </div>
          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="label mb-0">Chat ID</label>
              {current && <StatusBadge info={current.TELEGRAM_ID} />}
            </div>
            <input
              type="text"
              className="input-mono"
              placeholder={current?.TELEGRAM_ID.is_set ? current.TELEGRAM_ID.value : 'Your Telegram user ID'}
              value={fields.TELEGRAM_ID}
              onChange={e => updateField('TELEGRAM_ID', e.target.value)}
            />
          </div>
        </div>
      </div>

      <div className="border-t border-slate-800/60" />

      {/* Heartbeat */}
      <div className="space-y-3">
        <div className="flex items-center gap-2 text-sm font-bold text-white">
          <Activity className="w-4 h-4 text-emerald-400" />
          Heartbeat Monitoring
          <span className="text-slate-500 font-normal text-xs">optional</span>
        </div>

        <div className="space-y-2">
          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="label mb-0">Webhook URL</label>
              {current && <StatusBadge info={current.HEARTBEAT_WEBHOOK_URL} />}
            </div>
            <input
              type="url"
              className="input-mono"
              placeholder={current?.HEARTBEAT_WEBHOOK_URL.is_set ? current.HEARTBEAT_WEBHOOK_URL.value : 'https://...'}
              value={fields.HEARTBEAT_WEBHOOK_URL}
              onChange={e => updateField('HEARTBEAT_WEBHOOK_URL', e.target.value)}
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="label mb-0">Interval (s)</label>
                {current && <StatusBadge info={current.HEARTBEAT_INTERVAL_SECONDS} />}
              </div>
              <input
                type="number"
                className="input-mono"
                placeholder={current?.HEARTBEAT_INTERVAL_SECONDS.is_set ? current.HEARTBEAT_INTERVAL_SECONDS.value : '60'}
                value={fields.HEARTBEAT_INTERVAL_SECONDS}
                onChange={e => updateField('HEARTBEAT_INTERVAL_SECONDS', e.target.value)}
              />
            </div>
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="label mb-0">Auth Token</label>
                {current && <StatusBadge info={current.HEARTBEAT_AUTH_TOKEN} />}
              </div>
              <input
                type="password"
                className="input-mono"
                placeholder={current?.HEARTBEAT_AUTH_TOKEN.is_set ? current.HEARTBEAT_AUTH_TOKEN.value : 'Bearer token'}
                value={fields.HEARTBEAT_AUTH_TOKEN}
                onChange={e => updateField('HEARTBEAT_AUTH_TOKEN', e.target.value)}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Info */}
      <div className="flex items-start gap-2 bg-slate-800/30 rounded-xl p-3">
        <AlertCircle className="w-4 h-4 text-slate-500 flex-shrink-0 mt-0.5" />
        <p className="text-xs text-slate-500">
          Type a new value in any field to update it. Empty fields are left unchanged.
          Fields marked <span className="badge-info text-[10px] py-0">ENV</span> are set via docker-compose.yml and will be overridden by the environment variable on restart.
        </p>
      </div>

      {/* Save */}
      <button onClick={handleSave} disabled={saving} className="btn-primary w-full">
        {saving ? (
          <><Loader2 className="w-4 h-4 animate-spin" /> Saving...</>
        ) : (
          <><Save className="w-4 h-4" /> Save Changes</>
        )}
      </button>
    </div>
  );
}
