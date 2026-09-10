export type Persona = "fitness" | "family" | "agriculture" | "travel" | "health" | "commuter" | "outdoor_worker" | "event" | "general";

export interface Recommendation { id: string; type: string; title: string; message: string; priority: string; score: number; reason: string[]; action: string; badge?: string }
export interface WeatherAlert { id:string; title:string; message:string; severity:string; source:string; source_type:string; distance_km?:number; eta_minutes?:number; actions:string[]; reason:string[]; rank:number; location:string; valid_at:string; notification_eligible:boolean }
export interface Observation { id:string; type:string; location:string; area:string; details:string; distance_km?:number; reported_at:string; count:number; source_type:string; verified:boolean }
export interface Feed {
  location: { name: string; label: string };
  weather: { location: string; temperature: number; feels_like: number; humidity: number; wind_speed: number; rain_probability: number; uv_index: number; aqi?: number; visibility: number; condition: string; updated_at: string; source: string; latitude?: number; longitude?: number };
  impact: { score: number; level: string; label: string; factors: {name: string; status: string; contribution: number; explanation: string}[] };
  cards: Recommendation[]; recommendations: Recommendation[];
  alerts: WeatherAlert[]; notifications: WeatherAlert[]; notifications_enabled:boolean; model_version:string; data_gaps:string[];
  explanation: {title: string; items: string[]; summary: string}; hourly: {time: string; timestamp?:string; icon: string; temp: number; event: string; rain?:number; wind?:number; uv?:number}[]; daily: {day: string; date?:string; condition?:string; icon: string; high: number; low: number; rain: number}[];
  observations: Observation[];
  is_demo_data: boolean; provider: string;
}

export interface UserProfile { id:string; name:string; persona:Persona; location:string; activities:string[]; notifications_enabled:boolean; extra_protection:string[]; commute_time?:string|null; routine?:string|null }
export interface SavedLocation { id:string; name:string; label:string }
export interface LocationSearchResult { name:string; admin1?:string; country?:string; latitude:number; longitude:number }

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
