'use client';

import { cn } from '@/utils/cn';
import type { SearchMode } from '@/types/search';

interface SearchModeSelectProps {
  value: SearchMode;
  onChange: (mode: SearchMode) => void;
  disabled?: boolean;
}

const modes: Array<{ value: SearchMode; label: string; description: string; icon: string }> = [
  {
    value: 'local',
    label: 'Local',
    description: 'Search local face index only',
    icon: '💾',
  },
  {
    value: 'internet',
    label: 'Internet',
    description: 'Discover public profiles via OSINT',
    icon: '🌐',
  },
  {
    value: 'hybrid',
    label: 'Hybrid',
    description: 'Combine local + internet search',
    icon: '⚡',
  },
];

export function SearchModeSelect({ value, onChange, disabled }: SearchModeSelectProps) {
  return (
    <div className="w-full">
      <div className="grid grid-cols-3 gap-2" role="radiogroup" aria-label="Search mode">
        {modes.map((mode) => (
          <button
            key={mode.value}
            type="button"
            role="radio"
            aria-checked={value === mode.value}
            onClick={() => !disabled && onChange(mode.value)}
            disabled={disabled}
            className={cn(
              'relative flex flex-col items-center justify-center gap-2 rounded-xl p-4 border-2 transition-all duration-200',
              'focus-ring',
              value === mode.value
                ? 'border-primary bg-primary/5 text-primary'
                : 'border-border bg-background-elevated text-foreground hover:border-primary/50',
              disabled && 'opacity-50 cursor-not-allowed'
            )}
          >
            <span className="text-2xl" aria-hidden="true">{mode.icon}</span>
            <span className="font-medium">{mode.label}</span>
            <span className="text-xs text-muted-foreground text-center">{mode.description}</span>
            {value === mode.value && (
              <div className="absolute bottom-0 left-1/2 -translate-x-1/2 h-1 w-3/4 bg-primary rounded-full" />
            )}
          </button>
        ))}
      </div>
    </div>
  );
}