import { describe, it, expect } from "vitest";
import { news2, qsofa, news2Colour } from "../domain/news2.js";

describe("NEWS2 (RCP 2017)", () => {
  it("scores a fully normal adult as 0 / low", () => {
    const r = news2({ rr: 16, spo2: 98, on_oxygen: false, sbp: 120, hr: 72, temp: 36.8, altered_consciousness: false });
    expect(r.score).toBe(0);
    expect(r.band).toBe("low");
    expect(r.red_score).toBe(false);
  });

  it("scores supplemental oxygen as +2", () => {
    const air = news2({ rr: 16, spo2: 98, on_oxygen: false, sbp: 120, hr: 72, temp: 36.8, altered_consciousness: false });
    const o2 = news2({ rr: 16, spo2: 98, on_oxygen: true, sbp: 120, hr: 72, temp: 36.8, altered_consciousness: false });
    expect(o2.score - air.score).toBe(2);
  });

  it("worked example: septic deterioration scores high", () => {
    // RR 30(+3), SpO2 91(+3), on O2(+2), SBP 84(+3), HR 128(+2), temp 39.2(+2), altered(+3) = 18
    const r = news2({ rr: 30, spo2: 91, on_oxygen: true, sbp: 84, hr: 128, temp: 39.2, altered_consciousness: true });
    expect(r.score).toBe(18);
    expect(r.band).toBe("high");
    expect(r.red_score).toBe(true);
  });

  it("a single red parameter at low aggregate yields low-medium band", () => {
    // HR 38 (+3) only; everything else normal => aggregate 3, single red => low-medium
    const r = news2({ rr: 16, spo2: 98, on_oxygen: false, sbp: 120, hr: 38, temp: 36.8, altered_consciousness: false });
    expect(r.score).toBe(3);
    expect(r.band).toBe("low-medium");
  });

  it("boundary checks for component scoring", () => {
    expect(news2({ rr: 8, spo2: 96, on_oxygen: false, sbp: 120, hr: 80, temp: 37, altered_consciousness: false }).components.rr).toBe(3);
    expect(news2({ rr: 12, spo2: 96, on_oxygen: false, sbp: 120, hr: 80, temp: 37, altered_consciousness: false }).components.rr).toBe(0);
    expect(news2({ rr: 22, spo2: 96, on_oxygen: false, sbp: 120, hr: 80, temp: 37, altered_consciousness: false }).components.rr).toBe(2);
  });

  it("maps aggregate scores to board colours", () => {
    expect(news2Colour(3)).toBe("green");
    expect(news2Colour(6)).toBe("amber");
    expect(news2Colour(7)).toBe("red");
    expect(news2Colour(10)).toBe("darkred");
  });
});

describe("qSOFA (Sepsis-3)", () => {
  it("fires sepsis alert at >= 2 points", () => {
    const r = qsofa({ rr: 24, sbp: 96, altered_mentation: false });
    expect(r.score).toBe(2);
    expect(r.sepsis_alert).toBe(true);
  });
  it("does not fire below 2", () => {
    const r = qsofa({ rr: 18, sbp: 130, altered_mentation: true });
    expect(r.score).toBe(1);
    expect(r.sepsis_alert).toBe(false);
  });
});
