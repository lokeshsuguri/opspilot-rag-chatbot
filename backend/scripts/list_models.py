from pathlib import Path
import re
import os

# load GOOGLE_API_KEY from backend/.env
env_path = Path(__file__).resolve().parents[1] / '.env'
if env_path.exists():
    text = env_path.read_text()
    m = re.search(r'GOOGLE_API_KEY=(.*)', text)
    if m:
        os.environ['GOOGLE_API_KEY'] = m.group(1).strip()

print('GOOGLE_API_KEY set?', bool(os.environ.get('GOOGLE_API_KEY')))

try:
    from google import genai
    client = genai.Client()
    models = None
    # Try a few ways the SDK may expose model listings across versions
    if hasattr(client, 'list_models'):
        models = client.list_models()
    elif hasattr(genai, 'Model') and hasattr(genai.Model, 'list'):
        models = genai.Model.list()
    elif hasattr(genai, 'models') and hasattr(genai.models, 'list_models'):
        models = genai.models.list_models()
    else:
        # Last resort: try attribute name variations
        for name in ('list_models', 'list', 'models'):
            fn = getattr(client, name, None) or getattr(genai, name, None)
            if callable(fn):
                try:
                    models = fn()
                    break
                except Exception:
                    models = None
                    continue
    # models may be a list of dicts or model objects
    try:
        names = []
        for m in models:
            if isinstance(m, dict) and 'name' in m:
                names.append(m['name'])
            else:
                names.append(getattr(m, 'name', str(m)))
    except Exception:
        names = list(models)
    print('MODELS:')
    for n in names:
        print('-', n)
except Exception as e:
    print('ERROR:', e)
