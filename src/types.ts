export type Persona = "fitness" | "family" | "agriculture" | "travel" | "health" | "commuter" | "outdoor_worker" | "event" | "general";

export interface Recommendation { id: string; type: string; title: string; message: string; priority: string; score: number; reason: string[]; action: string; badge?: string }
export interface Feed {
  location: { name: string; label: string };
  weather: { location: string; temperature: number; feels_like: number; humidity: number; wind_speed: number; rain_probability: number; uv_index: number; aqi?: number; visibility: number; condition: string; updated_at: string };
  impact: { score: number; level: string; label: string; factors: {name: string; status: string; contribution: number; explanation: string}[] };
  cards: Recommendation[]; recommendations: Recommendation[];
  alerts: {title: string; message: string; severity: string; source: string; source_type: string; distance_km?: number; eta_minutes?: number; actions: string[]}[];
  explanation: {title: string; items: string[]; summary: string}; hourly: {time: string; icon: string; temp: number; event: string}[]; daily: {day: string; icon: string; high: number; low: number; rain: number}[];
  observations: {id:string;type:string;location:string;distance_km:number;reported_at:string;count:number;source_type:string;verified:boolean}[];
  is_demo_data: boolean;
}

export const personaDetails: Record<Persona, {label: string; icon: string; subtitle: string}> = {
  fitness: { label: "Fitness", icon: "🚴", subtitle: "Outdoor activity and comfort" },
  family: { label: "Family", icon: "👨‍👩‍👧", subtitle: "Outdoor time and school plans" },
  agriculture: { label: "Farmer", icon: "🌾", subtitle: "Garden and farm planning" },
  travel: { label: "Traveler", icon: "🧳", subtitle: "Destination and packing advice" },
  health: { label: "Health", icon: "🫁", subtitle: "Environmental comfort conditions" },
  commuter: { label: "Commuter", icon: "🚗", subtitle: "Weather-aware routine travel" },
  outdoor_worker: { label: "Outdoor worker", icon: "🦺", subtitle: "Work exposure and safer windows" },
  event: { label: "Event planner", icon: "🎪", subtitle: "Outdoor event timing" },
  general: { label: "General", icon: "🌤️", subtitle: "Everyday preventive guidance" }
};
