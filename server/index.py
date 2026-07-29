"""Vercel Python service entrypoint. `server/app` is a symlink to the
repo-root `app/` business-logic package for local dev; `installCommand` in
the repo-root vercel.json replaces it with a real copy for cloud builds."""
from app import exceptions
from fastapi import FastAPI

from _auth import router as auth_router
from _collection_routes import router as collection_router
from _comparator_routes import router as comparator_router
from _inventory_routes import router as inventory_router
from _audit_routes import router as audit_router
from _companies_routes import router as companies_router
from _master_excel_routes import router as master_excel_router
from _quotation_history_routes import router as quotation_history_router
from _quotation_routes import router as quotation_router
from _users_routes import router as users_router

app = FastAPI(title="Garg Dental Operations Toolkit API")

app.include_router(auth_router)
app.include_router(comparator_router)
app.include_router(collection_router)
app.include_router(inventory_router)
app.include_router(quotation_router)
app.include_router(quotation_history_router)
app.include_router(users_router)
app.include_router(master_excel_router)
app.include_router(audit_router)
app.include_router(companies_router)


@app.get("/api/ping")
def ping():
    return {"ok": True, "base_error_class": exceptions.AppError.__name__}
