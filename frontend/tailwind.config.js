/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        obsidian: {
          950: "#05080c",
          900: "#0a1018",
          850: "#0d141e",
          800: "#111b28",
          700: "#1a2636",
          600: "#243447",
          500: "#334155",
        },
        risk: {
          low: "#22c55e",
          medium: "#eab308",
          high: "#f97316",
          critical: "#ef4444",
        },
        geo: {
          accent: "#38bdf8",
          glow: "#0ea5e9",
          forest: "#166534",
          loss: "#b45309",
          water: "#1e3a5f",
        },
      },
      fontFamily: {
        sans: [
          "IBM Plex Sans",
          "ui-sans-serif",
          "system-ui",
          "Segoe UI",
          "Roboto",
          "sans-serif",
        ],
        mono: ["IBM Plex Mono", "ui-monospace", "monospace"],
      },
      boxShadow: {
        panel: "0 0 0 1px rgb(30 41 59 / 0.6), 0 8px 32px rgb(0 0 0 / 0.45)",
        glow: "0 0 24px rgb(14 165 233 / 0.15)",
      },
    },
  },
  plugins: [],
};
