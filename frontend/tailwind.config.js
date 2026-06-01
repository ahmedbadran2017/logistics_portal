/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Inter"', "system-ui", "-apple-system", "sans-serif"],
        arabic: ['"Alexandria"', "system-ui", "-apple-system", "sans-serif"],
      },
      colors: {
        accent: {
          50:  "#fdf5f3",
          100: "#fbe6e0",
          200: "#f6ccbf",
          300: "#eea894",
          400: "#e17f62",
          500: "#d45d3e",
          600: "#c4492a",
          700: "#a33a22",
          800: "#852f1e",
          900: "#6d291d",
        },
      },
    },
  },
  plugins: [],
};
