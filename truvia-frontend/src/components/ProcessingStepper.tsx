"use client";

import { Fragment } from "react";
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
  const isDone = stage === "completed";
  const current = activeIndex >= 0 ? STAGES[activeIndex] : null;

  return (
    <div className="w-full">
      {/* Icon rail — fixed icons, flexible connectors (never overflows) */}
      <div className="flex items-center w-full">
        {STAGES.map((s, i) => {
          const isCompleted = activeIndex > i || (isDone && i === STAGES.length - 1);
          const isActive = activeIndex === i && !isDone;
          return (
            <Fragment key={s.key}>
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
                    <span className="absolute inset-0 rounded-full bg-primary/20 animate-ping" />
                    <Icon name={s.icon} className="text-primary text-[18px] relative z-10" />
                  </>
                ) : (
                  <Icon name={s.icon} className="text-on-surface-variant/50 text-[18px]" />
                )}
              </div>
              {i < STAGES.length - 1 && (
                <div
                  className={`flex-1 h-px mx-1.5 sm:mx-2 min-w-[6px] ${
                    activeIndex > i ? "bg-primary/40" : "bg-outline-variant/30"
                  }`}
                />
              )}
            </Fragment>
          );
        })}
      </div>

      {/* Single centered status label */}
      <p className="mt-3 text-center text-body-sm">
        <span className={isDone ? "text-primary font-medium" : "text-on-surface font-medium"}>
          {current ? (isDone ? current.label : `${current.label}…`) : "Preparing…"}
        </span>
      </p>
    </div>
  );
}
