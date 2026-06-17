'use client';

import { useState } from 'react';
import { useAuth } from '@/lib/auth-context';
import { Button } from '@/components/ui/Button';

export function AuthForm() {
  const { login, register } = useAuth();
  const [mode, setMode] = useState<'login' | 'register'>('register');
  const [nickname, setNickname] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    setError(null);
    if (nickname.length < 3) return setError('Nickname must be at least 3 characters.');
    if (password.length < 6) return setError('Password must be at least 6 characters.');
    setBusy(true);
    try {
      if (mode === 'register') await register(nickname, password);
      else await login(nickname, password);
    } catch (e) {
      const msg = e instanceof Error ? e.message : '';
      if (msg.includes('already taken')) setError('That nickname is taken.');
      else if (msg.includes('Wrong nickname')) setError('Wrong nickname or password.');
      else if (msg.includes('3-20')) setError('Nickname: 3-20 letters, digits, or underscore.');
      else setError('Something went wrong. Try again.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="pixel-card p-6">
      <div className="mb-4 flex gap-2">
        {(['register', 'login'] as const).map((m) => (
          <button
            key={m}
            type="button"
            onClick={() => { setMode(m); setError(null); }}
            className={mode === m ? 'pixel-tab-active flex-1' : 'pixel-tab flex-1'}
          >
            {m === 'register' ? 'Sign Up' : 'Log In'}
          </button>
        ))}
      </div>

      <div className="space-y-3">
        <input
          value={nickname}
          onChange={(e) => setNickname(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && submit()}
          placeholder="Nickname"
          autoComplete="username"
          className="w-full border-2 border-cobweb-border bg-cobweb-bg px-3 py-2.5 font-mono text-sm text-gray-200 outline-none focus:border-cobweb-pink"
        />
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && submit()}
          placeholder="Password"
          autoComplete={mode === 'register' ? 'new-password' : 'current-password'}
          className="w-full border-2 border-cobweb-border bg-cobweb-bg px-3 py-2.5 font-mono text-sm text-gray-200 outline-none focus:border-cobweb-pink"
        />
        {error && <p className="font-mono text-xs text-cobweb-amber">{error}</p>}
        <Button onClick={submit} disabled={busy} className="w-full justify-center py-2.5">
          {busy ? 'Please wait…' : mode === 'register' ? 'Create Account' : 'Log In'}
        </Button>
      </div>

      <p className="mt-4 font-mono text-[10px] leading-relaxed text-gray-600">
        No email required. Just a nickname and password — your demo balance is tied
        to this account. Passwords are stored hashed, never in plain text.
      </p>
    </div>
  );
}
