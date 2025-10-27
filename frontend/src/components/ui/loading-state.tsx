import React from 'react';
import { Loader2 } from 'lucide-react';

interface LoadingStateProps {
    message?: string;
    size?: 'sm' | 'md' | 'lg';
    className?: string;
}

/**
 * Loading state component with spinner and optional message
 */
export const LoadingState: React.FC<LoadingStateProps> = ({ 
    message = 'Chargement...', 
    size = 'md',
    className = ''
}) => {
    const sizeClasses = {
        sm: 'h-4 w-4',
        md: 'h-6 w-6',
        lg: 'h-8 w-8'
    };

    const containerClasses = {
        sm: 'py-2',
        md: 'py-4',
        lg: 'py-8'
    };

    return (
        <div className={`flex flex-col items-center justify-center ${containerClasses[size]} ${className}`}>
            <Loader2 className={`${sizeClasses[size]} animate-spin text-gray-500 mb-2`} />
            {message && (
                <p className="text-sm text-gray-600 text-center">{message}</p>
            )}
        </div>
    );
};

/**
 * Inline loading spinner for buttons and small spaces
 */
export const InlineLoader: React.FC<{ size?: 'sm' | 'md' }> = ({ size = 'sm' }) => {
    const sizeClass = size === 'sm' ? 'h-4 w-4' : 'h-5 w-5';
    
    return (
        <Loader2 className={`${sizeClass} animate-spin`} />
    );
};

/**
 * Loading overlay for covering content during operations
 */
export const LoadingOverlay: React.FC<LoadingStateProps> = ({ 
    message = 'Traitement en cours...', 
    className = '' 
}) => {
    return (
        <div className={`absolute inset-0 bg-white bg-opacity-75 flex items-center justify-center z-50 ${className}`}>
            <div className="bg-white rounded-lg shadow-lg p-6 flex flex-col items-center">
                <Loader2 className="h-8 w-8 animate-spin text-blue-500 mb-3" />
                <p className="text-sm text-gray-700 text-center">{message}</p>
            </div>
        </div>
    );
};

export default LoadingState;
