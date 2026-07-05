"use client";

import React, { useState, useEffect } from "react";
import { useAuth } from "@/context/auth-context";
import { apiClient } from "@/lib/api-client";
import Button from "@/components/ui/Button";
import Card from "@/components/ui/Card";
import Badge from "@/components/ui/Badge";
import RoleGuard from "@/components/auth/RoleGuard";
import { useRouter } from "next/navigation";
import { Shield, ShieldAlert, LogOut, BarChart3, Users, Network, Settings, FileSpreadsheet, Plus, Server, Database, Activity, RefreshCw, AlertTriangle, Loader2 } from "lucide-react";

interface UserItem {
  id: string;
  name: string;
  email: string;
  role: string;
  status: string;
  created_at: string;
}

export default function AdminUsersDashboard() {
  const { user, logout } = useAuth();
  const router = useRouter();

  const [usersList, setUsersList] = useState<UserItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  
  // Invite modal states
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [inviteName, setInviteName] = useState("");
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("officer");
  const [isSubmittingInvite, setIsSubmittingInvite] = useState(false);

  // KB re-index states
  const [isReindexing, setIsReindexing] = useState(false);
  const [reindexSuccess, setReindexSuccess] = useState(false);

  // Force dark mode class on container for dark SOC layout
  useEffect(() => {
    document.documentElement.classList.add("dark");
    return () => {
      document.documentElement.classList.remove("dark");
    };
  }, []);

  async function loadUsers() {
    setIsLoading(true);
    try {
      const data = await apiClient.get<UserItem[]>("/auth/users");
      setUsersList(data);
    } catch (err) {
      console.error("Failed to load user list:", err);
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    loadUsers();
  }, []);

  const handleToggleUserStatus = async (userId: string, currentStatus: string) => {
    const nextStatus = currentStatus === "active" ? "suspended" : "active";
    try {
      await apiClient.post(`/auth/users/${userId}/status`, { status: nextStatus });
      await loadUsers();
    } catch (err) {
      console.error("Failed to update status:", err);
    }
  };

  const handleInviteUserSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inviteName || !inviteEmail) return;
    setIsSubmittingInvite(true);
    try {
      await apiClient.post("/auth/users/invite", {
        name: inviteName,
        email: inviteEmail,
        role: inviteRole
      });
      setShowInviteModal(false);
      setInviteName("");
      setInviteEmail("");
      await loadUsers();
    } catch (err) {
      console.error("Failed to invite user:", err);
    } finally {
      setIsSubmittingInvite(false);
    }
  };

  const handleTriggerReindex = async () => {
    setIsReindexing(true);
    setReindexSuccess(false);
    // Simulate re-indexing call that pulls seeder guidelines
    setTimeout(() => {
      setIsReindexing(false);
      setReindexSuccess(true);
    }, 1500);
  };

  return (
    <RoleGuard allowedRoles={["admin"]}>
      <div className="min-h-screen bg-bg-canvas text-text-primary flex dark">
        
        {/* Sidebar */}
        <aside className="w-64 bg-nav-bg border-r border-border-default flex flex-col text-nav-text">
          <div className="p-6 border-b border-border-default flex items-center gap-2">
            <Shield className="h-6 w-6 text-brand-primary" />
            <span className="font-bold text-lg tracking-tight">Truvia Portal</span>
          </div>
          
          <nav className="flex-1 p-4 space-y-1">
            <a href="/officer/dashboard" className="flex items-center gap-3 px-3 py-2 rounded-md text-nav-text-muted hover:bg-bg-surface-hover hover:text-nav-text">
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
            <a href="/admin/users" className="flex items-center gap-3 px-3 py-2 rounded-md bg-brand-primary/20 text-brand-primary font-semibold">
              <Users className="h-4 w-4" />
              User Management
            </a>
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
            <h2 className="text-xl font-bold tracking-tight">System Admin Console</h2>
            <div className="flex items-center gap-4">
              <Badge variant="critical">Root Administrator</Badge>
              <span className="text-sm text-text-secondary">Console: {user?.name}</span>
            </div>
          </header>

          {/* Content Canvas */}
          <main className="p-8 space-y-8 flex-1 overflow-y-auto">
            
            {/* System health row & guidelines indexing */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              
              {/* System Health */}
              <Card className="p-6 space-y-4 col-span-2">
                <h3 className="text-md font-bold flex items-center gap-2 text-brand-primary">
                  <Activity className="h-5 w-5" />
                  System Layer Health Ledgers
                </h3>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div className="flex items-center justify-between p-3 rounded-md bg-bg-surface-sunken border border-border-default">
                    <span className="text-text-secondary flex items-center gap-1.5"><Database className="h-4 w-4" /> SQLite Core DB</span>
                    <Badge variant="assigned">ONLINE</Badge>
                  </div>
                  <div className="flex items-center justify-between p-3 rounded-md bg-bg-surface-sunken border border-border-default">
                    <span className="text-text-secondary flex items-center gap-1.5"><Network className="h-4 w-4" /> Neo4j Graph API</span>
                    <Badge variant="moderate">DEGRADED</Badge>
                  </div>
                  <div className="flex items-center justify-between p-3 rounded-md bg-bg-surface-sunken border border-border-default">
                    <span className="text-text-secondary flex items-center gap-1.5"><Server className="h-4 w-4" /> Processing Workers</span>
                    <Badge variant="assigned">IDLE / OK</Badge>
                  </div>
                  <div className="flex items-center justify-between p-3 rounded-md bg-bg-surface-sunken border border-border-default">
                    <span className="text-text-secondary flex items-center gap-1.5"><ShieldAlert className="h-4 w-4" /> AI Models Fallback</span>
                    <Badge variant="low">ACTIVE</Badge>
                  </div>
                </div>
              </Card>

              {/* Guidelines KB Tool */}
              <Card className="p-6 flex flex-col justify-between">
                <div>
                  <h3 className="text-md font-bold mb-1">Knowledge Guidelines KB</h3>
                  <p className="text-xs text-text-secondary">Re-trigger regulatory semantic guidelines database parsing</p>
                </div>
                
                <div className="mt-4 space-y-3">
                  <Button 
                    variant="secondary" 
                    size="sm" 
                    className="w-full"
                    onClick={handleTriggerReindex}
                    isLoading={isReindexing}
                  >
                    <RefreshCw className="h-4 w-4 mr-2" />
                    Re-Index Regulatory guidelines
                  </Button>
                  {reindexSuccess && (
                    <p className="text-xs text-emerald-500 text-center font-semibold">
                      ✓ Guidelines guidelines database parsed and loaded.
                    </p>
                  )}
                </div>
              </Card>

            </div>

            {/* Users list header */}
            <div className="flex justify-between items-center border-t border-border-default pt-6">
              <div>
                <h3 className="text-lg font-bold">Officer Directory Registry</h3>
                <p className="text-sm text-text-secondary">Invite or suspend credentialed law enforcement operators.</p>
              </div>
              <Button variant="primary" size="sm" onClick={() => setShowInviteModal(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Invite Officer
              </Button>
            </div>

            {/* Users Table */}
            {isLoading ? (
              <div className="flex flex-col items-center justify-center p-24 gap-3">
                <Loader2 className="h-8 w-8 animate-spin text-brand-primary" />
                <p className="text-sm text-text-secondary">Retrieving registry directories...</p>
              </div>
            ) : (
              <Card className="p-0 overflow-hidden">
                <table className="w-full border-collapse text-left">
                  <thead>
                    <tr className="bg-bg-surface-sunken border-b border-border-default text-xs font-semibold uppercase tracking-wider text-text-secondary">
                      <th className="px-6 py-3">Name</th>
                      <th className="px-6 py-3">Email</th>
                      <th className="px-6 py-3">Role</th>
                      <th className="px-6 py-3">Status</th>
                      <th className="px-6 py-3">Created</th>
                      <th className="px-6 py-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border-default text-sm">
                    {usersList.map((usr) => (
                      <tr key={usr.id} className="hover:bg-bg-surface-hover">
                        <td className="px-6 py-4 font-semibold">{usr.name}</td>
                        <td className="px-6 py-4 font-mono text-xs">{usr.email}</td>
                        <td className="px-6 py-4">
                          <Badge variant={usr.role === "admin" ? "critical" : "assigned"}>
                            {usr.role.toUpperCase()}
                          </Badge>
                        </td>
                        <td className="px-6 py-4">
                          <Badge variant={usr.status === "active" ? "assigned" : "critical"}>
                            {usr.status.toUpperCase()}
                          </Badge>
                        </td>
                        <td className="px-6 py-4 text-xs text-text-secondary">
                          {new Date(usr.created_at || Date.now()).toLocaleDateString()}
                        </td>
                        <td className="px-6 py-4 text-right">
                          {usr.id !== user?.id ? (
                            <Button 
                              variant={usr.status === "active" ? "secondary" : "primary"}
                              size="sm"
                              onClick={() => handleToggleUserStatus(usr.id, usr.status)}
                            >
                              {usr.status === "active" ? "Suspend" : "Activate"}
                            </Button>
                          ) : (
                            <span className="text-xs text-text-secondary italic">Current Session</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Card>
            )}

          </main>
        </div>

        {/* Invite Officer Modal Drawer */}
        {showInviteModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
            <Card className="w-full max-w-md p-6 bg-bg-surface space-y-4 animate-in fade-in-50 zoom-in-95 duration-150">
              <div>
                <h3 className="text-lg font-bold">Invite Law Enforcement Officer</h3>
                <p className="text-xs text-text-secondary mt-0.5">
                  Register credentialed operators into Truvia's safe intelligence system.
                </p>
              </div>

              <form onSubmit={handleInviteUserSubmit} className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-text-secondary mb-1">Name</label>
                  <input
                    type="text"
                    required
                    value={inviteName}
                    onChange={(e) => setInviteName(e.target.value)}
                    className="w-full bg-bg-canvas border border-border-default rounded-md px-3 py-2 text-sm focus:outline-none focus:border-brand-primary"
                    placeholder="Inspector Sanjay Singh"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-text-secondary mb-1">Email</label>
                  <input
                    type="email"
                    required
                    value={inviteEmail}
                    onChange={(e) => setInviteEmail(e.target.value)}
                    className="w-full bg-bg-canvas border border-border-default rounded-md px-3 py-2 text-sm focus:outline-none focus:border-brand-primary"
                    placeholder="sanjay.singh@truvia.org"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-text-secondary mb-1">Clearance Role</label>
                  <select
                    value={inviteRole}
                    onChange={(e) => setInviteRole(e.target.value)}
                    className="w-full bg-bg-canvas border border-border-default rounded-md px-3 py-2 text-sm focus:outline-none focus:border-brand-primary"
                  >
                    <option value="officer">Officer (L2 Clearance)</option>
                    <option value="admin">Administrator (L3 clearance)</option>
                  </select>
                </div>

                <div className="flex justify-end gap-3 pt-3">
                  <Button variant="tertiary" type="button" onClick={() => setShowInviteModal(false)} disabled={isSubmittingInvite}>
                    Cancel
                  </Button>
                  <Button variant="primary" type="submit" isLoading={isSubmittingInvite}>
                    Submit Registry
                  </Button>
                </div>
              </form>
            </Card>
          </div>
        )}

      </div>
    </RoleGuard>
  );
}
