import { getApiInstance } from './api';

export interface VoiceControlRequest {
    transcript: string;
    response_type?: string;
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

export interface CardId {
    id: number;
}

export interface CardFilterResponse {
    description: string;
    cards: CardId[];
}

export const voiceControlService = {
    async processTranscript(transcript: string, responseType: string = 'card_update'): Promise<VoiceControlResponse | CardFilterResponse> {
        const response = await getApiInstance().post<VoiceControlResponse | CardFilterResponse>('/voice-control/', {
            transcript: transcript,
            response_type: responseType
        });
        return response.data;
    }
};
