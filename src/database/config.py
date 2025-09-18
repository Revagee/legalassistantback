import os


class DatabaseConfig:
    def __init__(self):
        self.connection_string = os.getenv("DATABASE_URL")

    @property
    def langchain_connection_string(self):
        return self.connection_string.replace("postgres", "postgresql+psycopg")


db_config = DatabaseConfig()
