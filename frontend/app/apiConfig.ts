export const getApiUrl = (): string => {
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL;
  }
  if (typeof window !== "undefined") {
    if (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1") {
      return `http://${window.location.hostname}:8000/api`;
    }
    // Fallback to the production backend URL on Render if env is not defined
    return "https://business-research-ai-agent.onrender.com/api";
  }
  return "https://business-research-ai-agent.onrender.com/api";
};

