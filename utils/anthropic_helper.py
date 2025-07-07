"""Helper to initialize Anthropic client without proxy issues."""
import os
import sys

def get_anthropic_client(api_key: str):
    """Get Anthropic client instance, handling proxy issues."""
    # Store original environment
    original_env = {}
    proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 
                  'ALL_PROXY', 'all_proxy', 'NO_PROXY', 'no_proxy']
    
    # Temporarily remove all proxy variables
    for var in proxy_vars:
        if var in os.environ:
            original_env[var] = os.environ[var]
            del os.environ[var]
    
    try:
        # Import Anthropic in clean environment
        from anthropic import Anthropic
        
        # Create client
        client = Anthropic(api_key=api_key)
        
        return client
        
    finally:
        # Restore original environment
        for var, value in original_env.items():
            os.environ[var] = value