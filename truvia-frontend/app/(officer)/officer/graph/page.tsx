"use client";

import React, { useState, useEffect, useRef } from "react";
import { useAuth } from "@/context/auth-context";
import { apiClient } from "@/lib/api-client";
import Button from "@/components/ui/Button";
import Card from "@/components/ui/Card";
import Badge from "@/components/ui/Badge";
import RoleGuard from "@/components/auth/RoleGuard";
import { ShieldAlert, Network, Search, Filter, ZoomIn, ZoomOut, RotateCcw, AlertTriangle, UserCheck, X, Link2, Loader2 } from "lucide-react";

interface GraphNode {
  id: string;
  label: string;
  type: string;
  risk_score: number;
  group: number;
  // Physics properties
  x: number;
  y: number;
  vx: number;
  vy: number;
}

interface GraphEdge {
  source: string;
  target: string;
  type: string;
  weight: number;
}

export default function SOCGraphCockpit() {
  const { logout } = useAuth();
  
  // Graph data states
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Filters
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedTypeFilter, setSelectedTypeFilter] = useState<string>("all");
  
  // UI Interaction states
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [hoveredNode, setHoveredNode] = useState<GraphNode | null>(null);
  const [relatedReports, setRelatedReports] = useState<any[]>([]);
  const [isLoadingDetails, setIsLoadingDetails] = useState(false);

  // Canvas refs and zoom/pan states
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const transformRef = useRef({ x: 0, y: 0, k: 1 });
  const isDraggingRef = useRef(false);
  const lastMousePosRef = useRef({ x: 0, y: 0 });

  // Force simulation constants
  const kRepulsion = 800;
  const kAttraction = 0.04;
  const kGravity = 0.01;
  const restLength = 120;
  const damping = 0.85;

  // Load Graph Data
  useEffect(() => {
    async function loadGraphData() {
      setIsLoading(true);
      setErrorMsg(null);
      try {
        const response = await apiClient.get<{ nodes: any[]; edges: any[] }>("/graph/overview");
        
        // Initialize node positions randomly around center
        const width = 800;
        const height = 500;
        const initializedNodes = response.nodes.map((node: any) => ({
          ...node,
          x: width / 2 + (Math.random() - 0.5) * 300,
          y: height / 2 + (Math.random() - 0.5) * 300,
          vx: 0,
          vy: 0
        }));
        
        setNodes(initializedNodes);
        setEdges(response.edges);
      } catch (err: any) {
        console.error("Failed to load threat graph:", err);
        setErrorMsg("Failed to load SOC threat graph network. Verify database.");
      } finally {
        setIsLoading(false);
      }
    }
    loadGraphData();
  }, []);

  // Fetch Entity details when clicked
  useEffect(() => {
    async function fetchEntityDetails() {
      if (!selectedNode) return;
      setIsLoadingDetails(true);
      try {
        // Mocking related reports lookups for local sqlite fallback
        const response = await apiClient.get<any[]>(`/reports`);
        
        // Filter reports containing selected node label
        const filtered = response.filter((rep: any) => 
          (rep.cleaned_text && rep.cleaned_text.toLowerCase().includes(selectedNode.label.toLowerCase()))
        );
        setRelatedReports(filtered);
      } catch (err) {
        console.error("Error loading node details:", err);
      } finally {
        setIsLoadingDetails(false);
      }
    }
    fetchEntityDetails();
  }, [selectedNode]);

  // Run Custom Physics Simulation Loop
  useEffect(() => {
    if (nodes.length === 0) return;

    let animId: number;
    const width = 800;
    const height = 500;

    const runPhysicsFrame = () => {
      // 1. Repulsion forces (Coulomb's Law)
      for (let i = 0; i < nodes.length; i++) {
        const n1 = nodes[i];
        for (let j = i + 1; j < nodes.length; j++) {
          const n2 = nodes[j];
          const dx = n1.x - n2.x;
          const dy = n1.y - n2.y;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          
          if (dist < 400) {
            const force = kRepulsion / (dist * dist);
            n1.vx += (dx / dist) * force;
            n1.vy += (dy / dist) * force;
            n2.vx -= (dx / dist) * force;
            n2.vy -= (dy / dist) * force;
          }
        }
      }

      // 2. Attraction forces (Hooke's Law)
      edges.forEach((edge) => {
        const sourceNode = nodes.find(n => n.id === edge.source);
        const targetNode = nodes.find(n => n.id === edge.target);
        
        if (sourceNode && targetNode) {
          const dx = targetNode.x - sourceNode.x;
          const dy = targetNode.y - sourceNode.y;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          
          const force = kAttraction * (dist - restLength);
          const fx = (dx / dist) * force;
          const fy = (dy / dist) * force;
          
          sourceNode.vx += fx;
          sourceNode.vy += fy;
          targetNode.vx -= fx;
          targetNode.vy -= fy;
        }
      });

      // 3. Gravity and Update positions
      nodes.forEach((node) => {
        // Attraction to center
        node.vx += (width / 2 - node.x) * kGravity;
        node.vy += (height / 2 - node.y) * kGravity;

        // Apply velocity & damping
        node.x += node.vx;
        node.y += node.vy;
        node.vx *= damping;
        node.vy *= damping;
      });

      // 4. Render Frame on Canvas
      drawGraph();
      animId = requestAnimationFrame(runPhysicsFrame);
    };

    const drawGraph = () => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;

      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.save();
      
      // Apply Pan & Zoom transformations
      ctx.translate(transformRef.current.x, transformRef.current.y);
      ctx.scale(transformRef.current.k, transformRef.current.k);

      // Filtered lists for rendering hover/fade effects
      const filteredNodeIds = new Set(
        nodes
          .filter(n => {
            const matchesSearch = n.label.toLowerCase().includes(searchQuery.toLowerCase());
            const matchesType = selectedTypeFilter === "all" || n.type === selectedTypeFilter;
            return matchesSearch && matchesType;
          })
          .map(n => n.id)
      );

      // A. Draw Edges
      edges.forEach((edge) => {
        const sourceNode = nodes.find(n => n.id === edge.source);
        const targetNode = nodes.find(n => n.id === edge.target);
        
        if (sourceNode && targetNode) {
          const isRelated = hoveredNode
            ? (edge.source === hoveredNode.id || edge.target === hoveredNode.id)
            : true;
          
          const isFiltered = filteredNodeIds.has(edge.source) && filteredNodeIds.has(edge.target);

          ctx.beginPath();
          ctx.moveTo(sourceNode.x, sourceNode.y);
          ctx.lineTo(targetNode.x, targetNode.y);
          ctx.strokeStyle = isFiltered && isRelated ? "#3B82F6" : "#2D3748";
          ctx.lineWidth = isRelated ? 2 : 0.8;
          ctx.stroke();
        }
      });

      // B. Draw Nodes
      nodes.forEach((node) => {
        const isHovered = hoveredNode?.id === node.id;
        const isSelected = selectedNode?.id === node.id;
        const isFiltered = filteredNodeIds.has(node.id);
        const opacity = isFiltered ? (hoveredNode && !isHovered ? 0.3 : 1.0) : 0.15;

        // Custom community color palette
        const colors = [
          "#EF4444", "#3B82F6", "#10B981", "#F59E0B", 
          "#8B5CF6", "#EC4899", "#14B8A6", "#06B6D4"
        ];
        const nodeColor = colors[node.group % colors.length];

        ctx.beginPath();
        // Radius scales with risk score (min 10, max 22)
        const radius = 10 + (node.risk_score / 100) * 12;
        ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI);
        
        ctx.fillStyle = nodeColor;
        ctx.globalAlpha = opacity;
        ctx.fill();

        // Stroke highlight
        ctx.strokeStyle = isSelected ? "#FFFFFF" : isHovered ? "#93C5FD" : "#0F172A";
        ctx.lineWidth = isSelected ? 3 : isHovered ? 2.5 : 1.5;
        ctx.globalAlpha = opacity;
        ctx.stroke();

        // Text label
        ctx.font = isHovered || isSelected ? "bold 12px Inter" : "10px Inter";
        ctx.fillStyle = isHovered || isSelected ? "#FFFFFF" : "#A0AEC0";
        ctx.fillText(node.label, node.x + radius + 4, node.y + 4);
        ctx.globalAlpha = 1.0; // Reset
      });

      ctx.restore();
    };

    animId = requestAnimationFrame(runPhysicsFrame);
    return () => cancelAnimationFrame(animId);
  }, [nodes, edges, searchQuery, selectedTypeFilter, hoveredNode, selectedNode]);

  // Zoom controls
  const handleZoom = (zoomIn: boolean) => {
    transformRef.current.k = zoomIn 
      ? Math.min(transformRef.current.k * 1.2, 5) 
      : Math.max(transformRef.current.k / 1.2, 0.2);
  };

  const handleResetZoom = () => {
    transformRef.current = { x: 0, y: 0, k: 1 };
  };

  // Drag to Pan & Click to select Handlers
  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    isDraggingRef.current = true;
    lastMousePosRef.current = { x: e.clientX, y: e.clientY };
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    
    // Convert client coordinates to canvas scale coordinates
    const mx = (e.clientX - rect.left - transformRef.current.x) / transformRef.current.k;
    const my = (e.clientY - rect.top - transformRef.current.y) / transformRef.current.k;

    // Pan engine
    if (isDraggingRef.current) {
      const dx = e.clientX - lastMousePosRef.current.x;
      const dy = e.clientY - lastMousePosRef.current.y;
      transformRef.current.x += dx;
      transformRef.current.y += dy;
      lastMousePosRef.current = { x: e.clientX, y: e.clientY };
      return;
    }

    // Hover detection
    const foundNode = nodes.find(node => {
      const dx = node.x - mx;
      const dy = node.y - my;
      const radius = 10 + (node.risk_score / 100) * 12;
      return (dx * dx + dy * dy) < (radius * radius);
    });

    setHoveredNode(foundNode || null);
  };

  const handleMouseUp = (e: React.MouseEvent<HTMLCanvasElement>) => {
    isDraggingRef.current = false;
    
    // If not a drag, detect click selection
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const mx = (e.clientX - rect.left - transformRef.current.x) / transformRef.current.k;
    const my = (e.clientY - rect.top - transformRef.current.y) / transformRef.current.k;

    const clickedNode = nodes.find(node => {
      const dx = node.x - mx;
      const dy = node.y - my;
      const radius = 10 + (node.risk_score / 100) * 12;
      return (dx * dx + dy * dy) < (radius * radius);
    });

    if (clickedNode) {
      setSelectedNode(clickedNode);
    }
  };

  const getBadgeVariant = (tier: string) => {
    if (tier === "critical") return "critical";
    if (tier === "high") return "high";
    if (tier === "moderate") return "moderate";
    return "low";
  };

  const getEntityRiskTier = (score: number): "low" | "moderate" | "high" | "critical" => {
    if (score >= 80) return "critical";
    if (score >= 60) return "high";
    if (score >= 35) return "moderate";
    return "low";
  };

  return (
    <RoleGuard allowedRoles={["officer", "admin"]}>
      <div className="min-h-screen bg-bg-canvas text-text-primary flex dark">
        {/* Left Control Sidebar */}
        <aside className="w-80 border-r border-border-default bg-bg-surface flex flex-col p-6 space-y-6">
          <div className="flex items-center gap-2">
            <Network className="h-6 w-6 text-brand-primary" />
            <h2 className="text-xl font-bold tracking-tight">Threat Graph</h2>
          </div>
          <a href="/officer/dashboard" className="text-xs font-semibold text-brand-primary hover:underline flex items-center gap-1">
            ← Return to SOC Cockpit
          </a>

          {/* Search bar */}
          <div className="relative">
            <Search className="absolute left-3 top-2.5 h-4.5 w-4.5 text-text-secondary" />
            <input
              type="text"
              placeholder="Search raw values..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-bg-surface-sunken border border-border-default rounded-md text-sm focus:outline-none focus:border-brand-primary"
            />
          </div>

          {/* Type Filters */}
          <div className="space-y-2">
            <label className="text-xs font-bold uppercase tracking-wider text-text-secondary flex items-center gap-1.5">
              <Filter className="h-3.5 w-3.5" />
              Entity Category
            </label>
            <div className="grid grid-cols-2 gap-2">
              {[
                { label: "All Types", value: "all" },
                { label: "Phone numbers", value: "phone" },
                { label: "UPI Addresses", value: "upi" },
                { label: "Emails", value: "email" },
                { label: "Domains", value: "domain" }
              ].map((filter) => (
                <button
                  key={filter.value}
                  onClick={() => setSelectedTypeFilter(filter.value)}
                  className={`px-3 py-2 text-xs font-medium border rounded transition-all duration-150 ${
                    selectedTypeFilter === filter.value
                      ? "border-brand-primary bg-brand-primary/20 text-brand-primary"
                      : "border-border-default bg-bg-surface hover:bg-bg-surface-hover text-text-secondary"
                  }`}
                >
                  {filter.label}
                </button>
              ))}
            </div>
          </div>

          {/* Statistics Card */}
          <Card className="p-4 space-y-3 bg-bg-surface-sunken">
            <h4 className="text-xs font-bold uppercase tracking-wider text-text-secondary">Network Summary</h4>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-[10px] text-text-secondary uppercase">Vertices</p>
                <p className="text-xl font-extrabold">{nodes.length}</p>
              </div>
              <div>
                <p className="text-[10px] text-text-secondary uppercase">Edges</p>
                <p className="text-xl font-extrabold">{edges.length}</p>
              </div>
            </div>
          </Card>

          {/* Instructions */}
          <div className="text-xs text-text-secondary space-y-1 bg-brand-primary/5 p-3 rounded-md border border-brand-primary/10">
            <p className="font-semibold text-brand-primary mb-1">Navigation Controls:</p>
            <p>• Click and drag the background to PAN.</p>
            <p>• Hover over nodes to inspect values.</p>
            <p>• Click nodes to unlock graph profile.</p>
          </div>
        </aside>

        {/* Main Canvas Area */}
        <main className="flex-1 flex flex-col relative bg-bg-canvas">
          {/* Top Panel Controls */}
          <div className="h-16 border-b border-border-default px-8 flex items-center justify-between bg-bg-surface z-10">
            <div className="flex items-center gap-3">
              <Badge variant="assigned">SOC COCKPIT</Badge>
              <h3 className="font-bold">Real-time Louvain Scam Rings</h3>
            </div>
            
            {/* Zoom Button cluster */}
            <div className="flex gap-2">
              <Button variant="secondary" size="sm" onClick={() => handleZoom(true)}>
                <ZoomIn className="h-4.5 w-4.5" />
              </Button>
              <Button variant="secondary" size="sm" onClick={() => handleZoom(false)}>
                <ZoomOut className="h-4.5 w-4.5" />
              </Button>
              <Button variant="secondary" size="sm" onClick={handleResetZoom}>
                <RotateCcw className="h-4.5 w-4.5" />
              </Button>
            </div>
          </div>

          {/* HTML5 Canvas Render target */}
          <div className="flex-1 relative cursor-crosshair">
            {isLoading ? (
              <div className="absolute inset-0 flex flex-col items-center justify-center gap-3">
                <Loader2 className="h-10 w-10 text-brand-primary animate-spin" />
                <p className="text-sm font-semibold tracking-wide text-text-secondary">Simulating graph physics...</p>
              </div>
            ) : errorMsg ? (
              <div className="absolute inset-0 flex flex-col items-center justify-center gap-3">
                <AlertTriangle className="h-10 w-10 text-severity-critical" />
                <p className="text-sm font-bold text-severity-critical">{errorMsg}</p>
              </div>
            ) : (
              <canvas
                ref={canvasRef}
                width={800}
                height={500}
                onMouseDown={handleMouseDown}
                onMouseMove={handleMouseMove}
                onMouseUp={handleMouseUp}
                className="w-full h-full bg-bg-canvas block"
              />
            )}
          </div>
        </main>

        {/* Right Entity Profile panel (Day 8 target!) */}
        {selectedNode && (
          <aside className="w-96 border-l border-border-default bg-bg-surface p-6 flex flex-col space-y-6 z-20 animate-in slide-in-from-right duration-200">
            <div className="flex justify-between items-start">
              <div>
                <span className="text-[10px] font-bold text-brand-primary uppercase tracking-widest">{selectedNode.type} Entity</span>
                <h3 className="text-xl font-bold tracking-tight mt-0.5 break-all max-w-[240px]">
                  {selectedNode.label}
                </h3>
              </div>
              <Button variant="icon-only" onClick={() => setSelectedNode(null)}>
                <X className="h-5 w-5" />
              </Button>
            </div>

            {/* Risk profile card */}
            <Card className="p-4 space-y-4">
              <div className="flex justify-between items-center">
                <span className="text-sm font-semibold">Calculated Threat Rating</span>
                <Badge variant={getBadgeVariant(getEntityRiskTier(selectedNode.risk_score))}>
                  {selectedNode.risk_score} / 100
                </Badge>
              </div>
              <div className="space-y-1">
                <div className="w-full bg-bg-surface-sunken h-2 rounded-full overflow-hidden">
                  <div 
                    className={`h-full rounded-full transition-all duration-300 ${
                      selectedNode.risk_score >= 80 
                        ? "bg-severity-critical" 
                        : selectedNode.risk_score >= 60 
                        ? "bg-severity-high" 
                        : selectedNode.risk_score >= 35 
                        ? "bg-severity-moderate" 
                        : "bg-severity-low"
                    }`}
                    style={{ width: `${selectedNode.risk_score}%` }}
                  />
                </div>
                <p className="text-[10px] text-text-secondary text-right">Cluster gravity weight: {selectedNode.group}</p>
              </div>
            </Card>

            {/* Ingested Reports Section */}
            <div className="space-y-3 flex-1 overflow-y-auto">
              <h4 className="text-xs font-bold uppercase tracking-wider text-text-secondary flex items-center gap-1">
                <Link2 className="h-3.5 w-3.5" />
                Linked Ingest Incidents ({relatedReports.length})
              </h4>
              
              {isLoadingDetails ? (
                <div className="flex items-center gap-2 text-sm text-text-secondary">
                  <Loader2 className="h-4 w-4 animate-spin text-brand-primary" />
                  Searching ledgers...
                </div>
              ) : relatedReports.length === 0 ? (
                <p className="text-xs text-text-secondary italic">No incidents directly linked in standard SQL tables.</p>
              ) : (
                <div className="space-y-3">
                  {relatedReports.map((rep) => (
                    <Card key={rep.id} className="p-3 space-y-2 bg-bg-surface-sunken hover:bg-bg-surface-hover transition-all duration-150">
                      <div className="flex justify-between items-center">
                        <span className="text-xs font-bold">Ticket: #{rep.id.substring(0, 8)}</span>
                        <Badge variant={rep.status === "escalated" ? "critical" : "assigned"}>
                          {rep.status}
                        </Badge>
                      </div>
                      <p className="text-xs text-text-secondary line-clamp-2 italic">
                        "{rep.cleaned_text}"
                      </p>
                    </Card>
                  ))}
                </div>
              )}
            </div>
          </aside>
        )}
      </div>
    </RoleGuard>
  );
}
