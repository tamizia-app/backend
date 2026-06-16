import sys
sys.path.insert(0, ".")
from fastapi import APIRouter

# Step by step trace
from app.api.routes import classrooms as cr_mod
print(f"classrooms module: {cr_mod}")
print(f"has router: {hasattr(cr_mod, 'router')}")

from app.api.routes import students as st_mod
print(f"students module: {st_mod}")

from app.api.routes import exercises as ex_mod
print(f"exercises module: {ex_mod}")

from app.api.routes import sessions as ss_mod
print(f"sessions module: {ss_mod}")

# Count routes from each
ar = APIRouter()
ar.include_router(cr_mod.router)
print(f"classrooms routes added: {len(ar.routes)}")
ar2 = APIRouter()
ar2.include_router(st_mod.router)
print(f"students routes added: {len(ar2.routes)}")
ar3 = APIRouter()
ar3.include_router(ex_mod.router)
print(f"exercises routes added: {len(ar3.routes)}")
ar4 = APIRouter()
ar4.include_router(ss_mod.router)
print(f"sessions routes added: {len(ar4.routes)}")

# Now the actual api_router
from app.api.router import api_router
print(f"\nactual api_router routes: {len(api_router.routes)}")
for r in api_router.routes:
    print(f"  path={r.path}, methods={r.methods}")
