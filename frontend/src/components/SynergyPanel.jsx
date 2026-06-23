const CATEGORY_PILL = {
	offensive:  'text-red-400   border-red-900/60   bg-red-950/30',
	defensive:  'text-green-400 border-green-900/60 bg-green-950/30',
	movement:   'text-sky-400   border-sky-900/60   bg-sky-950/30',
	supportive: 'text-amber-400 border-amber-900/60 bg-amber-950/30',
}

const AMMO_PILL = {
	long:    'text-yellow-400 border-yellow-900/60 bg-yellow-950/30',
	medium:  'text-orange-400 border-orange-900/60 bg-orange-950/30',
	compact: 'text-sky-400   border-sky-900/60   bg-sky-950/30',
	shotgun: 'text-red-400   border-red-900/60   bg-red-950/30',
	sparks:  'text-purple-400 border-purple-900/60 bg-purple-950/30',
	nitro:   'text-red-300   border-red-900/50   bg-red-950/20',
}

function Pill({ label, className }) {
	return (
		<span className={`inline text-xs px-2 py-0.5 rounded border capitalize ${className}`}>
			{label}
		</span>
	)
}

function SynergyRow({ syn, isWeapon, onNavigate }) {
	return (
		<button
			onClick={() => onNavigate(syn.id)}
			className="w-full text-left rounded border border-hunt-border bg-hunt-card
				hover:border-hunt-border-strong hover:bg-hunt-card-hover transition-all duration-150 p-3 group"
		>
			<div className="flex items-start gap-2 justify-between">
				<span className="font-display text-sm text-hunt-text font-medium
					group-hover:text-hunt-gold transition-colors leading-snug">
					{syn.name}
				</span>
				{isWeapon
					? syn.category && syn.category !== 'unknown' && (
						<Pill label={syn.category} className={CATEGORY_PILL[syn.category] ?? 'text-hunt-text-dim border-hunt-border'} />
					)
					: syn.ammo && syn.ammo !== 'unknown' && (
						<Pill label={syn.ammo} className={AMMO_PILL[syn.ammo] ?? 'text-hunt-text-dim border-hunt-border'} />
					)
				}
			</div>
			{syn.reason && (
				<p className="mt-1.5 text-xs text-hunt-text-muted leading-relaxed">
					{syn.reason}
				</p>
			)}
		</button>
	)
}

export default function SynergyPanel({ detail, onClose, onNavigate }) {
	const { item, synergies, type } = detail
	if (!item) return null
	const isWeapon = type === 'weapon'

	return (
		<div className="flex flex-col h-full">
			{/* Back / close — visible on mobile */}
			<button
				onClick={onClose}
				className="flex items-center gap-1.5 text-hunt-text-dim hover:text-hunt-text
					transition-colors mb-4 text-sm lg:hidden"
			>
				<svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
					<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
				</svg>
				Back
			</button>

			{/* Item header */}
			<div className="pb-4 mb-4 border-b border-hunt-border">
				<p className="text-xs uppercase tracking-widest text-hunt-text-dim mb-1">
					{isWeapon ? 'Weapon' : 'Trait'}
				</p>
				<h2 className="font-display text-hunt-gold text-xl font-semibold leading-tight glow-gold">
					{item.name}
				</h2>
				<div className="flex flex-wrap items-center gap-2 mt-2">
					{isWeapon ? (
						<>
							{item.ammo && item.ammo !== 'unknown' && (
								<Pill
									label={`${item.ammo} ammo`}
									className={AMMO_PILL[item.ammo] ?? 'text-hunt-text-dim border-hunt-border'}
								/>
							)}
							{item.size && item.size !== 'unknown' && (
								<span className="text-xs text-hunt-text-muted capitalize">{item.size}</span>
							)}
						</>
					) : (
						<>
							{item.category && item.category !== 'unknown' && (
								<Pill
									label={item.category}
									className={CATEGORY_PILL[item.category] ?? 'text-hunt-text-dim border-hunt-border'}
								/>
							)}
							{item.cost > 0 && (
								<span className="text-xs text-hunt-gold">{item.cost} upgrade points</span>
							)}
							{item.trait_type && item.trait_type !== 'normal' && (
								<span className="text-xs text-hunt-text-dim italic capitalize">{item.trait_type}</span>
							)}
						</>
					)}
				</div>
			</div>

			{/* Description */}
			{item.description && (
				<p className="text-hunt-text-muted text-sm leading-relaxed mb-5">
					{item.description}
				</p>
			)}

			{/* Synergy list */}
			<div className="flex-1 overflow-y-auto min-h-0">
				<p className="text-xs uppercase tracking-widest text-hunt-text-dim mb-3">
					{isWeapon
						? `Best traits for this weapon (${synergies.length})`
						: `Weapons benefiting from this trait (${synergies.length})`
					}
				</p>
				{synergies.length === 0 ? (
					<p className="text-sm text-hunt-text-dim italic">
						No synergy data available yet — run the build pipeline to populate.
					</p>
				) : (
					<div className="space-y-2 pr-1">
						{synergies.map(syn => (
							<SynergyRow
								key={syn.id}
								syn={syn}
								isWeapon={isWeapon}
								onNavigate={onNavigate}
							/>
						))}
					</div>
				)}
			</div>
		</div>
	)
}
