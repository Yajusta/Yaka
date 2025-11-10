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

interface ImportMetaEnv {
    VITE_VOICE_TRANSCRIPT_LIMIT?: string;
}

function isImportMetaEnv(env: unknown): env is ImportMetaEnv {
    return typeof env === 'object' && env !== null && 'VITE_VOICE_TRANSCRIPT_LIMIT' in env;
}

const getTranscriptLimit = () => {
    let raw: string | undefined = undefined;
    if (typeof import.meta !== 'undefined' && isImportMetaEnv((import.meta as { env?: unknown }).env)) {
        raw = ((import.meta as { env?: unknown }).env as ImportMetaEnv).VITE_VOICE_TRANSCRIPT_LIMIT;
    }
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
