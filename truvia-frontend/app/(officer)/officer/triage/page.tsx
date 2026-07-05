"use client";

import React, { useState, useEffect } from "react";
import { apiClient } from "@/lib/api-client";
import Button from "@/components/ui/Button";
import Card from "@/components/ui/Card";
import Badge from "@/components/ui/Badge";
import RoleGuard from "@/components/auth/RoleGuard";
import { useRouter } from "next/navigation";
import { Shield, FileText, ArrowLeft, Search, Filter, MessageSquare, AlertCircle, Loader2 } from "lucide-react";

interface ReportItem {
  id: string;
  source_type: string;
  cleaned_text: string;
  status: string;
  created_at: string;
}

export default function OfficerTriagePage() {
  const router = useRouter();

  const [reports, setReports] = useState<ReportItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  
  // Filtering and Searching
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [sourceFilter, setSourceFilter] = useState<string>("");

  useEffect(() => {
    document.documentElement.classList.add("dark");
    return () => {
      document.documentElement.classList.remove("dark");
    };
  }, []);

  async function loadReports() {
    setIsLoading(true);
    try {
      const params: Record<string, string> = {};
      if (searchQuery) params.search = searchQuery;
      if (statusFilter) params.status = statusFilter;
      if (sourceFilter) params.source_type = sourceFilter;

      const data = await apiClient.get<ReportItem[]>("/reports", params);
      setReports(data);
    } catch (err) {
      console.error("Failed to load reports ledger:", err);
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    loadReports();
  }, [searchQuery, statusFilter, sourceFilter]);

  const handleEscalateReport = async (reportId: string) => {
    try {
      await apiClient.post(`/reports/${reportId}/escalate`);
      await loadReports(); // Refresh logs
    } catch (err) {
      console.error("Failed to trigger escalation:", err);
    }
  };

  const getStatusBadge = (status: string) => {
    if (status === "escalated" || status === "critical") return "critical";
    if (status === "under_investigation" || status === "in_review") return "moderate";
    return "low";
  };

  return (
    <RoleGuard allowedRoles={["officer", "admin"]}>
      <div className="min-h-screen bg-bg-canvas text-text-primary p-8 space-y-8 dark">
        
        {/* Navigation header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button variant="secondary" size="sm" onClick={() => router.push("/officer/dashboard")}>
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Cockpit
            </Button>
            <div>
              <h1 className="text-2xl font-bold flex items-center gap-2">
                <FileText className="h-6 w-6 text-brand-primary" />
                Complaints Triage Table
              </h1>
              <p className="text-xs text-text-secondary mt-0.5">
                Audit, evaluate, and escalate incoming public safety transcripts.
              </p>
            </div>
          </div>
        </div>

        {/* Filters and Search Bar */}
        <Card className="p-4 grid grid-cols-1 md:grid-cols-3 gap-4 bg-bg-surface-sunken">
          {/* Search bar */}
          <div className="relative">
            <Search className="absolute left-3 top-3 h-4 w-4 text-text-secondary" />
            <input
              type="text"
              placeholder="Search transcript text..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-bg-surface border border-border-default rounded-md pl-10 pr-4 py-2 text-sm text-text-primary focus:outline-none focus:border-brand-primary"
            />
          </div>

          {/* Status Filter */}
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-text-secondary" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="flex-1 bg-bg-surface border border-border-default rounded-md px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-brand-primary"
            >
              <option value="">All Statuses</option>
              <option value="scored">Scored</option>
              <option value="escalated">Escalated</option>
              <option value="under_investigation">Under Investigation</option>
            </select>
          </div>

          {/* Ingest Source Filter */}
          <div className="flex items-center gap-2">
            <MessageSquare className="h-4 w-4 text-text-secondary" />
            <select
              value={sourceFilter}
              onChange={(e) => setSourceFilter(e.target.value)}
              className="flex-1 bg-bg-surface border border-border-default rounded-md px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-brand-primary"
            >
              <option value="">All Ingest Channels</option>
              <option value="text">SMS Text Paste</option>
              <option value="screenshot">Screenshot Upload</option>
              <option value="audio">Voice Audio Snippet</option>
            </select>
          </div>
        </Card>

        {/* Complaints Table Ledger */}
        {isLoading ? (
          <div className="flex flex-col items-center justify-center p-24 gap-3">
            <Loader2 className="h-8 w-8 animate-spin text-brand-primary" />
            <p className="text-sm text-text-secondary">Syncing active ledger records...</p>
          </div>
        ) : (
          <Card className="p-0 overflow-hidden">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-bg-surface-sunken border-b border-border-default text-xs font-bold uppercase tracking-wider text-text-secondary">
                  <th className="px-6 py-3">Complaint ID</th>
                  <th className="px-6 py-3">Ingest Channel</th>
                  <th className="px-6 py-3">Cleaned Transcript</th>
                  <th className="px-6 py-3">Status</th>
                  <th className="px-6 py-3">Ingested At</th>
                  <th className="px-6 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-default text-sm">
                {reports.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="p-12 text-center text-xs text-text-secondary italic">
                      No matching records found in complaints ledger.
                    </td>
                  </tr>
                ) : (
                  reports.map((rep) => (
                    <tr key={rep.id} className="hover:bg-bg-surface-hover">
                      <td className="px-6 py-4 font-mono font-bold text-xs select-all text-text-secondary">
                        #{rep.id.substring(0, 8)}
                      </td>
                      <td className="px-6 py-4 uppercase font-semibold text-xs text-brand-primary">
                        {rep.source_type}
                      </td>
                      <td className="px-6 py-4 max-w-md truncate text-text-secondary font-medium">
                        {rep.cleaned_text || "No transcript compiled"}
                      </td>
                      <td className="px-6 py-4">
                        <Badge variant={getStatusBadge(rep.status)}>{rep.status}</Badge>
                      </td>
                      <td className="px-6 py-4 text-xs text-text-secondary">
                        {new Date(rep.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4 text-right flex justify-end gap-2">
                        {rep.status !== "escalated" && rep.status !== "under_investigation" ? (
                          <Button
                            variant="primary"
                            size="sm"
                            onClick={() => handleEscalateReport(rep.id)}
                          >
                            Escalate to Case
                          </Button>
                        ) : (
                          <Button
                            variant="secondary"
                            size="sm"
                            disabled
                          >
                            Escalated
                          </Button>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </Card>
        )}

      </div>
    </RoleGuard>
  );
}
