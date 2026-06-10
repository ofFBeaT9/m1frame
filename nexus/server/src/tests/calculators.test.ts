import { describe, it, expect } from "vitest";
import { getCalculator } from "../domain/calculators.js";
import { news2 } from "../domain/news2.js";

const run = (id: string, inputs: Record<string, number | string | boolean>) =>
  getCalculator(id)!.compute(inputs);

describe("Calculator library (Cycle 2 red-team fixes)", () => {
  it("C1: CHA2DS2-VASc — woman with ONLY the sex point is low risk, not 'consider'", () => {
    const r = run("chads_vasc", { female: true, age: 50 });
    expect(r.value).toBe("1"); // total includes sex point
    expect(r.band).toBe("normal");
    expect(r.interpretation).toMatch(/not recommended/i);
  });

  it("C1: a man with one true risk factor (HTN) is 'consider'", () => {
    const r = run("chads_vasc", { htn: true, age: 50 });
    expect(r.value).toBe("1");
    expect(r.band).toBe("moderate");
    expect(r.interpretation).toMatch(/consider/i);
  });

  it("H1: NEWS2 calculator delegates to validated scorer (single-red preserved)", () => {
    // HR 38 (+3) alone -> validated news2 gives low-medium / red_score
    const r = run("news2", { hr: 38, rr: 16, spo2: 98, sbp: 120, temp: 36.8 });
    expect(r.value).toBe("3");
    expect(r.interpretation).toMatch(/single red parameter/i);
  });

  it("H2: Wells PE low band advises D-dimer, not PERC", () => {
    const r = run("wells_pe", {});
    expect(r.band).toBe("low");
    expect(r.interpretation).not.toMatch(/PERC/);
    expect(r.interpretation).toMatch(/D-dimer/);
  });

  it("Cockcroft-Gault female correction applied", () => {
    const male = run("cockcroft_gault", { age: 60, weight: 80, creatinine: 1.0, sex: "male" });
    const female = run("cockcroft_gault", { age: 60, weight: 80, creatinine: 1.0, sex: "female" });
    const mv = parseInt(male.value);
    const fv = parseInt(female.value);
    expect(fv).toBeLessThan(mv); // 0.85 factor
  });
});

describe("NEWS2 completeness guard (M1)", () => {
  it("flags an incomplete observation set", () => {
    const partial = news2({ rr: null, spo2: null, on_oxygen: true, sbp: null, hr: null, temp: null, altered_consciousness: false });
    expect(partial.complete).toBe(false);
    expect(partial.parameters_scored).toBe(2); // oxygen + consciousness only
  });
  it("a full vital set is complete", () => {
    const full = news2({ rr: 16, spo2: 98, on_oxygen: false, sbp: 120, hr: 72, temp: 36.8, altered_consciousness: false });
    expect(full.complete).toBe(true);
    expect(full.parameters_scored).toBe(7);
  });
});
