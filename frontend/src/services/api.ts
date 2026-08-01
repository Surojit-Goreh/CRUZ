const API_URL = "http://127.0.0.1:8000";

export async function getBackendMessage() {
    const response = await fetch(API_URL);

    if (!response.ok) {
        throw new Error("Failed to connect to backend.");
    }

    return response.json();
}