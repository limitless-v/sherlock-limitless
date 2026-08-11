'use client';

import { cn } from '@/utils/cn';
import { Check, Loader2, X } from 'lucide-react';

export type StepStatus = 'pending' | 'active' | 'completed' | 'failed';

interface ProgressStepProps {
  label: string;
  status: StepStatus;
  icon?: React.ReactNode;
  isLast?: boolean;
}

export function ProgressStep({ label, status, icon, isLast }: ProgressStepProps) {
  const statusStyles = {
    pending: 'text-muted-foreground',
    active: 'text-primary',
    completed: 'text-success',
    failed: 'text-danger',
  };

  const getIndicator = () => {
    switch (status) {
      case 'pending':
        return <div className="flex h-8 w-8 items-center justify-center rounded-full bg-muted text-muted-foreground" />;
      case 'active':
        return (
          <div className="relative flex h-8 w-8 items-center justify-center rounded-full bg-primary text-white">
            <Loader2 className="h-4 w-4 animate-spin" />
            <div className="absolute inset-0 rounded-full bg-primary/30 animate-ping" />
          </div>
        );
      case 'completed':
        return (
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-success text-white">
            <Check className="h-4 w-4" />
          </div>
        );
      case 'failed':
        return (
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-danger text-white">
            <X className="h-4 w-4" />
          </div>
        );
    }
  };

  return (
    <div className="relative flex flex-col items-center gap-2">
      {!isLast && (
        <div className={cn('absolute left-1/2 -translate-x-1/2 top-[-12px] w-px h-20', status === 'completed' ? 'bg-success' : 'bg-border')} />
      )}
      <div className="relative z-10">{getIndicator()}</div>
      <p className={cn('text-xs font-medium text-center whitespace-nowrap max-w-[100px]', statusStyles[status])}>
        {label}
      </p>
    </div>
  );
}

interface ProgressTrackerProps {
  steps: Array<{ label: string; key: string }>;
  currentStep: string;
  completedSteps: string[];
  failedStep?: string;
}

export function ProgressTracker({ steps, currentStep, completedSteps, failedStep }: ProgressTrackerProps) {
  return (
    <div className="flex items-center justify-center gap-4 overflow-x-auto pb-4">
      {steps.map((step, index) => (
        <ProgressStep
          key={step.key}
          label={step.label}
          status={
            failedStep === step.key
              ? 'failed'
              : currentStep === step.key
              ? 'active'
              : completedSteps.includes(step.key)
              ? 'completed'
              : 'pending'
          }
          isLast={index === steps.length - 1}
        />
      ))}
    </div>
  );
}