"use client";

import React, { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { apiClient } from "@/lib/api-client";
import { useRouter } from "next/navigation";

interface User {
  id: string;
  email: string;
  name: string;
  role: "citizen" | "officer" | "admin";
  status: string;
  created_at: string;
}

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  register: (name: string, email: string, password: str, phone?: string) => Promise<void>;
  error: string | null;
  clearError: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    // Check if user is already authenticated on mount
    const checkAuth = async () => {
      try {
        const currentUser = await apiClient.get<User>("/auth/me");
        setUser(currentUser);
      } catch (err) {
        // Silently fail if token is missing/expired, they will log in
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    };
    checkAuth();
  }, []);

  const login = async (email: string, password: str) => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await apiClient.post<{ access_token: string; expires_in: number }>(
        "/auth/login",
        { email, password }
      );
      apiClient.setAccessToken(response.access_token);
      
      const currentUser = await apiClient.get<User>("/auth/me");
      setUser(currentUser);

      // Role based redirects
      if (currentUser.role === "citizen") {
        router.push("/fraud-shield");
      } else if (currentUser.role === "officer") {
        router.push("/officer/dashboard");
      } else if (currentUser.role === "admin") {
        router.push("/admin/users");
      }
    } catch (err: any) {
      setError(err.message || "Login failed. Please check your credentials.");
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    setIsLoading(true);
    try {
      await apiClient.post("/auth/logout");
    } catch (err) {
      console.error("Logout request failed:", err);
    } finally {
      apiClient.setAccessToken(null);
      setUser(null);
      setIsLoading(false);
      router.push("/login");
    }
  };

  const register = async (name: string, email: string, password: str, phone?: string) => {
    setIsLoading(true);
    setError(null);
    try {
      await apiClient.post("/auth/register", {
        name,
        email,
        password,
        phone,
      });
      // Auto login after registration
      await login(email, password);
    } catch (err: any) {
      setError(err.message || "Registration failed.");
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const clearError = () => setError(null);

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        login,
        logout,
        register,
        error,
        clearError,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
type str = string;
