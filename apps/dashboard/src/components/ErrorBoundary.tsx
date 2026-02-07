import { Component, ReactNode } from 'react';
import { Card } from './ui/card';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: any) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-background p-4">
          <Card className="max-w-2xl w-full p-8">
            <h1 className="text-3xl font-bold mb-4 text-red-600">Something went wrong</h1>
            <p className="text-muted-foreground mb-4">
              The application encountered an unexpected error.
            </p>
            <Card className="bg-muted p-4 mb-4">
              <p className="text-sm font-mono text-red-600 whitespace-pre-wrap break-all">
                {this.state.error?.toString()}
              </p>
              <p className="text-xs mt-2 text-muted-foreground">
                Stack: {this.state.error?.stack}
              </p>
            </Card>
            <button
              onClick={() => window.location.reload()}
              className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
            >
              Reload Page
            </button>
          </Card>
        </div>
      );
    }

    return this.props.children;
  }
}
