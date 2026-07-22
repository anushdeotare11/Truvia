from neo4j import GraphDatabase, AsyncGraphDatabase
from app.config import settings
import logging

logger = logging.getLogger("truvia.neo4j")

class Neo4jClient:
    def __init__(self):
        self.driver = None

    def connect(self):
        try:
            self.driver = AsyncGraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
            )
            logger.info("Successfully connected to Neo4j graph database")
        except Exception as e:
            logger.warning(f"Neo4j unavailable — graph features will be degraded: {str(e)}")
            self.driver = None

    async def close(self):
        if self.driver:
            await self.driver.close()
            logger.info("Closed Neo4j driver connection")

    async def get_session(self):
        if not self.driver:
            self.connect()
        return self.driver.session()

    async def run_query(self, query: str, parameters: dict = None) -> list:
        """
        Helper method to run a read/write query against Neo4j.
        """
        if not self.driver:
            self.connect()
            
        async with self.driver.session() as session:
            try:
                result = await session.run(query, parameters or {})
                records = [record async for record in result]
                return records
            except Exception as e:
                logger.error(f"Error running Neo4j query: {str(e)}\nQuery: {query}")
                raise

neo4j_client = Neo4jClient()

async def get_neo4j_session():
    if not neo4j_client.driver:
        neo4j_client.connect()
    async with neo4j_client.driver.session() as session:
        yield session
