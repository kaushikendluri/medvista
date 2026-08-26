import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        base: {
          950: "#0a0c0e",
          900: "#101317",
          850: "#141820",
          800: "#1a1f28",
          700: "#242b36",
          600: "#33404f",
        },
        accent: {
          DEFAULT: "#4dd9e8",
          dim: "#2a8a94",
          muted: "#1e5158",
        },
        status: {
          info: "#4dd9e8",
          success: "#4ade80",
          warning: "#facc15",
          critical: "#f87171",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
      borderRadius: {
        panel: "10px",
      },
    },
  },
  plugins: [],
};

export default config;
