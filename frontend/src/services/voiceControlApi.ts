import axios from 'axios';

// Configuration de base d'Axios
const API_BASE_URL = (window as any).API_BASE_URL || 'http://localhost:8000';

const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Intercepteur pour ajouter le token d'authentification
api.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('token');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

export interface VoiceControlRequest {
    transcript: string;
}

export interface ChecklistItem {
    item_id?: number | null;
    item_name: string;
    is_done: boolean;
}

export interface LabelRef {
    label_id: number;
}

export interface VoiceControlResponse {
    task_id?: number | null;
    title: string;
    description?: string | null;
    checklist?: ChecklistItem[];
    due_date?: string | null;
    list_id?: number | null;
    priority?: string | null;
    assignee_id?: number | null;
    labels?: LabelRef[];
}

export const voiceControlService = {
    async processTranscript(transcript: string): Promise<VoiceControlResponse> {
        const response = await api.post<VoiceControlResponse>('/voice-control/', {
            transcript: transcript
        });
        return response.data;
    }
};
