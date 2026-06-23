import { useState, useMemo, useCallback } from 'preact/hooks'
import Fuse from 'fuse.js'
import data from './data.json'
import SearchBar from './components/SearchBar'
import ItemCard from './components/ItemCard'
import SynergyPanel from './components/SynergyPanel'

const AMMO_ORDER = ['long', 'medium', 'compact', 'shotgun', 'sparks', 'nitro']

const WEAPON_FUSE_OPTS = { keys: ['name', 'type', 'ammo', 'size'], threshold: 0.35 }
const TRAIT_FUSE_OPTS  = { keys: ['name', 'description', 'category'], threshold: 0.35 }

function buildSynergyDetail(item, type, weaponIdx, traitIdx) {
	if (!item) return null
	const isWeapon = type === 'weapon'
	const synergies = isWeapon
		? (item.trait_synergies ?? [])
			.map(s => {
				const t = traitIdx[s.trait_id]
				return t ? { ...t, reason: s.reason } : null
			})
			.filter(Boolean)
		: (item.weapon_synergies ?? [])
			.map(s => {
				const w = weaponIdx[s.weapon_id]
				return w ? { ...w, reason: s.reason } : null
			})
			.filter(Boolean)
	return { item, synergies, type }
}

export default function App() {
	const [mode, setMode] = useState('weapon')
	const [query, setQuery] = useState('')
	const [filter, setFilter] = useState(null)
	const [selectedId, setSelectedId] = useState(null)

	const weapons = data.weapons
	const traits  = data.traits

	const weaponIdx = useMemo(() => Object.fromEntries(weapons.map(w => [w.id, w])), [weapons])
	const traitIdx  = useMemo(() => Object.fromEntries(traits.map(t  => [t.id,  t])), [traits])

	const weaponFuse = useMemo(() => new Fuse(weapons, WEAPON_FUSE_OPTS), [weapons])
	const traitFuse  = useMemo(() => new Fuse(traits,  TRAIT_FUSE_OPTS),  [traits])

	const items = useMemo(() => {
		const source = mode === 'weapon' ? weapons : traits
		const fuse   = mode === 'weapon' ? weaponFuse : traitFuse

		let list = query.trim()
			? fuse.search(query.trim()).map(r => r.item)
			: source

		if (filter) {
			list = list.filter(item =>
				mode === 'weapon'
					? item.ammo === filter || item.size === filter
					: item.category === filter
			)
		}
		return list
	}, [mode, query, filter, weapons, traits, weaponFuse, traitFuse])

	const detail = useMemo(() => {
		if (!selectedId) return null
		const item = mode === 'weapon' ? weaponIdx[selectedId] : traitIdx[selectedId]
		return buildSynergyDetail(item, mode, weaponIdx, traitIdx)
	}, [selectedId, mode, weaponIdx, traitIdx])

	const switchMode = useCallback((m) => {
		setMode(m)
		setQuery('')
		setFilter(null)
		setSelectedId(null)
	}, [])

	const handleSelect = useCallback((id) => {
		setSelectedId(prev => prev === id ? null : id)
	}, [])

	// Navigate from a synergy row: flip mode and select the linked item
	const handleNavigate = useCallback((id) => {
		setMode(prev => {
			const next = prev === 'weapon' ? 'trait' : 'weapon'
			return next
		})
		setQuery('')
		setFilter(null)
		setSelectedId(id)
	}, [])

	const activeFilters = useMemo(() => {
		if (mode === 'weapon') {
			const present = new Set(weapons.map(w => w.ammo).filter(a => a && a !== 'unknown'))
			return AMMO_ORDER.filter(a => present.has(a))
		}
		const present = new Set(traits.map(t => t.category).filter(c => c && c !== 'unknown'))
		return [...present].sort()
	}, [mode, weapons, traits])

	const panelOpen = !!detail

	return (
		<div className="min-h-screen bg-hunt-bg font-body flex flex-col">

			{/* ── Header ── */}
			<header className="shrink-0 border-b border-hunt-border-strong bg-hunt-surface">
				<div className="max-w-[1800px] mx-auto px-4 sm:px-6 py-5 sm:py-6 flex items-center justify-between gap-4">
					<div>
						<h1 className="font-display text-hunt-gold font-semibold tracking-[0.06em] glow-gold
							text-2xl sm:text-3xl">
							Bayou Traits
						</h1>
						<p className="text-xs uppercase tracking-[0.25em] text-hunt-text-muted mt-1">
							Hunt: Showdown &middot; Trait &amp; Weapon Synergies
						</p>
					</div>
					<div className="text-right shrink-0">
						<p className="text-xs uppercase tracking-widest text-hunt-text-dim">Patch</p>
						<p className="font-display text-hunt-gold text-sm">{data.meta.patch}</p>
					</div>
				</div>
			</header>

			{/* ── Sticky controls ── */}
			<div className="shrink-0 border-b border-hunt-border bg-hunt-surface/80 sticky top-0 z-20 backdrop-blur-sm">
				<div className="max-w-[1800px] mx-auto px-4 sm:px-6 pt-3 pb-2 flex flex-col sm:flex-row gap-2 sm:gap-3">
					{/* Mode toggle */}
					<div className="flex rounded overflow-hidden border border-hunt-border shrink-0">
						{['weapon', 'trait'].map(m => (
							<button
								key={m}
								onClick={() => switchMode(m)}
								className={`px-4 py-2 text-sm font-medium transition-colors
									${mode === m
										? 'bg-hunt-gold text-hunt-bg'
										: 'bg-hunt-surface text-hunt-text-muted hover:text-hunt-text hover:bg-hunt-card'
									}`}
							>
								{m === 'weapon' ? 'By Weapon' : 'By Trait'}
							</button>
						))}
					</div>
					<SearchBar
						value={query}
						onChange={setQuery}
						placeholder={mode === 'weapon' ? 'Search weapons…' : 'Search traits…'}
					/>
				</div>

				{/* Filter pills */}
				<div className="max-w-[1800px] mx-auto px-4 sm:px-6 pb-2 flex gap-2 overflow-x-auto no-scrollbar">
					<button
						onClick={() => setFilter(null)}
						className={`px-3 py-1 text-xs rounded-full border shrink-0 transition-colors
							${!filter
								? 'border-hunt-gold text-hunt-gold bg-hunt-gold/10'
								: 'border-hunt-border text-hunt-text-muted hover:border-hunt-border-strong'
							}`}
					>
						All
					</button>
					{activeFilters.map(f => (
						<button
							key={f}
							onClick={() => setFilter(prev => prev === f ? null : f)}
							className={`px-3 py-1 text-xs rounded-full border shrink-0 capitalize transition-colors
								${filter === f
									? 'border-hunt-gold text-hunt-gold bg-hunt-gold/10'
									: 'border-hunt-border text-hunt-text-muted hover:border-hunt-border-strong'
								}`}
						>
							{f}
						</button>
					))}
				</div>
			</div>

			{/* ── Main content ── */}
			<div className="flex-1 overflow-hidden">
				<div className="max-w-[1800px] mx-auto h-full flex">

					{/* Item list — hidden on mobile when panel is open */}
					<div className={`${panelOpen ? 'hidden lg:flex' : 'flex'} flex-col
						w-full lg:w-1/2 xl:w-2/5 2xl:w-1/3
						overflow-y-auto border-r border-hunt-border`}
					>
						{items.length === 0 ? (
							<div className="flex-1 flex items-center justify-center">
								<p className="text-hunt-text-dim text-sm">Nothing found in the fog.</p>
							</div>
						) : (
							<div className="p-4 grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-2 2xl:grid-cols-3 3xl:grid-cols-4 gap-2 content-start">
								{items.map(item => (
									<ItemCard
										key={item.id}
										item={item}
										type={mode}
										selected={selectedId === item.id}
										onClick={() => handleSelect(item.id)}
									/>
								))}
							</div>
						)}
					</div>

					{/* Synergy panel */}
					{panelOpen ? (
						<div className="flex-1 overflow-y-auto p-4 lg:p-6">
							<SynergyPanel
								detail={detail}
								onClose={() => setSelectedId(null)}
								onNavigate={handleNavigate}
							/>
						</div>
					) : (
						/* Placeholder on desktop when nothing is selected */
						<div className="hidden lg:flex flex-1 items-center justify-center">
							<div className="text-center">
								<svg
									className="w-14 h-14 text-hunt-border-strong mb-4 mx-auto"
									viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={0.75}
								>
									<circle cx="12" cy="12" r="8.5" />
									<circle cx="12" cy="12" r="1.5" fill="currentColor" stroke="none" />
									<line x1="12" y1="1" x2="12" y2="5.5" />
									<line x1="12" y1="18.5" x2="12" y2="23" />
									<line x1="1" y1="12" x2="5.5" y2="12" />
									<line x1="18.5" y1="12" x2="23" y2="12" />
								</svg>
								<p className="text-hunt-text-dim text-sm">
									Select a {mode} to reveal its synergies
								</p>
							</div>
						</div>
					)}
				</div>
			</div>

			{/* ── Footer ── */}
			<footer className="shrink-0 border-t border-hunt-border bg-hunt-surface px-4 py-2">
				<p className="max-w-[1800px] mx-auto text-xs text-hunt-text-dim text-center">
					Data scraped from the{' '}
					<a
						href="https://huntshowdown.fandom.com"
						target="_blank"
						rel="noopener noreferrer"
						className="text-hunt-text-muted hover:text-hunt-gold transition-colors"
					>
						Hunt: Showdown Wiki
					</a>
					{' '}· Built {new Date(data.meta.scraped_at).toLocaleDateString()}
					{' '}· {data.meta.trait_count} traits · {data.meta.weapon_count} weapons
				</p>
			</footer>
		</div>
	)
}
