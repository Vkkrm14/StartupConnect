"""Common validators"""

import re
from typing import Optional

def validate_user_id(user_id: str) -> bool:
    """
    Validate user ID format
    
    Rules:
    - Alphanumeric with hyphens/underscores
    - 3-50 characters
    - Must start with letter or number
    """
    pattern = r'^[a-zA-Z0-9][a-zA-Z0-9_-]{2,49}$'
    return bool(re.match(pattern, user_id))

def validate_trust_score(score: float) -> bool:
    """Validate trust score is between 0 and 1"""
    return 0.0 <= score <= 1.0

def validate_email(email: str) -> bool:
    """Basic email validation"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_domain_tag(tag: str) -> bool:
    """Validate domain tag format"""
    # Lowercase alphanumeric with hyphens, 2-30 chars
    pattern = r'^[a-z0-9][a-z0-9-]{1,29}$'
    return bool(re.match(pattern, tag.lower()))

def sanitize_string(text: str, max_length: int = 1000) -> str:
    """Sanitize user input string"""
    # Remove leading/trailing whitespace
    text = text.strip()
    
    # Truncate to max length
    text = text[:max_length]
    
    # Remove control characters
    text = ''.join(char for char in text if ord(char) >= 32 or char == '\n')
    
    return text
