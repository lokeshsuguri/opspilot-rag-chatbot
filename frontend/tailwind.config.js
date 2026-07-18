/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#12151C",
          900: "#1A1E29",
          800: "#232838",
          700: "#2E3446",
          600: "#454C63",
          400: "#8892A6",
          200: "#C7CCD9",
        },
        paper: "#F7F6F3",
        manifest: {
          amber: "#D98E3D",
          amberDark: "#B8752E",
          green: "#4F7A5E",
          red: "#B8544A",
        },
      },
      fontFamily: {
        mono: ["'IBM Plex Mono'", "ui-monospace", "SFMono-Regular", "monospace"],
        sans: ["'Inter'", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      boxShadow: {
        tag: "0 1px 2px rgba(18, 21, 28, 0.08)",
      },
    },
  },
  plugins: [],
};
