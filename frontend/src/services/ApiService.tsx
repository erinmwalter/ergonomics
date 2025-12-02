import type { Environment, Zone, Process, ProcessStep } from '../models';

const API_BASE_URL = 'http://localhost:5000/api';

class ApiService {
  private async makeRequest<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
      ...options,
    });

    if (!response.ok) {
      throw new Error(`API call failed: ${response.statusText}`);
    }

    return response.json();
  }

  async getEnvironments(): Promise<Environment[]> {
    return this.makeRequest<Environment[]>('/environments');
  }

  async getEnvironmentById(id: number): Promise<Environment> {
    return this.makeRequest<Environment>(`/environments/${id}`);
  }

  async createEnvironment(name: string, imagePath: string, createdBy: string): Promise<Environment> {
    return this.makeRequest<Environment>('/environments', {
      method: 'POST',
      body: JSON.stringify({ name, imagePath, createdBy }),
    });
  }

  async updateEnvironment(id: number, updates: Partial<Environment>): Promise<Environment> {
    return this.makeRequest<Environment>(`/environments/${id}`, {
      method: 'PUT',
      body: JSON.stringify(updates),
    });
  }

  async getZonesForEnvironment(environmentId: number): Promise<Zone[]> {
    return this.makeRequest<Zone[]>(`/environments/${environmentId}/zones`);
  }

  async createZone(zone: Omit<Zone, 'Id' | 'CreatedAt'>): Promise<Zone> {
    return this.makeRequest<Zone>('/zones', {
      method: 'POST',
      body: JSON.stringify(zone),
    });
  }

  async updateZone(id: number, updates: Partial<Zone>): Promise<Zone> {
    return this.makeRequest<Zone>(`/zones/${id}`, {
      method: 'PUT',
      body: JSON.stringify(updates),
    });
  }

  async deleteZone(id: number): Promise<void> {
    return this.makeRequest<void>(`/zones/${id}`, {
      method: 'DELETE',
    });
  }

  async uploadImage(imageData: string): Promise<string> {
    const response = await this.makeRequest<{filename: string, path: string}>('/upload-image', {
      method: 'POST',
      body: JSON.stringify({ imageData }),
    });
    
    return response.path;
  }

  async saveZonesForEnvironment(environmentId: number, zones: Zone[]): Promise<Zone[]> {
    return this.makeRequest<Zone[]>(`/environments/${environmentId}/zones`, {
      method: 'PUT',
      body: JSON.stringify({ zones }),
    });
  }

  async getProcessesForEnvironment(environmentId: number): Promise<Process[]> {
    return this.makeRequest<Process[]>(`/environments/${environmentId}/processes`);
  }

  async createProcess(process: Omit<Process, 'Id' | 'CreatedAt'>): Promise<Process> {
    return this.makeRequest<Process>('/processes', {
      method: 'POST',
      body: JSON.stringify(process),
    });
  }

  async getProcessById(id: number): Promise<Process> {
    return this.makeRequest<Process>(`/processes/${id}`);
  }

  async updateProcess(id: number, updates: Partial<Process>): Promise<Process> {
    return this.makeRequest<Process>(`/processes/${id}`, {
      method: 'PUT',
      body: JSON.stringify(updates),
    });
  }

  async deleteProcess(id: number): Promise<void> {
    return this.makeRequest<void>(`/processes/${id}`, {
      method: 'DELETE',
    });
  }

  async getProcessSteps(processId: number): Promise<ProcessStep[]> {
    return this.makeRequest<ProcessStep[]>(`/processes/${processId}/steps`);
  }

  async saveProcessSteps(processId: number, steps: { StepName: string; TargetZoneId: number; Duration: number; Description: string; }[]): Promise<ProcessStep[]> {
    return this.makeRequest<ProcessStep[]>(`/processes/${processId}/steps`, {
      method: 'POST',
      body: JSON.stringify({ steps }),
    });
  }

  async startAnalysisSession(environmentId: number, processId: number): Promise<{ sessionId: string; status: string }> {
    return this.makeRequest<{ sessionId: string; status: string }>('/analysis/start', {
      method: 'POST',
      body: JSON.stringify({ environmentId, processId }),
    });
  }

  async stopAnalysisSession(sessionId: string): Promise<any> {
    return this.makeRequest<any>(`/analysis/stop/${sessionId}`, {
      method: 'POST',
    });
  }

  async getAnalysisStatus(sessionId: string): Promise<{
    isActive: boolean;
    currentStep: number;
    stepEvents: any[];
    elapsedTime: number;
  }> {
    return this.makeRequest<any>(`/analysis/status/${sessionId}`);
  }

  async saveAnalysisResults(sessionId: string, results: any): Promise<void> {
    return this.makeRequest<void>(`/analysis/results/${sessionId}`, {
      method: 'POST',
      body: JSON.stringify({ results }),
    });
  }

  async getAnalysisHistory(environmentId?: number, processId?: number): Promise<any[]> {
    const params = new URLSearchParams();
    if (environmentId) params.append('environmentId', environmentId.toString());
    if (processId) params.append('processId', processId.toString());
    
    const queryString = params.toString();
    return this.makeRequest<any[]>(`/analysis/history${queryString ? `?${queryString}` : ''}`);
  }
}

export const apiService = new ApiService();