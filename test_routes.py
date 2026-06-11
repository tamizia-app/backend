import sys
sys.path.insert(0, ".")
from app.main import app
print("App created OK")
for r in app.routes:
    methods = getattr(r, "methods", {"GET"})
    path = getattr(r, "path", str(r))
    print(f"  {methods} {path}")
