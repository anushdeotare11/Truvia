"use client";

import React, { useState, useEffect, useRef } from "react";
import { useAuth } from "@/context/auth-context";
import { apiClient } from "@/lib/api-client";
import Button from "@/components/ui/Button";
import Card from "@/components/ui/Card";
import Badge from "@/components/ui/Badge";
import ProcessingStepper from "@/components/ui/ProcessingStepper";
import RoleGuard from "@/components/auth/RoleGuard";
import { ShieldAlert, LogOut, History, Bell, Upload, FileText, Image as ImageIcon, Music, Trash2, ChevronDown, ChevronUp, AlertCircle, CheckCircle2, Download, Send, ShieldCheck, Loader2, MessageSquare, X, Bookmark } from "lucide-react";

interface ThreatScore {
  id: string;
  threat_score: number;
  severity_band: "low" | "moderate" | "high" | "critical";
  scam_category: string;
  confidence_score: number;
  reasoning_json: {
    key_indicators: string[];
    victim_instructions: string[];
    risk_explanation: string;
  };
  degraded_mode: boolean;
  created_at: string;
}

interface Report {
  id: string;
  source_type: "screenshot" | "audio" | "text";
  cleaned_text?: string;
  detected_language?: string;
  input_confidence?: number;
  low_confidence_flag: boolean;
  status: "submitted" | "processing" | "processed" | "scored" | "escalated" | "failed";
  created_at: string;
  threat_scores?: ThreatScore[];
}

interface Citation {
  source: string;
  title: string;
  url: string | null;
  excerpt: string;
}

interface Message {
  sender: "user" | "assistant";
  text: string;
  citations?: Citation[];
}

function ThreatGauge({ score, severity }: { score: number; severity: string }) {
  const radius = 50;
  const strokeWidth = 10;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;
  
  const colors = {
    low: "text-severity-low",
    moderate: "text-severity-moderate",
    high: "text-severity-high",
    critical: "text-severity-critical"
  };

  const color = colors[severity as keyof typeof colors] || "text-text-secondary";

  return (
    <div className="relative flex flex-col items-center justify-center h-44 w-44 mx-auto">
      <svg className="w-full h-full transform -rotate-90" viewBox="0 0 120 120">
        {/* Track */}
        <circle
          cx="60"
          cy="60"
          r={radius}
          className="stroke-border-default fill-none"
          strokeWidth={strokeWidth}
        />
        {/* Fill */}
        <circle
          cx="60"
          cy="60"
          r={radius}
          className={`${color} fill-none transition-all duration-500 ease-out`}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
        />
      </svg>
      {/* Center text */}
      <div className="absolute flex flex-col items-center justify-center text-center">
        <span className="text-4xl font-extrabold tracking-tight">{score}</span>
        <span className={`text-xs font-bold uppercase tracking-widest mt-0.5 ${color}`}>{severity}</span>
      </div>
    </div>
  );
}

export default function CitizenDashboard() {
  const { user, logout } = useAuth();
  const [activeTab, setActiveTab] = useState<"screenshot" | "audio" | "text">("screenshot");
  
  // File upload state
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [textContent, setTextContent] = useState("");
  const [validationError, setValidationError] = useState<string | null>(null);
  
  // Submission & Polling state
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [currentReport, setCurrentReport] = useState<Report | null>(null);
  const [polling, setPolling] = useState(false);
  
  // Low confidence editing state
  const [showEditModal, setShowEditModal] = useState(false);
  const [editableText, setEditableText] = useState("");
  const [isSavingText, setIsSavingText] = useState(false);

  // Escalation & Download loading states
  const [isEscalating, setIsEscalating] = useState(false);
  const [isDownloadingPdf, setIsDownloadingPdf] = useState(false);

  // Accordion state
  const [accordionOpen, setAccordionOpen] = useState<{ indicators: boolean; actions: boolean; explanation: boolean }>({
    indicators: true,
    actions: true,
    explanation: false
  });

  // AI Chat Assistant state
  const [chatOpen, setChatOpen] = useState(false);
  const [chatQuery, setChatQuery] = useState("");
  const [chatMessages, setChatMessages] = useState<Message[]>([
    {
      sender: "assistant",
      text: "Hello! I am your Truvia Cyber Safety Advisor. Ask me anything about banking regulations, customer liability rules, or digital arrest scams."
    }
  ]);
  const [isSendingChat, setIsSendingChat] = useState(false);
  const [expandedCitationIdx, setExpandedCitationIdx] = useState<string | null>(null);
  const [publicAlerts, setPublicAlerts] = useState<any[]>([]);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const chatBottomRef = useRef<HTMLDivElement>(null);

  // Fetch safety advisories
  useEffect(() => {
    async function loadAlerts() {
      try {
        const data = await apiClient.get<any[]>("/alerts/public");
        setPublicAlerts(data);
      } catch (err) {
        console.error("Failed to load advisories:", err);
      }
    }
    loadAlerts();
  }, []);

  // Poll report status
  useEffect(() => {
    let intervalId: NodeJS.Timeout;
    
    if (polling && currentReport) {
      intervalId = setInterval(async () => {
        try {
          const statusData = await apiClient.get<{
            status: Report["status"];
            low_confidence_flag: boolean;
            input_confidence: number;
          }>(`/reports/${currentReport.id}/status`);

          setCurrentReport((prev) => {
            if (!prev) return null;
            return {
              ...prev,
              status: statusData.status,
              low_confidence_flag: statusData.low_confidence_flag,
              input_confidence: statusData.input_confidence
            };
          });

          // Stop polling if it reaches finished states or failed
          if (["processed", "scored", "escalated", "failed"].includes(statusData.status)) {
            if (statusData.low_confidence_flag && statusData.status === "processed") {
              setPolling(false);
            }
            
            const fullReport = await apiClient.get<Report>(`/reports/${currentReport.id}`);
            setCurrentReport(fullReport);
            if (fullReport.cleaned_text) {
              setEditableText(fullReport.cleaned_text);
            }

            if (["scored", "escalated"].includes(statusData.status)) {
              setPolling(false);
            }
          }
        } catch (err) {
          console.error("Error polling status:", err);
          setPolling(false);
        }
      }, 2000);
    }

    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [polling, currentReport]);

  // Scroll to bottom of chat when messages change
  useEffect(() => {
    if (chatBottomRef.current) {
      chatBottomRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [chatMessages, chatOpen]);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setValidationError(null);
    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      validateAndSetFile(files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setValidationError(null);
    const files = e.target.files;
    if (files && files.length > 0) {
      validateAndSetFile(files[0]);
    }
  };

  const validateAndSetFile = (file: File) => {
    if (activeTab === "screenshot") {
      if (!file.type.startsWith("image/")) {
        setValidationError("Only image files (.png, .jpg, .jpeg) are allowed for screenshots.");
        return;
      }
    } else if (activeTab === "audio") {
      if (!file.type.startsWith("audio/") && !file.name.endsWith(".m4a")) {
        setValidationError("Only audio recordings (.mp3, .wav, .m4a) are allowed.");
        return;
      }
    }
    setSelectedFile(file);
  };

  const triggerFileSelect = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  const removeFile = () => {
    setSelectedFile(null);
    setValidationError(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setValidationError(null);
    
    if (activeTab !== "text" && !selectedFile) {
      setValidationError("Please select or drop an evidence file first.");
      return;
    }
    if (activeTab === "text" && textContent.length < 10) {
      setValidationError("Text content must be at least 10 characters long.");
      return;
    }

    setIsSubmitting(true);
    const formData = new FormData();
    formData.append("source_type", activeTab);

    if (activeTab === "text") {
      formData.append("text_content", textContent);
    } else if (selectedFile) {
      formData.append("files", selectedFile);
    }

    try {
      const response = await apiClient.post<Report>("/reports/submit", formData);
      setCurrentReport(response);
      setPolling(true);
      
      setSelectedFile(null);
      setTextContent("");
    } catch (err: any) {
      setValidationError(err.message || "Failed to submit report. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSaveVerifiedText = async () => {
    if (!currentReport) return;
    setIsSavingText(true);
    try {
      const response = await apiClient.patch<Report>(`/reports/${currentReport.id}/text`, {
        cleaned_text: editableText
      });
      setCurrentReport(response);
      setShowEditModal(false);
      setPolling(true);
    } catch (err) {
      console.error("Failed to update verified text:", err);
    } finally {
      setIsSavingText(false);
    }
  };

  const handleEscalateReport = async () => {
    if (!currentReport) return;
    setIsEscalating(true);
    try {
      await apiClient.post(`/reports/${currentReport.id}/escalate`);
      const updated = await apiClient.get<Report>(`/reports/${currentReport.id}`);
      setCurrentReport(updated);
    } catch (err) {
      console.error("Escalation failed:", err);
    } finally {
      setIsEscalating(false);
    }
  };

  const handleDownloadPdf = async () => {
    if (!currentReport) return;
    setIsDownloadingPdf(true);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
      const response = await fetch(`${apiUrl}/reports/${currentReport.id}/pdf`, {
        headers: {
          "Authorization": `Bearer ${apiClient.getAccessToken()}`
        }
      });
      if (!response.ok) throw new Error("Failed to download PDF");
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `truvia-report-${currentReport.id.substring(0, 8)}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch (err) {
      console.error("Error downloading PDF:", err);
    } finally {
      setIsDownloadingPdf(false);
    }
  };

  const handleSendChat = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatQuery.trim() || isSendingChat) return;

    const userText = chatQuery;
    setChatMessages(prev => [...prev, { sender: "user", text: userText }]);
    setChatQuery("");
    setIsSendingChat(true);

    try {
      const response = await apiClient.post<any>("/chat/", { query: userText });
      setChatMessages(prev => [...prev, {
        sender: "assistant",
        text: response.answer,
        citations: response.citations
      }]);
    } catch (err) {
      console.error("RAG Chat failed:", err);
      setChatMessages(prev => [...prev, {
        sender: "assistant",
        text: "I couldn't fetch an answer from the safety records. Check your internet connection."
      }]);
    } finally {
      setIsSendingChat(false);
    }
  };

  const getTabIcon = (tab: typeof activeTab) => {
    switch (tab) {
      case "screenshot": return <ImageIcon className="h-5 w-5" />;
      case "audio": return <Music className="h-5 w-5" />;
      case "text": return <FileText className="h-5 w-5" />;
    }
  };

  const formatLanguage = (lang?: string) => {
    if (!lang) return "N/A";
    if (lang === "en") return "English";
    if (lang === "hi") return "Hindi";
    if (lang === "hinglish") return "Hinglish (Hindi/English mix)";
    return lang.toUpperCase();
  };

  const toggleAccordion = (section: keyof typeof accordionOpen) => {
    setAccordionOpen(prev => ({ ...prev, [section]: !prev[section] }));
  };

  const getActiveThreatScore = (): ThreatScore | null => {
    if (!currentReport || !currentReport.threat_scores || currentReport.threat_scores.length === 0) {
      return null;
    }
    return currentReport.threat_scores[0];
  };

  const threatScore = getActiveThreatScore();

  return (
    <RoleGuard allowedRoles={["citizen"]}>
      <div className="min-h-screen bg-bg-canvas text-text-primary relative overflow-x-hidden">
        {/* Header */}
        <header className="bg-nav-bg text-nav-text border-b border-border-default px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ShieldAlert className="h-6 w-6 text-brand-primary" />
            <span className="font-bold text-lg">Truvia Citizen Fraud Shield</span>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-nav-text-muted">Welcome, {user?.name}</span>
            <Button variant="tertiary" size="sm" className="text-nav-text hover:bg-white/10" onClick={logout}>
              <LogOut className="h-4 w-4 mr-2" />
              Log Out
            </Button>
          </div>
        </header>

        {/* Main Content */}
        <main className="max-w-6xl mx-auto p-8 grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="md:col-span-2 space-y-8">
          
          {!currentReport ? (
            <>
              <div className="space-y-2 text-center">
                <h1 className="text-3xl font-bold tracking-tight">Evaluate Suspicious Call, Message or Screenshot</h1>
                <p className="text-text-secondary">AI-powered transcription and OCR scanning to evaluate fraud threat risk bands.</p>
              </div>

              {/* Submission Section */}
              <Card className="p-8">
                {/* Tab Selector */}
                <div className="flex border-b border-border-default mb-6">
                  {(["screenshot", "audio", "text"] as const).map((tab) => (
                    <button
                      key={tab}
                      onClick={() => {
                        setActiveTab(tab);
                        setSelectedFile(null);
                        setValidationError(null);
                      }}
                      className={`flex items-center gap-2 px-6 py-3 border-b-2 text-sm font-semibold capitalize transition-all duration-150 ${
                        activeTab === tab
                          ? "border-brand-primary text-brand-primary"
                          : "border-transparent text-text-secondary hover:text-text-primary"
                      }`}
                    >
                      {getTabIcon(tab)}
                      {tab}
                    </button>
                  ))}
                </div>

                {validationError && (
                  <div className="mb-4 rounded-md bg-severity-critical/10 p-3 border border-severity-critical/20 text-sm font-medium text-severity-critical">
                    {validationError}
                  </div>
                )}

                <form onSubmit={handleSubmit} className="space-y-6">
                  {/* File Dropzone */}
                  {activeTab !== "text" ? (
                    <div
                      onDragOver={handleDragOver}
                      onDrop={handleDrop}
                      onClick={selectedFile ? undefined : triggerFileSelect}
                      className={`flex flex-col items-center justify-center p-12 border-2 border-dashed rounded-lg text-center gap-4 transition-all duration-150 ${
                        selectedFile
                          ? "border-brand-primary bg-brand-primary/5 cursor-default"
                          : "border-border-default hover:border-brand-primary bg-bg-surface hover:bg-bg-surface-hover cursor-pointer"
                      }`}
                    >
                      <input
                        type="file"
                        ref={fileInputRef}
                        onChange={handleFileChange}
                        accept={activeTab === "screenshot" ? "image/*" : "audio/*,.m4a"}
                        className="hidden"
                      />

                      {selectedFile ? (
                        <div className="w-full flex items-center justify-between bg-bg-surface p-4 border border-border-default rounded-md shadow-sm">
                          <div className="flex items-center gap-3">
                            <div className="p-2 bg-brand-primary/10 rounded-lg text-brand-primary">
                              {activeTab === "screenshot" ? <ImageIcon className="h-6 w-6" /> : <Music className="h-6 w-6" />}
                            </div>
                            <div className="text-left">
                              <p className="font-semibold text-sm truncate max-w-xs">{selectedFile.name}</p>
                              <p className="text-xs text-text-secondary">{(selectedFile.size / 1024 / 1024).toFixed(2)} MB</p>
                            </div>
                          </div>
                          <Button
                            type="button"
                            variant="icon-only"
                            onClick={(e) => {
                              e.stopPropagation();
                              removeFile();
                            }}
                            className="text-severity-critical hover:bg-severity-critical/10"
                          >
                            <Trash2 className="h-5 w-5" />
                          </Button>
                        </div>
                      ) : (
                        <>
                          <div className="h-16 w-16 bg-brand-primary/10 rounded-full flex items-center justify-center text-brand-primary shadow-sm">
                            <Upload className="h-7 w-7" />
                          </div>
                          <div>
                            <h3 className="text-lg font-bold">Drag and drop file here</h3>
                            <p className="text-sm text-text-secondary mt-1">
                              or click to browse from files (Max size: 10MB)
                            </p>
                          </div>
                        </>
                      )}
                    </div>
                  ) : (
                    <div className="flex flex-col gap-1.5">
                      <label className="text-sm font-semibold uppercase tracking-wider text-text-primary">
                        Paste scam message contents
                      </label>
                      <textarea
                        rows={6}
                        value={textContent}
                        onChange={(e) => setTextContent(e.target.value)}
                        placeholder="Paste suspicious SMS text, WhatsApp messages, emails, or UPI refund links here..."
                        className="w-full p-4 border border-border-default bg-bg-surface rounded-md text-text-primary placeholder:text-text-secondary focus:outline-none focus:border-brand-primary focus:ring-3 focus:ring-brand-primary/35 transition-all duration-150 resize-none"
                      />
                    </div>
                  )}

                  <Button
                    type="submit"
                    className="w-full h-12"
                    isLoading={isSubmitting}
                  >
                    Analyze Content
                  </Button>
                </form>
              </Card>

              {/* Quick Nav Links */}
              <div className="grid grid-cols-2 gap-4">
                <Card className="flex items-center justify-between hoverable">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-brand-primary/10 rounded-lg text-brand-primary">
                      <History className="h-5 w-5" />
                    </div>
                    <div>
                      <h4 className="font-semibold">Scam Reports History</h4>
                      <p className="text-xs text-text-secondary">View your past submissions and statuses</p>
                    </div>
                  </div>
                </Card>

                <Card className="flex items-center justify-between hoverable">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-brand-primary/10 rounded-lg text-brand-primary">
                      <Bell className="h-5 w-5" />
                    </div>
                    <div>
                      <h4 className="font-semibold">Emerging Scams Alerts</h4>
                      <p className="text-xs text-text-secondary">Check recent safety advisories</p>
                    </div>
                  </div>
                </Card>
              </div>
            </>
          ) : (
            /* Report Processing & Result Details Screen */
            <div className="space-y-8">
              <div className="flex justify-between items-center">
                <div>
                  <span className="text-xs font-bold text-brand-primary uppercase tracking-wider">Analysis Ticket</span>
                  <h1 className="text-2xl font-bold mt-1">Ticket: #{currentReport.id.substring(0, 8)}</h1>
                </div>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => {
                    setCurrentReport(null);
                    setValidationError(null);
                    setSelectedFile(null);
                  }}
                >
                  Submit Another Check
                </Button>
              </div>

              {/* Live Pipeline Stepper */}
              <Card className="p-6">
                <h3 className="text-sm font-semibold uppercase tracking-wider mb-6 text-text-secondary">
                  Intake processing Pipeline status
                </h3>
                <ProcessingStepper
                  status={currentReport.status}
                  lowConfidenceFlag={currentReport.low_confidence_flag}
                  onEditTranscription={() => setShowEditModal(true)}
                />
              </Card>

              {/* Escalation Success Alert Banner */}
              {currentReport.status === "escalated" && (
                <div className="p-4 rounded-lg bg-severity-low/10 border border-severity-low/30 flex items-center gap-3 text-sm text-text-primary">
                  <ShieldCheck className="h-5 w-5 text-severity-low shrink-0" />
                  <div>
                    <span className="font-bold text-severity-low">Escalated to Cyber Police:</span> Case has been registered and enqueued for graph clustering.
                  </div>
                </div>
              )}

              {/* Threat Score Assessment Results (Once scored or escalated) */}
              {["scored", "escalated"].includes(currentReport.status) && threatScore && (
                <div className="space-y-6">
                  {/* Action buttons (Download PDF / Escalate to police) */}
                  <div className="flex flex-wrap gap-3">
                    <Button variant="secondary" onClick={handleDownloadPdf} isLoading={isDownloadingPdf}>
                      <Download className="h-4 w-4 mr-2" />
                      Download Court-Ready PDF
                    </Button>
                    
                    {currentReport.status !== "escalated" && (
                      <Button variant="destructive" onClick={handleEscalateReport} isLoading={isEscalating}>
                        <Send className="h-4 w-4 mr-2" />
                        Report to Cyber Police
                      </Button>
                    )}
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    {/* Gauge Card */}
                    <Card className="flex flex-col items-center justify-center p-8">
                      <h3 className="text-sm font-bold uppercase tracking-wider text-text-secondary mb-4">
                        Threat Risk Rating
                      </h3>
                      <ThreatGauge score={threatScore.threat_score} severity={threatScore.severity_band} />
                      <Badge variant={threatScore.severity_band} className="mt-4">
                        {threatScore.severity_band} RISK
                      </Badge>
                    </Card>

                    {/* Threat Description Card */}
                    <Card className="md:col-span-2 space-y-4">
                      <div>
                        <span className="text-xs font-bold text-text-secondary uppercase tracking-widest">Scam Categorization</span>
                        <h2 className="text-2xl font-extrabold tracking-tight mt-0.5 text-brand-primary">
                          {threatScore.scam_category}
                        </h2>
                      </div>

                      <div className="border-t border-border-default pt-4 space-y-4">
                        {/* Accordion 1: Indicators */}
                        <div className="border border-border-default rounded-md overflow-hidden bg-bg-surface">
                          <button
                            onClick={() => toggleAccordion("indicators")}
                            className="w-full flex items-center justify-between p-4 font-semibold text-sm hover:bg-bg-surface-hover text-left"
                          >
                            <span className="flex items-center gap-2 text-severity-critical">
                              <AlertCircle className="h-4 w-4" />
                              Scam Indicators Found ({threatScore.reasoning_json.key_indicators.length})
                            </span>
                            {accordionOpen.indicators ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                          </button>
                          {accordionOpen.indicators && (
                            <div className="p-4 border-t border-border-default bg-bg-surface-sunken space-y-2">
                              {threatScore.reasoning_json.key_indicators.map((ind, i) => (
                                <div key={i} className="text-sm flex items-start gap-2">
                                  <span className="text-severity-critical mt-1 font-bold">•</span>
                                  <span>{ind}</span>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>

                        {/* Accordion 2: Instructions */}
                        <div className="border border-border-default rounded-md overflow-hidden bg-bg-surface">
                          <button
                            onClick={() => toggleAccordion("actions")}
                            className="w-full flex items-center justify-between p-4 font-semibold text-sm hover:bg-bg-surface-hover text-left"
                          >
                            <span className="flex items-center gap-2 text-severity-low">
                              <CheckCircle2 className="h-4 w-4" />
                              Recommended Actions
                            </span>
                            {accordionOpen.actions ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                          </button>
                          {accordionOpen.actions && (
                            <div className="p-4 border-t border-border-default bg-bg-surface-sunken space-y-2">
                              {threatScore.reasoning_json.victim_instructions.map((inst, i) => (
                                <div key={i} className="text-sm flex items-start gap-2">
                                  <span className="text-severity-low mt-1 font-bold">✓</span>
                                  <span>{inst}</span>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>

                        {/* Accordion 3: Detailed Explanation */}
                        <div className="border border-border-default rounded-md overflow-hidden bg-bg-surface">
                          <button
                            onClick={() => toggleAccordion("explanation")}
                            className="w-full flex items-center justify-between p-4 font-semibold text-sm hover:bg-bg-surface-hover text-left"
                          >
                            <span>Detailed Analysis Explanation</span>
                            {accordionOpen.explanation ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                          </button>
                          {accordionOpen.explanation && (
                            <div className="p-4 border-t border-border-default bg-bg-surface-sunken text-sm text-text-secondary leading-relaxed">
                              {threatScore.reasoning_json.risk_explanation}
                            </div>
                          )}
                        </div>
                      </div>
                    </Card>
                  </div>
                </div>
              )}

              {/* Cleaned Text Output */}
              {["processed", "scored", "escalated"].includes(currentReport.status) && (
                <Card className="space-y-4">
                  <div className="flex justify-between items-center border-b border-border-default pb-3">
                    <h3 className="font-bold text-text-primary">Cleaned Text Extraction</h3>
                    <div className="flex gap-2">
                      <Badge variant="default">Lang: {formatLanguage(currentReport.detected_language)}</Badge>
                      <Badge variant={currentReport.low_confidence_flag ? "critical" : "indexed"}>
                        Confidence: {((currentReport.input_confidence || 0) * 100).toFixed(0)}%
                      </Badge>
                    </div>
                  </div>
                  <div className="p-4 rounded-md bg-bg-surface-sunken font-mono text-sm leading-relaxed whitespace-pre-wrap">
                    {currentReport.cleaned_text}
                  </div>
                  {currentReport.low_confidence_flag && (
                    <Button variant="secondary" size="sm" onClick={() => setShowEditModal(true)}>
                      Edit / Override Text
                    </Button>
                  )}
                </Card>
              )}

              {/* Polling/Running Loader */}
              {["submitted", "processing", "processed"].includes(currentReport.status) && !currentReport.low_confidence_flag && (
                <Card className="p-12 text-center flex flex-col items-center justify-center gap-3">
                  <div className="h-10 w-10 border-4 border-brand-primary border-t-transparent rounded-full animate-spin" />
                  <h4 className="font-bold mt-2">AI Agents Analyzing Evidence...</h4>
                  <p className="text-sm text-text-secondary">
                    Evaluating threat indicators, scam categories, and mapping extracted entities.
                  </p>
                </Card>
              )}
            </div>
          )}
          </div>

          {/* Right Column: Public Alerts & Advisories */}
          <div className="space-y-6">
            <Card className="p-6">
              <h3 className="text-lg font-bold flex items-center gap-2 mb-1 border-b border-border-default pb-3 text-text-primary">
                <ShieldAlert className="h-5 w-5 text-brand-primary animate-pulse" />
                Live Cyber Advisories
              </h3>
              
              <div className="space-y-4 pt-3">
                {publicAlerts.length === 0 ? (
                  <p className="text-xs text-text-secondary italic">No active safety warnings published today.</p>
                ) : (
                  publicAlerts.map((adv) => (
                    <div key={adv.id} className="p-4 border border-border-default rounded-md bg-bg-surface-sunken space-y-2">
                      <div className="flex justify-between items-start gap-2">
                        <h4 className="font-bold text-sm text-text-primary">{adv.title}</h4>
                        <Badge variant={adv.severity === "critical" ? "critical" : "high"}>
                          {adv.severity.toUpperCase()}
                        </Badge>
                      </div>
                      <p className="text-xs text-text-secondary leading-relaxed">{adv.description}</p>
                      <span className="text-[10px] text-text-secondary font-medium block text-right mt-1">Updated: {adv.date}</span>
                    </div>
                  ))
                )}
              </div>
            </Card>
          </div>
        </main>

        {/* Floating Chat Trigger Button */}
        <button
          onClick={() => setChatOpen(true)}
          className="fixed bottom-6 right-6 h-14 px-6 bg-brand-primary hover:bg-brand-primary-hover text-white rounded-full shadow-lg flex items-center gap-2.5 font-semibold transition-all hover:scale-105 active:scale-95 duration-150 z-40"
        >
          <MessageSquare className="h-5 w-5" />
          Ask Safety Advisor
        </button>

        {/* Slide-out AI Chat Drawer */}
        {chatOpen && (
          <>
            {/* Backdrop */}
            <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-40" onClick={() => setChatOpen(false)} />
            
            {/* Drawer */}
            <div className="fixed top-0 right-0 bottom-0 w-full max-w-md bg-bg-surface border-l border-border-default shadow-2xl flex flex-col z-50 animate-in slide-in-from-right duration-200">
              {/* Header */}
              <div className="p-4 border-b border-border-default flex items-center justify-between bg-bg-surface-sunken">
                <div className="flex items-center gap-2">
                  <ShieldAlert className="h-5 w-5 text-brand-primary" />
                  <div>
                    <h3 className="font-bold text-sm text-text-primary">Truvia Cyber Advisor</h3>
                    <p className="text-xs text-text-secondary">Grounded in RBI, CERT-In & MHA guides</p>
                  </div>
                </div>
                <Button variant="icon-only" onClick={() => setChatOpen(false)}>
                  <X className="h-5 w-5" />
                </Button>
              </div>

              {/* Message History */}
              <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-bg-canvas">
                {chatMessages.map((msg, idx) => (
                  <div key={idx} className={`flex flex-col ${msg.sender === "user" ? "items-end" : "items-start"}`}>
                    <div
                      className={`max-w-[85%] rounded-lg p-3 text-sm leading-relaxed ${
                        msg.sender === "user"
                          ? "bg-brand-primary text-white rounded-tr-none shadow-sm"
                          : "bg-bg-surface text-text-primary border border-border-default rounded-tl-none shadow-sm"
                      }`}
                    >
                      <p className="whitespace-pre-line">{msg.text}</p>
                    </div>

                    {/* Citations block */}
                    {msg.citations && msg.citations.length > 0 && (
                      <div className="mt-2 w-full max-w-[85%] space-y-1.5 self-start">
                        <span className="text-[10px] uppercase tracking-wider font-bold text-text-secondary flex items-center gap-1">
                          <Bookmark className="h-3 w-3" />
                          Sources Cited ({msg.citations.length})
                        </span>
                        
                        {msg.citations.map((cit, citIdx) => {
                          const key = `${idx}-${citIdx}`;
                          const isExpanded = expandedCitationIdx === key;
                          
                          return (
                            <div key={citIdx} className="border border-border-default rounded bg-bg-surface overflow-hidden">
                              <button
                                onClick={() => setExpandedCitationIdx(isExpanded ? null : key)}
                                className="w-full flex items-center justify-between p-2 text-xs font-semibold hover:bg-bg-surface-hover text-left"
                              >
                                <span className="text-brand-primary">[{cit.source}] {cit.title}</span>
                                {isExpanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                              </button>
                              {isExpanded && (
                                <div className="p-2 border-t border-border-default bg-bg-surface-sunken text-[11px] text-text-secondary italic leading-normal">
                                  "{cit.excerpt}"
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                ))}
                {isSendingChat && (
                  <div className="flex items-center gap-2 text-xs text-text-secondary">
                    <Loader2 className="h-4 w-4 animate-spin text-brand-primary" />
                    Searching regulations...
                  </div>
                )}
                <div ref={chatBottomRef} />
              </div>

              {/* Chat Input */}
              <form onSubmit={handleSendChat} className="p-4 border-t border-border-default bg-bg-surface-sunken flex gap-2">
                <input
                  type="text"
                  value={chatQuery}
                  onChange={(e) => setChatQuery(e.target.value)}
                  placeholder="Ask a question..."
                  disabled={isSendingChat}
                  className="flex-1 px-3 py-2 border border-border-default rounded bg-bg-surface text-sm focus:outline-none focus:border-brand-primary"
                />
                <Button type="submit" size="sm" className="h-9 px-4" isLoading={isSendingChat}>
                  Send
                </Button>
              </form>
            </div>
          </>
        )}

        {/* Edit/Verify Transcription Modal */}
        {showEditModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
            <Card className="w-full max-w-lg p-6 space-y-4 animate-in fade-in-50 zoom-in-95 duration-150">
              <div>
                <h3 className="text-lg font-bold text-text-primary">Verify OCR/Speech Transcription</h3>
                <p className="text-xs text-text-secondary mt-0.5">
                  Adjust any typos or errors in the extracted text to improve risk assessment accuracy.
                </p>
              </div>
              
              <textarea
                rows={8}
                value={editableText}
                onChange={(e) => setEditableText(e.target.value)}
                className="w-full p-3 border border-border-default bg-bg-surface rounded-md text-text-primary font-mono text-sm focus:outline-none focus:border-brand-primary focus:ring-3 focus:ring-brand-primary/35 transition-all duration-150 resize-none"
              />

              <div className="flex justify-end gap-3 mt-4">
                <Button
                  variant="tertiary"
                  onClick={() => setShowEditModal(false)}
                  disabled={isSavingText}
                >
                  Cancel
                </Button>
                <Button
                  variant="primary"
                  onClick={handleSaveVerifiedText}
                  isLoading={isSavingText}
                >
                  Confirm and Re-Submit
                </Button>
              </div>
            </Card>
          </div>
        )}
      </div>
    </RoleGuard>
  );
}
