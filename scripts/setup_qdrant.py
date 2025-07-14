#!/usr/bin/env python3
"""
Qdrant collection setup script for Vibe Kanban
Creates and configures all required Qdrant collections
"""

import sys
import os
import logging
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.qdrant_client import qdrant_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_qdrant():
    """Set up all Qdrant collections"""
    print("🚀 Setting up Qdrant collections for Vibe Kanban...")
    
    # Health check first
    health = qdrant_client.health_check()
    if health["status"] != "healthy":
        print(f"❌ Qdrant health check failed: {health.get('error', 'Unknown error')}")
        return False
    
    print(f"✅ Qdrant is healthy. Found {health['collections_count']} existing collections.")
    
    # Create collections
    success = qdrant_client.create_collections()
    if not success:
        print("❌ Failed to create collections")
        return False
    
    print("✅ All collections created successfully!")
    
    # Get collection info
    info = qdrant_client.get_collection_info()
    print("\n📊 Collection Status:")
    for collection_name, collection_info in info.items():
        if "error" in collection_info:
            print(f"  ❌ {collection_name}: Error - {collection_info['error']}")
        elif collection_info.get("status") == "not_found":
            print(f"  ❌ {collection_name}: Not found")
        else:
            status = collection_info.get("status", "unknown")
            points_count = collection_info.get("points_count", 0)
            print(f"  ✅ {collection_name}: {status} ({points_count} points)")
    
    return True

def reset_qdrant():
    """Reset all Qdrant collections (delete and recreate)"""
    print("🔄 Resetting Qdrant collections...")
    
    # Delete all collections
    success = qdrant_client.delete_collections()
    if not success:
        print("❌ Failed to delete collections")
        return False
    
    print("✅ All collections deleted")
    
    # Recreate collections
    return setup_qdrant()

def main():
    """Main function"""
    if len(sys.argv) > 1 and sys.argv[1] == "--reset":
        success = reset_qdrant()
    else:
        success = setup_qdrant()
    
    if success:
        print("\n🎉 Qdrant setup completed successfully!")
        sys.exit(0)
    else:
        print("\n💥 Qdrant setup failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()