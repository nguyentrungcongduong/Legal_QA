const BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

export async function queryLegalQA(question) {
  const response = await fetch(`${BASE_URL}/api/ai/query`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      question,
      top_k: 5,
    }),
  });

  if (!response.ok) {
    throw new Error(`Query failed: ${response.status}`);
  }
  return response.json();
}
