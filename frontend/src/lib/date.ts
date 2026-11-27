export type BangkokDate = {
  year: number
  month: number
  day: number
  isoDate: string
}

export function getBangkokDate(date = new Date()): BangkokDate {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Bangkok',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).formatToParts(date)
  const values = Object.fromEntries(parts.map((part) => [part.type, part.value]))
  const year = Number(values.year)
  const month = Number(values.month)
  const day = Number(values.day)

  return {
    year,
    month,
    day,
    isoDate: `${values.year}-${values.month}-${values.day}`,
  }
}
