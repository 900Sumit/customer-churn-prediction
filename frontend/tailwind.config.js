import daisyui from "daisyui";
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  daisyui: { themes: ["light", "dark"] },
  theme: {
    extend: { fontFamily: { sans: ["Inter", "ui-sans-serif", "system-ui"] } },
  },
  plugins: [daisyui],
};
