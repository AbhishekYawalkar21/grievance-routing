-- =====================================================
-- KNOWLEDGE GRAPH SCHEMA FOR GRIEVANCE ROUTING
-- =====================================================

-- Ministries
CREATE TABLE ministries (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    code TEXT UNIQUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Departments
CREATE TABLE departments (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    state TEXT,
    ministry_id INT REFERENCES ministries(id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Schemes
CREATE TABLE schemes (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    department_id INT REFERENCES departments(id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Government Services
CREATE TABLE services (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    service_type TEXT,
    department_id INT REFERENCES departments(id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Failure Types (why grievances fail)
CREATE TABLE failure_types (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    severity TEXT CHECK (severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    category TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Resolution Paths
CREATE TABLE resolution_paths (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    steps INT,
    time_to_resolve TEXT,
    authority TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Appeal Authorities
CREATE TABLE appeal_authorities (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    level TEXT,
    contact TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- =====================================================
-- RELATIONSHIPS (Edges in Knowledge Graph)
-- =====================================================

-- Scheme uses Service
CREATE TABLE scheme_service (
    scheme_id INT REFERENCES schemes(id),
    service_id INT REFERENCES services(id),
    PRIMARY KEY (scheme_id, service_id)
);

-- Service can fail with FailureType
CREATE TABLE service_failure (
    service_id INT REFERENCES services(id),
    failure_id INT REFERENCES failure_types(id),
    PRIMARY KEY (service_id, failure_id)
);

-- FailureType resolved by ResolutionPath
CREATE TABLE failure_resolution (
    failure_id INT REFERENCES failure_types(id),
    resolution_id INT REFERENCES resolution_paths(id),
    PRIMARY KEY (failure_id, resolution_id)
);

-- ResolutionPath owned by Authority
CREATE TABLE resolution_authority (
    resolution_id INT REFERENCES resolution_paths(id),
    authority_id INT REFERENCES appeal_authorities(id),
    PRIMARY KEY (resolution_id, authority_id)
);

-- Department has Appeal Authority
CREATE TABLE department_authority (
    department_id INT REFERENCES departments(id),
    authority_id INT REFERENCES appeal_authorities(id),
    PRIMARY KEY (department_id, authority_id)
);

-- Grievance Audit Log
CREATE TABLE grievance_audit (
    id SERIAL PRIMARY KEY,
    grievance_text TEXT,
    owner_department_id INT REFERENCES departments(id),
    confidence_score FLOAT,
    failure_types TEXT[],
    explanation TEXT,
    submitted_at TIMESTAMP DEFAULT NOW()
);

-- =====================================================
-- INSERT DATA (Knowledge Graph Seeding)
-- =====================================================

-- Ministries
INSERT INTO ministries (name, code) VALUES
('Ministry of Agriculture', 'MOA'),
('Ministry of DBT', 'MDB'),
('UIDAI', 'UIDAI');

-- Departments
INSERT INTO departments (name, state, ministry_id) VALUES
('Agriculture Department', 'National', 1),
('Banking Regulation Department', 'National', 2),
('NPCI - Payments', 'National', 2);

-- Schemes
INSERT INTO schemes (name, description, department_id) VALUES
('PM-Kisan Samman Nidhi', 'Direct income support to farmers', 1),
('Direct Benefit Transfer', 'Electronic fund transfer system', 3);

-- Services
INSERT INTO services (name, service_type, department_id) VALUES
('Aadhaar KYC', 'Identity Verification', 1),
('Bank Account Linking', 'Account Verification', 2),
('DBT Payment Processing', 'Payment', 3);

-- Failure Types
INSERT INTO failure_types (name, severity, category) VALUES
('Identity Mismatch', 'HIGH', 'BLOCKING'),
('Bank Account Mismatch', 'HIGH', 'BLOCKING'),
('Account Not Verified', 'MEDIUM', 'BLOCKING'),
('Payment Failure', 'CRITICAL', 'TRANSACTION'),
('Aadhaar Not Linked', 'HIGH', 'BLOCKING'),
('Bank Rejection', 'HIGH', 'BLOCKING');

-- Resolution Paths
INSERT INTO resolution_paths (name, steps, time_to_resolve, authority) VALUES
('Update Aadhaar-Bank Name Match', 3, '7-14 days', 'Aadhaar Enrolment Centers'),
('Correct Bank Account Details', 2, '3-5 days', 'Home Branch Manager'),
('Re-link Aadhaar to Bank', 4, '5-10 days', 'NPCI Resolution Cell'),
('Direct Visit to Agriculture Office', 1, '1-2 days', 'State Agriculture Department'),
('Bank Account Verification Update', 2, '2-3 days', 'Bank Manager');

-- Appeal Authorities
INSERT INTO appeal_authorities (name, level, contact) VALUES
('State Agriculture Department', 'STATE', 'agri@state.gov.in'),
('NPCI Resolution Cell', 'NATIONAL', 'resolution@npci.org.in'),
('UIDAI Grievance Cell', 'NATIONAL', 'grievance@uidai.gov.in'),
('District Banking Ombudsman', 'DISTRICT', 'ombudsman@district.gov.in');

-- =====================================================
-- RELATIONSHIPS DATA
-- =====================================================

-- PM-Kisan uses Aadhaar KYC and Bank Linking
INSERT INTO scheme_service (scheme_id, service_id) VALUES
(1, 1), (1, 2), (1, 3), (2, 3);

-- Services and their failure types
INSERT INTO service_failure (service_id, failure_id) VALUES
(1, 1), (1, 5),
(2, 2), (2, 3), (2, 6),
(3, 4);

-- Failure types and resolutions
INSERT INTO failure_resolution (failure_id, resolution_id) VALUES
(1, 1), (1, 3),
(2, 2), (2, 3),
(3, 5),
(4, 3),
(5, 1),
(6, 2);

-- Resolution paths owned by authorities
INSERT INTO resolution_authority (resolution_id, authority_id) VALUES
(1, 3), (2, 1), (3, 2), (4, 1), (5, 2);

-- Departments and their appeal authorities
INSERT INTO department_authority (department_id, authority_id) VALUES
(1, 1), (1, 2), (2, 4), (3, 2);

-- =====================================================
-- ENABLE ROW LEVEL SECURITY (Optional, for production)
-- =====================================================

ALTER TABLE grievance_audit ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Enable read access for all" ON grievance_audit
    FOR SELECT USING (true);

CREATE POLICY "Enable insert for all" ON grievance_audit
    FOR INSERT WITH CHECK (true);