from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import json
import os
from pyairtable import Api

app = Flask(__name__)
CORS(app) # Enable CORS for all routes

SCHOOLSTATUS_GRAPHQL_URL = "https://connect.schoolstatus.com/graphql"

# Airtable Configuration - Use environment variables in a real app
AIRTABLE_API_KEY = "patsURhjwJWu40rpv.eb8960d151bfcbd141a55521d7072a4a11b6dcdc17af7d206f35813cf37a4863" # User provided API key
AIRTABLE_BASE_ID = "appLu7BlsSJ0MzwXt"
AIRTABLE_ANNOUNCEMENTS_TABLE_ID = "tblFoUNsPSrOCeSXd"
AIRTABLE_DOCUMENTS_TABLE_ID = "tblpeThyD3PqCTAzK"

airtable_api = Api(AIRTABLE_API_KEY)
announcements_table = airtable_api.table(AIRTABLE_BASE_ID, AIRTABLE_ANNOUNCEMENTS_TABLE_ID)
documents_table = airtable_api.table(AIRTABLE_BASE_ID, AIRTABLE_DOCUMENTS_TABLE_ID)

@app.route("/api/fetch-and-save-announcements", methods=["POST"])
def fetch_and_save_announcements():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    session = requests.Session()

    # Step 1: Authenticate with SchoolStatus
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

    try:
        login_response = session.post(SCHOOLSTATUS_GRAPHQL_URL, json=login_payload, timeout=30)
        login_response.raise_for_status()
        login_data = login_response.json()

        if login_data.get("data", {}).get("sessionCreate", {}).get("error"):
            return jsonify({"error": f"SchoolStatus login failed: {login_data['data']['sessionCreate']['error']}"}), 401
        # Session cookies are now stored in `session` object

    except requests.exceptions.Timeout:
        return jsonify({"error": "SchoolStatus login request timed out"}), 504
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Error during SchoolStatus login: {str(e)}"}), 500
    except json.JSONDecodeError:
        return jsonify({"error": "Failed to parse SchoolStatus login response"}), 500

    # Step 2: Fetch Announcements from SchoolStatus
    announcements_payload = {
        "query": "query AnnouncementsListQuery { viewer { id dbId announcements(first: 15) { edges { node { id dbId titleInfo { origin } messageInfo { origin } createdAt user { permittedName avatarUrl } documentsCount } } } } }"
    }

    fetched_announcements_from_ss = []
    try:
        announcements_response = session.post(SCHOOLSTATUS_GRAPHQL_URL, json=announcements_payload, timeout=30)
        announcements_response.raise_for_status()
        announcements_data = announcements_response.json()

        if "errors" in announcements_data:
            return jsonify({"error": f"SchoolStatus announcements fetch error: {announcements_data['errors']}"}), 500

        edges = announcements_data.get("data", {}).get("viewer", {}).get("announcements", {}).get("edges", [])
        
        for edge in edges:
            node = edge.get("node", {})
            if node:
                announcement_detail = {
                    "id": node.get("dbId"),
                    "title": node.get("titleInfo", {}).get("origin"),
                    "message": node.get("messageInfo", {}).get("origin"),
                    "sender": node.get("user", {}).get("permittedName"),
                    "date": node.get("createdAt"),
                    "documentsCount": node.get("documentsCount"),
                    "attachments": [] # Placeholder, will be populated if we fetch document details
                }
                fetched_announcements_from_ss.append(announcement_detail)
                
                # Step 3: Save each announcement to Airtable "Announcements" table
                try:
                    airtable_record = {
                        "AnnouncementId": str(node.get("dbId")),
                        "Title": node.get("titleInfo", {}).get("origin"),
                        "Description": node.get("messageInfo", {}).get("origin"),
                        "SentByUser": node.get("user", {}).get("permittedName")
                    }
                    announcements_table.create(airtable_record)
                except Exception as e_airtable_ann:
                    # Log this error, but continue processing other announcements
                    print(f"Error saving announcement {node.get('dbId')} to Airtable: {str(e_airtable_ann)}")
                    # Optionally, you could add this error to a list to return to the user

                # Step 4: Handle Documents (Placeholder - requires another query to get document details)
                if node.get("documentsCount", 0) > 0:
                    # This is where you'd make another SchoolStatus API call to get document details for this announcement_id
                    # For example: query GetAnnouncementDocuments($announcementId: ID!) { ... details ... }
                    # Then loop through those documents and save to Airtable "AnnouncementDocuments" table
                    # For now, we'll just log that it has documents.
                    print(f"Announcement {node.get('dbId')} has {node.get('documentsCount')} documents. Details need to be fetched and saved.")
                    # Example of saving a (mock) document to Airtable:
                    # mock_document_record = {
                    #     "Id": "doc_mock_id_" + str(node.get("dbId")),
                    #     "Attachment": [{ "url": "http://example.com/mock.pdf", "filename": "mock_document.pdf" }],
                    #     "AccouncementId": str(node.get("dbId")),
                    #     "Filename": "mock_document.pdf"
                    # }
                    # try:
                    #     documents_table.create(mock_document_record)
                    # except Exception as e_airtable_doc:
                    #     print(f"Error saving mock document for announcement {node.get('dbId')} to Airtable: {str(e_airtable_doc)}")

        return jsonify(fetched_announcements_from_ss), 200

    except requests.exceptions.Timeout:
        return jsonify({"error": "SchoolStatus announcements request timed out"}), 504
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Error fetching SchoolStatus announcements: {str(e)}"}), 500
    except json.JSONDecodeError:
        return jsonify({"error": "Failed to parse SchoolStatus announcements response"}), 500
    except Exception as e_main:
        return jsonify({"error": f"An unexpected error occurred: {str(e_main)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)

