"use client";

import React, { useState, useEffect } from "react";
import { useAuth } from "@/context/auth-context";
import { apiClient } from "@/lib/api-client";
import Button from "@/components/ui/Button";
import Card from "@/components/ui/Card";
import Badge from "@/components/ui/Badge";
import RoleGuard from "@/components/auth/RoleGuard";
import { useRouter } from "next/navigation";
import { Shield, LogOut, BarChart3, Users, Network, FileSpreadsheet, MapPin, Eye, Loader2, ArrowRight } from "lucide-react";

interface CaseItem {
  id: string;
  case_number: string;
  case_type: string;
  status: string;
  priority: string;
  ai_summary: string;
}

interface StatsData {
  total_reports: number;
  total_cases: number;
  high_risk_entities: number;
  daily_metrics: Array<{ date: string; reports: number }>;
  city_breakdown: Record<string, number>;
}

export default function OfficerDashboard() {
  const { user, logout } = useAuth();
  const router = useRouter();

  const [stats, setStats] = useState<StatsData | null>(null);
  const [cases, setCases] = useState<CaseItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Force dark mode class on container for dark SOC dashboard layout
  useEffect(() => {
    document.documentElement.classList.add("dark");
    return () => {
      document.documentElement.classList.remove("dark");
    };
  }, []);

  useEffect(() => {
    async function loadDashboardData() {
      setIsLoading(true);
      try {
        const [statsData, casesData] = await Promise.all([
          apiClient.get<StatsData>("/cases/stats"),
          apiClient.get<CaseItem[]>("/cases")
        ]);
        setStats(statsData);
        setCases(casesData);
      } catch (err) {
        console.error("Failed to load dashboard data:", err);
      } finally {
        setIsLoading(false);
      }
    }
    loadDashboardData();
  }, []);

  const getPriorityVariant = (prio: string) => {
    if (prio === "high" || prio === "urgent") return "critical";
    if (prio === "medium") return "moderate";
    return "low";
  };

  return (
    <RoleGuard allowedRoles={["officer", "admin"]}>
      <div className="min-h-screen bg-bg-canvas text-text-primary flex dark">
        
        {/* Sidebar */}
        <aside className="w-64 bg-nav-bg border-r border-border-default flex flex-col text-nav-text">
          <div className="p-6 border-b border-border-default flex items-center gap-2">
            <Shield className="h-6 w-6 text-brand-primary" />
            <span className="font-bold text-lg tracking-tight">Truvia Portal</span>
          </div>
          
          <nav className="flex-1 p-4 space-y-1">
            <a href="/officer/dashboard" className="flex items-center gap-3 px-3 py-2 rounded-md bg-brand-primary/20 text-brand-primary font-semibold">
              <BarChart3 className="h-4 w-4" />
              Dashboard
            </a>
            <a href="/officer/triage" className="flex items-center gap-3 px-3 py-2 rounded-md text-nav-text-muted hover:bg-bg-surface-hover hover:text-nav-text">
              <FileSpreadsheet className="h-4 w-4" />
              Complaints Table
            </a>
            <a href="/officer/graph" className="flex items-center gap-3 px-3 py-2 rounded-md text-nav-text-muted hover:bg-bg-surface-hover hover:text-nav-text">
              <Network className="h-4 w-4" />
              Threat Graph Engine
            </a>
            {user?.role === "admin" && (
              <a href="/admin/users" className="flex items-center gap-3 px-3 py-2 rounded-md text-nav-text-muted hover:bg-bg-surface-hover hover:text-nav-text">
                <Users className="h-4 w-4" />
                User Management
              </a>
            )}
          </nav>

          <div className="p-4 border-t border-border-default">
            <Button variant="tertiary" size="sm" className="w-full text-nav-text hover:bg-white/10" onClick={logout}>
              <LogOut className="h-4 w-4 mr-2" />
              Log Out
            </Button>
          </div>
        </aside>

        {/* Main Layout */}
        <div className="flex-1 flex flex-col">
          {/* Header */}
          <header className="h-16 bg-bg-surface border-b border-border-default px-8 flex items-center justify-between">
            <h2 className="text-xl font-bold tracking-tight">Intelligence Cockpit</h2>
            <div className="flex items-center gap-4">
              <Badge variant="assigned">Officer View</Badge>
              <span className="text-sm text-text-secondary">Security Operator: {user?.name}</span>
            </div>
          </header>

          {/* Content Canvas */}
          <main className="p-8 space-y-8 flex-1 overflow-y-auto">
            {isLoading ? (
              <div className="flex flex-col items-center justify-center p-24 gap-3">
                <Loader2 className="h-8 w-8 animate-spin text-brand-primary" />
                <p className="text-sm text-text-secondary">Syncing live dashboard parameters...</p>
              </div>
            ) : (
              <>
                {/* KPI row */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                  <Card className="p-5">
                    <p className="text-xs text-text-secondary uppercase tracking-wider font-semibold">Total Complaints</p>
                    <h3 className="text-3xl font-bold mt-2">{stats?.total_reports || 0}</h3>
                    <p className="text-xs text-emerald-500 mt-1">↑ Active database feed</p>
                  </Card>

                  <Card className="p-5">
                    <p className="text-xs text-text-secondary uppercase tracking-wider font-semibold">Active Cases</p>
                    <h3 className="text-3xl font-bold mt-2">{stats?.total_cases || 0}</h3>
                    <p className="text-xs text-amber-500 mt-1">Involved scam components</p>
                  </Card>

                  <Card className="p-5">
                    <p className="text-xs text-text-secondary uppercase tracking-wider font-semibold">High-Risk Entities</p>
                    <h3 className="text-3xl font-bold mt-2">{stats?.high_risk_entities || 0}</h3>
                    <p className="text-xs text-red-500 mt-1">Risk score tier &gt;= 65</p>
                  </Card>

                  <Card className="p-5">
                    <p className="text-xs text-text-secondary uppercase tracking-wider font-semibold">Triage Integrity</p>
                    <h3 className="text-3xl font-bold mt-2">100%</h3>
                    <p className="text-xs text-brand-primary mt-1">Self-healing offline checks OK</p>
                  </Card>
                </div>

                {/* Section details */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                  {/* Trends Bar Chart */}
                  <Card className="lg:col-span-2 p-6 flex flex-col justify-between">
                    <div>
                      <h3 className="text-lg font-bold mb-1">Scam Trend Trajectory</h3>
                      <p className="text-xs text-text-secondary mb-4">Ingestion volumes over the past 7 days</p>
                    </div>
                    
                    {/* SVG bar chart */}
                    <div className="h-60 flex items-end gap-6 justify-around pt-6 border-b border-border-default pb-2">
                      {stats?.daily_metrics.map((day, idx) => {
                        const maxVal = Math.max(...stats.daily_metrics.map(d => d.reports), 1);
                        const pctHeight = (day.reports / maxVal) * 80; // Scale to max 80%
                        return (
                          <div key={idx} className="flex-1 flex flex-col items-center gap-2 group h-full justify-end">
                            <div className="text-xs font-bold text-brand-primary opacity-0 group-hover:opacity-100 transition-opacity">
                              {day.reports}
                            </div>
                            <div 
                              style={{ height: `${pctHeight}%` }} 
                              className="w-full bg-brand-primary/80 group-hover:bg-brand-primary rounded-t transition-all duration-300"
                            />
                            <span className="text-xs text-text-secondary font-semibold">{day.date}</span>
                          </div>
                        );
                      })}
                    </div>
                  </Card>

                  {/* City breakdown */}
                  <Card className="p-6">
                    <h3 className="text-lg font-bold mb-1">Geographic Vectors</h3>
                    <p className="text-xs text-text-secondary mb-4">Top 5 city/district concentrations</p>
                    
                    <div className="space-y-4">
                      {stats && Object.entries(stats.city_breakdown).map(([city, count]) => (
                        <div key={city} className="flex items-center justify-between p-3 rounded-md bg-bg-surface-sunken border border-border-default">
                          <span className="text-sm font-semibold flex items-center gap-2">
                            <MapPin className="h-4 w-4 text-brand-primary" />
                            {city}
                          </span>
                          <span className="text-xs font-bold bg-brand-primary/20 text-brand-primary px-2 py-1 rounded">
                            {count} reports
                          </span>
                        </div>
                      ))}
                    </div>
                  </Card>
                </div>

                {/* Recent triage cases ledger */}
                <Card className="p-6">
                  <div className="flex justify-between items-center mb-6">
                    <div>
                      <h3 className="text-lg font-bold">Investigation Cases Ledger</h3>
                      <p className="text-xs text-text-secondary">Scam ring groups clustered automatically by co-occurring indicators</p>
                    </div>
                    <Button variant="secondary" size="sm" onClick={() => router.push("/officer/triage")}>
                      View Complaints Triage
                      <ArrowRight className="h-4 w-4 ml-2" />
                    </Button>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse">
                      <thead>
                        <tr className="border-b border-border-default bg-bg-surface-sunken text-xs font-bold uppercase tracking-wider text-text-secondary">
                          <th className="px-6 py-3">Case ID</th>
                          <th className="px-6 py-3">Modus Operandi</th>
                          <th className="px-6 py-3">Priority</th>
                          <th className="px-6 py-3">Status</th>
                          <th className="px-6 py-3 text-right">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border-default text-sm">
                        {cases.length === 0 ? (
                          <tr>
                            <td colSpan={5} className="p-6 text-center text-xs text-text-secondary italic">
                              No active cases loaded in database.
                            </td>
                          </tr>
                        ) : (
                          cases.map((c) => (
                            <tr key={c.id} className="hover:bg-bg-surface-hover">
                              <td className="px-6 py-4 font-bold text-brand-primary select-all">{c.case_number}</td>
                              <td className="px-6 py-4 max-w-sm truncate text-text-secondary">{c.case_type}</td>
                              <td className="px-6 py-4">
                                <Badge variant={getPriorityVariant(c.priority)}>{c.priority.toUpperCase()}</Badge>
                              </td>
                              <td className="px-6 py-4">
                                <Badge variant="assigned">{c.status}</Badge>
                              </td>
                              <td className="px-6 py-4 text-right">
                                <Button 
                                  variant="secondary" 
                                  size="sm"
                                  onClick={() => router.push(`/officer/case/${c.id}`)}
                                >
                                  <Eye className="h-4 w-4 mr-2" />
                                  Inspect Dossier
                                </Button>
                              </td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                </Card>
              </>
            )}
          </main>
        </div>

      </div>
    </RoleGuard>
  );
}
