import type { NurseSkillRow } from "@/api/generated/model"
import { Badge } from "@/components/ui/badge"
import { shortDay } from "@/lib/utils"

/** The last day a skill counts, in the page's words. Whether that day has passed is the expiries page's to say (ticket 37),
 *  since it needs the hospital's today. */
export const untilWords = (skill: NurseSkillRow) => (skill.expiry ? `until ${shortDay(skill.expiry)}` : "")

/** A nurse's skills in a table cell: each name, its expiry, and whether the CNO has retired it. */
export function SkillList({ skills }: { skills: NurseSkillRow[] }) {
  if (skills.length === 0) return <span className="text-muted-foreground">None</span>
  return (
    <ul className="flex flex-col items-start gap-1">
      {skills.map((skill) => (
        <li key={skill.skill_id} className="flex flex-wrap items-center gap-1">
          <span>{skill.name}</span>
          {skill.expiry && <span className="tabular-nums text-muted-foreground">{untilWords(skill)}</span>}
          {!skill.active && <Badge variant="outline">Retired</Badge>}
        </li>
      ))}
    </ul>
  )
}
