import os
import logging
import asyncio

from config import Config
from syncer import OdooSyncService
from models import SyncTrigger

# Setup logging to print debug statements to stdout
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Use CONFIG_PATH env or default
CONFIG_PATH = os.getenv('CONFIG_PATH', 'config.yaml')

async def run_sync_test():
    # Load configuration
    logger.info(f"Loading configuration from {CONFIG_PATH}")
    config = Config(config_path=CONFIG_PATH)
    instances = config.instances
    print(f"Configured instances: {[inst.name for inst in instances]}")

    # Prepare sync service
    service = OdooSyncService(instances)
    logger.info("Initialized OdooSyncService with instances")

    # Define sync parameters (customize as needed)
    sync_params = SyncTrigger(
        module_ids=[],
        category_prefixes=["Custom"],
        max_depth=None,
        include_reverse=True,
        instance_names=None  # sync all instances
    )
    logger.debug(f"Sync parameters: {sync_params}")

    # Run synchronization across all instances
    try:
        logger.info("Starting sync_all for all instances...")
        results = await service.sync_all(sync_params)
        logger.info("sync_all completed")

        # Print results per instance
        for result in results:
            print(f"\n--- Instance: {result.instance} ---")
            data = result.data
            nodes = data.get('nodes', [])
            edges = data.get('edges', [])
            print(f"Nodes ({len(nodes)}):")
            for n in nodes:
                print(f"  id={n.id}, name={n.label}")
            print(f"Edges ({len(edges)}):")
            for e in edges:
                print(f"  {e.source} -> {e.target} ({e.relationship})")
    except Exception as e:
        logger.exception(f"Error during sync test: {e}")
    finally:
        service.cleanup()
        logger.info("Cleanup complete")

if __name__ == '__main__':
    asyncio.run(run_sync_test())
