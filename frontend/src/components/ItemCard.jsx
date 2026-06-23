const CATEGORY_PILL = {
	offensive:  'text-[#C04A4A] border-[#C04A4A]/40 bg-[#C04A4A]/10',
	defensive:  'text-[#4A8C5C] border-[#4A8C5C]/40 bg-[#4A8C5C]/10',
	movement:   'text-[#B87E4A] border-[#B87E4A]/40 bg-[#B87E4A]/10',
	supportive: 'text-[#A89060] border-[#A89060]/40 bg-[#A89060]/10',
}

const WEAPON_CLASS_COLOR = {
	long:     'text-yellow-400',
	medium:   'text-orange-400',
	compact:  'text-sky-400',
	shotgun:  'text-red-400',
	sparks:   'text-purple-400',
	nitro:    'text-red-300',
	melee:    'text-stone-400',
	bow:      'text-emerald-400',
	launcher: 'text-amber-300',
}

const TOOL_CLASS_COLOR = {
	explosive: 'text-orange-400',
	fire:      'text-red-400',
	healing:   'text-green-400',
	melee:     'text-stone-400',
	decoy:     'text-yellow-400',
	poison:    'text-lime-400',
	support:   'text-sky-400',
}

export default function ItemCard({ item, type, selected, onClick }) {
	const isWeapon = type === 'weapon'
	const isTool   = type === 'tool'
	const synCount = isWeapon || isTool
		? (item.trait_synergies?.length ?? 0)
		: (item.weapon_synergies?.length ?? 0)

	return (
		<button
			onClick={onClick}
			className={`card-shine relative w-full text-left rounded border transition-all duration-150 p-3
				${selected
					? 'border-hunt-gold shadow-gold bg-hunt-card-hover'
					: 'border-hunt-border bg-hunt-card hover:border-hunt-border-strong hover:bg-hunt-card-hover'
				}`}
		>
			{isWeapon ? (
				<>
					<p className="text-hunt-text text-sm font-medium leading-snug">
						{item.name}
					</p>
					<div className="flex items-center gap-2 mt-2 flex-wrap">
						{item.weapon_class && item.weapon_class !== 'unknown' && (
							<span className={`text-xs font-medium capitalize ${WEAPON_CLASS_COLOR[item.weapon_class] ?? 'text-hunt-text-muted'}`}>
								{item.weapon_class}
							</span>
						)}
						{item.size && item.size !== 'unknown' && item.size !== 'melee' && (
							<span className="text-xs text-hunt-text-dim capitalize">{item.size}</span>
						)}
					</div>
					{synCount > 0 && (
						<p className="mt-2 text-xs text-hunt-text-dim">
							{synCount} trait{synCount !== 1 ? 's' : ''}
						</p>
					)}
				</>
			) : isTool ? (
				<>
					<p className="text-hunt-text text-sm font-medium leading-snug">
						{item.name}
					</p>
					<div className="flex items-center gap-2 mt-2 flex-wrap">
						{item.tool_class && (
							<span className={`text-xs font-medium capitalize ${TOOL_CLASS_COLOR[item.tool_class] ?? 'text-hunt-text-muted'}`}>
								{item.tool_class}
							</span>
						)}
						{item.cost > 0 && (
							<span className="text-xs text-hunt-gold font-semibold tabular-nums">
								{item.cost}pt
							</span>
						)}
					</div>
					{item.description && (
						<p className="mt-2 text-xs text-hunt-text-muted line-clamp-2 leading-relaxed">
							{item.description}
						</p>
					)}
					{synCount > 0 && (
						<p className="mt-2 text-xs text-hunt-text-dim">
							{synCount} trait{synCount !== 1 ? 's' : ''}
						</p>
					)}
				</>
			) : (
				<>
					<div className="flex items-start justify-between gap-2">
						<p className="text-hunt-text text-sm font-medium leading-snug">
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
