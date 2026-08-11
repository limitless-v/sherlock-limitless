'use client';

import { HTMLAttributes, forwardRef } from 'react';
import { cn } from '@/utils/cn';

export type BadgeVariant = 
  | 'default' 
  | 'strong' 
  | 'medium' 
  | 'weak' 
  | 'primary' 
  | 'success' 
  | 'danger' 
  | 'completed' 
  | 'degraded' 
  | 'failed' 
  | 'running' 
  | 'pending';

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
  size?: 'sm' | 'md';
}

export const Badge = forwardRef<HTMLSpanElement, BadgeProps>(
  ({ className, variant = 'default', size = 'md', children, ...props }, ref) => {
    const variants: Record<BadgeVariant, string> = {
      default: 'bg-muted text-muted-foreground border-border',
      strong: 'bg-success/15 text-success border-success/30',
      medium: 'bg-accent/15 text-accent border-accent/30',
      weak: 'bg-muted text-muted-foreground border-border',
      primary: 'bg-primary/15 text-primary border-primary/30',
      success: 'bg-success/15 text-success border-success/30',
      danger: 'bg-danger/15 text-danger border-danger/30',
      completed: 'bg-success/15 text-success border-success/30',
      degraded: 'bg-accent/15 text-accent border-accent/30',
      failed: 'bg-danger/15 text-danger border-danger/30',
      running: 'bg-primary/15 text-primary border-primary/30',
      pending: 'bg-muted text-muted-foreground border-border',
    };
    
    const sizes = {
      sm: 'px-2 py-0.5 text-xs',
      md: 'px-2.5 py-1 text-sm',
    };

    return (
      <span
        ref={ref}
        className={cn(
          'inline-flex items-center gap-1.5 rounded-full border font-medium',
          variants[variant],
          sizes[size],
          className
        )}
        {...props}
      >
        {children}
      </span>
    );
  }
);

Badge.displayName = 'Badge';