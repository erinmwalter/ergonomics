import type { Zone } from '../models';

const API_BASE_URL = 'http://localhost:5000/api';

export interface TrackingStatus {
  available: boolean;
  model_loaded: boolean;
}

interface TrackingZone {
  id: number;
  name: string;
  x: number;
  y: number;
  width: number;
  height: number;
  color: string;
}

class TrackingService {
  async checkTrackingStatus(): Promise<TrackingStatus> {
    const response = await fetch(`${API_BASE_URL}/tracking/status`);
    
    if (!response.ok) {
      throw new Error(`Failed to check tracking status: ${response.statusText}`);
    }
    
    return response.json();
  }

  getStreamUrl(zones?: Zone[], sessionId?: string): string {
    let url = `${API_BASE_URL}/tracking/stream`;
    const params = new URLSearchParams();
    
    if (zones && zones.length > 0) {
      // Convert to tracking format before sending
      const trackingZones = this.convertDatabaseZones(zones);
      params.append('zones', JSON.stringify(trackingZones));
    }
    
    if (sessionId) {
      params.append('sessionId', sessionId);
    }
    
    if (params.toString()) {
      url += `?${params.toString()}`;
    }
    
    return url;
  }


  private convertDatabaseZone(dbZone: Zone): TrackingZone {
    return {
      id: dbZone.Id,
      name: dbZone.ZoneName,
      x: dbZone.Xstart,
      y: dbZone.Ystart,
      width: dbZone.Xend - dbZone.Xstart,
      height: dbZone.Yend - dbZone.Ystart,
      color: dbZone.Color
    };
  }

  private convertDatabaseZones(dbZones: Zone[]): TrackingZone[] {
    return dbZones.map(zone => this.convertDatabaseZone(zone));
  }
}

export const trackingService = new TrackingService();
export default trackingService;