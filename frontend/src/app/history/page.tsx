'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { ChevronRight, Trash2, Search as SearchIcon, Filter, Calendar, Download } from 'lucide-react';
import { cn } from '@/utils/cn';
import { Button } from '@/components/ui/Button';
import { Card, CardContent } from '@/components/ui/Card';
import { Badge, type BadgeVariant } from '@/components/ui/Badge';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/Table';
import { Select } from '@/components/ui/Select';
import { Input } from '@/components/ui/Input';
import { Modal } from '@/components/ui/Modal';
import { LoadingOverlay } from '@/components/ui/Spinner';
import { useSearchHistory, useDeleteSearch } from '@/hooks/useSearch';
import type { SearchHistoryItem, SearchMode, SearchStatus } from '@/types/search';

const STATUS_COLORS: Record<SearchStatus, BadgeVariant> = {
  completed: 'completed',
  degraded: 'degraded',
  failed: 'failed',
  running: 'running',
  pending: 'pending',
};

const MODE_LABELS: Record<SearchMode, string> = {
  local: 'Local',
  internet: 'Internet',
  hybrid: 'Hybrid',
};

export default function HistoryPage() {
  const router = useRouter();
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [modeFilter, setModeFilter] = useState<SearchMode | ''>('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<SearchHistoryItem | null>(null);

  const { data: history, isLoading, refetch } = useSearchHistory(page, pageSize, {
    status: statusFilter || undefined,
    mode: modeFilter || undefined,
    created_from: dateFrom || undefined,
    created_to: dateTo || undefined,
  });

  const deleteMutation = useDeleteSearch();

  const handleDelete = (item: SearchHistoryItem) => {
    setDeleteConfirm(item);
  };

  const confirmDelete = async () => {
    if (!deleteConfirm) return;
    try {
      await deleteMutation.mutateAsync({ searchId: deleteConfirm.id });
      refetch();
      setDeleteConfirm(null);
    } catch (error) {
      console.error('Failed to delete search:', error);
    }
  };

  const total = history?.total || 0;
  const totalPages = Math.ceil(total / pageSize);

  const STATUS_OPTIONS = [
    { value: '', label: 'All Status' },
    { value: 'completed', label: 'Completed' },
    { value: 'degraded', label: 'Degraded' },
    { value: 'failed', label: 'Failed' },
    { value: 'running', label: 'Running' },
    { value: 'pending', label: 'Pending' },
  ];

  const MODE_OPTIONS = [
    { value: '', label: 'All Modes' },
    { value: 'local', label: 'Local' },
    { value: 'internet', label: 'Internet' },
    { value: 'hybrid', label: 'Hybrid' },
  ];

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border bg-background/80 backdrop-blur sticky top-0 z-40">
        <div className="mx-auto max-w-6xl px-4 py-4">
          <h1 className="text-2xl font-bold">Search History</h1>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-8">
        {/* Filters */}
        <Card className="mb-6">
          <CardContent className="p-4">
            <div className="flex items-center justify-between gap-4 mb-4">
              <h3 className="font-semibold">Filters</h3>
              <Button variant="outline" size="sm" onClick={() => setShowFilters(!showFilters)}>
                {showFilters ? 'Hide' : 'Show'} Filters
                <Filter className="h-4 w-4 ml-1" />
              </Button>
            </div>

            {showFilters && (
              <div className="grid gap-4 md:grid-cols-4">
                <Select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  options={STATUS_OPTIONS}
                  placeholder="Status"
                />
                <Select
                  value={modeFilter}
                  onChange={(e) => setModeFilter(e.target.value as SearchMode)}
                  options={MODE_OPTIONS}
                  placeholder="Mode"
                />
                <Input
                  label="From Date"
                  type="date"
                  value={dateFrom}
                  onChange={(e) => setDateFrom(e.target.value)}
                />
                <Input
                  label="To Date"
                  type="date"
                  value={dateTo}
                  onChange={(e) => setDateTo(e.target.value)}
                />
              </div>
            )}
            {(statusFilter || modeFilter || dateFrom || dateTo) && (
              <div className="mt-4 flex items-center gap-2">
                <span className="text-sm text-muted-foreground">Active filters:</span>
                {statusFilter && <Badge variant="primary" className="mr-1">{statusFilter}</Badge>}
                {modeFilter && <Badge variant="primary" className="mr-1">{MODE_LABELS[modeFilter]}</Badge>}
                {dateFrom && <Badge variant="weak" className="mr-1">From: {dateFrom}</Badge>}
                {dateTo && <Badge variant="weak" className="mr-1">To: {dateTo}</Badge>}
                <Button variant="ghost" size="sm" onClick={() => {
                  setStatusFilter('');
                  setModeFilter('');
                  setDateFrom('');
                  setDateTo('');
                }}>
                  Clear All
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

        {/* History Table */}
        <Card>
          <LoadingOverlay isLoading={isLoading}>
            {history?.items.length === 0 ? (
              <CardContent className="p-12 text-center">
                <SearchIcon className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                <h3 className="text-lg font-semibold mb-2">No Search History</h3>
                <p className="text-muted-foreground mb-4">
                  {isLoading ? 'Loading...' : 'No searches found matching your criteria.'}
                </p>
                {!isLoading && (
                  <Button onClick={() => router.push('/upload')}>
                    Start New Search
                  </Button>
                )}
              </CardContent>
            ) : (
              <>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-12"></TableHead>
                      <TableHead>Image</TableHead>
                      <TableHead>Mode</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Date</TableHead>
                      <TableHead className="w-32">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {history?.items.map((item) => (
                      <TableRow key={item.id}>
                        <TableCell>
                          <input
                            type="checkbox"
                            className="h-4 w-4 rounded border-border"
                            onChange={() => {}}
                          />
                        </TableCell>
                        <TableCell>
                          <img
                            src={item.uploaded_image}
                            alt="Uploaded"
                            className="h-12 w-12 rounded-lg object-cover"
                          />
                        </TableCell>
                        <TableCell>
                          <Badge variant="primary" className="text-xs">
                            {MODE_LABELS[item.mode as SearchMode] || item.mode}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Badge variant={STATUS_COLORS[item.status as SearchStatus] || 'default'}>
                            {item.status}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          {new Date(item.created_at).toLocaleString()}
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-1">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => router.push(`/search/${item.id}/results`)}
                            >
                              <ChevronRight className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleDelete(item)}
                            >
                              <Trash2 className="h-4 w-4 text-danger" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>

                {/* Pagination */}
                {totalPages > 1 && (
                  <div className="mt-4 flex items-center justify-between">
                    <p className="text-sm text-muted-foreground">
                      Page {page} of {totalPages} • {total} total
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
                )}
              </>
            )}
          </LoadingOverlay>
        </Card>

        {/* Delete Confirmation Modal */}
        <Modal
          isOpen={!!deleteConfirm}
          onClose={() => setDeleteConfirm(null)}
          title="Delete Search"
          description="This action cannot be undone."
        >
          {deleteConfirm && (
            <div className="space-y-4">
              <p>Are you sure you want to delete search <strong>#{deleteConfirm.id}</strong>?</p>
              <p className="text-sm text-muted-foreground">
                This will permanently remove the search and all associated data.
              </p>
              <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={() => setDeleteConfirm(null)}>
                  Cancel
                </Button>
                <Button variant="danger" onClick={confirmDelete} disabled={deleteMutation.isPending}>
                  {deleteMutation.isPending ? 'Deleting...' : 'Delete'}
                </Button>
              </div>
            </div>
          )}
        </Modal>
      </main>
    </div>
  );
}