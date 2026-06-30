import type { TuiPlugin } from "@opencode-ai/plugin/tui"

export default (async (api) => {
  let active = false
  let pct = 0
  let prevUpdate = Date.now()

  api.event.on("message.part.updated", (event: any) => {
    const part = event?.properties?.part
    if (part?.tool === "bash_stream") {
      if (part?.state?.status === "running") {
        active = true
        const m = part.state.metadata
        if (m?.pct) {
          pct = parseFloat(m.pct)
          prevUpdate = Date.now()
        }
      } else if (
        part?.state?.status === "completed" ||
        part?.state?.status === "error"
      ) {
        active = false
      }
    }
  })

  api.event.on("session.status", (event: any) => {
    if (event?.properties?.status === "idle") active = false
  })

  const BAR_W = 21

  function face(pct: number, stuck: boolean): string {
    if (stuck) return "/ᐠ-ᆺ-ᐟ\\"
    if (pct >= 100) return ""
    if (pct < 10) return "/ᐠ ᵕ ᐟ\\"
    if (pct < 30) return "/ᐠ ._. ᐟ\\"
    if (pct < 55) return "/ᐠ ᴗ ᴗ ᐟ\\"
    if (pct < 75) return "/ᐠ^ᆺ^ᐟ\\"
    if (pct < 90) return "/ᐠ >ᆺ< ᐟ\\"
    return "/ᐠ ᐳᆺᐸ ᐟ\\"
  }

  function tailChar(frame: number): string {
    return ["~", "∫", "ζ", "≋"][frame % 4]
  }

  const BAR_W_C1 = 12

  api.slots.register({
    slots: {
      sidebar_footer: () => {
        if (!active) return null

        if (pct >= 100) {
          return `100% █${"█".repeat(BAR_W_C1)}█`
        }

        const filled = Math.round((pct / 100) * BAR_W_C1)
        const bar = "█".repeat(filled) + "░".repeat(BAR_W_C1 - filled)
        return `${Math.round(pct)}% ${bar}`
      },
    },
  })
}) satisfies TuiPlugin
