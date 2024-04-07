import os
import json

env_file = "env.json"
if os.path.exists(env_file):
    with open(env_file) as f:
        env_vars = json.loads(f.read())
else:
    env_vars = dict(os.environ)

dbname = env_vars.get('DATABASE_URL_PRIMARY') or env_vars.get('DATABASE_URL') or 'sqlite:///test.db'

if dbname.startswith('postgres://'):
    dbname = dbname.replace('postgres://', 'postgresql://', 1)
