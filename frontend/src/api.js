const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8090";

export class ApiError extends Error {
    constructor(status, message) {
        super(message);
        this.status = status;
    }
}

// FastAPI присылает ошибку либо строкой {detail: "..."}, либо списком проверок {detail: [{msg}]}.
export function errorMessage(data, status) {
    const detail = data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) return detail.map((item) => item.msg).join("; ");
    return `Ошибка сервера (${status})`;
}

async function request(method, path, body) {
    const hasBody = body !== undefined;
    const response = await fetch(`${BASE_URL}${path}`, {
        method,
        headers: hasBody ? { "Content-Type": "application/json" } : {},
        body: hasBody ? JSON.stringify(body) : undefined,
    });
    const data = await response.json().catch(() => null);
    if (!response.ok) {
        throw new ApiError(response.status, errorMessage(data, response.status));
    }
    return data;
}

export const searchOffers = (query = "", limit = 20) =>
    request("GET", `/api/offers?q=${encodeURIComponent(query)}&limit=${limit}`);

export const searchCampaigns = (query = "", limit = 20) =>
    request("GET", `/api/campaigns?q=${encodeURIComponent(query)}&limit=${limit}`);

export const createCampaign = (campaign) => request("POST", "/api/campaigns", campaign);

export const getStreams = (campaignId) => request("GET", `/api/campaigns/${campaignId}/streams`);

export const refreshStreams = (campaignId) =>
    request("POST", `/api/campaigns/${campaignId}/streams/refresh`);

export const addOffer = (streamId, offerId) =>
    request("POST", `/api/streams/${streamId}/offers`, { offer_id: offerId });

export const removeOffer = (streamId, offerId) =>
    request("DELETE", `/api/streams/${streamId}/offers/${offerId}`);

export const restoreOffer = (streamId, offerId) =>
    request("POST", `/api/streams/${streamId}/offers/${offerId}/restore`);

export const togglePin = (streamId, offerId) =>
    request("POST", `/api/streams/${streamId}/offers/${offerId}/pin`);

export const cancelStream = (streamId) => request("POST", `/api/streams/${streamId}/cancel`);

export const pushStream = (streamId) => request("POST", `/api/streams/${streamId}/push`);
