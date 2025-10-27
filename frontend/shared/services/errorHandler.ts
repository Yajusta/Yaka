import i18n from '../i18n';

// Error handling utility for API services
export class ApiError extends Error {
    constructor(
        message: string,
        public status?: number,
        public code?: string
    ) {
        super(message);
        this.name = 'ApiError';
    }
}

// Helper function to handle API errors with i18n support
export const handleApiError = (error: any, customMessages?: Record<number, string>): never => {
    // Handle network errors
    if (!error.response) {
        throw new ApiError(
            i18n.t('apiErrors.networkError'),
            0,
            'NETWORK_ERROR'
        );
    }

    // Handle specific HTTP status codes with user-friendly messages
    const { status } = error.response;
    const detail = error.response.data?.detail;
    
    // Use custom message if provided, otherwise use i18n translation
    const getMessage = (key: string, fallback: string) => 
        customMessages?.[status] || i18n.t(key, { defaultValue: fallback });

    switch (status) {
        case 400:
            throw new ApiError(
                detail || getMessage('apiErrors.validationError', 'Invalid data'),
                status,
                'VALIDATION_ERROR'
            );
        case 401:
            throw new ApiError(
                getMessage('apiErrors.unauthorized', 'Unauthorized'),
                status,
                'UNAUTHORIZED'
            );
        case 403:
            throw new ApiError(
                getMessage('apiErrors.forbidden', 'Forbidden'),
                status,
                'FORBIDDEN'
            );
        case 404:
            throw new ApiError(
                detail || getMessage('apiErrors.notFound', 'Not found'),
                status,
                'NOT_FOUND'
            );
        case 409:
            throw new ApiError(
                detail || getMessage('apiErrors.conflict', 'Conflict'),
                status,
                'CONFLICT'
            );
        case 422:
            throw new ApiError(
                detail || getMessage('apiErrors.unprocessableEntity', 'Unprocessable entity'),
                status,
                'UNPROCESSABLE_ENTITY'
            );
        case 500:
            throw new ApiError(
                getMessage('apiErrors.internalServerError', 'Internal server error'),
                status,
                'INTERNAL_SERVER_ERROR'
            );
        case 503:
            throw new ApiError(
                getMessage('apiErrors.serviceUnavailable', 'Service unavailable'),
                status,
                'SERVICE_UNAVAILABLE'
            );
        default:
            throw new ApiError(
                detail || getMessage('apiErrors.unknownError', 'Unknown error'),
                status,
                'UNKNOWN_ERROR'
            );
    }
};

// Service-specific error handlers
export const createErrorHandler = (_servicePrefix: string) => {
    return (error: any, customMessages?: Record<number, string>): never => {
        return handleApiError(error, {
            ...customMessages,
            // Add service-specific error messages here if needed
        });
    };
};