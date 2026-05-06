import { describe, it, expect } from "vitest";
import { groupByPriority } from "../utils/skillUtils";
import type { SkillOut } from "../utils/skillUtils";

const makeSkill = (overrides: Partial<SkillOut> = {}): SkillOut => ({
  skill_id: "python",
  skill: "Python",
  category: "Programming Languages",
  ...overrides,
});

describe("groupByPriority", () => {
  it("places High-priority skills in the High bucket", () => {
    const skills = [makeSkill({ priority: "High" })];
    const result = groupByPriority(skills);
    expect(result.High).toHaveLength(1);
    expect(result.Medium).toHaveLength(0);
    expect(result.Low).toHaveLength(0);
  });

  it("places Medium-priority skills in the Medium bucket", () => {
    const skills = [makeSkill({ priority: "Medium" })];
    const result = groupByPriority(skills);
    expect(result.Medium).toHaveLength(1);
  });

  it("places Low-priority skills in the Low bucket", () => {
    const skills = [makeSkill({ priority: "Low" })];
    const result = groupByPriority(skills);
    expect(result.Low).toHaveLength(1);
  });

  it("defaults to Low when priority is undefined", () => {
    const skills = [makeSkill({ priority: undefined })];
    const result = groupByPriority(skills);
    expect(result.Low).toHaveLength(1);
  });

  it("handles an empty array", () => {
    const result = groupByPriority([]);
    expect(result.High).toHaveLength(0);
    expect(result.Medium).toHaveLength(0);
    expect(result.Low).toHaveLength(0);
  });

  it("distributes multiple skills across correct buckets", () => {
    const skills = [
      makeSkill({ skill_id: "a", priority: "High" }),
      makeSkill({ skill_id: "b", priority: "High" }),
      makeSkill({ skill_id: "c", priority: "Medium" }),
      makeSkill({ skill_id: "d", priority: "Low" }),
    ];
    const result = groupByPriority(skills);
    expect(result.High).toHaveLength(2);
    expect(result.Medium).toHaveLength(1);
    expect(result.Low).toHaveLength(1);
  });

  it("preserves skill data in the output", () => {
    const skill = makeSkill({ skill_id: "docker", skill: "Docker", priority: "High" });
    const result = groupByPriority([skill]);
    expect(result.High[0].skill_id).toBe("docker");
    expect(result.High[0].skill).toBe("Docker");
  });
});
