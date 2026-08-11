export type SearchMode = 'local' | 'internet' | 'hybrid';

export type SearchStatus = 'pending' | 'running' | 'completed' | 'degraded' | 'failed';

export type ConfidenceLevel = 'high' | 'medium' | 'low';

export interface SearchCreateRequest {
  image_id: string;
  mode: SearchMode;
  max_results?: number;
  sources?: string[];
  user_id?: number;
  uploaded_image?: string;
}

export interface SearchResult {
  id: string;
  source: string;
  url: string;
  title: string;
  username: string;
  display_name: string;
  image_urls: string[];
  text: string;
  discovery_method: string;
  face_similarity: number;
  confidence: ConfidenceLevel;
  discovered_at: string | null;
  location?: string | null;
  date?: string | null;
  profiles: Array<{
    profile_url: string;
    platform: string;
    username?: string | null;
    display_name?: string | null;
  }>;
}

export interface SearchResponse {
  search_id: string;
  mode: SearchMode;
  status: SearchStatus;
  results: SearchResult[];
  providers: Record<string, unknown>;
  ranked_evidence?: EvidenceGraph | null;
}

export interface SearchCreateResponse {
  search_id: number;
  status: SearchStatus;
}

export interface DetectedFace {
  id: number;
  face_image: string;
  embedding_path: string | null;
  matched_profiles: MatchedProfile[];
}

export interface MatchedProfile {
  id: number;
  platform: string;
  profile_url: string;
  image_url: string | null;
  confidence: number;
}

export interface SearchDetail {
  id: number;
  uploaded_image: string;
  created_at: string;
  detected_faces: DetectedFace[];
  matched_profiles: MatchedProfile[];
  mode: string;
  status: string;
  providers: Record<string, unknown>;
  ranked_evidence?: EvidenceGraph | null;
}

export interface SearchHistoryItem {
  id: number;
  uploaded_image: string;
  created_at: string;
  mode: string;
  status: string;
}

export interface SearchHistoryResponse {
  items: SearchHistoryItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface SearchResultsResponse {
  search_id: number;
  page: number;
  page_size: number;
  total: number;
  results: SearchResult[];
}

export interface EvidenceNode {
  id: number;
  type: string;
  entity_id: string;
  entity_value: string;
  attributes?: Record<string, unknown> | null;
  source_url?: string | null;
  source_evidence_id?: number | null;
  created_at?: string | null;
}

export interface EvidenceEdge {
  id: number;
  source: number;
  target: number;
  type: string;
  source_url: string;
  source_evidence_id?: number | null;
  confidence?: number | null;
  metadata?: Record<string, unknown> | null;
  created_at?: string | null;
}

export interface EvidenceGraph {
  search_id: number;
  nodes: EvidenceNode[];
  edges: EvidenceEdge[];
}

export interface SearchEvent {
  event_type: string;
  payload: Record<string, unknown>;
}

export interface UploadResponse {
  image_id: string;
  search_id: number;
  filename: string;
  status: string;
}