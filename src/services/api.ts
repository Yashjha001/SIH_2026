import type { Feed, Persona } from "../types";

const endpoint = (persona: Persona, location: string) => `/api/users/demo-user/personalized-feed?persona=${persona}&location=${encodeURIComponent(location)}`;

export async function getFeed(persona: Persona, location: string): Promise<Feed> {
  const response = await fetch(endpoint(persona, location));
  if (!response.ok) throw new Error("Weather data is temporarily unavailable.");
  return response.json() as Promise<Feed>;
}

export async function reportObservation(type: string, location: string) {
  const response = await fetch("/api/community/observations", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({type, location})});
  if (!response.ok) throw new Error("Could not submit the observation.");
  return response.json();
}
