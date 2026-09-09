"use client";

import React, { Component, ErrorInfo, ReactNode } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Uncaught error:", error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div
          role="alert"
          className="flex flex-col items-center justify-center min-h-dvh p-6 text-center bg-background"
        >
          <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-destructive/10 text-destructive mb-4 shadow-sm" aria-hidden="true">
            <AlertTriangle className="h-8 w-8" />
          </div>
          <h1 className="text-xl font-heading font-semibold mb-2">Something went wrong unexpectedly</h1>
          <p className="text-muted-foreground text-sm max-w-md mb-6">
            We encountered an unexpected rendering error. Don&apos;t worry, your data and chat history are safely stored.
          </p>
          <Button
            onClick={() => window.location.reload()}
            className="gap-2 rounded-xl"
          >
            <RefreshCw className="h-4 w-4" aria-hidden="true" />
            Reload Application
          </Button>
        </div>
      );
    }

    return this.props.children;
  }
}