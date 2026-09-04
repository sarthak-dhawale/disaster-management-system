from fastapi import FastAPI

from app.database import test_database_connection
from app.routes.disasters import router as disasters_router
from app.routes import shelters
from app.routes import locations
from app.routes import users
from app.routes import volunteers
from app.routes import resources
from app.routes import emergency_reports
from app.routes import resource_allocations
from app.routes import volunteer_assignments
from app.routes import shelter_registrations
from app.routes import dashboard
from app.routes import search

app = FastAPI(
    title="Disaster Management System",
    description="DBMS-based Disaster Management System API",
    version="1.0.0"
)

app.include_router(disasters_router)
app.include_router(shelters.router)
app.include_router(locations.router)
app.include_router(users.router)
app.include_router(volunteers.router)
app.include_router(resources.router)
app.include_router(emergency_reports.router)
app.include_router(resource_allocations.router)
app.include_router(volunteer_assignments.router)
app.include_router(shelter_registrations.router)
app.include_router(dashboard.router)
app.include_router(search.router)

@app.get("/")
def root():
    return {
        "message": "Disaster Management System API is running",
        "status": "success"
    }


@app.get("/health")
def health_check():
    database_status = test_database_connection()

    return {
        "status": "healthy",
        "database": "connected" if database_status else "disconnected"
    }