'use client';

import { useState } from 'react';
import { useParams } from 'next/navigation';
import { ChevronRight, ExternalLink, Search as SearchIcon, Eye, Image as ImageIcon } from 'lucide-react';
import { cn } from '@/utils/cn';
import { Button } from '@/components/ui/Button';
import { Card, CardContent } from '@/components/ui/Card';
import { Badge, type BadgeVariant } from '@/components/ui/Badge';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/Table';
import { Modal } from '@/components/ui/Modal';
import { LoadingOverlay } from '@/components/ui/Spinner';
import { useSearch, useSearchResults, useSearchHistory } from '@/hooks/useSearch';
import type { SearchResult, SearchDetail, ConfidenceLevel } from '@/types/search';
import { apiClient } from '@/lib/api';

const CONFIDENCE_COLORS: Record<ConfidenceLevel, BadgeVariant> = {
  high: 'strong',
  medium: 'medium',
  low: 'weak',
};

const STATUS_COLORS: Record<string, BadgeVariant> = {
  completed: 'completed',
  degraded: 'degraded',
  failed: 'failed',
  running: 'running',
  pending: 'pending',
};

export default function SearchResultsPage() {
  const params = useParams();
  const searchId = parseInt(params.id as string, 10);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [selectedResult, setSelectedResult] = useState<SearchResult | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);

  const { data: search, isLoading: searchLoading } = useSearch(searchId);
  const { data: resultsData, isLoading: resultsLoading, refetch } = useSearchResults(searchId, page, pageSize);

  const handleViewDetails = (result: SearchResult) => {
    setSelectedResult(result);
  };

  const handleImagePreview = (url: string) => {
    setImagePreview(url);
  };

  if (searchLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="h-12 w-12 animate-spin border-4 border-primary border-t-transparent rounded-full" />
          <p>Loading search details...</p>
        </div>
      </div>
    );
  }

  if (!search) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Card className="max-w-md w-full mx-4">
          <CardContent className="p-6 text-center">
            <h2 className="text-xl font-semibold mb-2">Search Not Found</h2>
            <p className="text-muted-foreground">The search you're looking for doesn't exist.</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const results = resultsData?.results || [];
  const total = resultsData?.total || 0;
  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border bg-background/80 backdrop-blur sticky top-0 z-40">
        <div className="mx-auto max-w-6xl px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="sm" onClick={() => window.history.back()}>
              <ChevronRight className="h-4 w-4 rotate-180" />
            </Button>
            <div>
              <h1 className="font-semibold">Results</h1>
              <p className="text-sm text-muted-foreground">Search #{searchId} • {search.mode} • {total} results</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant={STATUS_COLORS[search.status] || 'default'}>
              {search.status}
            </Badge>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-8">
        <LoadingOverlay isLoading={resultsLoading} message="Loading results...">

        {results.length === 0 ? (
          <Card>
            <CardContent className="p-12 text-center">
              <SearchIcon className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">No Results Found</h3>
              <p className="text-muted-foreground">
                The search completed but didn't find any matching results.
                Try a different search mode or upload a clearer image.
              </p>
            </CardContent>
          </Card>
        ) : (
          <>
            <div className="mb-4 flex items-center justify-between">
              <p className="text-sm text-muted-foreground">
                Showing {Math.min((page - 1) * pageSize + 1, total)} to {Math.min(page * pageSize, total)} of {total} results
              </p>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                >
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                >
                  Next
                </Button>
              </div>
            </div>

            <Card>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-8"></TableHead>
                    <TableHead>Source</TableHead>
                    <TableHead>Title / Username</TableHead>
                    <TableHead className="w-32">Confidence</TableHead>
                    <TableHead className="w-24">Face Sim.</TableHead>
                    <TableHead className="w-32">Discovered</TableHead>
                    <TableHead className="w-12"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {results.map((result) => (
                    <TableRow key={result.id} className="cursor-pointer hover:bg-muted/50" onClick={() => handleViewDetails(result)}>
                      <TableCell>
                        {result.image_urls[0] && (
                          <img
                            src={result.image_urls[0]}
                            alt=""
                            className="h-10 w-10 rounded-lg object-cover"
                            loading="lazy"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleImagePreview(result.image_urls[0]);
                            }}
                          />
                        )}
                      </TableCell>
                      <TableCell>
                        <Badge variant="primary" className="text-xs">{result.source}</Badge>
                      </TableCell>
                      <TableCell>
                        <div className="max-w-xs">
                          {result.display_name && (
                            <p className="font-medium truncate">{result.display_name}</p>
                          )}
                          {result.username && (
                            <p className="text-sm text-muted-foreground truncate">@{result.username}</p>
                          )}
                          {!result.display_name && !result.username && result.title && (
                            <p className="text-sm truncate">{result.title}</p>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant={CONFIDENCE_COLORS[result.confidence]}>
                          {result.confidence}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        {result.face_similarity > 0 && (
                          <div className="flex items-center gap-1">
                            <div className="relative h-4 w-16">
                              <div
                                className="absolute inset-0 h-full bg-muted rounded"
                              />
                              <div
                                className="absolute left-0 top-0 h-full bg-primary rounded"
                                style={{ width: `${result.face_similarity * 100}%` }}
                              />
                            </div>
                            <span className="text-xs text-muted-foreground">
                              {Math.round(result.face_similarity * 100)}%
                            </span>
                          </div>
                        )}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {result.discovered_at ? new Date(result.discovered_at).toLocaleDateString() : '-'}
                      </TableCell>
                      <TableCell>
                        <Button variant="ghost" size="sm" onClick={(e) => { e.stopPropagation(); handleViewDetails(result); }}>
                          <Eye className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Card>

            <div className="mt-4 flex items-center justify-between">
              <p className="text-sm text-muted-foreground">
                Showing {Math.min((page - 1) * pageSize + 1, total)} to {Math.min(page * pageSize, total)} of {total} results
              </p>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                >
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                >
                  Next
                </Button>
              </div>
            </div>
          </>
        )}

        </LoadingOverlay>
      </main>

      {/* Result Detail Modal */}
      <Modal
        isOpen={!!selectedResult}
        onClose={() => setSelectedResult(null)}
        title="Result Details"
        size="lg"
      >
        {selectedResult && (
          <div className="space-y-6">
            <div className="flex items-start gap-4">
              {selectedResult.image_urls[0] && (
                <img
                  src={selectedResult.image_urls[0]}
                  alt="Result preview"
                  className="h-32 w-32 rounded-lg object-cover flex-shrink-0"
                />
              )}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-2">
                  <Badge variant="primary">{selectedResult.source}</Badge>
                  <Badge variant={CONFIDENCE_COLORS[selectedResult.confidence]}>
                    {selectedResult.confidence} confidence
                  </Badge>
                </div>
                {selectedResult.display_name && (
                  <h4 className="font-semibold truncate">{selectedResult.display_name}</h4>
                )}
                {selectedResult.username && (
                  <p className="text-muted-foreground">@{selectedResult.username}</p>
                )}
                {selectedResult.title && !selectedResult.display_name && (
                  <p className="text-sm truncate">{selectedResult.title}</p>
                )}
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <h5 className="font-medium mb-2">URL</h5>
                <div className="flex items-center gap-2">
                  <a
                    href={selectedResult.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex-1 text-sm text-primary hover:underline truncate block"
                  >
                    {selectedResult.url}
                  </a>
                  <Button variant="ghost" size="sm" onClick={() => window.open(selectedResult.url, '_blank')}>
                    <ExternalLink className="h-4 w-4" />
                  </Button>
                </div>
              </div>

              <div>
                <h5 className="font-medium mb-2">Discovery Method</h5>
                <p className="text-sm text-muted-foreground">{selectedResult.discovery_method || 'Unknown'}</p>
              </div>

              {selectedResult.face_similarity > 0 && (
                <div>
                  <h5 className="font-medium mb-2">Face Similarity</h5>
                  <div className="flex items-center gap-2">
                    <div className="flex-1 h-2 bg-muted rounded">
                      <div
                        className="h-full bg-primary rounded"
                        style={{ width: `${selectedResult.face_similarity * 100}%` }}
                      />
                    </div>
                    <span className="text-sm font-medium">
                      {Math.round(selectedResult.face_similarity * 100)}%
                    </span>
                  </div>
                </div>
              )}

              {selectedResult.location && (
                <div>
                  <h5 className="font-medium mb-2">Location</h5>
                  <p className="text-sm">{selectedResult.location}</p>
                </div>
              )}

              {selectedResult.date && (
                <div>
                  <h5 className="font-medium mb-2">Date</h5>
                  <p className="text-sm">{new Date(selectedResult.date).toLocaleDateString()}</p>
                </div>
              )}

              {selectedResult.profiles.length > 0 && (
                <div className="md:col-span-2">
                  <h5 className="font-medium mb-2">Associated Profiles</h5>
                  <div className="space-y-2">
                    {selectedResult.profiles.map((profile, index) => (
                      <div key={index} className="flex items-center justify-between p-3 bg-muted rounded-lg">
                        <div>
                          <p className="font-medium">{profile.platform}</p>
                          {profile.username && <p className="text-sm text-muted-foreground">@{profile.username}</p>}
                          {profile.display_name && <p className="text-sm text-muted-foreground">{profile.display_name}</p>}
                        </div>
                        <Button variant="ghost" size="sm" onClick={() => window.open(profile.profile_url, '_blank')}>
                          <ExternalLink className="h-4 w-4" />
                        </Button>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {selectedResult.image_urls.length > 1 && (
                <div className="md:col-span-2">
                  <h5 className="font-medium mb-2">All Images</h5>
                  <div className="flex gap-2 overflow-x-auto pb-2">
                    {selectedResult.image_urls.map((url, index) => (
                      <img
                        key={index}
                        src={url}
                        alt={`Image ${index + 1}`}
                        className="h-24 w-24 rounded-lg object-cover flex-shrink-0 cursor-pointer"
                        onClick={() => handleImagePreview(url)}
                      />
                    ))}
                  </div>
                </div>
              )}

              {selectedResult.text && (
                <div className="md:col-span-2">
                  <h5 className="font-medium mb-2">Extracted Text</h5>
                  <p className="text-sm text-muted-foreground whitespace-pre-wrap max-h-48 overflow-y-auto">
                    {selectedResult.text.slice(0, 1000)}{selectedResult.text.length > 1000 ? '...' : ''}
                  </p>
                </div>
              )}
            </div>
          </div>
        )}
      </Modal>

      {/* Image Preview Modal */}
      <Modal
        isOpen={!!imagePreview}
        onClose={() => setImagePreview(null)}
        size="xl"
      >
        {imagePreview && (
          <div className="relative">
            <img
              src={imagePreview}
              alt="Full size preview"
              className="max-h-[70vh] w-auto mx-auto rounded-lg"
            />
          </div>
        )}
      </Modal>
    </div>
  );
}