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

def save_announcements_to_airtable(announcements):
    """Save announcements to Airtable."""
    try:
        logger.info("\n=== SAVING TO AIRTABLE ===")
        logger.info(f"Number of announcements to save: {len(announcements)}")
        
        # Prepare records for Airtable
        records = []
        for announcement in announcements:
            record = {
                "fields": {
                    "AnnouncementId": announcement["dbId"],
                    "Title": announcement["title"],
                    "Description": announcement["message"],
                    "SentByUser": announcement["user"]["permittedName"],
                    "DocumentsCount": announcement["documentsCount"],
                    "SentTime": announcement["createdAt"]  # Add SentTime from createdAt
                }
            }
            records.append(record)
            logger.info(f"\nPrepared record for announcement {announcement['dbId']}:")
            logger.info(f"  - Title: {announcement['title']}")
            logger.info(f"  - Sent by: {announcement['user']['permittedName']}")
            logger.info(f"  - Documents: {announcement['documentsCount']}")
            logger.info(f"  - Sent Time: {announcement['createdAt']}")
        
        # Send to Airtable
        logger.info("\nSending records to Airtable...")
        response = requests.post(
            AIRTABLE_API_URL,
            headers={
                "Authorization": f"Bearer {AIRTABLE_API_KEY}",
                "Content-Type": "application/json"
            },
            json={"records": records}
        )
        
        if response.status_code == 200:
            logger.info("\n✅ Successfully saved to Airtable")
            return True
        else:
            logger.error(f"\n❌ Failed to save to Airtable: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"\n❌ Error saving to Airtable: {str(e)}", exc_info=True)
        return False

@app.route("/api/fetch-and-save-announcements", methods=["POST"])
def fetch_and_save_announcements():
    try:
        logger.info("\n" + "="*50)
        logger.info("STARTING FETCH AND SAVE ANNOUNCEMENTS")
        logger.info("="*50)
        
        data = request.get_json()
        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            logger.error("❌ Username and password are required")
            return jsonify({"error": "Username and password are required"}), 400

        logger.info(f"🔑 Attempting login for user: {username}")
        
        session = requests.Session()
        
        # Login to SchoolStatus
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
            
            logger.info("\n=== SCHOOLSTATUS LOGIN RESPONSE ===")
            logger.info(f"Status code: {login_response.status_code}")
            logger.info(f"Response headers: {dict(login_response.headers)}")
            logger.info(f"Response cookies: {dict(login_response.cookies)}")
            logger.info(f"Raw response text: {login_response.text}")
            
            login_response.raise_for_status()
            login_data = login_response.json()

            if login_data.get("errors"):
                error_message = login_data["errors"][0]["message"]
                logger.error(f"\n❌ SCHOOLSTATUS LOGIN GRAPHQL ERROR: {error_message}")
                return jsonify({"error": f"SchoolStatus login failed: {error_message}"}), 401
            
            if login_data.get("data", {}).get("sessionCreate", {}).get("error"):
                error_message = login_data["data"]["sessionCreate"]["error"]
                logger.error(f"\n❌ SCHOOLSTATUS LOGIN ERROR (sessionCreate): {error_message}")
                return jsonify({"error": f"SchoolStatus login failed: {error_message}"}), 401
                
            logger.info("\n✅ SCHOOLSTATUS LOGIN SUCCESSFUL")
            logger.info(f"Session cookies: {session.cookies.get_dict()}")

        except requests.exceptions.RequestException as e_login_req:
            logger.error("Login RequestException Details:", exc_info=True)
            return jsonify({"error": f"Error during SchoolStatus login: {str(e_login_req)}"}), 500
        except json.JSONDecodeError as e_login_json:
            logger.error("Login JSONDecodeError Details:", exc_info=True)
            logger.error(f"Failed to parse SchoolStatus login response. Response text: {login_response.text if login_response else None}")
            return jsonify({"error": "Failed to parse SchoolStatus login response"}), 500

        logger.info("\n=== FETCHING ANNOUNCEMENTS ===")
        announcements_payload = {
            "query": """
                query AnnouncementsListQuery {
                  viewer {
                    id
                    dbId
                    announcements(first: 15)  {
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
                    }
                  }
                }
            """
        }

        try:
            logger.info("\n=== SENDING ANNOUNCEMENTS QUERY ===")
            logger.info(f"Query payload: {json.dumps(announcements_payload, indent=2)}")
            announcements_response = session.post(SCHOOLSTATUS_GRAPHQL_URL, json=announcements_payload, headers=headers, timeout=30)
            logger.info(f"Announcements Response Status: {announcements_response.status_code}")
            logger.info(f"Announcements Response Text: {announcements_response.text}")
            announcements_response.raise_for_status()
            announcements_data_full_response = announcements_response.json()

            if "errors" in announcements_data_full_response:
                error_details = announcements_data_full_response["errors"]
                logger.error(f"Failed to fetch announcements: {json.dumps(error_details)}")
                return jsonify({"error": f"Failed to fetch announcements: {error_details[0]['message'] if error_details else 'Unknown GraphQL error'}"}), 500
            
            logger.info("\n=== PROCESSING ANNOUNCEMENTS RESPONSE ===")
            data_content = announcements_data_full_response.get("data")
            if data_content:
                viewer_data = data_content.get("viewer", {})
                announcements_data = viewer_data.get("announcements", {})
                if announcements_data and announcements_data.get("edges"):
                    processed_announcements = []
                    for edge in announcements_data["edges"]:
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
                            
                            logger.info(f"\nProcessing announcement: {announcement.get('title')}")
                            logger.info(f"dbId: {announcement.get('dbId')}")
                            logger.info(f"Documents count: {announcement.get('documentsCount', 0)}")
                            
                            # Ensure dbId is included in the announcement data
                            if "dbId" not in announcement:
                                logger.error(f"❌ No dbId found in announcement: {announcement}")
                                continue
                            
                            # Fetch documents if the announcement has any
                            if announcement.get("documentsCount", 0) > 0:
                                logger.info(f"📎 This announcement has {announcement.get('documentsCount')} documents, fetching...")
                                documents = fetch_announcement_documents(session, announcement["dbId"], username, password)
                                if documents:
                                    logger.info(f"✅ Successfully fetched {len(documents)} documents")
                                    for doc in documents:
                                        logger.info(f"  - {doc.get('fileFilename')} ({doc.get('contentType')})")
                                    announcement["documents"] = documents
                                else:
                                    logger.info("❌ No documents fetched or error occurred")
                                    announcement["documents"] = []
                            else:
                                logger.info("ℹ️ Announcement has no documents")
                                announcement["documents"] = []
                            
                            processed_announcements.append(announcement)

                    logger.info(f"\nProcessed {len(processed_announcements)} announcements")
                    
                    # Add logging before saving to Airtable
                    logger.info("\n=== ATTEMPTING TO SAVE TO AIRTABLE ===")
                    logger.info(f"Number of announcements to save: {len(processed_announcements)}")
                    
                    # Save to Airtable
                    airtable_success = save_announcements_to_airtable(processed_announcements)
                    if airtable_success:
                        logger.info("✅ Successfully saved to Airtable")
                    else:
                        logger.error("❌ Failed to save to Airtable")
                    
                    logger.info("Sending response to frontend:")
                    logger.info(json.dumps({"announcements": processed_announcements}, indent=2))
                    return jsonify({"announcements": processed_announcements}), 200
                else:
                    logger.info("No announcements found or announcements data is null.")
                    return jsonify({"message": "No announcements found or announcements data is null."}), 200 
            else:
                logger.error("Failed to parse announcements: 'data' field missing or null.")
                return jsonify({"error": "Failed to parse announcements: 'data' field missing or null."}), 500

        except requests.exceptions.RequestException as e_ann_req:
            logger.error("Announcements RequestException Details:", exc_info=True)
            return jsonify({"error": f"Error fetching announcements: {str(e_ann_req)}"}), 500
        except json.JSONDecodeError as e_ann_json:
            logger.error("Announcements JSONDecodeError Details:", exc_info=True)
            logger.error(f"Failed to parse announcements response. Response text: {announcements_response.text if announcements_response else None}")
            return jsonify({"error": "Failed to parse announcements response"}), 500

    except Exception as e_main:
        logger.error("Unhandled Exception in fetch_and_save_announcements:", exc_info=True)
        return jsonify({"error": f"An unexpected server error occurred: {str(e_main)}"}), 500

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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True, use_reloader=False)

