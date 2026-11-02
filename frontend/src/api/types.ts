/** Types des données renvoyées par l'API (miroir des schémas Pydantic du backend). */
export type Role = "admin" | "coordinator" | "analyst";

export interface User {
  id: number;
  username: string;
  full_name: string;
  email: string | null;
  role: Role;
  is_active: boolean;
  last_login_at?: string | null;
  created_at?: string | null;
}

export interface TokenOut { access_token: string; expires_at: string; user: User }

export type KpiUnit = "count" | "amount" | "rate" | "percent";
export interface Kpi { key: string; label: string; unit: KpiUnit; definition: string; value: number | null }

export interface Domain { id: number; name: string; description?: string | null }
export interface Cohort {
  id: number; name: string; year: number; start_date: string; end_date: string; description: string | null;
  is_simulated: boolean;
}

export interface ProjectItem {
  id: number; name: string; leader: string; domain: string; domain_id: number; cohort: string; cohort_id: number;
  status: string; progress_pct: number; planned_budget: number; funding_obtained: number; deadline: string | null;
  is_delayed: boolean; created_at: string; updated_at: string; is_simulated: boolean;
}

export interface Page<T> { items: T[]; total: number; page: number; page_size: number }

export interface Milestone { id: number; title: string; position: number; due_date: string; completed_date: string | null }
export interface Evaluation { id: number; evaluator: string; score: number; recommendation: string; comment: string | null; evaluated_at: string }

export interface ProjectDetail {
  id: number; name: string; description: string | null; status: string; progress_pct: number; planned_budget: number;
  deadline: string | null; created_at: string; updated_at: string; is_simulated: boolean; is_archived: boolean;
  is_delayed: boolean;
  domain: { id: number; name: string };
  cohort: { id: number; name: string; start_date: string; end_date: string };
  leader: { id: number; first_name: string; last_name: string; gender: string | null; profile: string; email: string | null; phone: string | null };
  application: { id: number; status: string; submitted_at: string; decision_date: string | null; average_score: number | null };
  evaluations: Evaluation[];
  milestones: Milestone[];
  fundings: { id: number; source_type: string; partner: string | null; amount_requested: number; amount_granted: number; amount_received: number; status: string; request_date: string }[];
  funding: { planned_budget: number; requested: number; granted: number; received: number; remaining_to_receive: number; uncovered_need: number };
  funding_obtained: number;
  history: { old_status: string | null; new_status: string; comment: string | null; changed_at: string; changed_by: string | null }[];
  allowed_transitions: string[];
}

export interface Funding {
  id: number; project_id: number; project_name: string; cohort: string; domain: string; partner_id: number | null;
  partner: string | null; source_type: string; amount_requested: number; amount_granted: number;
  amount_received: number; remaining: number; request_date: string; grant_date: string | null; status: string;
  notes: string | null; is_simulated: boolean;
}

export interface CohortStats {
  cohort_id: number; cohort: string; year: number; applications: number; selected: number; total_projects: number;
  completed: number; delayed: number; active: number; incubated: number; selection_rate: number | null;
  completion_rate: number | null; success_rate: number | null; delay_rate: number | null; avg_progress: number | null;
  avg_funding: number | null; funding_granted: number; funding_received: number; prototypes: number; in_incubation: number;
}

export interface Charts {
  perimetre: string;
  applications_monthly: { month: string; received: number; accepted: number; rejected: number }[];
  by_domain: { domain: string; applications: number; projects: number; completed: number }[];
  by_status: { status: string; count: number }[];
  cohorts: CohortStats[];
  fundings_monthly: { month: string; requested: number; granted: number; received: number }[];
  fundings_by_domain: { label: string; count: number; requested: number; granted: number; received: number }[];
  fundings_by_source: { label: string; count: number; requested: number; granted: number; received: number }[];
  progress_distribution: { range: string; count: number }[];
}

export interface DelayedProject {
  id: number; name: string; leader?: string; domain: string; cohort: string; status: string; progress_pct: number;
  deadline: string | null; deadline_passed: boolean; late_milestones: number; first_late_milestone: string | null;
  days_late: number;
}

export interface Meta {
  simulated: boolean; institution: string; statuses: string[]; delay_tolerance_days: number;
  definitions: Record<string, { label: string; unit: KpiUnit; definition: string }>;
}

export interface Partner { id: number; name: string; type: string }
export interface Leader { id: number; first_name: string; last_name: string; gender: string | null; profile: string; email: string | null; phone: string | null }

export interface AskResult {
  answer: string; mode: string; simulated: boolean;
  tools: { name: string; arguments: unknown; result: unknown; error: string | null }[];
}
