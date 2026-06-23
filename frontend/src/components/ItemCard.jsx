const CATEGORY_PILL = {
	offensive:  'text-red-400   border-red-900/60   bg-red-950/30',
	defensive:  'text-green-400 border-green-900/60 bg-green-950/30',
	movement:   'text-sky-400   border-sky-900/60   bg-sky-950/30',
	supportive: 'text-amber-400 border-amber-900/60 bg-amber-950/30',
}

const AMMO_COLOR = {
	long:    'text-yellow-400',
	medium:  'text-orange-400',
	compact: 'text-sky-400',
	shotgun: 'text-red-400',
	sparks:  'text-purple-400',
	nitro:   'text-red-300',
}

export default function ItemCard({ item, type, selected, onClick }) {
	const isWeapon = type === 'weapon'
	const synCount = isWeapon
		? (item.trait_synergies?.length ?? 0)
		: (item.weapon_synergies?.length ?? 0)

	return (
		<button
			onClick={onClick}
			className={`relative w-full text-left rounded border transition-all duration-150 p-3
				${selected
					? 'border-hunt-gold shadow-gold bg-hunt-card-hover'
					: 'border-hunt-border bg-hunt-card hover:border-hunt-border-strong hover:bg-hunt-card-hover'
				}`}
		>
			{isWeapon ? (
				<>
					<p className="font-display text-hunt-text text-sm font-medium leading-snug">
						{item.name}
					</p>
					<div className="flex items-center gap-2 mt-2 flex-wrap">
						{item.ammo && item.ammo !== 'unknown' && (
							<span className={`text-xs font-medium capitalize ${AMMO_COLOR[item.ammo] ?? 'text-hunt-text-muted'}`}>
								{item.ammo}
							</span>
						)}
						{item.size && item.size !== 'unknown' && (
							<span className="text-xs text-hunt-text-dim capitalize">{item.size}</span>
						)}
					</div>
					{synCount > 0 && (
						<p className="mt-2 text-xs text-hunt-text-dim">
							{synCount} trait{synCount !== 1 ? 's' : ''}
						</p>
					)}
				</>
			) : (
				<>
					<div className="flex items-start justify-between gap-2">
						<p className="font-display text-hunt-text text-sm font-medium leading-snug">
							{item.name}
						</p>
						{item.cost > 0 && (
							<span className="shrink-0 text-xs text-hunt-gold font-semibold tabular-nums">
								{item.cost}pt
							</span>
						)}
					</div>
					{item.category && item.category !== 'unknown' && (
						<div className="mt-2">
							<span className={`inline text-xs px-2 py-0.5 rounded border capitalize
								${CATEGORY_PILL[item.category] ?? 'text-hunt-text-dim border-hunt-border bg-transparent'}`}>
								{item.category}
							</span>
						</div>
					)}
					{item.description && (
						<p className="mt-2 text-xs text-hunt-text-muted line-clamp-2 leading-relaxed">
							{item.description}
						</p>
					)}
					{synCount > 0 && (
						<p className="mt-2 text-xs text-hunt-text-dim">
							{synCount} weapon{synCount !== 1 ? 's' : ''}
						</p>
					)}
				</>
			)}
		</button>
	)
}
