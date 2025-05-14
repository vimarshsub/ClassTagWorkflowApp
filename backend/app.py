from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import json
import os
from datetime import datetime, timezone # Keep for now, might be used elsewhere or for future needs
import traceback
import sys
import logging
import atexit
import signal
import base64
import io
import time
from PIL import Image

# Configure logging to write to both file and console with more visible format
logging.basicConfig(
    level=logging.INFO,
    format='\n%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log', mode='w'),  # Write to file, overwrite each time
        logging.StreamHandler(sys.stdout)  # Write to console
    ]
)
logger = logging.getLogger(__name__)

# Force all loggers to use the same handlers
for handler in logging.getLogger().handlers:
    logging.getLogger('werkzeug').addHandler(handler)
    logging.getLogger('urllib3').addHandler(handler)

# Test log messages
logger.info("\n" + "="*50)
logger.info("BACKEND SERVER STARTED")
logger.info("="*50)
logger.info("\nTest log message 1")
logger.info("Test log message 2")
logger.info("Test log message 3")
logger.info("="*50 + "\n")

app = Flask(__name__)
app.config['PROPAGATE_EXCEPTIONS'] = True
app.config['DEBUG'] = True
app.config['USE_RELOADER'] = False  # Disable reloader to prevent semaphore issues

CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:3000"],  # Only allow local frontend
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "Accept"],
        "supports_credentials": True
    }
})

def cleanup():
    logger.info("\n" + "="*50)
    logger.info("CLEANING UP RESOURCES")
    logger.info("="*50)

# Register cleanup function
atexit.register(cleanup)

# Handle SIGTERM gracefully
def handle_sigterm(signum, frame):
    logger.info("\n" + "="*50)
    logger.info("RECEIVED SIGTERM - SHUTTING DOWN")
    logger.info("="*50)
    cleanup()
    sys.exit(0)

signal.signal(signal.SIGTERM, handle_sigterm)

@app.before_request
def log_request_info():
    logger.info("\n" + "="*50)
    logger.info("REQUEST RECEIVED")
    logger.info(f"Method: {request.method}")
    logger.info(f"URL: {request.url}")
    logger.info(f"Headers: {dict(request.headers)}")
    logger.info(f"Body: {request.get_data(as_text=True)}")
    logger.info("="*50)

@app.after_request
def log_response_info(response):
    logger.info("\n" + "="*50)
    logger.info("RESPONSE SENT")
    logger.info(f"Status: {response.status}")
    logger.info(f"Headers: {dict(response.headers)}")
    logger.info(f"Body: {response.get_data(as_text=True)}")
    logger.info("="*50)
    return response

SCHOOLSTATUS_GRAPHQL_URL = "https://connect.schoolstatus.com/graphql"

AIRTABLE_API_KEY = "patsURhjwJWu40rpv.eb8960d151bfcbd141a55521d7072a4a11b6dcdc17af7d206f35813cf37a4863"
AIRTABLE_BASE_ID = "appLu7BlsSJ0MzwXt"
AIRTABLE_TABLE_NAME = "Announcements"
AIRTABLE_API_URL = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}"

def fetch_announcement_documents(session, announcement_id, username, password):
    """Fetch documents for a specific announcement."""
    try:
        logger.info(f"\n{'='*50}")
        logger.info(f"DOCUMENT FETCH STARTED FOR ANNOUNCEMENT {announcement_id}")
        logger.info(f"{'='*50}")
        
        # First login to get fresh session
        logger.info(f"\n=== SCHOOLSTATUS LOGIN STARTED ===")
        logger.info(f"Attempting login for user: {username}")
        
        login_payload = {
            "query": "mutation SessionCreateMutation($input: Session__CreateInput!) { sessionCreate(input: $input) { error location user { id dbId churnZeroId userCredentials { id dbId credential credentialType } } } }",
            "variables": {
                "input": {
                    "credential": username,
                    "password": password,
                    "rememberMe": True
                }
            }
        }

        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Origin': 'https://connect.schoolstatus.com',
            'Referer': 'https://connect.schoolstatus.com/'
        }

        try:
            logger.info("\n=== SENDING LOGIN REQUEST TO SCHOOLSTATUS ===")
            logger.info(f"URL: {SCHOOLSTATUS_GRAPHQL_URL}")
            logger.info(f"Login payload: {json.dumps(login_payload, indent=2)}")
            
            login_response = session.post(SCHOOLSTATUS_GRAPHQL_URL, json=login_payload, headers=headers, timeout=30)
            login_response.raise_for_status()
            login_data = login_response.json()
            
            if login_data.get("errors"):
                error_message = login_data["errors"][0]["message"]
                logger.error(f"\n❌ LOGIN ERROR: {error_message}")
                return None
                
            if not login_data.get("data", {}).get("sessionCreate", {}).get("user"):
                logger.error("\n❌ LOGIN FAILED: No user data in response")
                return None
                
            logger.info("\n✅ SCHOOLSTATUS LOGIN SUCCESSFUL")
            logger.info(f"Session cookies: {session.cookies.get_dict()}")
            
        except Exception as e:
            logger.error(f"\n❌ LOGIN ERROR: {str(e)}", exc_info=True)
            return None

        # Now fetch the documents directly
        documents_payload = {
            "query": """
                query AnnouncementDocumentsQuery($id: ID!) {
                    announcement(id: $id) {
                        id
                        dbId
                        documents {
                            id
                            fileFilename
                            fileUrl
                            contentType
                        }
                    }
                }
            """,
            "variables": {
                "id": announcement_id
            }
        }

        logger.info("\n=== SENDING DOCUMENT QUERY TO SCHOOLSTATUS ===")
        logger.info(f"URL: {SCHOOLSTATUS_GRAPHQL_URL}")
        logger.info(f"Query payload: {json.dumps(documents_payload, indent=2)}")
        logger.info(f"Session cookies: {session.cookies.get_dict()}")
        logger.info(f"Headers: {json.dumps(headers, indent=2)}")
        
        response = session.post(
            SCHOOLSTATUS_GRAPHQL_URL, 
            json=documents_payload, 
            headers=headers,
            timeout=30
        )
        
        logger.info("\n=== SCHOOLSTATUS RESPONSE ===")
        logger.info(f"Status code: {response.status_code}")
        logger.info(f"Response headers: {dict(response.headers)}")
        logger.info(f"Response cookies: {dict(response.cookies)}")
        logger.info(f"Raw response text: {response.text}")
        
        response.raise_for_status()
        data = response.json()

        if "errors" in data:
            error_message = data["errors"][0]["message"]
            logger.error(f"\n❌ SCHOOLSTATUS GRAPHQL ERRORS: {error_message}")
            return None

        documents = data.get("data", {}).get("announcement", {}).get("documents", [])
        logger.info(f"\n📄 Found {len(documents)} documents:")
        for idx, doc in enumerate(documents, 1):
            logger.info(f"\nDocument {idx}:")
            logger.info(f"  - Filename: {doc.get('fileFilename')}")
            logger.info(f"  - Type: {doc.get('contentType')}")
            logger.info(f"  - URL: {doc.get('fileUrl')}")
        
        logger.info(f"\n{'='*50}")
        logger.info(f"DOCUMENT FETCH COMPLETED FOR ANNOUNCEMENT {announcement_id}")
        logger.info(f"{'='*50}\n")
        return documents
    except Exception as e:
        logger.error(f"❌ ERROR fetching documents: {str(e)}", exc_info=True)
        return None

def download_document(session, url, filename):
    """Download a document using the authenticated session."""
    try:
        logger.info(f"Downloading document from URL: {url}")
        response = session.get(url, timeout=30)
        response.raise_for_status()
        
        # Get the content
        content = response.content
        logger.info(f"Successfully downloaded document: {filename}, size: {len(content)} bytes")
        
        # Create a temporary file
        temp_file_path = f"/tmp/{filename}"
        with open(temp_file_path, "wb") as f:
            f.write(content)
        
        logger.info(f"Saved document to temporary file: {temp_file_path}")
        return temp_file_path
    except Exception as e:
        logger.error(f"Error downloading document: {str(e)}", exc_info=True)
        return None

def save_announcements_to_airtable(announcements, session, username, password):
    """Save announcements to Airtable."""
    try:
        logger.info("\n=== SAVING TO AIRTABLE ===")
        logger.info(f"Number of announcements to save: {len(announcements)}")
        
        success_count = 0
        error_count = 0
        
        # Process each announcement individually
        for announcement in announcements:
            try:
                logger.info(f"\n=== PROCESSING ANNOUNCEMENT {announcement.get('dbId')} ===")
                logger.info(f"Title: {announcement.get('title')}")
                
                # Extract document URLs
                attachments = []
                if announcement.get("documents"):
                    # Find PDF documents only
                    pdf_docs = [doc for doc in announcement["documents"] 
                               if doc.get("contentType") == "application/pdf" or 
                               (doc.get("fileFilename") and doc.get("fileFilename").lower().endswith('.pdf'))]
                    
                    # Process up to 5 PDF documents
                    docs_to_process = pdf_docs[:5]
                    total_pdf_docs = len(pdf_docs)
                    
                    if total_pdf_docs > 0:
                        logger.info(f"Found {total_pdf_docs} PDF documents, processing up to 5")
                        
                        for doc in docs_to_process:
                            logger.info(f"Processing PDF document: {doc.get('fileFilename')}")
                            
                            if doc.get("fileUrl") and doc.get("fileFilename"):
                                # Use direct URL format for Airtable attachments
                                attachments.append({
                                    "url": doc.get("fileUrl"),
                                    "filename": doc.get("fileFilename")
                                })
                                logger.info(f"Added PDF attachment: {doc.get('fileFilename')} with URL: {doc.get('fileUrl')}")
                            else:
                                logger.info(f"No URL or filename found for PDF document")
                    else:
                        logger.info("No PDF documents found for this announcement")
                else:
                    logger.info("No documents found for this announcement")
                
                # Prepare record for this announcement
                record = {
                    "fields": {
                        "AnnouncementId": announcement["dbId"],
                        "Title": announcement["title"],
                        "Description": announcement["message"],
                        "SentByUser": announcement["user"]["permittedName"],
                        "DocumentsCount": announcement["documentsCount"],
                        "SentTime": announcement["createdAt"]
                    }
                }
                
                # Add attachments if we have any
                if attachments:
                    logger.info(f"Adding {len(attachments)} PDF attachments to Airtable record")
                    record["fields"]["Attachments"] = attachments
                    # Log the first attachment for debugging
                    if attachments:
                        logger.info(f"Sample attachment: {json.dumps(attachments[0])}")
                else:
                    logger.info("No PDF attachments to add to Airtable record")
                
                logger.info(f"Prepared record for announcement {announcement['dbId']}:")
                logger.info(f"  - Title: {announcement['title']}")
                logger.info(f"  - Sent by: {announcement['user']['permittedName']}")
                logger.info(f"  - Documents: {announcement['documentsCount']}")
                logger.info(f"  - PDF Attachments: {len(attachments) if attachments else 0}")
                
                # Send this announcement to Airtable individually
                logger.info(f"\nSending announcement {announcement['dbId']} to Airtable...")
                
                response = requests.post(
                    AIRTABLE_API_URL,
                    headers={
                        "Authorization": f"Bearer {AIRTABLE_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={"records": [record]}  # Send just this one record
                )
                
                logger.info(f"Airtable API response status for announcement {announcement['dbId']}: {response.status_code}")
                logger.info(f"Airtable API response: {response.text[:500]}")  # Log first 500 chars to avoid huge logs
                
                if response.status_code == 200:
                    logger.info(f"\n✅ Successfully saved announcement {announcement['dbId']} to Airtable")
                    success_count += 1
                else:
                    logger.error(f"\n❌ Failed to save announcement {announcement['dbId']} to Airtable: {response.text}")
                    error_count += 1
                    
                # Add a small delay between requests to avoid rate limiting
                time.sleep(0.5)
                    
            except Exception as e:
                logger.error(f"\n❌ Error processing announcement {announcement.get('dbId')}: {str(e)}", exc_info=True)
                error_count += 1
        
        logger.info(f"\n=== AIRTABLE SAVE SUMMARY ===")
        logger.info(f"Successfully saved: {success_count} announcements")
        logger.info(f"Failed to save: {error_count} announcements")
        
        return success_count > 0  # Return True if at least one announcement was saved successfully
            
    except Exception as e:
        logger.error(f"\n❌ Error saving to Airtable: {str(e)}", exc_info=True)
        return False

def fetch_paginated_announcements(session, username, password, after_cursor=None, items_per_page=20):
    """Fetch paginated announcements from SchoolStatus."""
    try:
        logger.info(f"\n{'='*50}")
        logger.info(f"FETCHING PAGINATED ANNOUNCEMENTS")
        logger.info(f"After cursor: {after_cursor}")
        logger.info(f"Items per page: {items_per_page}")
        logger.info(f"{'='*50}")
        
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Origin': 'https://connect.schoolstatus.com',
            'Referer': 'https://connect.schoolstatus.com/'
        }

        # Login first if no session
        login_payload = {
            "query": "mutation SessionCreateMutation($input: Session__CreateInput!) { sessionCreate(input: $input) { error location user { id dbId churnZeroId userCredentials { id dbId credential credentialType } } } }",
            "variables": {
                "input": {
                    "credential": username,
                    "password": password,
                    "rememberMe": True
                }
            }
        }

        login_response = session.post(SCHOOLSTATUS_GRAPHQL_URL, json=login_payload, headers=headers, timeout=30)
        login_response.raise_for_status()
        login_data = login_response.json()

        if login_data.get("errors") or login_data.get("data", {}).get("sessionCreate", {}).get("error"):
            logger.error(f"Login failed")
            return {"announcements": [], "hasNextPage": False, "endCursor": None, "error": "Login failed"}

        # Fetch announcements with pagination
        announcements_payload = {
            "query": """
                query AnnouncementsListQuery($first: Int, $after: String) {
                  viewer {
                    id
                    dbId
                    announcements(first: $first, after: $after) {
                      edges {
                        node {
                          id
                          dbId
                          titleInfo {
                            origin
                          }
                          messageInfo {
                            origin
                          }
                          createdAt
                          user {
                            permittedName
                            avatarUrl
                          }
                          documentsCount
                        }
                      }
                      pageInfo {
                        hasNextPage
                        endCursor
                      }
                    }
                  }
                }
            """,
            "variables": {
                "first": items_per_page,
                "after": after_cursor
            }
        }

        logger.info(f"Query payload: {json.dumps(announcements_payload, indent=2)}")
        announcements_response = session.post(SCHOOLSTATUS_GRAPHQL_URL, json=announcements_payload, headers=headers, timeout=30)
        announcements_response.raise_for_status()
        announcements_data = announcements_response.json()

        if "errors" in announcements_data:
            logger.error(f"GraphQL errors: {announcements_data['errors']}")
            return {"announcements": [], "hasNextPage": False, "endCursor": None, "error": announcements_data['errors']}

        # Process the response
        viewer_data = announcements_data.get("data", {}).get("viewer", {})
        announcements_info = viewer_data.get("announcements", {})
        page_info = announcements_info.get("pageInfo", {})
        
        processed_announcements = []
        if announcements_info.get("edges"):
            for edge in announcements_info["edges"]:
                if edge and edge.get("node"):
                    node = edge["node"]
                    announcement = {
                        "id": node.get("id"),
                        "dbId": node.get("dbId"),
                        "title": node.get("titleInfo", {}).get("origin"),
                        "message": node.get("messageInfo", {}).get("origin"),
                        "createdAt": node.get("createdAt"),
                        "documentsCount": node.get("documentsCount", 0),
                        "user": node.get("user", {})
                    }
                    
                    # Fetch documents if available
                    if announcement.get("documentsCount", 0) > 0:
                        logger.info(f"Fetching documents for announcement: {announcement.get('title')}")
                        documents = fetch_announcement_documents(session, announcement["dbId"], username, password)
                        announcement["documents"] = documents or []
                    else:
                        announcement["documents"] = []
                    
                    processed_announcements.append(announcement)

        return {
            "announcements": processed_announcements,
            "hasNextPage": page_info.get("hasNextPage", False),
            "endCursor": page_info.get("endCursor"),
            "error": None
        }

    except Exception as e:
        logger.error(f"Error fetching paginated announcements: {str(e)}", exc_info=True)
        return {"announcements": [], "hasNextPage": False, "endCursor": None, "error": str(e)}

@app.route("/api/fetch-announcements", methods=["POST"])
def fetch_announcements():
    """Fetch first page of announcements."""
    try:
        data = request.get_json()
        username = data.get("username")
        password = data.get("password")
        items_per_page = data.get("itemsPerPage", 20)

        if not username or not password:
            return jsonify({"error": "Username and password are required"}), 400

        session = requests.Session()
        result = fetch_paginated_announcements(session, username, password, None, items_per_page)
        
        if result["error"]:
            return jsonify({"error": result["error"]}), 500

        # Save to Airtable
        if result["announcements"]:
            airtable_success = save_announcements_to_airtable(result["announcements"], session, username, password)
            if not airtable_success:
                logger.warning("Failed to save to Airtable, but continuing with response")

        return jsonify({
            "announcements": result["announcements"],
            "hasNextPage": result["hasNextPage"],
            "endCursor": result["endCursor"]
        }), 200

    except Exception as e:
        logger.error(f"Error in fetch_announcements: {str(e)}", exc_info=True)
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route("/api/load-more-announcements", methods=["POST"])
def load_more_announcements():
    """Load more announcements using cursor-based pagination."""
    try:
        data = request.get_json()
        username = data.get("username")
        password = data.get("password")
        after_cursor = data.get("afterCursor")
        items_per_page = data.get("itemsPerPage", 20)

        if not username or not password:
            return jsonify({"error": "Username and password are required"}), 400

        if not after_cursor:
            return jsonify({"error": "Cursor is required for pagination"}), 400

        session = requests.Session()
        result = fetch_paginated_announcements(session, username, password, after_cursor, items_per_page)
        
        if result["error"]:
            return jsonify({"error": result["error"]}), 500

        # Save new announcements to Airtable
        if result["announcements"]:
            airtable_success = save_announcements_to_airtable(result["announcements"], session, username, password)
            if not airtable_success:
                logger.warning("Failed to save to Airtable, but continuing with response")

        return jsonify({
            "announcements": result["announcements"],
            "hasNextPage": result["hasNextPage"],
            "endCursor": result["endCursor"]
        }), 200

    except Exception as e:
        logger.error(f"Error in load_more_announcements: {str(e)}", exc_info=True)
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route("/api/test-fetch-documents", methods=["POST", "OPTIONS"])
def test_fetch_documents():
    if request.method == "OPTIONS":
        return "", 200
        
    try:
        data = request.get_json()
        username = data.get("username")
        password = data.get("password")
        announcement_id = data.get("announcementId")  # Get the ID from the request

        if not username or not password:
            return jsonify({"error": "Username and password are required"}), 400
            
        if not announcement_id:
            return jsonify({"error": "Announcement ID is required"}), 400

        session = requests.Session()
        
        # Test document fetch with login
        logger.info(f"\nTesting document fetch for announcement ID: {announcement_id}")
        
        # Add required headers
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Origin': 'https://connect.schoolstatus.com',
            'Referer': 'https://connect.schoolstatus.com/'
        }
        
        documents = fetch_announcement_documents(session, announcement_id, username, password)
        
        if documents:
            return jsonify({
                "message": "Successfully fetched documents",
                "documents": documents
            }), 200
        else:
            return jsonify({
                "message": "No documents found or error occurred",
                "documents": []
            }), 200

    except Exception as e:
        logger.error(f"Server error: {str(e)}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route("/api/test", methods=["GET"])
def test_route():
    logger.info("\n" + "="*50)
    logger.info("TEST ROUTE CALLED")
    logger.info("="*50)
    return jsonify({"message": "Test route working"})

@app.route('/api/test-pdf-documents', methods=['POST'])
def test_pdf_documents():
    """Test endpoint to test PDF document handling."""
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Create a session and login
        session = requests.Session()
        logger.info(f"\n=== SCHOOLSTATUS LOGIN STARTED ===")
        logger.info(f"Attempting login for user: {username}")
        
        login_payload = {
            "query": "mutation SessionCreateMutation($input: Session__CreateInput!) { sessionCreate(input: $input) { error location user { id dbId churnZeroId userCredentials { id dbId credential credentialType } } } }",
            "variables": {
                "input": {
                    "credential": username,
                    "password": password,
                    "rememberMe": True
                }
            }
        }

        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Origin': 'https://connect.schoolstatus.com',
            'Referer': 'https://connect.schoolstatus.com/'
        }

        try:
            logger.info("\n=== SENDING LOGIN REQUEST TO SCHOOLSTATUS ===")
            logger.info(f"URL: {SCHOOLSTATUS_GRAPHQL_URL}")
            logger.info(f"Login payload: {json.dumps(login_payload, indent=2)}")
            
            login_response = session.post(SCHOOLSTATUS_GRAPHQL_URL, json=login_payload, headers=headers, timeout=30)
            login_response.raise_for_status()
            login_data = login_response.json()
            
            if login_data.get("errors"):
                error_message = login_data["errors"][0]["message"]
                logger.error(f"\n❌ LOGIN ERROR: {error_message}")
                return jsonify({'error': f'Login failed: {error_message}'}), 401
                
            if not login_data.get("data", {}).get("sessionCreate", {}).get("user"):
                logger.error("\n❌ LOGIN FAILED: No user data in response")
                return jsonify({'error': 'Login failed: No user data in response'}), 401
                
            logger.info("\n✅ SCHOOLSTATUS LOGIN SUCCESSFUL")
            logger.info(f"Session cookies: {session.cookies.get_dict()}")
            
        except Exception as e:
            logger.error(f"\n❌ LOGIN ERROR: {str(e)}", exc_info=True)
            return jsonify({'error': f'Login error: {str(e)}'}), 500
        
        # Create a test announcement with both image and PDF documents
        test_announcement = {
            "dbId": "test123",
            "title": "Test Announcement with PDF",
            "message": "<p>This is a test announcement with PDF documents</p>",
            "createdAt": "2025-05-14T12:00:00-04:00",
            "user": {
                "permittedName": "Test User",
                "avatarUrl": ""
            },
            "documents": [
                {
                    "contentType": "image/jpeg",
                    "fileFilename": "test_image.jpeg",
                    "fileUrl": "https://assets.connect.schoolstatus.com/attachments/example/test_image.jpeg?force_download=true",
                    "id": "image123"
                },
                {
                    "contentType": "application/pdf",
                    "fileFilename": "test_document.pdf",
                    "fileUrl": "https://assets.connect.schoolstatus.com/attachments/example/test_document.pdf?force_download=true",
                    "id": "pdf123"
                },
                {
                    "contentType": "application/pdf",
                    "fileFilename": "test_document2.pdf",
                    "fileUrl": "https://assets.connect.schoolstatus.com/attachments/example/test_document2.pdf?force_download=true",
                    "id": "pdf456"
                },
                {
                    "contentType": "application/pdf",
                    "fileFilename": "test_document3.pdf",
                    "fileUrl": "https://assets.connect.schoolstatus.com/attachments/example/test_document3.pdf?force_download=true",
                    "id": "pdf789"
                }
            ],
            "documentsCount": 4
        }
        
        # Save the test announcement to Airtable
        save_announcements_to_airtable([test_announcement], session, username, password)
        
        return jsonify({
            'success': True,
            'message': 'Test announcement with PDF documents processed',
            'announcement': test_announcement
        })
        
    except Exception as e:
        logger.error(f"Error in test-pdf-documents: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True, use_reloader=False)

