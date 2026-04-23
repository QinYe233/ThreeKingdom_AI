export interface Block {
  name: string;
  owner: string;
  garrison: number;
  order: number;
  morale: number;
  base_manpower: number;
  manpower_pool: number;
  neighbors: string[];
  region_type: "core" | "frontier";
  supply_connected: boolean;
  geographic_trait: string;
  specialization: string | null;
  develop_count: number;
  recently_conquered: boolean;
}

export interface Country {
  name: string;
  gold: number;
  order: number;
  morale: number;
  capital: string;
  goal: string;
  in_exile: boolean;
  is_defeated: boolean;
  has_declared_emperor: boolean;
  action_points: number;
  blocks_count?: number;
  total_garrison?: number;
}

export interface Relation {
  trust: number;
  grudge: number;
  is_allied: boolean;
  at_war: boolean;
}

export interface GameState {
  round: number;
  timeline: { year: number; month: number };
  countries: Record<string, Country>;
  blocks_count: number;
  relations: Record<string, Relation>;
}

export interface General {
  name: string;
  country: string;
  block: string;
  trait: string;
  alive: boolean;
  death_round: number | null;
}

export interface BattleResult {
  attacker: string;
  defender: string;
  attacker_block: string;
  defender_block: string;
  attacker_troops: number;
  defender_troops: number;
  attacker_loss: number;
  defender_loss: number;
  attacker_won: boolean;
  block_captured: boolean;
  collapse: boolean;
  war_pressure_change: number;
}

export interface Narrative {
  round: number;
  date: string;
  narrative?: string;
  trend?: Record<string, {
    blocks: number;
    garrison: number;
    order_desc: string;
    morale_desc: string;
    military_trend: string;
    economy_trend: string;
  }>;
  events: Array<{
    type: string;
    country?: string;
    message: string;
  }>;
}

export type ActionType = 
  | "move" | "attack" | "harass" | "recruit"
  | "develop" | "tax" | "send_message" | "disband"
  | "move_capital" | "declare_emperor";

export interface ThinkingRecord {
  round: number;
  country: string;
  thinking: string;
  content: string;
  actions: string[];
}
