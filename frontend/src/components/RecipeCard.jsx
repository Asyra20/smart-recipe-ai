import { useState, useEffect } from "react"
import { createPortal } from "react-dom"

function ScoreBar({ score }) {
  const pct   = Math.round(score * 100)
  const color = pct >= 80 ? "bg-green-500" : pct >= 50 ? "bg-amber-400" : "bg-red-400"
  const label = pct >= 80 ? "Great match" : pct >= 50 ? "Good match" : "Low match"

  return (
    <div className="mt-4">
      <div className="flex justify-between items-center mb-1.5">
        <span className="text-xs text-zinc-500">{label}</span>
        <span className="text-xs font-medium text-zinc-300">{pct}%</span>
      </div>
      <div className="w-full h-1.5 bg-zinc-800 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}

function ConfidenceBadge({ confidence }) {
  const styles = {
    high:   "bg-green-900/40 text-green-400 border-green-800/50",
    medium: "bg-amber-900/40 text-amber-400 border-amber-800/50",
    low:    "bg-zinc-800 text-zinc-500 border-zinc-700",
  }
  return (
    <span className={`text-[10px] px-2 py-0.5 rounded-full border font-medium ${styles[confidence] ?? styles.low}`}>
      {confidence} confidence
    </span>
  )
}

function ExplanationSection({ explanation }) {
  if (!explanation || !explanation.reasons?.length) return null

  return (
    <div className="mt-4 pt-4 border-t border-zinc-800">
      <div className="flex items-center gap-2 mb-2.5">
        <svg className="w-3.5 h-3.5 text-green-500 shrink-0" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24" aria-hidden="true">
          <path d="M9.663 17h4.673M12 3v1m6.364 1.636-.707.707M21 12h-1M4 12H3m3.343-5.657-.707-.707m2.828 9.9a5 5 0 1 1 7.072 0l-.548.547A3.374 3.374 0 0 0 14 18.469V19a2 2 0 1 1-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547Z" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
        <span className="text-[11px] font-medium text-zinc-400">Recommended because</span>
        {explanation.used_llm && (
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-purple-900/40 text-purple-400 border border-purple-800/50">
            AI
          </span>
        )}
      </div>
      <ul className="space-y-1.5">
        {explanation.reasons.map((reason, i) => (
          <li key={i} className="flex items-start gap-2 text-xs text-zinc-400">
            <span className="mt-1 w-1 h-1 rounded-full bg-green-600 shrink-0" aria-hidden="true" />
            {reason}
          </li>
        ))}
      </ul>
      <div className="mt-2.5">
        <ConfidenceBadge confidence={explanation.confidence} />
      </div>
    </div>
  )
}

function ScoreBreakdown({ scores }) {
  if (!scores) return null
  const items = [
    { label: "Semantic", value: scores.sbert, color: "bg-blue-500" },
    { label: "Content",  value: scores.cbf,   color: "bg-amber-500" },
    { label: "Collab",   value: scores.cf,    color: "bg-purple-500" },
  ]
  return (
    <div className="mt-3 space-y-1.5">
      {items.map(({ label, value, color }) => (
        <div key={label} className="flex items-center gap-2">
          <span className="text-[10px] text-zinc-600 w-14 shrink-0">{label}</span>
          <div className="flex-1 h-1 bg-zinc-800 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full ${color} opacity-70`}
              style={{ width: `${Math.round(value * 100)}%` }}
            />
          </div>
          <span className="text-[10px] text-zinc-600 w-6 text-right">
            {Math.round(value * 100)}
          </span>
        </div>
      ))}
    </div>
  )
}

function RecipeModal({ recipe, onClose, onRecommend }) {
  const [showScores, setShowScores] = useState(false)

  useEffect(() => {
    const handleKey = (e) => e.key === "Escape" && onClose()
    window.addEventListener("keydown", handleKey)
    return () => window.removeEventListener("keydown", handleKey)
  }, [onClose])

  useEffect(() => {
    document.body.style.overflow = "hidden"
    return () => { document.body.style.overflow = "" }
  }, [])

  const { recipe_id, name, score, scores, tags, description, ingredients, explanation,
          calories, protein, is_quick, is_high_protein, is_low_calorie } = recipe
  const pct = Math.round((scores?.hybrid ?? score ?? 0) * 100)

  return createPortal(
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="relative w-full max-w-lg max-h-[85vh] overflow-y-auto bg-zinc-900 border border-zinc-700 rounded-3xl shadow-2xl shadow-black/60">
        <button
          onClick={onClose}
          aria-label="Close"
          className="absolute top-4 right-4 z-10 p-1.5 rounded-full bg-zinc-800 hover:bg-zinc-700 text-zinc-400 hover:text-white transition"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24" aria-hidden="true">
            <path d="M18 6 6 18M6 6l12 12" strokeLinecap="round" />
          </svg>
        </button>

        <div className="p-6">
          {/* Score + tags */}
          <div className="flex flex-wrap items-center gap-2 mb-3">
            <span className="text-[11px] font-medium px-2 py-0.5 rounded-full bg-zinc-800 text-zinc-400 border border-zinc-700">
              {pct}% match
            </span>
            {is_quick && (
              <span className="text-[11px] px-2 py-0.5 rounded-full bg-blue-900/40 text-blue-400 border border-blue-800/50">
                ⚡ Quick
              </span>
            )}
            {is_high_protein && (
              <span className="text-[11px] px-2 py-0.5 rounded-full bg-amber-900/40 text-amber-400 border border-amber-800/50">
                💪 High protein
              </span>
            )}
            {is_low_calorie && (
              <span className="text-[11px] px-2 py-0.5 rounded-full bg-teal-900/40 text-teal-400 border border-teal-800/50">
                🥗 Low calorie
              </span>
            )}
            {tags?.slice(0, 2).map((tag) => (
              <span key={tag} className="text-[11px] px-2 py-0.5 rounded-full bg-green-900/40 text-green-400 border border-green-800/50">
                {tag}
              </span>
            ))}
          </div>

          {/* Title */}
          <h2 className="text-2xl font-bold text-white leading-tight mb-1 pr-8">{name}</h2>

          {/* Nutrition summary */}
          {(calories > 0 || protein > 0) && (
            <div className="flex gap-4 mb-3 text-xs text-zinc-500">
              {calories > 0 && <span>{Math.round(calories)} cal</span>}
              {protein > 0  && <span>{Math.round(protein)}% protein DV</span>}
            </div>
          )}

          {/* Description */}
          {description && (
            <p className="text-sm text-zinc-400 leading-relaxed mb-4 pb-4 border-b border-zinc-800">
              {description}
            </p>
          )}

          {/* Explanation */}
          <ExplanationSection explanation={explanation} />

          {/* Score breakdown toggle */}
          {scores && (
            <div className="mt-3">
              <button
                onClick={() => setShowScores(v => !v)}
                className="text-[11px] text-zinc-600 hover:text-zinc-400 transition flex items-center gap-1"
              >
                <svg className={`w-3 h-3 transition-transform ${showScores ? "rotate-180" : ""}`} fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M19 9l-7 7-7-7" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
                {showScores ? "Hide" : "Show"} score breakdown
              </button>
              {showScores && <ScoreBreakdown scores={scores} />}
            </div>
          )}

          {/* Ingredients */}
          {ingredients?.length > 0 && (
            <div className="mt-5 mb-6">
              <h3 className="text-sm font-semibold text-zinc-300 mb-3 flex items-center gap-2">
                <svg className="w-4 h-4 text-green-500" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2M9 5a2 2 0 0 0 2 2h2a2 2 0 0 0 2-2M9 5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2" strokeLinecap="round" />
                </svg>
                Ingredients
                <span className="text-xs font-normal text-zinc-600">{ingredients.length} items</span>
              </h3>
              <ul className="grid grid-cols-2 gap-1.5">
                {ingredients.map((item, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-zinc-400">
                    <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-green-600 shrink-0" aria-hidden="true" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Steps */}
          {recipe.steps?.length > 0 && (
            <div className="mb-6">
              <h3 className="text-sm font-semibold text-zinc-300 mb-3 flex items-center gap-2">
                <svg className="w-4 h-4 text-green-500" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5.586a1 1 0 0 1 .707.293l5.414 5.414a1 1 0 0 1 .293.707V19a2 2 0 0 1-2 2Z" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
                Instructions
                <span className="text-xs font-normal text-zinc-600">{recipe.steps.length} steps</span>
              </h3>
              <ol className="space-y-3">
                {recipe.steps.map((step, i) => (
                  <li key={i} className="flex gap-3 text-sm text-zinc-400">
                    <span className="shrink-0 w-5 h-5 rounded-full bg-zinc-800 border border-zinc-700 text-[10px] text-zinc-500 flex items-center justify-center mt-0.5">
                      {i + 1}
                    </span>
                    <span className="leading-relaxed">{step}</span>
                  </li>
                ))}
              </ol>
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-3">
            <button
              onClick={() => { onRecommend(recipe_id); onClose() }}
              className="flex-1 flex items-center justify-center gap-2 bg-green-600 hover:bg-green-500 active:scale-[0.98] text-white text-sm font-medium py-2.5 rounded-xl transition-all duration-150"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24" aria-hidden="true">
                <path d="M5 12h14M12 5l7 7-7 7" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              Find similar recipes
            </button>
            <button
              onClick={onClose}
              className="px-4 py-2.5 rounded-xl text-sm text-zinc-400 border border-zinc-700 hover:border-zinc-600 hover:text-zinc-200 transition-all duration-150"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>,
    document.body
  )
}

function RecipeCard({ recipe, onClick }) {
  const [showModal, setShowModal] = useState(false)
  const { name, score, scores, tags, description, explanation } = recipe
  const hybridScore = scores?.hybrid ?? score ?? 0

  return (
    <>
      <div
        role="button"
        tabIndex={0}
        onClick={() => setShowModal(true)}
        onKeyDown={(e) => e.key === "Enter" && setShowModal(true)}
        className="group relative bg-zinc-900 border border-zinc-800 rounded-2xl p-5 hover:border-zinc-600 hover:bg-zinc-800/60 active:scale-[0.98] transition-all duration-200 cursor-pointer"
      >
        <div className="absolute top-4 right-4 opacity-0 group-hover:opacity-100 transition-opacity duration-150">
          <svg className="w-4 h-4 text-zinc-500" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24" aria-hidden="true">
            <path d="M7 17 17 7M7 7h10v10" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>

        {tags?.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-3">
            {tags.slice(0, 2).map((tag) => (
              <span key={tag} className="text-[11px] px-2 py-0.5 rounded-full bg-green-900/40 text-green-400 border border-green-800/50">
                {tag}
              </span>
            ))}
            {tags.length > 2 && (
              <span className="text-[11px] px-2 py-0.5 rounded-full bg-zinc-800 text-zinc-500 border border-zinc-700">
                +{tags.length - 2}
              </span>
            )}
          </div>
        )}

        <h2 className="text-base font-semibold text-white leading-snug pr-6">{name}</h2>

        {description && (
          <p className="text-xs text-zinc-500 mt-2 line-clamp-2 leading-relaxed">{description}</p>
        )}

        {/* Preview 1 reason di card (kalau ada) */}
        {explanation?.reasons?.length > 0 && (
          <p className="text-[11px] text-zinc-600 mt-2 flex items-center gap-1.5">
            <span className="w-1 h-1 rounded-full bg-green-700 shrink-0" aria-hidden="true" />
            {explanation.reasons[0]}
          </p>
        )}

        <ScoreBar score={hybridScore} />
      </div>

      {showModal && (
        <RecipeModal
          recipe={recipe}
          onClose={() => setShowModal(false)}
          onRecommend={onClick}
        />
      )}
    </>
  )
}

export default RecipeCard