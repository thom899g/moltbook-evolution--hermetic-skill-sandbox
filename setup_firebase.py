"""
Firebase Project Setup & Initialization for Moltbook Evolution
Autonomous setup script for Firebase Firestore ledger system
"""
import json
import os
import subprocess
import sys
import time
from typing import Dict, Any, Optional
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FirebaseSetupError(Exception):
    """Custom exception for Firebase setup failures"""
    pass

class FirebaseProjectSetup:
    """
    Autonomous Firebase project setup for the Moltbook Transparency Ledger
    Handles project creation, Firestore initialization, and service account generation
    """
    
    def __init__(self, project_id: str = "moltbook-evolution"):
        self.project_id = project_id
        self.firebase_config: Dict[str, Any] = {}
        
    def check_prerequisites(self) -> bool:
        """Verify all required tools are available"""
        prerequisites = ['gcloud', 'firebase']
        missing = []
        
        for tool in prerequisites:
            try:
                subprocess.run([tool, '--version'], 
                             capture_output=True, 
                             check=True)
                logger.info(f"✓ {tool} is available")
            except (subprocess.CalledProcessError, FileNotFoundError):
                missing.append(tool)
                logger.warning(f"✗ {tool} not found")
        
        if missing:
            logger.error(f"Missing prerequisites: {', '.join(missing)}")
            logger.info("Attempting to install via apt...")
            try:
                subprocess.run(['apt-get', 'update'], check=True)
                subprocess.run(['apt-get', 'install', '-y', 'google-cloud-sdk'], 
                             check=True)
                logger.info("Successfully installed Google Cloud SDK")
                return True
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to install prerequisites: {e}")
                return False
        return True
    
    def create_firebase_project(self) -> bool:
        """Create Firebase project via gcloud and Firebase CLI"""
        try:
            logger.info(f"Creating Firebase project: {self.project_id}")
            
            # Create Google Cloud project
            subprocess.run([
                'gcloud', 'projects', 'create', self.project_id,
                '--name=Moltbook Evolution Stage'
            ], check=True, capture_output=True)
            
            # Enable billing (requires billing account setup)
            logger.warning("⚠️  Billing account setup required manually")
            logger.info("Please enable billing at: https://console.cloud.google.com/billing")
            
            # Enable required APIs
            apis = [
                'firebase.googleapis.com',
                'firestore.googleapis.com',
                'cloudresourcemanager.googleapis.com'
            ]
            
            for api in apis:
                subprocess.run([
                    'gcloud', 'services', 'enable', api,
                    '--project', self.project_id
                ], check=True, capture_output=True)
                logger.info(f"✓ Enabled {api}")
            
            # Initialize Firebase
            subprocess.run([
                'firebase', 'init', 'firestore',
                '--project', self.project_id,
                '--non-interactive'
            ], check=True, capture_output=True)
            
            logger.info("✓ Firebase project created successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Firebase project creation failed: {e.stderr.decode()}")
            raise FirebaseSetupError(f"Project creation failed: {e}")
    
    def generate_service_account_key(self) -> Optional[str]:
        """Generate and download service account key for firebase-admin"""
        try:
            service_account_name = f"moltbook-stage-manager@{self.project_id}.iam.gserviceaccount.com"
            
            # Create service account
            subprocess.run([
                'gcloud', 'iam', 'service-accounts', 'create',
                'moltbook-stage-manager',
                '--display-name="Moltbook Stage Manager Service Account"',
                '--project', self.project_id
            ], check=True, capture_output=True)
            
            # Grant Firestore admin role
            subprocess.run([
                'gcloud', 'projects', 'add-iam-policy-binding', self.project_id,
                '--member', f'serviceAccount:{service_account_name}',
                '--role', 'roles/datastore.owner',
                '--condition', 'None'
            ], check=True, capture_output=True)
            
            # Generate key file
            key_file = f"{self.project_id}-service-account-key.json"
            subprocess.run([
                'gcloud', 'iam', 'service-accounts', 'keys', 'create',
                key_file,
                '--iam-account', service_account_name,
                '--project', self.project_id
            ], check=True, capture_output=True)
            
            logger.info(f"✓ Service account key saved to: {key_file}")
            
            # Read and return key content
            with open(key_file, 'r') as f:
                key_content = json.load(f)
            
            # Set environment variable for firebase-admin
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.path.abspath(key_file)
            
            return key_file
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Service account creation failed: {e.stderr.decode()}")
            return None
    
    def initialize_firestore(self) -> bool:
        """Initialize Firestore database with proper configuration"""
        try:
            import firebase_admin
            from firebase_admin import firestore, credentials
            
            # Initialize Firebase Admin SDK
            cred = credentials.ApplicationDefault()
            firebase_admin.initialize_app(cred, {
                'projectId': self.project_id,
            })
            
            # Get Firestore client
            db = firestore.client()
            
            # Create collections if they don't exist
            collections = [
                'skill_executions',
                'capability_requests',
                'transparency_ledger',
                'reputation_scores'
            ]
            
            # Create a document in each collection to initialize
            for collection in collections:
                doc_ref = db.collection(collection).document('_initialized')
                doc_ref.set({
                    'initialized_at': firestore.SERVER_TIMESTAMP,
                    'system': 'moltbook-evolution',
                    'version': '1.0.0'
                })
                logger.info(f"✓ Initialized collection: {collection}")
            
            # Create indexes for performance
            self._create_composite_indexes(db)
            
            logger.info("✓ Firestore database initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Firestore initialization failed: {e}")
            return False
    
    def _create_composite_indexes(self, db) -> None:
        """Create composite indexes for efficient queries"""
        indexes = [
            {
                'collection': 'skill_executions',
                'fields': ['skill_id', 'timestamp'],
                'order': ('skill_id', 'DESCENDING')
            },
            {
                'collection': 'transparency_ledger',
                'fields': ['skill_id', 'action_type', 'timestamp'],
                'order': ('timestamp', 'DESCENDING')
            }
        ]
        
        logger.info("Note: Composite indexes should be created in Firebase Console")
        logger.info("Visit: https://console.firebase.google.com/project/{}/database/firestore/indexes".format(self.project_id))
    
    def run_complete_setup(self) -> Dict[str, Any]:
        """Execute full setup sequence"""
        results = {
            'project_id': self.project_id,
            'prerequisites': False,
            'project_created': False,
            'service_account': False,
            'firestore_initialized': False
        }
        
        try:
            # Step 1: Check prerequisites
            logger.info("Step 1: Checking prerequisites...")
            results['prerequisites'] = self.check_prerequisites()
            
            if not results['prerequisites']:
                raise FirebaseSetupError("Prerequisites check failed")
            
            # Step 2: Create Firebase project
            logger.info("Step 2: Creating Firebase project...")
            results['project_created'] = self.create_firebase_project()
            
            # Step 3: Generate service account
            logger.info("Step 3: Generating service account key...")
            key_file = self.generate_service_account_key()
            results['service_account'] = key_file is not None
            
            # Step 4: Initialize Firestore
            logger.info("Step 4: Initializing Firestore...")
            results['firestore_initialized'] = self.initialize_firestore()
            
            # Generate summary
            if all(results.values()):
                logger.info("🎉 Firebase setup completed successfully!")
                logger.info(f"Project ID: {self.project_id}")
                logger.info("Next steps:")
                logger.info("1. Enable billing at: https://console.cloud.google.com/billing")
                logger.info("2. Create composite indexes in Firebase Console")
            else:
                logger.warning("⚠️  Setup completed with warnings")
            
            return results
            
        except FirebaseSetupError as e:
            logger.error(f"Setup failed: {e}")
            return results
        except Exception as e:
            logger.error(f"Unexpected error during setup: {e}")
            return results

def main():
    """Main execution function"""
    logger.info("Starting Moltbook Evolution Firebase Setup")
    
    # Get project ID from environment or use default
    project_id = os.getenv('FIREBASE_PROJECT_ID', 'moltbook-evolution-stage')
    
    setup = FirebaseProjectSetup(project_id)
    results = setup.run_complete_setup()
    
    # Write results to file
    with open('firebase_setup_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info("Setup results saved to firebase_setup_results.json")
    
    if not all(results.values()):
        logger.error("⚠️  Setup failed or incomplete. Human intervention required.")
        logger.info("Please check the logs above and complete manually:")
        logger.info("1. Visit https://console.firebase.google.com/")
        logger.info("2. Create project manually")
        logger.info("3. Enable Firestore")
        logger.info("4. Download service account key")
        sys.exit(1)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())