const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export async function uploadFiles(files: File[]): Promise<{ generation_id: string; files: { name: string; type: string }[] }> {
  const formData = new FormData();
  for (const file of files) {
    formData.append('files', file);
  }

  const res = await fetch(`${API_URL}/api/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Upload failed: ${res.status} ${body}`);
  }

  return res.json();
}

export interface GenerateParams {
  generation_id: string;
  client_name: string;
  analyst_prompt: string;
  market_context?: string;
}

export async function startGeneration(params: GenerateParams): Promise<{ generation_id: string; status: string }> {
  const res = await fetch(`${API_URL}/api/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });

  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Generation failed: ${res.status} ${body}`);
  }

  return res.json();
}

export function getDownloadUrl(generationId: string): string {
  return `${API_URL}/api/download/${generationId}`;
}
