from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import json
import os
from datetime import datetime
import traceback # Import the new library

app = Flask(__name__)
CORS(app)

SCHOOLSTATUS_GRAPHQL_URL = "https://connect.schoolstatus.com/graphql"

@app.route("/api/fetch-and-save-announcements", methods=["POST"])
def fetch_and_save_announcements():
    try:
        data = request.get_json()
        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            return jsonify({"error": "Username and password are required"}), 400

        session = requests.Session()

        # Step 1: Authenticate with SchoolStatus
        login_payload = {
            "query": "mutation SessionCreateMutation($input: SessionCreateInput!) { sessionCreate(input: $input) { error location { id name } user { id dbId churnZeroId userCredentials { id dbId credential credentialType } } } }",
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
            login_response.raise_for_status() # Raise an exception for bad status codes
            login_data = login_response.json()

            # Corrected f-string: Use single quotes for dictionary keys inside the f-string
            if login_data.get("data", {}).get("sessionCreate", {}).get("error"):
                error_message = login_data['data']['sessionCreate']['error']
                return jsonify({"error": f"SchoolStatus login failed: {error_message}"}), 401
            # Session cookies are now stored in `session`

        except requests.exceptions.RequestException as e_login_req:
            print("Login RequestException Details:")
            traceback.print_exc(e_login_req)
            return jsonify({"error": f"Error during SchoolStatus login: {str(e_login_req)}"}), 500
        except json.JSONDecodeError as e_login_json:
            print("Login JSONDecodeError Details:")
            traceback.print_exc(e_login_json)
            return jsonify({"error": "Failed to parse SchoolStatus login response"}), 500

        # Step 2: Fetch Announcements from SchoolStatus
        announcements_payload = {
            "query": """
                query AnnouncementsListQuery {
                  viewer {
                    id
                    announcements(first: 15) {
                      edges {
                        node {
                          id
                          title
                          message
                          createdAt
                          user {
                            id
                            name
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
            announcements_response = session.post(SCHOOLSTATUS_GRAPHQL_URL, json=announcements_payload, timeout=30)
            announcements_response.raise_for_status()
            announcements_data = announcements_response.json()

            if "errors" in announcements_data:
                # Corrected f-string: Use single quotes for dictionary keys inside the f-string
                error_details = announcements_data['errors']
                return jsonify({"error": f"Failed to fetch announcements: {error_details}"}), 500

            # Process and return announcements
            return jsonify(announcements_data.get("data", {}).get("viewer", {}).get("announcements", {})), 200

        except requests.exceptions.RequestException as e_ann_req:
            print("Announcements RequestException Details:")
            traceback.print_exc(e_ann_req)
            return jsonify({"error": f"Error fetching announcements: {str(e_ann_req)}"}), 500
        except json.JSONDecodeError as e_ann_json:
            print("Announcements JSONDecodeError Details:")
            traceback.print_exc(e_ann_json)
            return jsonify({"error": "Failed to parse announcements response"}), 500

    except Exception as e_main:
        # Catch any other unexpected errors in the main function body
        print("Unhandled Exception in fetch_and_save_announcements:")
        traceback.print_exc(e_main) # Use the new library here
        return jsonify({"error": f"An unexpected server error occurred: {str(e_main)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)

