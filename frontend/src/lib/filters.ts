import type { FilterClause } from '../api/players'
import { FILTER_OP_OPTIONS, METRIC_OPTIONS } from '../api/players'

export interface Filters {
  name: string; position: string; team: string; nationality: string; underpredicted_flag: string
  stats_view: string; clauses: FilterClause[]
}

export const EMPTY_FILTERS: Filters = {
  name: '', position: '', team: '', nationality: '', underpredicted_flag: '', stats_view: '', clauses: [],
}

export const metricLabel = (field: string) =>
  METRIC_OPTIONS.find((m) => m.value === field)?.label ?? field

export const clauseLabel = (c: FilterClause) =>
  `${metricLabel(c.field)} ${FILTER_OP_OPTIONS.find((o) => o.value === c.op)?.label ?? c.op} ${c.value}`
