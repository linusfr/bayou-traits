export default function SearchBar({ value, onChange, placeholder }) {
	return (
		<div className="relative flex-1">
			<svg
				className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-hunt-text-dim pointer-events-none"
				fill="none" viewBox="0 0 24 24" stroke="currentColor"
			>
				<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
					d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
			</svg>
			<input
				type="search"
				value={value}
				onInput={e => onChange(e.target.value)}
				placeholder={placeholder}
				className="w-full bg-hunt-card border border-hunt-border rounded
					pl-9 pr-9 py-2 text-sm text-hunt-text placeholder-hunt-text-dim
					focus:outline-none focus:border-hunt-gold transition-colors"
			/>
			{value && (
				<button
					onClick={() => onChange('')}
					className="absolute right-3 top-1/2 -translate-y-1/2
						text-hunt-text-dim hover:text-hunt-text transition-colors"
					aria-label="Clear search"
				>
					<svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
						<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
					</svg>
				</button>
			)}
		</div>
	)
}
