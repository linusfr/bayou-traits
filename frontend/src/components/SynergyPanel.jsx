const CATEGORY_PILL = {
  offensive: "text-[#C04A4A] border-[#C04A4A]/40 bg-[#C04A4A]/10",
  defensive: "text-[#4A8C5C] border-[#4A8C5C]/40 bg-[#4A8C5C]/10",
  movement: "text-[#B87E4A] border-[#B87E4A]/40 bg-[#B87E4A]/10",
  supportive: "text-[#A89060] border-[#A89060]/40 bg-[#A89060]/10",
};

const WEAPON_CLASS_PILL = {
  long: "text-yellow-400 border-yellow-900/60 bg-yellow-950/30",
  medium: "text-orange-400 border-orange-900/60 bg-orange-950/30",
  compact: "text-sky-400   border-sky-900/60   bg-sky-950/30",
  shotgun: "text-red-400   border-red-900/60   bg-red-950/30",
  sparks: "text-purple-400 border-purple-900/60 bg-purple-950/30",
  nitro: "text-red-300   border-red-900/50   bg-red-950/20",
  melee: "text-stone-400  border-stone-700/60  bg-stone-950/30",
  bow: "text-emerald-400 border-emerald-900/60 bg-emerald-950/30",
  launcher: "text-amber-300  border-amber-800/60  bg-amber-950/30",
};

const TRAIT_TYPE_PILL = {
  scarce: "text-amber-400 border-amber-900/60 bg-amber-950/30",
  event: "text-cyan-400  border-cyan-900/60  bg-cyan-950/30",
};

const BURN_PILL = "text-red-400 border-red-900/60 bg-red-950/30";
const SOLO_PILL = "text-violet-400 border-violet-900/60 bg-violet-950/30";

const CONSUMABLE_CLASSES = new Set(["healing", "support"]);

const TOOL_CLASS_PILL = {
  explosive: "text-orange-400 border-orange-900/60 bg-orange-950/30",
  fire: "text-red-400   border-red-900/60   bg-red-950/30",
  healing: "text-green-400  border-green-900/60  bg-green-950/30",
  melee: "text-stone-400  border-stone-700/60  bg-stone-950/30",
  decoy: "text-yellow-400 border-yellow-900/60 bg-yellow-950/30",
  poison: "text-lime-400   border-lime-900/60   bg-lime-950/30",
  support: "text-sky-400   border-sky-900/60   bg-sky-950/30",
};

function Pill({ label, className }) {
  return (
    <span
      className={`inline text-xs px-2 py-0.5 rounded border capitalize ${className}`}
    >
      {label}
    </span>
  );
}

function SynergyRow({ syn, isWeapon, isTool, onNavigate, targetMode }) {
  return (
    <button
      onClick={() => onNavigate(syn.id, targetMode)}
      className="w-full text-left rounded border border-hunt-border bg-hunt-card
				hover:border-hunt-border-strong hover:bg-hunt-card-hover transition-all duration-150 p-3 group"
    >
      <div className="flex items-start gap-2 justify-between">
        <span
          className="font-display text-sm text-hunt-text font-medium
					group-hover:text-hunt-gold transition-colors leading-snug"
        >
          {syn.name}
        </span>
        {isWeapon
          ? syn.category &&
            syn.category !== "unknown" && (
              <Pill
                label={syn.category}
                className={
                  CATEGORY_PILL[syn.category] ??
                  "text-hunt-text-dim border-hunt-border"
                }
              />
            )
          : isTool
            ? syn.tool_class && (
                <Pill
                  label={syn.tool_class}
                  className={
                    TOOL_CLASS_PILL[syn.tool_class] ??
                    "text-hunt-text-dim border-hunt-border"
                  }
                />
              )
            : syn.weapon_class &&
              syn.weapon_class !== "unknown" && (
                <Pill
                  label={syn.weapon_class}
                  className={
                    WEAPON_CLASS_PILL[syn.weapon_class] ??
                    "text-hunt-text-dim border-hunt-border"
                  }
                />
              )}
      </div>
      {syn.reason && (
        <p className="mt-1.5 text-xs text-hunt-text-muted leading-relaxed">
          {syn.reason}
        </p>
      )}
    </button>
  );
}

export default function SynergyPanel({ detail, onClose, onNavigate }) {
  const { item, synergies, toolSynergies, type } = detail;
  if (!item) return null;
  const isWeapon = type === "weapon";
  const isTool = type === "tool" || type === "consumable";
  const isTrait = type === "trait";
  const isConsumable = type === "consumable";

  return (
    <div className="flex flex-col h-full">
      {/* Back / close — visible on mobile */}
      <button
        onClick={onClose}
        className="flex items-center gap-1.5 text-hunt-text-dim hover:text-hunt-text
					transition-colors mb-4 text-sm lg:hidden"
      >
        <svg
          className="w-4 h-4"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M15 19l-7-7 7-7"
          />
        </svg>
        Back
      </button>

      {/* Item header */}
      <div className="pb-4 mb-4 border-b border-hunt-border">
        <p className="text-xs uppercase tracking-widest text-hunt-text-dim mb-1">
          {isWeapon ? "Weapon" : isConsumable ? "Consumable" : isTool ? "Tool" : "Trait"}
        </p>
        <h2 className="font-display text-hunt-gold text-xl font-semibold leading-tight glow-gold">
          {item.name}
        </h2>
        <div className="flex flex-wrap items-center gap-2 mt-2">
          {isWeapon ? (
            <>
              {item.weapon_class && item.weapon_class !== "unknown" && (
                <Pill
                  label={
                    item.ammo !== "unknown"
                      ? `${item.weapon_class} ammo`
                      : item.weapon_class
                  }
                  className={
                    WEAPON_CLASS_PILL[item.weapon_class] ??
                    "text-hunt-text-dim border-hunt-border"
                  }
                />
              )}
              {item.size > 0 && (
                <span className="text-xs text-hunt-text-muted">
                  {item.size}-slot
                </span>
              )}
            </>
          ) : isTool ? (
            <>
              {item.tool_class && (
                <Pill
                  label={item.tool_class}
                  className={
                    TOOL_CLASS_PILL[item.tool_class] ??
                    "text-hunt-text-dim border-hunt-border"
                  }
                />
              )}
            </>
          ) : (
            <>
              {item.category && item.category !== "unknown" && (
                <Pill
                  label={item.category}
                  className={
                    CATEGORY_PILL[item.category] ??
                    "text-hunt-text-dim border-hunt-border"
                  }
                />
              )}
              {item.cost > 0 && (
                <span className="text-xs text-hunt-gold">
                  {item.cost} upgrade points
                </span>
              )}
              {item.trait_type &&
                item.trait_type !== "normal" &&
                TRAIT_TYPE_PILL[item.trait_type] && (
                  <Pill
                    label={item.trait_type}
                    className={TRAIT_TYPE_PILL[item.trait_type]}
                  />
                )}
              {item.is_burn && <Pill label="Burn" className={BURN_PILL} />}
              {item.is_solo && <Pill label="Solo" className={SOLO_PILL} />}
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
            : isConsumable
              ? `Traits for this consumable (${synergies.length})`
              : isTool
                ? `Traits for this tool (${synergies.length})`
                : `Weapons benefiting from this trait (${synergies.length})`}
        </p>
        {synergies.length === 0 ? (
          <p className="text-sm text-hunt-text-dim italic">
            No synergies found.
          </p>
        ) : (
          <div className="space-y-2 pr-1">
            {synergies.map((syn) => (
              <SynergyRow
                key={syn.id}
                syn={syn}
                isWeapon={isWeapon}
                isTool={false}
                targetMode={isWeapon || isTool ? "trait" : "weapon"}
                onNavigate={onNavigate}
              />
            ))}
          </div>
        )}

        {/* Tool synergies section — only shown when viewing a trait */}
        {isTrait && toolSynergies?.length > 0 && (
          <div className="mt-4">
            <p className="text-xs uppercase tracking-widest text-hunt-text-dim mb-3">
              Tools benefiting from this trait ({toolSynergies.length})
            </p>
            <div className="space-y-2 pr-1">
              {toolSynergies.map((syn) => (
                <SynergyRow
                  key={syn.id}
                  syn={syn}
                  isWeapon={false}
                  isTool={true}
                  targetMode={CONSUMABLE_CLASSES.has(syn.tool_class) ? "consumable" : "tool"}
                  onNavigate={onNavigate}
                />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
