CREATE TABLE DiagnosticReport
(
    ReportID INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    FileName VARCHAR(255),
    FilePath VARCHAR(1000),
    SW_I_Step VARCHAR(100),
    SA_Codes VARCHAR(500),
    UploadTimestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE ECUVersion
(
    ECUVersionID INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ReportID INT,
    FileName VARCHAR(255),
    SW_I_Step VARCHAR(100),
    ECUName VARCHAR(100),
    HardwareVersion VARCHAR(100),
    BootloaderVersion VARCHAR(100),
    SWVersion VARCHAR(100),
    Coding VARCHAR(100)
);

CREATE TABLE DTCEvent
(
    EventID BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ReportID INT,
    FileName VARCHAR(255),
    SW_I_Step VARCHAR(100),
    ECUName VARCHAR(100),
    DTCCode VARCHAR(20),
    Description VARCHAR(500),
    FaultCategory VARCHAR(100),
    Status VARCHAR(50),
    OccurrenceCounter INT,
    AgingCounter INT,
    Priority INT,
    EventTimestamp TIMESTAMP,
    RiskScore INT
);

CREATE TABLE EnvironmentSignal
(
    SignalID BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    EventID BIGINT,
    ReportID INT,
    FileName VARCHAR(255),
    SW_I_Step VARCHAR(100),
    ECUName VARCHAR(100),
    DTCCode VARCHAR(20),
    SignalName VARCHAR(100),
    SignalValue VARCHAR(100),
    EventTimestamp TIMESTAMP
);