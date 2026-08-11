'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Loader2, CheckCircle, AlertCircle, X, ChevronRight } from 'lucide-react';
import { cn } from '@/utils/cn';
import { ProgressTracker } from '@/components/ui/ProgressStep';
import { Card, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { ToastContainer, Toast } from '@/components/ui/Toast';
import { useSearch } from '@/hooks/useSearch';
import type { SearchStatus, SearchEvent } from '@/types/search';

const SEARCH_STEPS = [
  { key: 'upload', label: 'Uploading' },
  { key: 'analyze', label: 'Analyzing Image' },
  { key: 'metadata', label: 'Extracting Metadata' },
  { key: 'ocr', label: 'Running OCR' },
  { key: 'context', label: 'Building Context' },
  { key: 'search', label: 'Searching Sources' },
  { key: 'research', label: 'Analyzing Pages' },
  { key: 'correlate', label: 'Correlating Evidence' },
  { key: 'rank', label: 'Ranking Results' },
  { key: 'complete', label: 'Complete' },
];

const STEP_EVENT_MAP: Record<string, string> = {
  upload: 'upload_completed',
  analyze: 'analysis_completed',
  metadata: 'metadata_completed',
  ocr: 'ocr_completed',
  context: 'context_completed',
  search: 'search_completed',
  research: 'research_completed',
  correlate: 'correlation_completed',
  rank: 'ranking_completed',
  complete: 'search_completed',
};

export default function SearchProgressPage() {
  const params = useParams();
  const router = useRouter();
  const searchId = parseInt(params.id as string, 10);
  
  const [completedSteps, setCompletedSteps] = useState<string[]>([]);
  const [currentStep, setCurrentStep] = useState<string>('upload');
  const [failedStep, setFailedStep] = useState<string | undefined>();
  const [eventLog, setEventLog] = useState<Array<{ type: string; message: string; timestamp: string }>>([]);
  const [toasts, setToasts] = useState<Array<{ id: string; type: 'success' | 'error' | 'info'; message: string }>>([]);
  const eventSourceRef = useRef<EventSource | null>(null);
  const [isConnected, setIsConnected] = useState(false);

  const { data: search, isLoading, error, refetch } = useSearch(searchId);

  const addToast = (type: 'success' | 'error' | 'info', message: string) => {
    const id = Math.random().toString(36).slice(2);
    setToasts((prev) => [...prev, { id, type, message }]);
  };

  const removeToast = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  const addEventLog = useCallback((type: string, message: string) => {
    setEventLog((prev) => [...prev, { type, message, timestamp: new Date().toISOString() }]);
  }, []);

  useEffect(() => {
    if (!search) return;

    const status = search.status as SearchStatus;
    
    // Update current step based on status
    if (status === 'running' || status === 'pending') {
      // Find the first non-completed step
      const completedKeys = new Set(completedSteps);
      const nextStep = SEARCH_STEPS.find((s) => !completedKeys.has(s.key));
      if (nextStep) {
        setCurrentStep(nextStep.key);
      }
    } else if (status === 'completed' || status === 'degraded') {
      setCurrentStep('complete');
      setCompletedSteps(SEARCH_STEPS.map((s) => s.key));
      addToast('success', status === 'degraded' ? 'Search completed with warnings' : 'Search completed successfully');
      
      // Navigate to results after a short delay
      setTimeout(() => {
        router.push(`/search/${searchId}/results`);
      }, 2000);
    } else if (status === 'failed') {
      addToast('error', 'Search failed');
      setFailedStep(currentStep);
    }
  }, [search, completedSteps, currentStep, router, searchId, addToast]);

  // SSE Connection
  useEffect(() => {
    if (!searchId) return;

    const eventSource = new EventSource(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/search/${searchId}/events`);
    eventSourceRef.current = eventSource;

    eventSource.onopen = () => {
      setIsConnected(true);
      addEventLog('system', 'Connected to search progress stream');
    };

    eventSource.onerror = () => {
      setIsConnected(false);
      addEventLog('error', 'Connection lost, will retry...');
    };

    eventSource.addEventListener('search_started', (e: MessageEvent) => {
      const data = JSON.parse(e.data);
      addEventLog('info', `Search started: ${data.mode} mode`);
    });

    eventSource.addEventListener('stage_completed', (e: MessageEvent) => {
      const data = JSON.parse(e.data);
      const stage = data.stage || data.step;
      if (stage) {
        setCompletedSteps((prev) => [...new Set([...prev, stage])]);
        addEventLog('success', `Completed: ${stage}`);
      }
    });

    eventSource.addEventListener('stage_started', (e: MessageEvent) => {
      const data = JSON.parse(e.data);
      const stage = data.stage || data.step;
      if (stage) {
        setCurrentStep(stage);
        addEventLog('info', `Started: ${stage}`);
      }
    });

    eventSource.addEventListener('progress', (e: MessageEvent) => {
      const data = JSON.parse(e.data);
      addEventLog('info', data.message || `Progress: ${data.percent}%`);
    });

    eventSource.addEventListener('search_completed', (e: MessageEvent) => {
      const data = JSON.parse(e.data);
      addEventLog('success', `Search ${data.status}`);
      eventSource.close();
    });

    eventSource.addEventListener('search_failed', (e: MessageEvent) => {
      const data = JSON.parse(e.data);
      addEventLog('error', `Search failed: ${data.error}`);
      setFailedStep(currentStep);
      eventSource.close();
    });

    // Generic event handler
    eventSource.onmessage = (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data);
        if (data.event_type && !e.type.includes('_')) {
          addEventLog('info', `${data.event_type}: ${JSON.stringify(data.payload)}`);
        }
      } catch {
        addEventLog('info', e.data);
      }
    };

    return () => {
      eventSource.close();
      eventSourceRef.current = null;
    };
  }, [searchId, addEventLog]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="h-12 w-12 animate-spin text-primary" />
          <p>Loading search progress...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Card className="max-w-md w-full mx-4">
          <CardContent className="p-6 text-center">
            <AlertCircle className="h-12 w-12 text-danger mx-auto mb-4" />
            <h2 className="text-xl font-semibold mb-2">Failed to Load Search</h2>
            <p className="text-muted-foreground mb-4">Unable to load search progress. The search may not exist.</p>
            <Button onClick={() => router.back()}>Go Back</Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <ToastContainer toasts={toasts} onClose={removeToast} />
      
      <header className="border-b border-border bg-background/80 backdrop-blur sticky top-0 z-40">
        <div className="mx-auto max-w-6xl px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="sm" onClick={() => router.back()}>
              <ChevronRight className="h-4 w-4 rotate-180" />
            </Button>
            <div>
              <h1 className="font-semibold">Search Progress</h1>
              <p className="text-sm text-muted-foreground">Search #{searchId}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className={cn('flex h-2 w-2 rounded-full', isConnected ? 'bg-success' : 'bg-muted-foreground animate-pulse')} />
            <span className="text-xs text-muted-foreground">{isConnected ? 'Live' : 'Reconnecting...'}</span>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-8">
        <ProgressTracker
          steps={SEARCH_STEPS}
          currentStep={currentStep}
          completedSteps={completedSteps}
          failedStep={failedStep}
        />

        <div className="mt-8 grid gap-6 lg:grid-cols-2">
          <Card>
            <CardContent className="p-6">
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <Loader2 className="h-5 w-5 text-primary" />
                Status Details
              </h3>
              <div className="space-y-3">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Status</span>
                  <Badge variant={
                    search?.status === 'completed' ? 'success' :
                    search?.status === 'degraded' ? 'medium' :
                    search?.status === 'failed' ? 'danger' :
                    search?.status === 'running' ? 'primary' : 'weak'
                  }>
                    {search?.status || 'Unknown'}
                  </Badge>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Mode</span>
                  <span className="font-medium capitalize">{search?.mode || 'Unknown'}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Sources Checked</span>
                  <span className="font-medium">{search?.providers && Object.keys(search.providers).length || 0}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Pages Analyzed</span>
                  <span className="font-medium">
                    {search?.providers && typeof search.providers === 'object' && 'pages_analyzed' in search.providers 
                      ? (search.providers as Record<string, unknown>).pages_analyzed as number 
                      : 0}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <ChevronRight className="h-5 w-5 text-primary" />
                Event Log
              </h3>
              <div className="h-80 overflow-y-auto space-y-2 font-mono text-xs bg-background-elevated rounded-lg p-3">
                {eventLog.length === 0 ? (
                  <p className="text-muted-foreground text-center py-8">Waiting for events...</p>
                ) : (
                  eventLog.map((event, index) => (
                    <div key={index} className="flex gap-2 border-b border-border pb-2 last:border-0">
                      <span className="text-muted-foreground whitespace-nowrap">
                        {new Date(event.timestamp).toLocaleTimeString()}
                      </span>
                      <span className={cn(
                        'whitespace-nowrap',
                        event.type === 'success' && 'text-success',
                        event.type === 'error' && 'text-danger',
                        event.type === 'info' && 'text-primary',
                        event.type === 'system' && 'text-muted-foreground'
                      )}>
                        [{event.type.toUpperCase()}]
                      </span>
                      <span className="flex-1 truncate">{event.message}</span>
                    </div>
                  ))
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        {search && (search.status === 'completed' || search.status === 'degraded') && (
          <div className="mt-8 text-center">
            <Button 
              variant="primary" 
              size="lg" 
              onClick={() => router.push(`/search/${searchId}/results`)}
            >
              View Results
              <ChevronRight className="h-4 w-4 ml-2" />
            </Button>
          </div>
        )}
      </main>
    </div>
  );
}