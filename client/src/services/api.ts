const API_BASE = `${window.location.protocol}//${window.location.hostname}:8000/api/v1`;

const handleResponse = async (res: Response) => {
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `请求失败: ${res.status}`);
  }
  return res.json();
};

export const submitJob = async (file: File) => {
  const formData = new FormData();
  formData.append('video_file', file);
  
  const res = await fetch(`${API_BASE}/jobs/submit`, {
    method: 'POST',
    body: formData
  });
  return handleResponse(res);
};

export const approveJob = async (jobId: string, data: any) => {
  const res = await fetch(`${API_BASE}/jobs/approve/${jobId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      job_id: jobId,
      ...data
    })
  });
  return handleResponse(res);
};

export const getJobStatus = async (jobId: string) => {
  const res = await fetch(`${API_BASE}/jobs/${jobId}/status`);
  return handleResponse(res);
};

export const getJobTranscription = async (jobId: string) => {
  const res = await fetch(`${API_BASE}/jobs/${jobId}/transcription`);
  return handleResponse(res);
};

export const getJobResults = async (jobId: string) => {
  const res = await fetch(`${API_BASE}/jobs/${jobId}/results`);
  return handleResponse(res);
};

export const getOutroTemplates = async () => {
  const res = await fetch(`${API_BASE}/jobs/outro-templates`);
  return handleResponse(res);
};

export const abortJob = async (jobId: string) => {
  const res = await fetch(`${API_BASE}/jobs/${jobId}/abort`, {
    method: 'POST'
  });
  return handleResponse(res);
};

export const getJobsHistory = async () => {
  const res = await fetch(`${API_BASE}/jobs`);
  return handleResponse(res);
};
