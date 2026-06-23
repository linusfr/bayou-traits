/** @type {import('tailwindcss').Config} */
export default {
	content: ['./index.html', './src/**/*.{js,jsx}'],
	theme: {
		extend: {
			colors: {
				hunt: {
					bg:             '#0B0906',
					surface:        '#160E08',
					card:           '#221810',
					'card-hover':   '#2A1F13',
					border:         '#2C2016',
					'border-strong':'#5C3E20',
					gold:           '#C9932A',
					'gold-bright':  '#E8B048',
					text:           '#E4D5B8',
					'text-muted':   '#8A7356',
					'text-dim':     '#6B5A44',
				},
			},
			fontFamily: {
				display: ['Cinzel', 'Georgia', 'serif'],
				body:    ['Inter', 'system-ui', 'sans-serif'],
			},
			boxShadow: {
				gold:    '0 0 0 1px rgba(201,147,42,0.6), 0 0 20px rgba(201,147,42,0.15)',
				'gold-sm': '0 0 0 1px rgba(201,147,42,0.4)',
			},
			screens: {
				'3xl': '1920px',
			},
		},
	},
	plugins: [],
}
