import styles from './BreakdownChart.module.css'

export interface BreakdownRow {
  key: string
  label: string
  count: number
  color: string
}

interface BreakdownChartProps {
  title: string
  rows: BreakdownRow[]
}

// Plain CSS horizontal bars -- no SVG, no charting library. Each row's bar
// width is relative to the largest count in the set, so the chart reads as
// a shape at a glance rather than requiring the viewer to compare raw
// numbers. Rows with count 0 still render (a hairline bar), so "nothing
// critical right now" is visible, not a missing row.
export function BreakdownChart({ title, rows }: BreakdownChartProps) {
  const max = Math.max(1, ...rows.map((r) => r.count))

  return (
    <div className={styles.card}>
      <h3 className={styles.title}>{title}</h3>
      <div className={styles.rows}>
        {rows.map((row) => (
          <div key={row.key} className={styles.row}>
            <span className={styles.label}>{row.label}</span>
            <div className={styles.track}>
              <div
                className={styles.bar}
                style={{
                  width: `${Math.max((row.count / max) * 100, row.count > 0 ? 4 : 0)}%`,
                  background: row.color,
                }}
              />
            </div>
            <span className={styles.count}>{row.count}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
