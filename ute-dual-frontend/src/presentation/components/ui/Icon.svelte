<script>
  export let name = 'user'
  export let size = 20
  const paths = {
    menu: 'M4 6h16M4 12h16M4 18h16', close: 'm6 6 12 12M6 18 18 6',
    user: 'M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0ZM4 21v-2a8 8 0 0 1 16 0v2',
    report: 'M14 2H6v20h14V8ZM14 2v6h6M8 13h8M8 17h6',
    building: 'M3 21h18M5 21V3h14v18M9 7h1m4 0h1M9 11h1m4 0h1M10 21v-5h4v5',
    folder: 'M3 7V3h7l2 3h9v15H3ZM3 10h18',
    calendar: 'M4 5h16v16H4ZM4 10h16M8 3v4M16 3v4',
    group: 'M3 3h7v7H3ZM14 3h7v7h-7ZM3 14h7v7H3ZM14 14h7v7h-7Z',
    people: 'M15 7a3 3 0 1 1-6 0 3 3 0 0 1 6 0ZM6 21v-2a6 6 0 0 1 12 0v2M18 4a3 3 0 0 1 0 6M21 20v-2a5 5 0 0 0-3-4M6 4a3 3 0 0 0 0 6M3 20v-2a5 5 0 0 1 3-4',
    chat: 'M21 11a8 8 0 0 1-8 8H8l-5 3V7a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4ZM7 8h10M7 12h7',
    key: 'M14 5a5 5 0 1 1-1 8L5 21H2v-3l8-8a5 5 0 0 1 4-5ZM16 8h.01',
    logout: 'M9 4H4v16h5M10 12h11m-4-4 4 4-4 4',
    moon: 'M21 13A9 9 0 0 1 11 3a9 9 0 1 0 10 10Z',
    sun: 'M16 12a4 4 0 1 1-8 0 4 4 0 0 1 8 0ZM12 2v2m0 16v2M2 12h2m16 0h2M5 5l1 1m12 12 1 1M5 19l1-1M18 6l1-1',
    eye: 'M2 12s3-7 10-7 10 7 10 7-3 7-10 7S2 12 2 12ZM15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z',
    eyeOff: 'm3 3 18 18M10 5h2c7 0 10 7 10 7a18 18 0 0 1-3 4M6 6a18 18 0 0 0-4 6s3 7 10 7a12 12 0 0 0 5-1M10 10a3 3 0 0 0 4 4'
  }
</script>
<svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d={paths[name] || paths.user} /></svg>
