'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api';
import type { SearchMode, SearchDetail, SearchResultsResponse, EvidenceGraph, SearchHistoryResponse, SearchResult } from '@/types/search';

export function useSearch(searchId: number | null) {
  return useQuery({
    queryKey: ['search', searchId],
    queryFn: () => apiClient.getSearch(searchId!),
    enabled: !!searchId,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data && (data.status === 'running' || data.status === 'pending')) {
        return 2000;
      }
      return false;
    },
  });
}

export function useSearchResults(searchId: number | null, page = 1, pageSize = 20) {
  return useQuery({
    queryKey: ['searchResults', searchId, page, pageSize],
    queryFn: () => apiClient.getSearchResults(searchId!, page, pageSize),
    enabled: !!searchId,
    placeholderData: (previousData) => previousData,
  });
}

export function useSearchEvidence(searchId: number | null) {
  return useQuery({
    queryKey: ['searchEvidence', searchId],
    queryFn: () => apiClient.getSearchEvidence(searchId!),
    enabled: !!searchId,
  });
}

export function useSearchHistory(
  page = 1,
  pageSize = 20,
  filters?: { status?: string; mode?: SearchMode; created_from?: string; created_to?: string; user_id?: number }
) {
  return useQuery({
    queryKey: ['searchHistory', page, pageSize, filters],
    queryFn: () => apiClient.getHistory(page, pageSize, filters),
    placeholderData: (previousData) => previousData,
  });
}

export function useStartSearch() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (request: { image_id: string; mode: SearchMode; max_results?: number }) => 
      apiClient.startSearch(request),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['searchHistory'] });
    },
  });
}

export function useDeleteSearch() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ searchId, userId }: { searchId: number; userId?: number }) => 
      apiClient.deleteHistory(searchId, userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['searchHistory'] });
    },
  });
}

export function useSearchEvents(searchId: number | null, onEvent?: (event: MessageEvent) => void) {
  // This would be used with SSE - for now we use polling via useSearch
  return { data: null, isConnected: false };
}