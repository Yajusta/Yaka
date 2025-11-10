const FALLBACK_LIMIT = 500;

const normalizeLimit = (value?: string) => {
    if (!value) {
        return FALLBACK_LIMIT;
    }
    const parsed = Number(value);
    if (!Number.isFinite(parsed) || parsed <= 0) {
        return FALLBACK_LIMIT;
    }
    return Math.min(parsed, 5000);
};

const getTranscriptLimit = () => {
    const raw = typeof import.meta !== 'undefined' ? (import.meta as any).env?.VITE_VOICE_TRANSCRIPT_LIMIT : undefined;
    if (typeof raw === 'string') {
        return normalizeLimit(raw);
    }
    if (typeof process !== 'undefined') {
        const envValue = (process.env as Record<string, string | undefined>)?.VITE_VOICE_TRANSCRIPT_LIMIT;
        return normalizeLimit(envValue);
    }
    return FALLBACK_LIMIT;
};

export const VOICE_TRANSCRIPT_LIMIT = getTranscriptLimit();
