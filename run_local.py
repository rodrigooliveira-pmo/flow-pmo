import os
from shared.env_utils import load_env_file

# Load configuration from .env.local (excluded from git via .gitignore)
_env_file = os.path.join(os.path.dirname(__file__), '.env.local')
load_env_file(_env_file)

import api.index
print("Successfully loaded api.index")
