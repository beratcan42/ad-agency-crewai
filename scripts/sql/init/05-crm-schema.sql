-- CRM Schema

CREATE SCHEMA IF NOT EXISTS crm;

CREATE TABLE IF NOT EXISTS crm.clients (
    client_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    sector VARCHAR(100),
    email VARCHAR(100),
    phone VARCHAR(50),
    address TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS crm.proposals (
    proposal_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id VARCHAR(50) REFERENCES crm.clients(client_id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    status VARCHAR(50) DEFAULT 'draft', -- draft, sent, accepted, rejected
    total_amount NUMERIC(10, 2) NOT NULL DEFAULT 0,
    pdf_path TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS crm.invoices (
    invoice_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    proposal_id UUID REFERENCES crm.proposals(proposal_id) ON DELETE SET NULL,
    client_id VARCHAR(50) REFERENCES crm.clients(client_id) ON DELETE CASCADE,
    amount NUMERIC(10, 2) NOT NULL,
    tax_rate NUMERIC(5, 2) DEFAULT 20.00,
    total_amount NUMERIC(10, 2) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending', -- pending, paid, cancelled
    pdf_path TEXT,
    due_date TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Insert dummy data for testing
INSERT INTO crm.clients (client_id, name, sector, email)
VALUES ('akme-tekstil', 'Akme Tekstil A.Ş.', 'Tekstil', 'info@akmetekstil.com')
ON CONFLICT (client_id) DO NOTHING;
