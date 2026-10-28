/**
 * AI Image Studio — API client library.
 *
 * Connects the Next.js frontend to the FastAPI backend.
 * All calls go through the singleton `api` object.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

// ── Types ────────────────────────────────────────────────────────────

export interface ImageInfo {
  id: string;
  width: number;
  height: number;
  format: string;
  size_bytes: number;
  filename: string;
}

export interface ProcessingResult {
  success: boolean;
  image?: ImageInfo;
  error?: string;
  processing_time_ms?: number;
}

export interface JobResponse {
  job_id: string;
  status: "pending" | "running" | "completed" | "failed" | "cancelled";
  progress: number;
  result?: ProcessingResult;
  error?: string;
  created_at?: string;
}

export interface HealthResponse {
  status: string;
  version: string;
  device: string;
  models: Record<string, boolean>;
}

// ── Helpers ──────────────────────────────────────────────────────────

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, init);
  if (!res.ok) {
    const body = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(body.detail ?? body.error ?? `API error ${res.status}`);
  }
  return res.json();
}

function formData(fields: Record<string, string | number | boolean | File | Blob | undefined>): FormData {
  const fd = new FormData();
  for (const [k, v] of Object.entries(fields)) {
    if (v === undefined || v === null) continue;
    if (v instanceof File || v instanceof Blob) {
      fd.append(k, v);
    } else {
      fd.append(k, String(v));
    }
  }
  return fd;
}

// ── API ──────────────────────────────────────────────────────────────

export const api = {
  // Health
  health: () => request<HealthResponse>("/health"),

  // Upload
  upload: (file: File) =>
    request<ImageInfo>("/upload", {
      method: "POST",
      body: formData({ file }),
    }),

  // Download URL (for <img src>)
  imageUrl: (fileId: string) => `${API_BASE}/images/${fileId}`,

  // ── Processing endpoints ────────────────────────────────────────

  upscale: (imageId: string, opts: { scale_factor?: number; face_enhance?: boolean; output_format?: string; quality?: number } = {}) =>
    request<JobResponse>("/upscale", {
      method: "POST",
      body: formData({ image_id: imageId, ...opts }),
    }),

  sharpen: (imageId: string, opts: { intensity?: number; radius?: number; output_format?: string; quality?: number } = {}) =>
    request<ProcessingResult>("/sharpen", {
      method: "POST",
      body: formData({ image_id: imageId, ...opts }),
    }),

  denoise: (imageId: string, opts: { strength?: number; output_format?: string; quality?: number } = {}) =>
    request<ProcessingResult>("/denoise", {
      method: "POST",
      body: formData({ image_id: imageId, ...opts }),
    }),

  faceEnhance: (imageId: string, opts: { upscale?: number; output_format?: string; quality?: number } = {}) =>
    request<JobResponse>("/face/enhance", {
      method: "POST",
      body: formData({ image_id: imageId, ...opts }),
    }),

  colorAdjust: (imageId: string, opts: { brightness?: number; contrast?: number; saturation?: number; exposure?: number; warmth?: number; output_format?: string; quality?: number } = {}) =>
    request<ProcessingResult>("/color/adjust", {
      method: "POST",
      body: formData({ image_id: imageId, ...opts }),
    }),

  backgroundRemove: (imageId: string, opts: { alpha_matting?: boolean; output_format?: string } = {}) =>
    request<JobResponse>("/background/remove", {
      method: "POST",
      body: formData({ image_id: imageId, ...opts }),
    }),

  backgroundChange: (imageId: string, opts: {
    bg_type?: string;
    bg_color?: string;
    gradient_start?: string;
    gradient_end?: string;
    gradient_direction?: string;
    blur_amount?: number;
    original_image_id?: string;
    output_format?: string;
    quality?: number;
  } = {}) =>
    request<JobResponse>("/background/change", {
      method: "POST",
      body: formData({ image_id: imageId, ...opts }),
    }),

  // Editing
  crop: (imageId: string, opts: { x: number; y: number; width: number; height: number; output_format?: string; quality?: number }) =>
    request<ProcessingResult>("/image/crop", {
      method: "POST",
      body: formData({ image_id: imageId, ...opts }),
    }),

  resize: (imageId: string, opts: { width?: number; height?: number; maintain_aspect?: boolean; output_format?: string; quality?: number }) =>
    request<ProcessingResult>("/image/resize", {
      method: "POST",
      body: formData({ image_id: imageId, ...opts }),
    }),

  rotate: (imageId: string, opts: { angle?: number; expand?: boolean; output_format?: string; quality?: number } = {}) =>
    request<ProcessingResult>("/image/rotate", {
      method: "POST",
      body: formData({ image_id: imageId, ...opts }),
    }),

  flip: (imageId: string, opts: { direction?: string; output_format?: string; quality?: number } = {}) =>
    request<ProcessingResult>("/image/flip", {
      method: "POST",
      body: formData({ image_id: imageId, ...opts }),
    }),

  // Jobs
  getJob: (jobId: string) => request<JobResponse>(`/jobs/${jobId}`),
  listJobs: () => request<JobResponse[]>("/jobs"),
  cancelJob: (jobId: string) =>
    request<{ status: string }>(`/jobs/${jobId}/cancel`, { method: "POST" }),

  // Batch
  batchProcess: (files: File[], operation: string, opts: Record<string, string | number> = {}) => {
    const fd = new FormData();
    for (const f of files) fd.append("files", f);
    fd.append("operation", operation);
    for (const [k, v] of Object.entries(opts)) fd.append(k, String(v));
    return request<JobResponse>("/batch/process", { method: "POST", body: fd });
  },
};

// ── Job polling ─────────────────────────────────────────────────────

/**
 * Poll a job until it completes/fails. Calls `onProgress` with each update.
 */
export async function pollJob(
  jobId: string,
  onProgress?: (job: JobResponse) => void,
  intervalMs = 1000,
  maxAttempts = 300,
): Promise<JobResponse> {
  for (let i = 0; i < maxAttempts; i++) {
    const job = await api.getJob(jobId);
    onProgress?.(job);
    if (job.status === "completed" || job.status === "failed" || job.status === "cancelled") {
      return job;
    }
    await new Promise((r) => setTimeout(r, intervalMs));
  }
  throw new Error("Job timed out");
}
