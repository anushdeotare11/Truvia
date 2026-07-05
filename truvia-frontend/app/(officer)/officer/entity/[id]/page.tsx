"use client";

import React, { useState, useEffect, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import { apiClient } from "@/lib/api-client";
import Button from "@/components/ui/Button";
import Card from "@/components/ui/Card";
import Badge from "@/components/ui/Badge";
import RoleGuard from "@/components/auth/RoleGuard";
import { ShieldAlert, ArrowLeft, Calendar, Shield, Activity, User, Network, FileText, Loader2, AlertCircle } from "lucide-react";

interface SubgraphNode {
  id: string;
  label: string;
  type: string;
  risk_score: number;
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
}

interface SubgraphEdge {
  source: string;
  target: string;
  type: string;
  weight: number;
}

interface EntityProfile {
  id: string;
  raw_value: string;
  normalized_value: string;
  type: string;
  risk_score: number;
  risk_tier: string;
  occurrence_count: number;
  first_seen_at: string | null;
  last_seen_at: string | null;
  linked_reports: Array<{
    id: string;
    source_type: string;
    status: string;
    created_at: string;
  }>;
  subgraph: {
    nodes: SubgraphNode[];
    edges: SubgraphEdge[];
  };
}

export default function EntityExplorerPage() {
  const params = useParams();
  const router = useRouter();
  const entityId = params.id as string;

  const [profile, setProfile] = useState<EntityProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const canvasRef = useRef<HTMLCanvasElement>(null);
  const transformRef = useRef({ x: 0, y: 0, k: 1 });
  const nodesRef = useRef<SubgraphNode[]>([]);

  // Physics settings for local neighborhood subgraph
  const kRepulsion = 600;
  const kAttraction = 0.05;
  const restLength = 100;
  const damping = 0.85;

  useEffect(() => {
    async function loadProfile() {
      setIsLoading(true);
      setErrorMsg(null);
      try {
        const data = await apiClient.get<EntityProfile>(`/entities/${entityId}`);
        
        // Initialize node coordinates relative to center (300, 200)
        const center = { x: 300, y: 200 };
        const initializedNodes = data.subgraph.nodes.map((node) => {
          const isCenter = node.id === entityId;
          return {
            ...node,
            x: center.x + (isCenter ? 0 : (Math.random() - 0.5) * 200),
            y: center.y + (isCenter ? 0 : (Math.random() - 0.5) * 200),
            vx: 0,
            vy: 0
          };
        });
        
        nodesRef.current = initializedNodes;
        setProfile(data);
      } catch (err) {
        console.error("Failed to load entity profile:", err);
        setErrorMsg("Failed to load entity details. Check if entity UUID exists.");
      } finally {
        setIsLoading(false);
      }
    }
    if (entityId) {
      loadProfile();
    }
  }, [entityId]);

  // Subgraph physics loop
  useEffect(() => {
    if (!profile || nodesRef.current.length === 0) return;

    let animId: number;
    const center = { x: 300, y: 200 };

    const runPhysicsFrame = () => {
      const nodes = nodesRef.current;
      const edges = profile.subgraph.edges;

      // 1. Repulsion
      for (let i = 0; i < nodes.length; i++) {
        const n1 = nodes[i];
        for (let j = i + 1; j < nodes.length; j++) {
          const n2 = nodes[j];
          const dx = (n1.x || 0) - (n2.x || 0);
          const dy = (n1.y || 0) - (n2.y || 0);
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          
          if (dist < 300) {
            const force = kRepulsion / (dist * dist);
            n1.vx = (n1.vx || 0) + (dx / dist) * force;
            n1.vy = (n1.vy || 0) + (dy / dist) * force;
            n2.vx = (n2.vx || 0) - (dx / dist) * force;
            n2.vy = (n2.vy || 0) - (dy / dist) * force;
          }
        }
      }

      // 2. Attraction
      edges.forEach((edge) => {
        const s = nodes.find(n => n.id === edge.source);
        const t = nodes.find(n => n.id === edge.target);
        
        if (s && t) {
          const dx = (t.x || 0) - (s.x || 0);
          const dy = (t.y || 0) - (s.y || 0);
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          
          const force = kAttraction * (dist - restLength);
          const fx = (dx / dist) * force;
          const fy = (dy / dist) * force;
          
          s.vx = (s.vx || 0) + fx;
          s.vy = (s.vy || 0) + fy;
          t.vx = (t.vx || 0) - fx;
          t.vy = (t.vy || 0) - fy;
        }
      });

      // 3. Update position (pinning the center node)
      nodes.forEach((node) => {
        if (node.id === entityId) {
          // Keep center node strictly centered
          node.x = center.x;
          node.y = center.y;
          node.vx = 0;
          node.vy = 0;
          return;
        }

        // Center gravity pulls towards center
        node.vx = (node.vx || 0) + (center.x - (node.x || 0)) * 0.015;
        node.vy = (node.vy || 0) + (center.y - (node.y || 0)) * 0.015;

        node.x = (node.x || 0) + (node.vx || 0);
        node.y = (node.y || 0) + (node.vy || 0);
        node.vx = (node.vx || 0) * damping;
        node.vy = (node.vy || 0) * damping;
      });

      drawFrame();
      animId = requestAnimationFrame(runPhysicsFrame);
    };

    const drawFrame = () => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;

      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.save();

      // Render edges
      profile.subgraph.edges.forEach((edge) => {
        const s = nodesRef.current.find(n => n.id === edge.source);
        const t = nodesRef.current.find(n => n.id === edge.target);
        
        if (s && t) {
          ctx.beginPath();
          ctx.moveTo(s.x || 0, s.y || 0);
          ctx.lineTo(t.x || 0, t.y || 0);
          ctx.strokeStyle = "#3B82F6";
          ctx.lineWidth = 2;
          ctx.stroke();
        }
      });

      // Render nodes
      nodesRef.current.forEach((node) => {
        const isCenter = node.id === entityId;
        const radius = isCenter ? 20 : 12;

        ctx.beginPath();
        ctx.arc(node.x || 0, node.y || 0, radius, 0, 2 * Math.PI);
        
        ctx.fillStyle = isCenter ? "#EF4444" : "#10B981";
        ctx.fill();

        ctx.strokeStyle = "#0F172A";
        ctx.lineWidth = 1.5;
        ctx.stroke();

        // Node label
        ctx.font = isCenter ? "bold 11px Inter" : "9px Inter";
        ctx.fillStyle = "#FFFFFF";
        ctx.fillText(node.label, (node.x || 0) + radius + 4, (node.y || 0) + 4);
      });

      ctx.restore();
    };

    animId = requestAnimationFrame(runPhysicsFrame);
    return () => cancelAnimationFrame(animId);
  }, [profile, entityId]);

  const formatDate = (isoStr: string | null) => {
    if (!isoStr) return "N/A";
    return new Date(isoStr).toLocaleString();
  };

  const getBadgeVariant = (tier: string) => {
    if (tier === "critical" || tier === "high") return "critical";
    if (tier === "moderate") return "moderate";
    return "low";
  };

  return (
    <RoleGuard allowedRoles={["officer", "admin"]}>
      <div className="min-h-screen bg-bg-canvas text-text-primary p-8 space-y-8">
        
        {/* Navigation back */}
        <div className="flex items-center gap-4">
          <Button variant="secondary" size="sm" onClick={() => router.back()}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Cockpit
          </Button>
          <div className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-brand-primary" />
            <span className="text-sm font-semibold text-text-secondary uppercase">Threat Entity Intelligence Dossier</span>
          </div>
        </div>

        {isLoading ? (
          <div className="flex flex-col items-center justify-center p-24 gap-4">
            <Loader2 className="h-10 w-10 text-brand-primary animate-spin" />
            <p className="text-sm text-text-secondary">Retrieving ledger profiles and linked subgraphs...</p>
          </div>
        ) : errorMsg || !profile ? (
          <div className="flex flex-col items-center justify-center p-24 gap-3 bg-bg-surface border border-border-default rounded-lg">
            <AlertCircle className="h-10 w-10 text-severity-critical" />
            <p className="text-sm font-bold text-severity-critical">{errorMsg || "Unknown Error"}</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            
            {/* Left dossiers profile details column */}
            <div className="space-y-6 lg:col-span-1">
              <Card className="p-6 space-y-6">
                <div>
                  <span className="text-xs font-bold text-brand-primary uppercase tracking-widest">{profile.type} Dossier</span>
                  <h1 className="text-2xl font-extrabold tracking-tight mt-1 break-all">
                    {profile.raw_value}
                  </h1>
                </div>

                <div className="border-t border-border-default pt-4 space-y-4">
                  <div className="flex justify-between items-center text-sm">
                    <span className="text-text-secondary">Risk Score Value</span>
                    <Badge variant={getBadgeVariant(profile.risk_tier)}>
                      {profile.risk_score} / 100
                    </Badge>
                  </div>
                  <div className="flex justify-between items-center text-sm">
                    <span className="text-text-secondary">Incident occurrences</span>
                    <span className="font-semibold">{profile.occurrence_count} reports</span>
                  </div>
                  <div className="flex justify-between items-center text-sm">
                    <span className="text-text-secondary">First Ingestion</span>
                    <span className="text-xs font-medium text-right">{formatDate(profile.first_seen_at)}</span>
                  </div>
                  <div className="flex justify-between items-center text-sm">
                    <span className="text-text-secondary">Last Update</span>
                    <span className="text-xs font-medium text-right">{formatDate(profile.last_seen_at)}</span>
                  </div>
                </div>
              </Card>

              {/* Linked complaints incidents timeline */}
              <Card className="p-6 space-y-4">
                <h3 className="font-bold flex items-center gap-2 border-b border-border-default pb-3">
                  <FileText className="h-4.5 w-4.5 text-brand-primary" />
                  Linked Incidents Log ({profile.linked_reports.length})
                </h3>
                
                {profile.linked_reports.length === 0 ? (
                  <p className="text-xs text-text-secondary italic">No incident tickets logged for this entity.</p>
                ) : (
                  <div className="space-y-4 max-h-72 overflow-y-auto pr-1">
                    {profile.linked_reports.map((rep) => (
                      <div key={rep.id} className="relative pl-6 border-l-2 border-border-default pb-2 last:pb-0">
                        <div className="absolute -left-1.5 top-1.5 h-3 w-3 bg-brand-primary rounded-full border-2 border-bg-surface" />
                        <div className="flex justify-between items-center text-xs">
                          <span className="font-bold">Ticket: #{rep.id.substring(0, 8)}</span>
                          <span className="text-text-secondary">{new Date(rep.created_at).toLocaleDateString()}</span>
                        </div>
                        <p className="text-[10px] text-text-secondary uppercase mt-0.5">Ingest: {rep.source_type}</p>
                      </div>
                    ))}
                  </div>
                )}
              </Card>
            </div>

            {/* Right local neighborhood subgraph visualization column */}
            <div className="lg:col-span-2 space-y-6">
              <Card className="p-6 flex flex-col h-full">
                <div className="flex items-center gap-2 border-b border-border-default pb-3 mb-4">
                  <Network className="h-5 w-5 text-brand-primary" />
                  <div>
                    <h3 className="font-bold">Threat Neighbor network</h3>
                    <p className="text-xs text-text-secondary">Spring-forces network of co-occurring scam entities</p>
                  </div>
                </div>

                <div className="flex-1 bg-bg-canvas rounded-md border border-border-default relative overflow-hidden h-[400px]">
                  <canvas
                    ref={canvasRef}
                    width={600}
                    height={400}
                    className="w-full h-full block"
                  />
                  <div className="absolute bottom-4 left-4 text-[10px] bg-bg-surface border border-border-default px-2 py-1 rounded text-text-secondary flex gap-4">
                    <span className="flex items-center gap-1">
                      <span className="h-2 w-2 rounded-full bg-red-500" /> Center Entity
                    </span>
                    <span className="flex items-center gap-1">
                      <span className="h-2 w-2 rounded-full bg-emerald-500" /> Co-occurring Neighbors
                    </span>
                  </div>
                </div>
              </Card>
            </div>

          </div>
        )}

      </div>
    </RoleGuard>
  );
}
