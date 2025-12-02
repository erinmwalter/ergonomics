import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any, Optional
import logging
from contextlib import contextmanager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseService:
    def __init__(self, 
                 host: str = "localhost",
                 port: int = 5432, 
                 database: str = "postgres",
                 username: str = "postgres",
                 password: str = "password"):
        
        self.connection_params = {
            "host": host,
            "port": port,
            "database": database,
            "user": username,
            "password": password
        }
        
        self.test_connection()
    
    def test_connection(self):
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    logger.info("Database connection successful")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise
    
    @contextmanager
    def get_connection(self):
        conn = None
        try:
            conn = psycopg2.connect(**self.connection_params)
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def execute_query(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
    
    def execute_insert(self, query: str, params: tuple = None) -> int:
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                return cursor.fetchone()[0] if cursor.description else None
    
    def execute_update(self, query: str, params: tuple = None) -> int:
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                return cursor.rowcount

    def create_environment(self, name: str, image_path: str, created_by: str) -> int:
        query = """
        INSERT INTO public."Environments" ("Name", "ImagePath", "CreatedBy", "CreatedAt", "IsActive")
        VALUES (%s, %s, %s, CURRENT_TIMESTAMP, true)
        RETURNING "Id"
        """
        result = self.execute_insert(query, (name, image_path, created_by))
        logger.info(f"Created environment: {name} (ID: {result})")
        return result
    
    def get_environments(self, active_only: bool = True) -> List[Dict[str, Any]]:
        query = "SELECT * FROM public.\"Environments\""
        if active_only:
            query += " WHERE \"IsActive\" = true"
        query += " ORDER BY \"CreatedAt\" DESC"
        
        return self.execute_query(query)
    
    def get_environment_by_id(self, env_id: int) -> Optional[Dict[str, Any]]:
        query = "SELECT * FROM public.\"Environments\" WHERE \"Id\" = %s"
        results = self.execute_query(query, (env_id,))
        return results[0] if results else None
    
    def update_environment(self, env_id: int, name: str = None, image_path: str = None, 
                          is_active: bool = None) -> bool:
        updates = []
        params = []
        
        if name is not None:
            updates.append("\"Name\" = %s")
            params.append(name)
        if image_path is not None:
            updates.append("\"ImagePath\" = %s")
            params.append(image_path)
        if is_active is not None:
            updates.append("\"IsActive\" = %s")
            params.append(is_active)
        
        if not updates:
            return False
            
        params.append(env_id)
        query = f"UPDATE public.\"Environments\" SET {', '.join(updates)} WHERE \"Id\" = %s"
        
        rows_affected = self.execute_update(query, tuple(params))
        return rows_affected > 0

    def create_zone(self, environment_id: int, zone_name: str, x_start: int, y_start: int,
                   x_end: int, y_end: int, color: str, created_by: str) -> int:
        """Create new zone and return its ID"""
        query = """
        INSERT INTO public."Zones" ("EnvironmentId", "ZoneName", "Xstart", "Ystart", "Xend", "Yend", 
                          "Color", "CreatedAt", "CreatedBy", "IsActive")
        VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, %s, true)
        RETURNING "Id"
        """
        params = (environment_id, zone_name, x_start, y_start, x_end, y_end, color, created_by)
        result = self.execute_insert(query, params)
        logger.info(f"Created zone: {zone_name} in environment {environment_id} (ID: {result})")
        return result
    
    def get_zones_for_environment(self, environment_id: int, active_only: bool = True) -> List[Dict[str, Any]]:
        query = "SELECT * FROM public.\"Zones\" WHERE \"EnvironmentId\" = %s"
        if active_only:
            query += " AND \"IsActive\" = true"
        query += " ORDER BY \"CreatedAt\" ASC"
        
        return self.execute_query(query, (environment_id,))
    
    def get_zone_by_id(self, zone_id: int) -> Optional[Dict[str, Any]]:
        """Get specific zone by ID"""
        query = "SELECT * FROM public.\"Zones\" WHERE \"Id\" = %s"
        results = self.execute_query(query, (zone_id,))
        return results[0] if results else None
    
    def update_zone(self, zone_id: int, **kwargs) -> bool:
        valid_fields = ['ZoneName', 'Xstart', 'Ystart', 'Xend', 'Yend', 'Color', 'IsActive']
        updates = []
        params = []
        
        for field, value in kwargs.items():
            if field in valid_fields and value is not None:
                updates.append(f"\"{field}\" = %s")
                params.append(value)
        
        if not updates:
            return False
            
        params.append(zone_id)
        query = f"UPDATE public.\"Zones\" SET {', '.join(updates)} WHERE \"Id\" = %s"
        
        rows_affected = self.execute_update(query, tuple(params))
        return rows_affected > 0
    
    def delete_zone(self, zone_id: int) -> bool:
        """Soft delete zone (set is_active = false)"""
        return self.update_zone(zone_id, IsActive=False)
    
    # Process operations
    def create_process(self, environment_id: int, process_name: str, description: str, 
                      duration: int, created_by: str) -> int:
        """Create new process and return its ID"""
        query = """
        INSERT INTO public."Processes" ("EnvironmentId", "ProcessName", "Description", "Duration",
                          "CreatedAt", "CreatedBy", "IsActive")
        VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, %s, true)
        RETURNING "Id"
        """
        params = (environment_id, process_name, description, duration, created_by)
        result = self.execute_insert(query, params)
        logger.info(f"Created process: {process_name} in environment {environment_id} (ID: {result})")
        return result
    
    def get_processes_for_environment(self, environment_id: int, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get all processes for an environment"""
        query = "SELECT * FROM public.\"Processes\" WHERE \"EnvironmentId\" = %s"
        if active_only:
            query += " AND \"IsActive\" = true"
        query += " ORDER BY \"CreatedAt\" DESC"
        
        return self.execute_query(query, (environment_id,))
    
    def get_process_by_id(self, process_id: int) -> Optional[Dict[str, Any]]:
        """Get specific process by ID"""
        query = "SELECT * FROM public.\"Processes\" WHERE \"Id\" = %s"
        results = self.execute_query(query, (process_id,))
        return results[0] if results else None
    
    def update_process(self, process_id: int, **kwargs) -> bool:
        """Update process fields"""
        valid_fields = ['ProcessName', 'Description', 'Duration', 'IsActive']
        updates = []
        params = []
        
        for field, value in kwargs.items():
            if field in valid_fields and value is not None:
                updates.append(f"\"{field}\" = %s")
                params.append(value)
        
        if not updates:
            return False
            
        params.append(process_id)
        query = f"UPDATE public.\"Processes\" SET {', '.join(updates)} WHERE \"Id\" = %s"
        
        rows_affected = self.execute_update(query, tuple(params))
        return rows_affected > 0
    
    def delete_process(self, process_id: int) -> bool:
        """Soft delete process (set is_active = false)"""
        return self.update_process(process_id, IsActive=False)
    
    # Process steps operations
    def create_process_step(self, process_id: int, step_number: int, step_name: str, 
                           target_zone_id: int, duration: int, description: str, created_by: str) -> int:
        """Create new process step and return its ID"""
        query = """
        INSERT INTO public."ProcessSteps" ("ProcessId", "StepNumber", "StepName", "TargetZoneId",
                          "Duration", "Description", "CreatedAt", "CreatedBy", "IsActive")
        VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, %s, true)
        RETURNING "Id"
        """
        params = (process_id, step_number, step_name, target_zone_id, duration, description, created_by)
        result = self.execute_insert(query, params)
        logger.info(f"Created process step: {step_name} for process {process_id} (ID: {result})")
        return result
    
    def get_process_steps(self, process_id: int, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get all steps for a process with zone information"""
        query = """
        SELECT ps.*, z."ZoneName", z."Color" 
        FROM public."ProcessSteps" ps
        JOIN public."Zones" z ON ps."TargetZoneId" = z."Id"
        WHERE ps."ProcessId" = %s
        """
        if active_only:
            query += " AND ps.\"IsActive\" = true"
        query += " ORDER BY ps.\"StepNumber\" ASC"
        
        return self.execute_query(query, (process_id,))
    
    def update_process_step(self, step_id: int, **kwargs) -> bool:
        """Update process step fields"""
        valid_fields = ['StepNumber', 'StepName', 'TargetZoneId', 'Duration', 'Description', 'IsActive']
        updates = []
        params = []
        
        for field, value in kwargs.items():
            if field in valid_fields and value is not None:
                updates.append(f"\"{field}\" = %s")
                params.append(value)
        
        if not updates:
            return False
            
        params.append(step_id)
        query = f"UPDATE public.\"ProcessSteps\" SET {', '.join(updates)} WHERE \"Id\" = %s"
        
        rows_affected = self.execute_update(query, tuple(params))
        return rows_affected > 0
    
    def delete_process_step(self, step_id: int) -> bool:
        """Soft delete process step (set is_active = false)"""
        return self.update_process_step(step_id, IsActive=False)
    
    def save_process_steps(self, process_id: int, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Replace all steps for a process with new steps"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("UPDATE public.\"ProcessSteps\" SET \"IsActive\" = false WHERE \"ProcessId\" = %s", (process_id,))
                
                for i, step in enumerate(steps):
                    self.create_process_step(
                        process_id=process_id,
                        step_number=i + 1,
                        step_name=step['StepName'],
                        target_zone_id=step['TargetZoneId'],
                        duration=step['Duration'],
                        description=step['Description'],
                        created_by=step.get('CreatedBy', 'admin')
                    )
        
        return self.get_process_steps(process_id)

# FOR TESTING PURPOSES ONLY - TEST DIFFERENT ASPECTS OF THE DATABASE HERE (WILL NOT BE USED IN APP)
if __name__ == "__main__":
    db = DatabaseService(database="postgres")
    
    # Test creating an environment
    env_id = db.create_environment(
        name="Test Workstation",
        image_path="/uploads/test_workspace.jpg",
        created_by="admin"
    )
    
    # Test creating zones
    zone1_id = db.create_zone(
        environment_id=env_id,
        zone_name="Button A",
        x_start=100, y_start=100,
        x_end=200, y_end=200,
        color="#FF0000",
        created_by="admin"
    )
    
    zone2_id = db.create_zone(
        environment_id=env_id,
        zone_name="Safety Switch",
        x_start=300, y_start=150,
        x_end=400, y_end=250,
        color="#00FF00",
        created_by="admin"
    )
    
    # Test retrieving data
    environments = db.get_environments()
    print("Environments:", environments)
    
    zones = db.get_zones_for_environment(env_id)
    print("Zones:", zones)