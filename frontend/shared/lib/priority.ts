export function mapPriorityToBackend(priority: string): string {
    if (!priority) return priority;
    const p = String(priority).toLowerCase();

    // Normalize and return backend english keys: low/medium/high
    if (p === 'low' || p === 'l' || p.includes('low')) return 'low';
    if (p === 'medium' || p === 'm' || p.includes('med')) return 'medium';
    if (p === 'high' || p === 'h' || p.includes('high')) return 'high';

    // Accept french values as well (allow accents and case variations)
    const normalized = p.normalize('NFD').replace(/\p{Diacritic}/gu, '');
    if (normalized.includes('faibl') || normalized === 'faible') return 'low';
    if (normalized.includes('moy') || normalized === 'moyen') return 'medium';
    if (normalized.includes('elev') || normalized.includes('eleve')) return 'high';

    // Fallback: return as-is
    return priority;
}

export function mapPriorityFromBackend(priority: string): 'low' | 'medium' | 'high' {
    if (!priority) return 'low';
    const p = String(priority).toLowerCase();
    const normalized = p.normalize('NFD').replace(/\p{Diacritic}/gu, '');

    if (normalized.includes('faibl') || normalized.includes('low')) return 'low';
    if (normalized.includes('moy') || normalized.includes('med') || normalized.includes('medium')) return 'medium';
    if (normalized.includes('elev') || normalized.includes('high')) return 'high';

    return 'low';
}