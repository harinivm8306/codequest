import type { Config } from "tailwindcss";

export default {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#F6F6FA",
        card: "#FFFFFF",
        ink: "#1C1B29",
        muted: "#5B5870",
        line: "#DCDAE6",
        stamp: { DEFAULT: "#4B2E83", soft: "#ECE6F6", deep: "#33205C" },
        leaf: { DEFAULT: "#1B7F4B", soft: "#E3F2EA" },
        turmeric: { DEFAULT: "#8A5A00", bright: "#E0A100", soft: "#FBF1D6" },
        brick: { DEFAULT: "#B3261E", soft: "#FBE7E5" },
      },
      fontFamily: {
        sans: ['"Mukta Malar"', '"Mukta"', "system-ui", "sans-serif"],
      },
      fontSize: {
        // scale 1.2 from 17px base, for reading at arm's length
        sm: ["0.94rem", "1.45"],
        base: ["1.0625rem", "1.55"],
        lg: ["1.275rem", "1.45"],
        xl: ["1.53rem", "1.35"],
        "2xl": ["1.84rem", "1.25"],
      },
    },
  },
  plugins: [],
} satisfies Config;
