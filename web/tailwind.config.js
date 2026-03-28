/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          navy: "#1a237e",
          orange: "#f57c00",
          "orange-light": "#ff9800",
        },
      },
    },
  },
  plugins: [],
};
