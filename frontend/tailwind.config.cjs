/** Tailwind build for FairLendAI — replaces the runtime CDN script. */
/** Tailwind v3 scanner configuration (no CDN script in production). */
module.exports = {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0B1F2A",        // deepest navy — hero/near-black surfaces
        navy: {
          900: "#0F2231",       // portal header chrome
          800: "#173247",
          700: "#24323D",       // legacy primary text continuity
        },
        teal: {                // brand actions (overridden hue, WCAG-checked)
          700: "#0C655C",
          600: "#0E766B",
          500: "#148A7F",
          100: "#E3F2EF",
        },
        paper: "#F6F7F4",      // warm institutional background
        line: "#E4E8E4",
        body: "#23313C",
        fsub: "#5C6B78",
      },
      fontFamily: {
        sans: ['"IBM Plex Sans"', '"IBM Plex Sans Devanagari"', "-apple-system", "Segoe UI", "Roboto", "sans-serif"],
        serif: ['"IBM Plex Sans"', '"IBM Plex Sans Devanagari"', "Georgia", "sans-serif"],  // legacy .font-serif → same system
        deva: ['"IBM Plex Sans Devanagari"', '"IBM Plex Sans"', "sans-serif"],
        mono: ['"IBM Plex Mono"', "ui-monospace", "SFMono-Regular", "monospace"],
      },
      boxShadow: {
        card: "0 2px 8px rgba(11, 31, 42, 0.05), 0 1px 2px rgba(11, 31, 42, 0.03)",
        hover: "0 10px 24px -4px rgba(11, 31, 42, 0.08), 0 4px 8px -2px rgba(11, 31, 42, 0.04)",
      },
    },
  },
  plugins: [],
};
