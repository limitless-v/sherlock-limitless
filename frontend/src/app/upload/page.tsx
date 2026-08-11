'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Search, Loader2 } from 'lucide-react';
import { cn } from '@/utils/cn';
import { Button } from '@/components/ui/Button';
import { Card, CardContent } from '@/components/ui/Card';
import { DropZone } from '@/components/upload/DropZone';
import { SearchModeSelect } from '@/components/upload/SearchModeSelect';
import { ToastContainer, Toast } from '@/components/ui/Toast';
import type { SearchMode, UploadResponse } from '@/types/search';
import { apiClient } from '@/lib/api';

export default function UploadPage() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [mode, setMode] = useState<SearchMode>('hybrid');
  const [isSearching, setIsSearching] = useState(false);
  const [toasts, setToasts] = useState<Array<{ id: string; type: 'success' | 'error' | 'info'; message: string }>>([]);

  const addToast = (type: 'success' | 'error' | 'info', message: string) => {
    const id = Math.random().toString(36).slice(2);
    setToasts((prev) => [...prev, { id, type, message }]);
  };

  const removeToast = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  const handleFileSelect = (newFile: File | null) => {
    setFile(newFile);
    if (newFile) {
      const url = URL.createObjectURL(newFile);
      setPreview(url);
    } else {
      setPreview(null);
    }
  };

  const handleSearch = async () => {
    if (!file) {
      addToast('error', 'Please select an image first');
      return;
    }

    setIsSearching(true);
    try {
      // Upload image
      const uploadResponse: UploadResponse = await apiClient.uploadImage(file);
      addToast('success', 'Image uploaded successfully');

      // Start search
      const searchResponse = await apiClient.startSearch({
        image_id: uploadResponse.image_id,
        mode,
        max_results: 50,
      });

      addToast('success', 'Search started');
      router.push(`/search/${searchResponse.search_id}`);
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to start search';
      addToast('error', message);
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <ToastContainer toasts={toasts} onClose={removeToast} />
      
      <main className="mx-auto max-w-3xl px-4 py-12">
        <div className="text-center mb-12">
          <h1 className="text-3xl font-bold tracking-tight">Start New Search</h1>
          <p className="mt-2 text-muted-foreground">
            Upload an image to begin face search and OSINT discovery
          </p>
        </div>

        <Card className="mb-8">
          <CardContent className="p-6">
            <DropZone
              onFileSelect={handleFileSelect}
              preview={preview}
              disabled={isSearching}
            />
          </CardContent>
        </Card>

        <Card className="mb-8">
          <CardContent className="p-6">
            <h3 className="text-lg font-semibold mb-4">Search Mode</h3>
            <SearchModeSelect
              value={mode}
              onChange={setMode}
              disabled={isSearching}
            />
          </CardContent>
        </Card>

        <Button
          onClick={handleSearch}
          disabled={isSearching || !file}
          className="w-full"
          size="lg"
        >
          {isSearching ? (
            <>
              <Loader2 className="h-5 w-5 animate-spin mr-2" />
              Starting Search...
            </>
          ) : (
            <>
              <Search className="h-5 w-5 mr-2" />
              Start Search
            </>
          )}
        </Button>

        <p className="mt-4 text-center text-sm text-muted-foreground">
          Search will run in the background. You can track progress on the next page.
        </p>
      </main>
    </div>
  );
}