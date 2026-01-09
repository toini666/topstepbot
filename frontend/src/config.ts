// Centralized API Configuration
// In development with Vite proxy, this can be just "" or "/api"
// In production, it can be set via VITE_API_URL

export const API_BASE = import.meta.env.VITE_API_URL || "/api";
