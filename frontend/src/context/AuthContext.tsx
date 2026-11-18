import React, { createContext, useContext, useState, useEffect } from 'react';
import { authApi, setAuthToken, removeAuthToken, getAuthToken } from '../services/api';

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName: string, role?: string) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(() => {
    const saved = localStorage.getItem('dfs_user');
    return saved ? JSON.parse(saved) : null;
  });
  const [token, setToken] = useState<string | null>(getAuthToken);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const refreshUser = async () => {
    try {
      const activeUser = await authApi.getMe();
      setUser(activeUser);
      localStorage.setItem('dfs_user', JSON.stringify(activeUser));
    } catch {
      logout();
    }
  };

  useEffect(() => {
    const initAuth = async () => {
      const existingToken = getAuthToken();
      if (existingToken) {
        setToken(existingToken);
        try {
          const activeUser = await authApi.getMe();
          setUser(activeUser);
          localStorage.setItem('dfs_user', JSON.stringify(activeUser));
        } catch {
          logout();
        }
      }
      setIsLoading(false);
    };
    initAuth();
  }, []);

  const login = async (email: string, password: string) => {
    const res = await authApi.login({ email, password });
    setAuthToken(res.access_token);
    setToken(res.access_token);
    setUser(res.user);
    localStorage.setItem('dfs_user', JSON.stringify(res.user));
  };

  const register = async (email: string, password: string, fullName: string, role = 'user') => {
    const res = await authApi.register({ email, password, full_name: fullName, role });
    setAuthToken(res.access_token);
    setToken(res.access_token);
    setUser(res.user);
    localStorage.setItem('dfs_user', JSON.stringify(res.user));
  };

  const logout = () => {
    removeAuthToken();
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!user && !!token,
        isLoading,
        login,
        register,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

