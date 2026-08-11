'use client';

import { useState } from 'react';
import { Save, Loader2, Moon, Sun, Key, Bell, Shield, Database, Palette } from 'lucide-react';
import { cn } from '@/utils/cn';
import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardHeader } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Badge } from '@/components/ui/Badge';
import { ToastContainer, Toast } from '@/components/ui/Toast';
import { LoadingOverlay } from '@/components/ui/Spinner';

const THEMES = [
  { value: 'dark', label: 'Dark', icon: Moon },
  { value: 'light', label: 'Light', icon: Sun },
  { value: 'system', label: 'System', icon: Palette },
];

const SEARCH_MODES = [
  { value: 'local', label: 'Local Only', description: 'Search local face index only' },
  { value: 'internet', label: 'Internet (OSINT)', description: 'Discover public profiles via web search' },
  { value: 'hybrid', label: 'Hybrid', description: 'Combine local and internet search' },
];

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<'general' | 'search' | 'appearance' | 'api' | 'privacy'>('general');
  const [toasts, setToasts] = useState<Array<{ id: string; type: 'success' | 'error' | 'info'; message: string }>>([]);
  const [isSaving, setIsSaving] = useState(false);

  // Settings state
  const [settings, setSettings] = useState({
    // General
    defaultSearchMode: 'hybrid' as const,
    maxResults: 50,
    autoStartSearch: true,
    // Search
    enableLocalSearch: true,
    enableInternetSearch: true,
    similarityThreshold: 0.6,
    maxPagesPerSearch: 20,
    // Appearance
    theme: 'dark' as const,
    compactMode: false,
    showConfidenceColors: true,
    // API
    apiUrl: 'http://localhost:8000/api/v1',
    apiKey: '',
    // Privacy
    autoDeleteDays: 30,
    anonymizeData: false,
    shareUsageStats: false,
  });

  const addToast = (type: 'success' | 'error' | 'info', message: string) => {
    const id = Math.random().toString(36).slice(2);
    setToasts((prev) => [...prev, { id, type, message }]);
  };

  const removeToast = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      // In a real app, this would call an API
      await new Promise((resolve) => setTimeout(resolve, 1000));
      // Save to localStorage
      localStorage.setItem('sherlock_settings', JSON.stringify(settings));
      addToast('success', 'Settings saved successfully');
    } catch (error) {
      addToast('error', 'Failed to save settings');
    } finally {
      setIsSaving(false);
    }
  };

  const handleReset = () => {
    // Reset to defaults
    setSettings({
      defaultSearchMode: 'hybrid',
      maxResults: 50,
      autoStartSearch: true,
      enableLocalSearch: true,
      enableInternetSearch: true,
      similarityThreshold: 0.6,
      maxPagesPerSearch: 20,
      theme: 'dark',
      compactMode: false,
      showConfidenceColors: true,
      apiUrl: 'http://localhost:8000/api/v1',
      apiKey: '',
      autoDeleteDays: 30,
      anonymizeData: false,
      shareUsageStats: false,
    });
    addToast('info', 'Settings reset to defaults');
  };

  const tabs = [
    { id: 'general', label: 'General', icon: null },
    { id: 'search', label: 'Search', icon: null },
    { id: 'appearance', label: 'Appearance', icon: Palette },
    { id: 'api', label: 'API', icon: Key },
    { id: 'privacy', label: 'Privacy', icon: Shield },
  ];

  return (
    <div className="min-h-screen bg-background">
      <ToastContainer toasts={toasts} onClose={removeToast} />
      
      <header className="border-b border-border bg-background/80 backdrop-blur sticky top-0 z-40">
        <div className="mx-auto max-w-4xl px-4 py-4">
          <div className="flex items-center justify-between">
            <h1 className="text-2xl font-bold">Settings</h1>
            <div className="flex gap-2">
              <Button variant="outline" onClick={handleReset}>
                Reset
              </Button>
              <Button onClick={handleSave} disabled={isSaving}>
                {isSaving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                Save
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-4 py-8">
        <LoadingOverlay isLoading={isSaving}>
        <div className="flex flex-col lg:flex-row gap-8">
          {/* Sidebar */}
          <aside className="lg:w-48 flex-shrink-0">
            <nav className="space-y-1">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as typeof activeTab)}
                  className={cn(
                    'w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left transition-colors',
                    activeTab === tab.id
                      ? 'bg-primary/10 text-primary font-medium'
                      : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                  )}
                >
                  {tab.icon && <tab.icon className="h-5 w-5" />}
                  <span>{tab.label}</span>
                </button>
              ))}
            </nav>
          </aside>

          {/* Content */}
          <div className="flex-1">
            {activeTab === 'general' && (
              <div className="space-y-6">
                <Card>
                  <CardHeader>
                    <h2 className="text-lg font-semibold">Search Behavior</h2>
                    <p className="text-sm text-muted-foreground">Configure default search behavior</p>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <Select
                      label="Default Search Mode"
                      value={settings.defaultSearchMode}
                      onChange={(e) => setSettings((s) => ({ ...s, defaultSearchMode: e.target.value as typeof settings.defaultSearchMode }))}
                      options={SEARCH_MODES}
                    />
                    <Input
                      label="Max Results per Search"
                      type="number"
                      value={settings.maxResults}
                      onChange={(e) => setSettings((s) => ({ ...s, maxResults: parseInt(e.target.value, 10) }))}
                    />
                    <div className="flex items-center justify-between">
                      <div>
                        <label className="font-medium">Auto-start Search After Upload</label>
                        <p className="text-sm text-muted-foreground">Automatically begin search when image is uploaded</p>
                      </div>
                      <input
                        type="checkbox"
                        checked={settings.autoStartSearch}
                        onChange={(e) => setSettings((s) => ({ ...s, autoStartSearch: e.target.checked }))}
                        className="h-4 w-4 rounded border-border text-primary focus:ring-primary"
                      />
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <h2 className="text-lg font-semibold">Results Display</h2>
                    <p className="text-sm text-muted-foreground">How results are presented</p>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <label className="font-medium">Show Confidence Colors</label>
                        <p className="text-sm text-muted-foreground">Color-code results by confidence level</p>
                      </div>
                      <input
                        type="checkbox"
                        checked={settings.showConfidenceColors}
                        onChange={(e) => setSettings((s) => ({ ...s, showConfidenceColors: e.target.checked }))}
                        className="h-4 w-4 rounded border-border text-primary focus:ring-primary"
                      />
                    </div>
                  </CardContent>
                </Card>
              </div>
            )}

            {activeTab === 'search' && (
              <div className="space-y-6">
                <Card>
                  <CardHeader>
                    <h2 className="text-lg font-semibold">Search Sources</h2>
                    <p className="text-sm text-muted-foreground">Enable or disable search providers</p>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <label className="font-medium">Local Face Index</label>
                        <p className="text-sm text-muted-foreground">Search against local FAISS index</p>
                      </div>
                      <input
                        type="checkbox"
                        checked={settings.enableLocalSearch}
                        onChange={(e) => setSettings((s) => ({ ...s, enableLocalSearch: e.target.checked }))}
                        className="h-4 w-4 rounded border-border text-primary focus:ring-primary"
                      />
                    </div>
                    <div className="flex items-center justify-between">
                      <div>
                        <label className="font-medium">Internet (OSINT) Search</label>
                        <p className="text-sm text-muted-foreground">Discover public profiles via Agent Reach</p>
                      </div>
                      <input
                        type="checkbox"
                        checked={settings.enableInternetSearch}
                        onChange={(e) => setSettings((s) => ({ ...s, enableInternetSearch: e.target.checked }))}
                        className="h-4 w-4 rounded border-border text-primary focus:ring-primary"
                      />
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <h2 className="text-lg font-semibold">Search Parameters</h2>
                    <p className="text-sm text-muted-foreground">Fine-tune search sensitivity</p>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium mb-2">
                        Face Similarity Threshold: {settings.similarityThreshold.toFixed(2)}
                      </label>
                      <input
                        type="range"
                        min="0.1"
                        max="0.9"
                        step="0.05"
                        value={settings.similarityThreshold}
                        onChange={(e) => setSettings((s) => ({ ...s, similarityThreshold: parseFloat(e.target.value) }))}
                        className="w-full"
                      />
                      <p className="text-sm text-muted-foreground mt-1">
                        Minimum similarity score for face matches. Lower = more results, higher = stricter matches.
                      </p>
                    </div>
                    <Input
                      label="Max Pages to Analyze (Internet Search)"
                      type="number"
                      value={settings.maxPagesPerSearch}
                      onChange={(e) => setSettings((s) => ({ ...s, maxPagesPerSearch: parseInt(e.target.value, 10) }))}
                    />
                  </CardContent>
                </Card>
              </div>
            )}

            {activeTab === 'appearance' && (
              <div className="space-y-6">
                <Card>
                  <CardHeader>
                    <h2 className="text-lg font-semibold">Theme</h2>
                    <p className="text-sm text-muted-foreground">Choose your preferred color scheme</p>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <Select
                      label="Color Theme"
                      value={settings.theme}
                      onChange={(e) => {
                        const newTheme = e.target.value as typeof settings.theme;
                        setSettings((s) => ({ ...s, theme: newTheme }));
                        document.documentElement.classList.remove('light', 'dark');
                        if (newTheme === 'dark' || (newTheme === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
                          document.documentElement.classList.add('dark');
                        } else {
                          document.documentElement.classList.add('light');
                        }
                      }}
                      options={THEMES}
                    />
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <h2 className="text-lg font-semibold">Layout</h2>
                    <p className="text-sm text-muted-foreground">Interface density and spacing</p>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <label className="font-medium">Compact Mode</label>
                        <p className="text-sm text-muted-foreground">Reduce padding and spacing for denser views</p>
                      </div>
                      <input
                        type="checkbox"
                        checked={settings.compactMode}
                        onChange={(e) => setSettings((s) => ({ ...s, compactMode: e.target.checked }))}
                        className="h-4 w-4 rounded border-border text-primary focus:ring-primary"
                      />
                    </div>
                  </CardContent>
                </Card>
              </div>
            )}

            {activeTab === 'api' && (
              <div className="space-y-6">
                <Card>
                  <CardHeader>
                    <h2 className="text-lg font-semibold">API Configuration</h2>
                    <p className="text-sm text-muted-foreground">Backend API connection settings</p>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <Input
                      label="API Base URL"
                      value={settings.apiUrl}
                      onChange={(e) => setSettings((s) => ({ ...s, apiUrl: e.target.value }))}
                      placeholder="http://localhost:8000/api/v1"
                    />
                    <Input
                      label="API Key (Optional)"
                      type="password"
                      value={settings.apiKey}
                      onChange={(e) => setSettings((s) => ({ ...s, apiKey: e.target.value }))}
                      placeholder="Enter API key if required"
                    />
                    <div className="p-3 bg-muted rounded-lg text-sm text-muted-foreground">
                      The API key is stored locally in your browser and sent with each request.
                      For production, consider using environment variables.
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <h2 className="text-lg font-semibold">Connection Test</h2>
                    <p className="text-sm text-muted-foreground">Verify API connectivity</p>
                  </CardHeader>
                  <CardContent>
                    <Button variant="outline" onClick={() => addToast('info', 'API connection test not implemented yet')}>
                      Test Connection
                    </Button>
                  </CardContent>
                </Card>
              </div>
            )}

            {activeTab === 'privacy' && (
              <div className="space-y-6">
                <Card>
                  <CardHeader>
                    <h2 className="text-lg font-semibold">Data Retention</h2>
                    <p className="text-sm text-muted-foreground">Control how long your data is kept</p>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <Input
                      label="Auto-delete Searches After (Days)"
                      type="number"
                      value={settings.autoDeleteDays}
                      onChange={(e) => setSettings((s) => ({ ...s, autoDeleteDays: parseInt(e.target.value, 10) }))}
                    />
                    <p className="text-sm text-muted-foreground">
                      Set to 0 to disable auto-deletion. Searches older than this will be automatically removed.
                    </p>
                    <Button variant="outline" onClick={() => addToast('info', 'Manual cleanup not implemented yet')}>
                      Clean Up Now
                    </Button>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <h2 className="text-lg font-semibold">Privacy Options</h2>
                    <p className="text-sm text-muted-foreground">Control data processing and sharing</p>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <label className="font-medium">Anonymize Data</label>
                        <p className="text-sm text-muted-foreground">Remove personally identifiable information from stored results</p>
                      </div>
                      <input
                        type="checkbox"
                        checked={settings.anonymizeData}
                        onChange={(e) => setSettings((s) => ({ ...s, anonymizeData: e.target.checked }))}
                        className="h-4 w-4 rounded border-border text-primary focus:ring-primary"
                      />
                    </div>
                    <div className="flex items-center justify-between">
                      <div>
                        <label className="font-medium">Share Anonymous Usage Stats</label>
                        <p className="text-sm text-muted-foreground">Help improve the product by sharing anonymous usage data</p>
                      </div>
                      <input
                        type="checkbox"
                        checked={settings.shareUsageStats}
                        onChange={(e) => setSettings((s) => ({ ...s, shareUsageStats: e.target.checked }))}
                        className="h-4 w-4 rounded border-border text-primary focus:ring-primary"
                      />
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <h2 className="text-lg font-semibold">Data Export</h2>
                    <p className="text-sm text-muted-foreground">Export or delete your data</p>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex gap-2">
                      <Button variant="outline" onClick={() => addToast('info', 'Data export not implemented yet')}>
                        Export All Data
                      </Button>
                      <Button variant="outline" onClick={() => addToast('info', 'Account deletion not implemented yet')}>
                        Delete Account
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              </div>
            )}
          </div>
        </div>
        </LoadingOverlay>
      </main>
    </div>
  );
}