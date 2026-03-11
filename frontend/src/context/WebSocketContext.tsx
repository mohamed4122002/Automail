import React, { createContext, useContext, useEffect, useRef, useState, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';

interface WebSocketMessage {
    type: string;
    [key: string]: any;
}

interface WebSocketContextType {
    isConnected: boolean;
    lastMessage: WebSocketMessage | null;
    sendMessage: (message: any) => void;
}

const WebSocketContext = createContext<WebSocketContextType>({
    isConnected: false,
    lastMessage: null,
    sendMessage: () => { console.warn('WebSocket not connected'); }
});

export const useGlobalWebSocket = () => useContext(WebSocketContext);

interface WebSocketProviderProps {
    children: React.ReactNode;
}

export const WebSocketProvider: React.FC<WebSocketProviderProps> = ({ children }) => {
    const [isConnected, setIsConnected] = useState(false);
    const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
    const wsRef = useRef<WebSocket | null>(null);
    const reconnectAttemptsRef = useRef(0);
    const reconnectTimeoutRef = useRef<NodeJS.Timeout>();
    const queryClient = useQueryClient();

    const maxReconnectAttempts = 10;
    const reconnectInterval = 3000;

    const connect = useCallback(() => {
        try {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            // We use the dashboard websocket for all global events
            const url = `${protocol}//${window.location.host}/api/ws/dashboard`;

            const ws = new WebSocket(url);

            ws.onopen = () => {
                console.log('Global WebSocket connected');
                setIsConnected(true);
                reconnectAttemptsRef.current = 0;
            };

            ws.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    setLastMessage(message);

                    // Intelligent React Query Invalidation based on message type
                    if (message.type === 'event' || message.type === 'crm_event') {
                        // Global invalidations
                        // We do not invalidate specific items here, we let the components
                        // that subscribe manually do optimistic updates if needed.
                        // However, we can invalidate generic lists to ensure background freshness.
                        queryClient.invalidateQueries({ queryKey: ['dashboard'] });
                        queryClient.invalidateQueries({ queryKey: ['lead-stats'] });
                    }

                    if (message.type === 'crm_event') {
                        // Specific lead event matching
                        if (message.lead_id) {
                            queryClient.invalidateQueries({ queryKey: ['lead', message.lead_id] });
                            queryClient.invalidateQueries({ queryKey: ['lead-activity', message.lead_id] });
                            queryClient.invalidateQueries({ queryKey: ['lead-tasks', message.lead_id] });
                        }
                        // Refresh lists if items were changed globally
                        queryClient.invalidateQueries({ queryKey: ['leads'] });
                    }
                } catch (error) {
                    console.error('Failed to parse WebSocket message:', error);
                }
            };

            ws.onerror = (error) => {
                console.error('WebSocket error:', error);
            };

            ws.onclose = () => {
                console.log('Global WebSocket disconnected');
                setIsConnected(false);

                // Attempt to reconnect
                if (reconnectAttemptsRef.current < maxReconnectAttempts) {
                    reconnectAttemptsRef.current += 1;
                    console.log(`Reconnecting... Attempt ${reconnectAttemptsRef.current}`);

                    reconnectTimeoutRef.current = setTimeout(() => {
                        connect();
                    }, reconnectInterval);
                } else {
                    console.error('Max reconnection attempts reached');
                }
            };

            wsRef.current = ws;
        } catch (error) {
            console.error('Failed to create WebSocket connection:', error);
        }
    }, [queryClient]);

    const disconnect = useCallback(() => {
        if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
        }
        if (wsRef.current) {
            wsRef.current.close();
            wsRef.current = null;
        }
    }, []);

    const sendMessage = useCallback((message: any) => {
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            wsRef.current.send(typeof message === 'string' ? message : JSON.stringify(message));
        } else {
            console.warn('WebSocket is not connected');
        }
    }, []);

    useEffect(() => {
        connect();

        return () => {
            disconnect();
        };
    }, [connect, disconnect]);

    // Send ping every 20 seconds to keep connection alive
    useEffect(() => {
        if (!isConnected) return;

        const pingInterval = setInterval(() => {
            sendMessage('ping');
        }, 20000);

        return () => clearInterval(pingInterval);
    }, [isConnected, sendMessage]);

    return (
        <WebSocketContext.Provider value={{ isConnected, lastMessage, sendMessage }}>
            {children}
        </WebSocketContext.Provider>
    );
};
