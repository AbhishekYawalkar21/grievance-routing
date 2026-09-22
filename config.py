"""
Configuration and constants
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Supabase Configuration (from Settings → API)
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# HuggingFace Configuration (optional, can be empty for free tier)
HUGGINGFACE_API_TOKEN = os.getenv('HUGGINGFACE_API_TOKEN', '')

# App Configuration
APP_TITLE = "⚖️ Intelligent Government Grievance Routing"
APP_DESCRIPTION = "Route citizen grievances to correct government department using Knowledge Graph"

# Domain mappings for keyword matching
SCHEME_KEYWORDS = {
    'pm_kisan': ['pm-kisan', 'kisan', 'samman nidhi', 'farmer payment', 'kisan payment'],
    'dbt': ['dbt', 'direct benefit', 'payment', 'dbdbt transfer']
}

FAILURE_KEYWORDS = {
    'identity_mismatch': ['mismatch', 'name', 'aadhaar', 'not match', 'different name'],
    'bank_mismatch': ['bank', 'account', 'account mismatch', 'bank account'],
    'payment_fail': ['not received', 'payment failed', 'rejected', 'no payment', 'stuck'],
    'not_verified': ['not verified', 'verification failed', 'not linked', 'cannot verify']
}

SERVICE_KEYWORDS = {
    'aadhaar_kyc': ['aadhaar', 'kyc', 'identity', 'verification'],
    'bank_linking': ['bank', 'linking', 'link account', 'bank account'],
    'dbt_payment': ['payment', 'dbt', 'transfer', 'deposit']
}