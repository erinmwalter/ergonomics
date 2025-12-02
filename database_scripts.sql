CREATE TABLE tracking_sessions (
    Id SERIAL PRIMARY KEY,
    SessionId VARCHAR(50) UNIQUE NOT NULL,
    EnvironmentId INTEGER REFERENCES "Environments"(Id),
    ProcessId INTEGER REFERENCES "Processes"(Id),
    StartTime TIMESTAMP NOT NULL,
    EndTime TIMESTAMP,
    TotalDuration FLOAT, 
    Status VARCHAR(20),  
    OverallAdherence FLOAT, 
    StepsCompleted INTEGER,
    StepsExpected INTEGER,
    CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE step_events (
    Id SERIAL PRIMARY KEY,
    SessionId VARCHAR(50) REFERENCES tracking_sessions(SessionId),
    StepNumber INTEGER NOT NULL,
    StepName VARCHAR(100),
    ZoneName VARCHAR(100),
    TargetDuration FLOAT, 
    ActualDuration FLOAT, 
    StepAdherence FLOAT,  
    CompletedAt TIMESTAMP NOT NULL,
    CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);