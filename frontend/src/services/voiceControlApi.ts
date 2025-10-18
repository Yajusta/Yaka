import { getApiInstance } from './api';

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
        const response = await getApiInstance().post<VoiceControlResponse>('/voice-control/', {
            transcript: transcript
        });
        return response.data;
    }
};
