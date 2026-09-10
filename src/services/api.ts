import type { Feed, Persona } from "../types";

const endpoint = (persona: Persona, location: string) => `/api/users/demo-user/personalized-feed?persona=${persona}&location=${encodeURIComponent(location)}`;

export async function getFeed(persona: Persona, location: string): Promise<Feed> {
  const response = await fetch(endpoint(persona, location));
  if (!response.ok) throw new Error("Weather data is temporarily unavailable.");
  return response.json() as Promise<Feed>;
}
