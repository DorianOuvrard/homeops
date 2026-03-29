/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          terra: "#c45d3e",
          "terra-hover": "#a84e34",
          "terra-light": "#f0ded8",
          sage: "#7a9e7e",
          "sage-light": "#e8f0e9",
          cream: "#faf8f5",
          warm: "#d4915e",
          "warm-light": "#fdf6ef",
          danger: "#c45d5d",
        },
        warm: {
          900: "#3d3833",
          700: "#5a524b",
          600: "#6b6359",
          500: "#8a8078",
          400: "#b5ada5",
          300: "#d4cdc5",
          200: "#e8e2db",
          100: "#f0ece7",
          50: "#faf8f5",
        },
      },
      borderRadius: {
        "2xl": "16px",
        "3xl": "20px",
      },
      boxShadow: {
        soft: "0 1px 8px rgba(61, 56, 51, 0.06)",
        "soft-md": "0 2px 16px rgba(61, 56, 51, 0.08)",
        "soft-lg": "0 4px 24px rgba(61, 56, 51, 0.1)",
      },
    },
  },
  plugins: [],
};
