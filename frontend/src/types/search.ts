export type SearchStatus = "pending" | "processing" | "completed" | "failed";

export interface SearchCreateResponse {
  search_id: number;
  status: SearchStatus;
}

export interface MatchedProfile {
  id: number;
  platform: string;
  profile_url: string;
  image_url: string | null;
  confidence: number;
}
