import api from "./api";

/**
 * Batch multiple GET requests into a single Promise.all.
 * Reduces network waterfall by initiating all requests simultaneously.
 */
export async function batchRequests<T extends any[]>(urls: string[]): Promise<T> {
    const startTime = performance.now();
    try {
        const results = await Promise.all(urls.map((url) => api.get(url)));
        const endTime = performance.now();
        console.debug(`[Batch] Fetched ${urls.length} resources in ${(endTime - startTime).toFixed(2)}ms`);
        return results.map((res) => res.data) as T;
    } catch (error) {
        console.error("[Batch] Failed to fetch batch", error);
        throw error;
    }
}
