export type Priority = "High" | "Medium" | "Low";

export type SkillOut = {
  skill_id: string;
  skill: string;
  category: string;
  found_as?: string[];
  confidence?: number;
  importance?: number;
  priority?: Priority;
  reason?: string;
  suggested_path?: string[];
};

export type AnalyzeResponse = {
  matched: SkillOut[];
  missing: SkillOut[];
  summary: { target_role: string; matched_count: number; missing_count: number };
};

export function groupByPriority(skills: SkillOut[]): Record<Priority, SkillOut[]> {
  const out: Record<Priority, SkillOut[]> = { High: [], Medium: [], Low: [] };
  skills.forEach((s) => out[(s.priority ?? "Low") as Priority].push(s));
  return out;
}
