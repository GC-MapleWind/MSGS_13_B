SELECT 'CREATE DATABASE maplewind'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'maplewind')\gexec

SELECT 'CREATE DATABASE chatbot'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'chatbot')\gexec
