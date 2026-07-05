import React from "react";
import { Check, Loader2, AlertTriangle, ShieldAlert } from "lucide-react";

export interface ProcessingStepperProps {
  status: "submitted" | "processing" | "processed" | "scored" | "escalated" | "failed";
  lowConfidenceFlag: boolean;
  onEditTranscription?: () => void;
}

export default function ProcessingStepper({
  status,
  lowConfidenceFlag,
  onEditTranscription
}: ProcessingStepperProps) {
  
  const steps = [
    {
      id: "intake",
      label: "Document Ingestion",
      description: "Evidence received & stored",
      isComplete: ["submitted", "processing", "processed", "scored", "escalated"].includes(status),
      isActive: status === "submitted"
    },
    {
      id: "ocr_asr",
      label: "OCR / Voice Transcription",
      description: "Extracting readable contents",
      isComplete: ["processed", "scored", "escalated"].includes(status),
      isActive: status === "processing"
    },
    {
      id: "threat",
      label: "AI Threat Evaluation",
      description: "Scoring risk band",
      isComplete: ["scored", "escalated"].includes(status),
      isActive: status === "processed"
    },
    {
      id: "entity",
      label: "Relationship Mapping",
      description: "Connecting nodes to SOC network",
      isComplete: ["escalated"].includes(status),
      isActive: status === "scored"
    }
  ];

  return (
    <div className="w-full space-y-6">
      <div className="flex flex-col gap-4 md:flex-row md:justify-between md:items-start">
        {steps.map((step, idx) => {
          const isDone = step.isComplete;
          const isCurrent = step.isActive;
          
          return (
            <div key={step.id} className="flex-1 flex gap-3 md:flex-col md:items-center text-left md:text-center relative">
              {/* Connector line for desktop */}
              {idx < steps.length - 1 && (
                <div 
                  className={`hidden md:block absolute top-5 left-[60%] right-[-40%] h-0.5 transition-all duration-300 ${
                    isDone ? "bg-brand-primary" : "bg-border-default"
                  }`} 
                />
              )}

              {/* Step indicator circle */}
              <div 
                className={`h-10 w-10 rounded-full flex items-center justify-center shrink-0 border-2 transition-all duration-150 ${
                  isDone 
                    ? "bg-brand-primary border-brand-primary text-text-on-brand"
                    : isCurrent
                      ? "border-brand-primary text-brand-primary bg-bg-surface shadow-[0_0_0_4px_rgba(25,89,184,0.15)]"
                      : "border-border-default text-text-secondary bg-bg-surface-sunken"
                }`}
              >
                {isDone ? (
                  <Check className="h-5 w-5 stroke-[2.5]" />
                ) : isCurrent ? (
                  <Loader2 className="h-5 w-5 animate-spin" />
                ) : (
                  <span className="text-sm font-semibold">{idx + 1}</span>
                )}
              </div>

              {/* Labels */}
              <div className="flex flex-col gap-0.5">
                <span className={`font-semibold text-sm ${isCurrent ? "text-brand-primary" : "text-text-primary"}`}>
                  {step.label}
                </span>
                <span className="text-xs text-text-secondary">
                  {step.description}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Low confidence warning banner */}
      {lowConfidenceFlag && (
        <div className="p-4 rounded-lg bg-severity-moderate/10 border border-severity-moderate/30 flex flex-col sm:flex-row sm:items-center justify-between gap-4 mt-6 animate-pulse">
          <div className="flex items-start gap-3">
            <AlertTriangle className="h-5 w-5 text-severity-moderate shrink-0 mt-0.5" />
            <div>
              <h4 className="font-bold text-sm text-text-primary">Low-Confidence Transcript Detected</h4>
              <p className="text-xs text-text-secondary mt-0.5">
                OCR scan or voice quality returned less than 60% confidence score. Correcting details ensures accurate risk rating.
              </p>
            </div>
          </div>
          {onEditTranscription && (
            <button
              onClick={onEditTranscription}
              className="text-xs font-bold text-brand-primary hover:underline hover:text-brand-primary-hover shrink-0 self-start sm:self-center"
            >
              Verify Transcription
            </button>
          )}
        </div>
      )}
    </div>
  );
}
