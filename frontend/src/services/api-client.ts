import axios from "axios";

const baseURL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const apiClient = axios.create({
  baseURL,
  timeout: 60_000,
  headers: { "Content-Type": "application/json" },
});
