import sqlite3
class DatabaseConnection:
    """
    Handles database connection and query execution.
    """

    def __init__(self, db_path="masks.db"):
        """Initialize the database connection and create tables."""
        self.db_path = db_path
        # Open a persistent connection to avoid overhead on every query
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._initialize_database()

    def _initialize_database(self):
        """
        Create required tables if they don't exist.
        """
        cursor = self.conn.cursor()

        # ✅ Create masks table
        cursor.execute(
            """
                CREATE TABLE IF NOT EXISTS masks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    image_name TEXT NOT NULL,
                    mask_data BLOB NOT NULL,
                    class_name TEXT NOT NULL
                )
            """
        )

        # ✅ Create classes table
        cursor.execute(
            """
                CREATE TABLE IF NOT EXISTS classes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    class_name TEXT UNIQUE NOT NULL,
                    color TEXT NOT NULL
                )
            """
        )

        self.conn.commit()

    def execute_query(self, query, params=()):
        """
        Execute an SQL query with optional parameters.
        """
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        self.conn.commit()

    def fetch_all(self, query, params=()):
        """
        Fetch all results from an SQL query.
        """
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()

    def fetch_one(self, query, params=()):
        """
        Fetch a single result from an SQL query.
        """
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchone()

    def close(self):
        """Close the persistent database connection."""
        self.conn.close()
