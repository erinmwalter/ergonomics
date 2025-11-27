export type Process = {
  Id: number;
  EnvironmentId: number;
  ProcessName: string;
  Description: string;
  Duration: number; 
  CreatedAt: string;
  CreatedBy: string;
  IsActive: boolean;
}