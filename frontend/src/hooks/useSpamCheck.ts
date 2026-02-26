import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { useAuth } from '../auth/AuthContext';

interface SpamReport {
    is_spam: boolean;
    score: number;
    triggers: string[];
}

export const useSpamCheck = (text: string, delay: number = 800) => {
    const [report, setReport] = useState<SpamReport | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const { token } = useAuth();

    const checkSpam = useCallback(async (textToCheck: string) => {
        if (!textToCheck || textToCheck.length < 5) {
            setReport(null);
            return;
        }

        setIsLoading(true);
        try {
            const response = await axios.post('/api/spam-shield/check',
                { text: textToCheck },
                { headers: { Authorization: `Bearer ${token}` } }
            );
            setReport(response.data);
        } catch (error) {
            console.error('Spam check failed:', error);
        } finally {
            setIsLoading(false);
        }
    }, [token]);

    useEffect(() => {
        const handler = setTimeout(() => {
            checkSpam(text);
        }, delay);

        return () => {
            clearTimeout(handler);
        };
    }, [text, delay, checkSpam]);

    return { report, isLoading };
};
