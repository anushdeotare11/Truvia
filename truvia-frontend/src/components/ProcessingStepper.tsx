"use client";

import { Icon } from "@/components/Icon";

type PipelineStage =
  | "ingesting"
  | "extracting_text"
  | "evaluating_threat"
  | "extracting_entities"
  | "indexing_graph"
  | "completed";

interface ProcessingStepperProps {
  stage: string | null;
}

const STAGES: { key: PipelineStage; label: string; icon: string }[] = [
  { key: "ingesting", label: "Submitting Report", icon: "upload" },
  { key: "extracting_text", label: "Extracting Text", icon: "description" },
  { key: "evaluating_threat", label: "Evaluating Threats", icon: "shield" },
  { key: "extracting_entities", label: "Extracting Entities", icon: "hub" },
  { key: "indexing_graph", label: "Indexing Graph", icon: "account_tree" },
  { key: "completed", label: "Analysis Complete", icon: "check_circle" },
];

function getStageIndex(stage: string | null): number {
  if (!stage) return -1;
  return STAGES.findIndex((s) => s.key === stage);
}

export function ProcessingStepper({ stage }: ProcessingStepperProps) {
  const activeIndex = getStageIndex(stage);

  return (
    <div className="flex flex-col sm:flex-row items-start sm:items-center gap-2 sm:gap-0 w-full">
      {STAGES.map((s, i) => {
        const isCompleted = activeIndex > i || (stage === "completed" && i === STAGES.length - 1);
        const isActive = activeIndex === i && stage !== "completed";

        return (
          <div key={s.key} className="flex items-center flex-1 w-full sm:w-auto">
            {/* Step indicator + label */}
            <div className="flex items-center gap-2 min-w-0">
              {/* Icon / number indicator */}
              <div
                className={`relative flex items-center justify-center w-8 h-8 rounded-full shrink-0 ${
                  isCompleted
                    ? "bg-primary/20"
                    : isActive
                    ? "bg-primary-container/30"
                    : "bg-surface-container-high"
                }`}
              >
                {isCompleted ? (
                  <Icon name="check" className="text-primary text-[18px]" />
                ) : isActive ? (
                  <>
                    {/* Pulse ring */}
                    <span className="absolute inset-0 rounded-full bg-primary/20 animate-ping" />
                    <Icon name={s.icon} className="text-primary text-[18px] relative z-10" />
                  </>
                ) : (
                  <Icon name={s.icon} className="text-on-surface-variant/50 text-[18px]" />
                )}
              </div>

              {/* Label */}
              <span
                className={`text-body-sm whitespace-nowrap ${
                  isCompleted
                    ? "text-primary"
                    : isActive
                    ? "text-on-surface font-medium"
                    : "text-on-surface-variant/50"
                }`}
              >
                {s.label}
              </span>
            </div>

            {/* Connector line (hidden for last item) */}
            {i < STAGES.length - 1 && (
              <div
                className={`hidden sm:block flex-1 h-px mx-3 ${
                  activeIndex > i ? "bg-primary/40" : "bg-outline-variant/30"
                }`}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
