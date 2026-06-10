import { describe, it, expect } from "vitest";
import { can, permissionFor, canInvokeCodeBlue, ROLE_PRIVILEGE, clientPermissions } from "../domain/rbac.js";
import { categoryFromDob, flagFor, meanArterialPressure } from "../domain/vitalRanges.js";

describe("RBAC permission matrix (spec §2.2)", () => {
  it("physician has full chart read; nurse is assigned-scoped", () => {
    expect(permissionFor("physician", "read_chart")).toBe(true);
    expect(permissionFor("nurse", "read_chart")).toBe("assigned");
    expect(permissionFor("patient", "read_chart")).toBe("own");
  });

  it("only admin manages users and reads audit", () => {
    expect(can("admin", "user_management")).toBe(true);
    expect(can("physician", "user_management")).toBe(false);
    expect(can("admin", "audit_read")).toBe(true);
    expect(can("nurse", "audit_read")).toBe(false);
  });

  it("nurses cannot write orders; residents co-sign", () => {
    expect(can("nurse", "write_orders")).toBe(false);
    expect(permissionFor("resident", "write_orders")).toBe("co-sign");
    expect(permissionFor("np_pa", "write_orders")).toBe("limited");
  });

  it("Code Blue override gated at privilege >= 6", () => {
    expect(canInvokeCodeBlue("nurse")).toBe(true); // privilege 6
    expect(canInvokeCodeBlue("med_tech")).toBe(false); // privilege 5
    expect(canInvokeCodeBlue("pharmacist")).toBe(false);
    expect(ROLE_PRIVILEGE.physician).toBe(9);
  });

  it("client matrix mirrors server matrix (no drift)", () => {
    const c = clientPermissions("nurse");
    expect(c.read_chart).toBe(permissionFor("nurse", "read_chart"));
    expect(c.write_vitals).toBe(permissionFor("nurse", "write_vitals"));
  });
});

describe("Patient category + age-adjusted ranges (spec §3.8)", () => {
  it("derives category from DOB", () => {
    const d = (days: number) => { const x = new Date(); x.setDate(x.getDate() - days); return x.toISOString().slice(0, 10); };
    expect(categoryFromDob(d(10))).toBe("neonatal");
    expect(categoryFromDob(d(200))).toBe("infant");
    expect(categoryFromDob(d(365 * 8))).toBe("pediatric");
    expect(categoryFromDob(d(365 * 40))).toBe("adult");
    expect(categoryFromDob(d(365 * 80))).toBe("geriatric");
  });

  it("flags HR by age band", () => {
    expect(flagFor("hr", 80, "adult")).toBe("normal");
    expect(flagFor("hr", 140, "adult")).toBe("critical");
    expect(flagFor("hr", 140, "neonatal")).toBe("normal"); // 120-160 normal for neonate
  });

  it("computes MAP", () => {
    expect(meanArterialPressure(120, 60)).toBe(80);
  });
});
