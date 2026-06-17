'use client';

import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { api, getToken, setToken } from './api';

interface AuthState {
  nickname: string | null;
  loading: boolean;
  login: (nickname: string, password: string) => Promise<void>;
  register: (nickname: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [nickname, setNickname] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = getToken();
    if (!token) {
      setLoading(false);
      return;
    }
    api
      .me()
      .then((r) => setNickname(r.nickname))
      .catch(() => setToken(null))
      .finally(() => setLoading(false));
  }, []);

  const login = async (nick: string, password: string) => {
    const res = await api.login(nick, password);
    setToken(res.access_token);
    setNickname(res.nickname);
  };

  const register = async (nick: string, password: string) => {
    const res = await api.register(nick, password);
    setToken(res.access_token);
    setNickname(res.nickname);
  };

  const logout = () => {
    setToken(null);
    setNickname(null);
  };

  return (
    <AuthContext.Provider value={{ nickname, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
