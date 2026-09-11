import type { Feed, LocationSearchResult, Observation, Persona, SavedLocation, UserProfile } from "../types";

const apiBase = (import.meta.env.VITE_API_URL ?? "").replace(/\/$/, "");
const apiUrl = (path: string) => `${apiBase}${path}`;
const endpoint = (persona: Persona, location: string) => `/api/users/demo-user/personalized-feed?persona=${persona}&location=${encodeURIComponent(location)}`;

export async function getFeed(persona: Persona, location: string, signal?:AbortSignal): Promise<Feed> {
  const response = await fetch(apiUrl(endpoint(persona, location)), {cache:"no-store", signal});
  if (!response.ok) throw new Error("Weather data is temporarily unavailable.");
  return response.json() as Promise<Feed>;
}

export async function getProfile(): Promise<UserProfile> {
  const response = await fetch(apiUrl("/api/users/demo-user"), {cache:"no-store"});
  if (!response.ok) throw new Error("Could not load profile.");
  return response.json();
}

export async function updatePreferences(changes: Partial<UserProfile>): Promise<UserProfile> {
  const response = await fetch(apiUrl("/api/users/demo-user/preferences"), {method:"PUT", headers:{"Content-Type":"application/json"}, body:JSON.stringify(changes)});
  if (!response.ok) throw new Error("Could not save preferences.");
  return response.json();
}

export async function getLocations(): Promise<SavedLocation[]> {
  const response = await fetch(apiUrl("/api/users/demo-user/locations"), {cache:"no-store"});
  if (!response.ok) throw new Error("Could not load locations.");
  return response.json();
}

export async function addLocation(name:string, label="Other"): Promise<SavedLocation> {
  const response = await fetch(apiUrl("/api/users/demo-user/locations"), {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({name,label})});
  if (!response.ok) throw new Error(response.status===409?"Location is already saved.":"Could not save location.");
  return response.json();
}

export async function searchLocations(query:string): Promise<LocationSearchResult[]> {
  if (query.trim().length < 2) return [];
  const response = await fetch(apiUrl(`/api/locations/search?q=${encodeURIComponent(query)}`));
  if (!response.ok) throw new Error("Location search is unavailable.");
  return response.json();
}

export async function reportObservation(type: string, location: string, area:string, details:string):Promise<Observation> {
  const response = await fetch(apiUrl("/api/community/observations"), {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({type, location, area, details})});
  if (!response.ok) throw new Error("Could not submit the observation.");
  return response.json();
}

export async function getObservations(location:string):Promise<Observation[]> {
  const response = await fetch(apiUrl(`/api/community/observations?location=${encodeURIComponent(location)}`), {cache:"no-store"});
  if(!response.ok) throw new Error("Reports could not be loaded");
  return response.json();
}

export async function markNotificationRead(id:string) {
  const response = await fetch(apiUrl(`/api/users/demo-user/notifications/${encodeURIComponent(id)}/read`), {method:"POST"});
  if(!response.ok) throw new Error("Could not update notification");
}

export async function getDemo(persona:Persona):Promise<Feed> {
  const response = await fetch(apiUrl(`/api/demo/scenarios/${persona}`), {method:"POST"});
  if(!response.ok) throw new Error("Could not load demonstration");
  return response.json();
}
