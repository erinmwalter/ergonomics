export type ProcessStep = {
  Id: number;
  ProcessId: number;
  StepNumber: number;
  StepName: string;
  TargetZoneId: number;
  Description: string;
  CreatedAt: string;
  CreatedBy: string;
  IsActive: boolean;
  ZoneName?: string;
  Color?: string;
  Duration: number;
}