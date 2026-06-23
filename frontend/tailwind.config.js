/** @type {import('tailwindcss').Config} */
export default {
	content: ['./index.html', './src/**/*.{js,jsx}'],
	theme: {
		extend: {
			colors: {
				hunt: {
					bg:             '#0B0906',
					surface:        '#131009',
					card:           '#1C1510',
					'card-hover':   '#251C12',
					border:         '#2C2016',
					'border-strong':'#5C3E20',
					gold:           '#C9932A',
					'gold-bright':  '#E8B048',
					text:           '#E4D5B8',
					'text-muted':   '#8A7356',
					'text-dim':     '#4A3E2E',
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
