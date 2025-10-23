import React from 'react';

interface ProgressBarProps {
    current: number;
    total: number;
    label?: string;
    showPercentage?: boolean;
    className?: string;
}

export const ProgressBar: React.FC<ProgressBarProps> = ({
    current,
    total,
    label,
    showPercentage = true,
    className = ''
}) => {
    const percentage = total > 0 ? Math.round((current / total) * 100) : 0;

    return (
        <div className={`space-y-2 ${className}`}>
            {label && (
                <div className="flex justify-between items-center text-sm">
                    <span className="text-gray-700">{label}</span>
                    {showPercentage && (
                        <span className="text-gray-500">
                            {current}/{total} ({percentage}%)
                        </span>
                    )}
                </div>
            )}
            <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                    className="bg-blue-600 h-2 rounded-full transition-all duration-300 ease-out"
                    style={{ width: `${percentage}%` }}
                />
            </div>
        </div>
    );
};

export default ProgressBar;
