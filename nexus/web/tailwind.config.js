/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        // Spec §16.1 palette (dark mode only)
        base: "#0A0E17",
        surface: "#111827",
        elevated: "#1C2536",
        input: "#1E2A3A",
        "accent-primary": "#2DD4BF",
        "accent-secondary": "#3B82F6",
        warning: "#F59E0B",
        critical: "#EF4444",
        success: "#10B981",
        info: "#6366F1",
        "text-primary": "#F1F5F9",
        "text-secondary": "#94A3B8",
        "text-muted": "#475569",
        "border-subtle": "#1E293B",
        "border-active": "#334155",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};
