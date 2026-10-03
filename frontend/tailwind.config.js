export default {
  content: ['./src/**/*.{html,js,svelte,ts}'],
  theme: {
    extend: {
      colors: {
        paper: '#f3efe6',
        ink: '#1a1814',
        muted: '#6f675e',
        line: '#e4dcd0',
        forest: '#0f6a4a',
        sand: '#efe8dc',
        clay: '#8f3d1f'
      },
      fontFamily: {
        sans: ['Avenir Next', 'Segoe UI', 'sans-serif'],
        serif: ['Iowan Old Style', 'Palatino Linotype', 'Palatino', 'Georgia', 'serif']
      }
    }
  },
  plugins: []
};
