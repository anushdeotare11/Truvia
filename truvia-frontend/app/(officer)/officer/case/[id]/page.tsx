"use client";

import React, { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { apiClient } from "@/lib/api-client";
import Button from "@/components/ui/Button";
import Card from "@/components/ui/Card";
import Badge from "@/components/ui/Badge";
import RoleGuard from "@/components/auth/RoleGuard";
import { Shield, ArrowLeft, Download, UserPlus, FileText, Users, Clock, AlertTriangle, Loader2 } from "lucide-react";

interface LinkedReport {
  id: string;
  source_type: string;
  status: string;
  cleaned_text: string;
  created_at: string;
}

interface LinkedEntity {
  id: string;
  raw_value: string;
  type: string;
  risk_score: number;
  risk_tier: string;
  occurrence_count: number;
}

interface AuditLog {
  id: string;
  actor_type: string;
  action: string;
  diff_json: any;
  created_at: string;
}

interface CaseDetails {
  id: string;
  case_number: string;
  case_type: string;
  status: string;
  priority: string;
  ai_summary: string;
  assigned_officer_id: string | null;
  assigned_officer_name: string;
  created_at: string;
  linked_reports: LinkedReport[];
  entities: LinkedEntity[];
  audit_logs: AuditLog[];
}

export default function CaseDetailsPage() {
  const params = useParams();
  const router = useRouter();
  const caseId = params.id as string;

  const [details, setDetails] = useState<CaseDetails | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  
  // Tab control
  const [activeTab, setActiveTab] = useState<"summary" | "entities" | "evidence" | "timeline">("summary");

  // Assignment states
  const [showAssignModal, setShowAssignModal] = useState(false);
  const [isAssigning, setIsAssigning] = useState(false);
  const [isDownloadingPdf, setIsDownloadingPdf] = useState(false);

  // Hardcoded list of cyber officers for triage assignment
  const demoOfficers = [
    { id: "00000000-0000-0000-0000-000000000003", name: "Inspector Amit Kumar" }
  ];

  async function loadCaseDetails() {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const data = await apiClient.get<CaseDetails>(`/cases/${caseId}`);
      setDetails(data);
    } catch (err) {
      console.error("Failed to load case details:", err);
      setErrorMsg("Failed to load investigation dossier. Verify case UUID.");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    if (caseId) {
      loadCaseDetails();
    }
  }, [caseId]);

  const handleAssignOfficer = async (officerId: string) => {
    setIsAssigning(true);
    try {
      await apiClient.post(`/cases/${caseId}/assign`, { officer_id: officerId });
      setShowAssignModal(false);
      await loadCaseDetails(); // Reload details to fetch newly logged audit trails and assigned names
    } catch (err) {
      console.error("Failed to assign case:", err);
    } finally {
      setIsAssigning(false);
    }
  };

  const handleDownloadDossierPdf = async () => {
    setIsDownloadingPdf(true);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api/v1";
      const response = await fetch(`${apiUrl}/cases/${caseId}/package`, {
        headers: {
          "Authorization": `Bearer ${apiClient.getAccessToken()}`
        }
      });
      if (!response.ok) throw new Error("Failed to compile dossier");
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `dossier-${details?.case_number || "case"}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch (err) {
      console.error("Error downloading case package:", err);
    } finally {
      setIsDownloadingPdf(false);
    }
  };

  const getPriorityColor = (prio: string) => {
    if (prio === "high" || prio === "urgent") return "critical";
    if (prio === "medium") return "moderate";
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
              Back to Dashboard
            </Button>
            <h1 className="text-2xl font-bold">Dossier: {details?.case_number || "Loading..."}</h1>
          </div>

          {details && (
            <div className="flex gap-3">
              <Button variant="secondary" size="sm" onClick={handleDownloadDossierPdf} isLoading={isDownloadingPdf}>
                <Download className="h-4 w-4 mr-2" />
                Compile Court Dossier PDF
              </Button>
              <Button variant="primary" size="sm" onClick={() => setShowAssignModal(true)}>
                <UserPlus className="h-4 w-4 mr-2" />
                Assign Case
              </Button>
            </div>
          )}
        </div>

        {isLoading ? (
          <div className="flex flex-col items-center justify-center p-24 gap-3">
            <Loader2 className="h-8 w-8 animate-spin text-brand-primary" />
            <p className="text-sm text-text-secondary">Retrieving active dossiers...</p>
          </div>
        ) : errorMsg || !details ? (
          <Card className="p-12 text-center flex flex-col items-center justify-center gap-3">
            <AlertTriangle className="h-10 w-10 text-severity-critical" />
            <p className="text-sm font-bold text-severity-critical">{errorMsg}</p>
          </Card>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
            
            {/* Left metadata summary card */}
            <div className="lg:col-span-1 space-y-6">
              <Card className="p-6 space-y-6">
                <div>
                  <span className="text-[10px] font-bold text-text-secondary uppercase tracking-widest">Case Profile</span>
                  <h3 className="text-xl font-bold mt-1 text-brand-primary">{details.case_number}</h3>
                </div>

                <div className="space-y-4 border-t border-border-default pt-4 text-sm">
                  <div className="flex justify-between items-center">
                    <span className="text-text-secondary">Assigned Operator</span>
                    <span className="font-semibold text-text-primary">{details.assigned_officer_name}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-text-secondary">Case Priority</span>
                    <Badge variant={getPriorityColor(details.priority)}>{details.priority.toUpperCase()}</Badge>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-text-secondary">Ingest Date</span>
                    <span>{new Date(details.created_at).toLocaleDateString()}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-text-secondary">Total Evidence</span>
                    <span className="font-semibold">{details.linked_reports.length} incidents</span>
                  </div>
                </div>
              </Card>
            </div>

            {/* Right main tabbed content panel */}
            <div className="lg:col-span-3 space-y-6">
              {/* Tab Selector */}
              <div className="flex border-b border-border-default">
                {[
                  { id: "summary", label: "Executive Summary", icon: <FileText className="h-4.5 w-4.5" /> },
                  { id: "entities", label: "Threat Entities", icon: <Users className="h-4.5 w-4.5" /> },
                  { id: "evidence", label: "Complaints Log", icon: <Shield className="h-4.5 w-4.5" /> },
                  { id: "timeline", label: "Audit Timeline", icon: <Clock className="h-4.5 w-4.5" /> }
                ].map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id as any)}
                    className={`flex items-center gap-2 px-6 py-3 border-b-2 text-sm font-semibold transition-all duration-150 ${
                      activeTab === tab.id
                        ? "border-brand-primary text-brand-primary"
                        : "border-transparent text-text-secondary hover:text-text-primary"
                    }`}
                  >
                    {tab.icon}
                    {tab.label}
                  </button>
                ))}
              </div>

              {/* Tab canvas contents */}
              <div className="mt-4">
                
                {/* 1. Summary Tab */}
                {activeTab === "summary" && (
                  <Card className="p-6 space-y-4">
                    <h3 className="text-lg font-bold text-brand-primary">AI-Generated Modus Operandi Brief</h3>
                    <p className="text-sm text-text-secondary leading-relaxed bg-bg-surface-sunken p-4 rounded-md border border-border-default whitespace-pre-wrap">
                      {details.ai_summary}
                    </p>
                  </Card>
                )}

                {/* 2. Entities Tab */}
                {activeTab === "entities" && (
                  <Card className="p-0 overflow-hidden">
                    <table className="w-full text-left border-collapse">
                      <thead>
                        <tr className="bg-bg-surface-sunken border-b border-border-default text-xs font-bold uppercase tracking-wider text-text-secondary">
                          <th className="px-6 py-3">Type</th>
                          <th className="px-6 py-3">Raw Value</th>
                          <th className="px-6 py-3">Risk score</th>
                          <th className="px-6 py-3">Occurrences</th>
                          <th className="px-6 py-3 text-right">Action</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border-default text-sm">
                        {details.entities.length === 0 ? (
                          <tr>
                            <td colSpan={5} className="p-6 text-center text-xs text-text-secondary italic">
                              No threat entities mapped to this case.
                            </td>
                          </tr>
                        ) : (
                          details.entities.map((ent) => (
                            <tr key={ent.id} className="hover:bg-bg-surface-hover">
                              <td className="px-6 py-4 font-semibold capitalize">{ent.type}</td>
                              <td className="px-6 py-4 font-mono select-all">{ent.raw_value}</td>
                              <td className="px-6 py-4">
                                <Badge variant={getPriorityColor(ent.risk_tier)}>{ent.risk_score} / 100</Badge>
                              </td>
                              <td className="px-6 py-4">{ent.occurrence_count} times</td>
                              <td className="px-6 py-4 text-right">
                                <Button 
                                  variant="tertiary" 
                                  size="sm"
                                  onClick={() => router.push(`/officer/entity/${ent.id}`)}
                                >
                                  View Dossier
                                </Button>
                              </td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </Card>
                )}

                {/* 3. Evidence Tab */}
                {activeTab === "evidence" && (
                  <div className="space-y-4">
                    {details.linked_reports.map((rep) => (
                      <Card key={rep.id} className="p-6 space-y-3">
                        <div className="flex justify-between items-center border-b border-border-default pb-2">
                          <span className="text-xs font-bold">Ticket ID: #{rep.id.substring(0, 8)}</span>
                          <div className="flex gap-2">
                            <Badge variant="default">Channel: {rep.source_type.toUpperCase()}</Badge>
                            <Badge variant="assigned">{rep.status}</Badge>
                          </div>
                        </div>
                        <p className="text-sm font-mono leading-relaxed bg-bg-surface-sunken p-3 rounded text-text-secondary whitespace-pre-wrap">
                          {rep.cleaned_text}
                        </p>
                      </Card>
                    ))}
                  </div>
                )}

                {/* 4. Timeline Tab */}
                {activeTab === "timeline" && (
                  <Card className="p-6 space-y-6">
                    <h3 className="text-lg font-bold border-b border-border-default pb-3">Audit Logs Trail</h3>
                    <div className="space-y-4">
                      {details.audit_logs.map((log) => (
                        <div key={log.id} className="flex gap-4 items-start text-sm">
                          <div className="p-2 bg-brand-primary/10 rounded-full text-brand-primary">
                            <Clock className="h-4 w-4" />
                          </div>
                          <div>
                            <p className="font-semibold text-text-primary">
                              {log.action === "case.assign" 
                                ? `Assigned to ${log.diff_json?.assigned_to || "officer"}` 
                                : "Incident registered and linked"}
                            </p>
                            <p className="text-xs text-text-secondary mt-0.5">
                              Actor: {log.actor_type.toUpperCase()} | {new Date(log.created_at).toLocaleString()}
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </Card>
                )}

              </div>
            </div>

          </div>
        )}

        {/* Assignment Modal Drawer */}
        {showAssignModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
            <Card className="w-full max-w-md p-6 space-y-4 animate-in fade-in-50 zoom-in-95 duration-150 bg-bg-surface">
              <div>
                <h3 className="text-lg font-bold">Assign Triage Case</h3>
                <p className="text-xs text-text-secondary mt-0.5">
                  Select a certified cyber investigator officer to assign this fraud dossier.
                </p>
              </div>

              <div className="space-y-2 max-h-60 overflow-y-auto pr-1 pt-2">
                {demoOfficers.map((off) => (
                  <button
                    key={off.id}
                    onClick={() => handleAssignOfficer(off.id)}
                    disabled={isAssigning}
                    className="w-full flex items-center justify-between p-3 border border-border-default rounded-md bg-bg-surface hover:bg-bg-surface-hover text-left transition-all duration-150"
                  >
                    <div>
                      <p className="font-semibold text-sm">{off.name}</p>
                      <p className="text-xs text-text-secondary">Security clearance level: L2</p>
                    </div>
                    <span className="text-xs text-brand-primary font-bold">Select</span>
                  </button>
                ))}
              </div>

              <div className="flex justify-end gap-3 mt-4">
                <Button variant="tertiary" onClick={() => setShowAssignModal(false)} disabled={isAssigning}>
                  Cancel
                </Button>
              </div>
            </Card>
          </div>
        )}

      </div>
    </RoleGuard>
  );
}
