import { geoAlbersUsa } from 'd3-geo'
import type { Lead } from '../types'

// City-precision gazetteer of REAL cities that appear in the DB's
// job_location field. Coordinates are true city centers; each lead gets a
// small deterministic offset so a city with many businesses reads as a
// constellation, not a stack. Honest: real place, city-level precision.
const CITIES: Record<string, [number, number]> = {
  // [lat, lng]
  'phoenix, az': [33.4484, -112.0740],
  'scottsdale, az': [33.4942, -111.9261],
  'mesa, az': [33.4152, -111.8315],
  'tampa, fl': [27.9506, -82.4572],
  'seattle, wa': [47.6062, -122.3321],
  'san diego, ca': [32.7157, -117.1611],
  'sacramento, ca': [38.5816, -121.4944],
  'portland, or': [45.5152, -122.6784],
  'nashville, tn': [36.1627, -86.7816],
  'miami, fl': [25.7617, -80.1918],
  'las vegas, nv': [36.1699, -115.1398],
  'kansas city, mo': [39.0997, -94.5786],
  'jacksonville, fl': [30.3322, -81.6557],
  'denver, co': [39.7392, -104.9903],
  'dallas, tx': [32.7767, -96.7970],
  'columbus, oh': [39.9612, -82.9988],
  'chicago, il': [41.8781, -87.6298],
  'charlotte, nc': [35.2271, -80.8431],
  'boston, ma': [42.3601, -71.0589],
  'baltimore, md': [39.2904, -76.6122],
  'austin, tx': [30.2672, -97.7431],
  'atlanta, ga': [33.7490, -84.3880],
  'orlando, fl': [28.5384, -81.3789],
  'minneapolis, mn': [44.9778, -93.2650],
  'houston, tx': [29.7604, -95.3698],
  'hartford, ct': [41.7658, -72.6734],
  'cleveland, oh': [41.4993, -81.6944],
  'cincinnati, oh': [39.1031, -84.5120],
  'boulder, co': [40.0150, -105.2705],
  // Bergen County, NJ pivot towns (targeting home turf)
  'englewood, nj': [40.8929, -73.9726],
  'englewood cliffs, nj': [40.8859, -73.9532],
  'fort lee, nj': [40.8509, -73.9701],
  'hackensack, nj': [40.8859, -74.0435],
  'teaneck, nj': [40.8976, -74.0160],
  'paramus, nj': [40.9445, -74.0754],
  'fair lawn, nj': [40.9404, -74.1318],
  'ridgewood, nj': [40.9793, -74.1165],
  'bergenfield, nj': [40.9276, -73.9976],
  'tenafly, nj': [40.9254, -73.9629],
}

// Where the agency lives — every connection grows from here.
export const HQ = { lat: 40.8859, lng: -73.9532, label: 'Englewood Cliffs, NJ' }

// The same projection us-atlas *-albers-10m files are pre-projected with,
// so lead coordinates and the map mesh share one space (975 × 610).
export const ALBERS = geoAlbersUsa().scale(1300).translate([487.5, 305])
export const MAP_W = 975
export const MAP_H = 610

function hash(n: number): number {
  let x = (n | 0) + 0x9e3779b9
  x = Math.imul(x ^ (x >>> 16), 0x21f0aaad)
  x = Math.imul(x ^ (x >>> 15), 0x735a2d97)
  return ((x ^ (x >>> 15)) >>> 0) / 0xffffffff
}

export interface MapPoint {
  lead: Lead
  x: number
  y: number
  city: string
}

/** Project real leads into map space; unknown/remote locations are counted, not faked. */
export function projectLeads(leads: Lead[]): { points: MapPoint[]; unmapped: Lead[] } {
  const points: MapPoint[] = []
  const unmapped: Lead[] = []
  for (const lead of leads) {
    const key = (lead.job_location || '').trim().toLowerCase()
    const city = CITIES[key]
    const projected = city && ALBERS([city[1], city[0]])
    if (!projected) { unmapped.push(lead); continue }
    // deterministic constellation offset, ~city-radius in map units
    const a = hash(lead.id) * Math.PI * 2
    const r = 2.2 + hash(lead.id * 7 + 1) * 6.5
    points.push({
      lead,
      x: projected[0] + Math.cos(a) * r,
      y: projected[1] + Math.sin(a) * r * 0.8,
      city: lead.job_location || '',
    })
  }
  return { points, unmapped }
}

export function projectHQ(): [number, number] {
  const p = ALBERS([HQ.lng, HQ.lat])
  return p ? [p[0], p[1]] : [860, 180]
}
