import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { Button } from './button';
import { Card, CardContent, CardHeader, CardTitle } from './card';

interface Props {
    children: ReactNode;
    fallback?: ReactNode;
}

interface State {
    hasError: boolean;
    error?: Error;
    errorInfo?: ErrorInfo;
}

/**
 * Error Boundary component for catching and displaying React errors
 * Provides user-friendly error messages and recovery options
 */
export class ErrorBoundary extends Component<Props, State> {
    constructor(props: Props) {
        super(props);
        this.state = { hasError: false };
    }

    static getDerivedStateFromError(error: Error): State {
        return { hasError: true, error };
    }

    componentDidCatch(error: Error, errorInfo: ErrorInfo) {
        console.error('ErrorBoundary caught an error:', error, errorInfo);
        this.setState({ error, errorInfo });
    }

    handleRetry = () => {
        this.setState({ hasError: false, error: undefined, errorInfo: undefined });
    };

    handleReload = () => {
        window.location.reload();
    };

    render() {
        if (this.state.hasError) {
            if (this.props.fallback) {
                return this.props.fallback;
            }

            return (
                <div className="min-h-[400px] flex items-center justify-center p-4">
                    <Card className="w-full max-w-md">
                        <CardHeader className="text-center">
                            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-red-100">
                                <AlertTriangle className="h-6 w-6 text-red-600" />
                            </div>
                            <CardTitle className="text-red-900">
                                Une erreur s'est produite
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <p className="text-sm text-gray-600 text-center">
                                Nous nous excusons pour ce problème. Vous pouvez essayer de recharger la page ou réessayer l'action.
                            </p>
                            
                            {process.env.NODE_ENV === 'development' && this.state.error && (
                                <details className="mt-4">
                                    <summary className="cursor-pointer text-sm font-medium text-gray-700">
                                        Détails de l'erreur (développement)
                                    </summary>
                                    <div className="mt-2 p-3 bg-gray-50 rounded text-xs font-mono text-gray-800 overflow-auto max-h-32">
                                        <div className="font-semibold text-red-600 mb-1">
                                            {this.state.error.name}: {this.state.error.message}
                                        </div>
                                        {this.state.error.stack && (
                                            <pre className="whitespace-pre-wrap">
                                                {this.state.error.stack}
                                            </pre>
                                        )}
                                    </div>
                                </details>
                            )}
                            
                            <div className="flex space-x-2 pt-2">
                                <Button
                                    onClick={this.handleRetry}
                                    variant="outline"
                                    className="flex-1"
                                >
                                    <RefreshCw className="h-4 w-4 mr-2" />
                                    Réessayer
                                </Button>
                                <Button
                                    onClick={this.handleReload}
                                    className="flex-1"
                                >
                                    Recharger la page
                                </Button>
                            </div>
                        </CardContent>
                    </Card>
                </div>
            );
        }

        return this.props.children;
    }
}

/**
 * Hook version of error boundary for functional components
 */
export const useErrorHandler = () => {
    const handleError = (error: Error, errorInfo?: string) => {
        console.error('Error caught by useErrorHandler:', error, errorInfo);
        
        // In a real application, you might want to send this to an error reporting service
        // like Sentry, LogRocket, etc.
    };

    return handleError;
};

export default ErrorBoundary;
