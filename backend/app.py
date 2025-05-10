from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import json
import os
from datetime import datetime, timezone # Keep for now, might be used elsewhere or for future needs
import traceback
import sys

app = Flask(__name__)
CORS(app)

SCHOOLSTATUS_GRAPHQL_URL = "https://connect.schoolstatus.com/graphql"

AIRTABLE_API_KEY = "patsURhjwJWu40rpv.eb8960d151bfcbd141a55521d7072a4a11b6dcdc17af7d206f35813cf37a4863"
AIRTABLE_BASE_ID = "appLu7BlsSJ0MzwXt"
AIRTABLE_TABLE_NAME = "Announcements"
AIRTABLE_API_URL = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}"

# format_datetime_for_airtable function is no longer needed as SentTime is removed.

def save_announcements_to_airtable(announcements_list):
    print("Attempting to save AnnId, Title, Desc, and SentByUser (ID only) to Airtable...", flush=True)
    if not announcements_list or not isinstance(announcements_list, list):
        print("No announcements provided to save or invalid format.", flush=True)
        return False

    headers = {
        "Authorization": f"Bearer {AIRTABLE_API_KEY}",
        "Content-Type": "application/json"
    }

    records_to_create = []
    for ann_node in announcements_list:
        user_info = ann_node.get("user", {})
        sender_identifier = user_info.get("id") # Use only user ID

        fields = {
            "AnnouncementId": ann_node.get("id"),
            "Title": ann_node.get("title"),
            "Description": ann_node.get("message"),
            "SentByUser": sender_identifier # This will now be the User ID
            # "SentTime": format_datetime_for_airtable(ann_node.get("createdAt")) # Removed SentTime
        }
        filtered_fields = {k: v for k, v in fields.items() if v is not None}
        records_to_create.append({"fields": filtered_fields})
    
    if not records_to_create:
        print("No valid records to create for Airtable (ID only test).", flush=True)
        return False

    airtable_payload = {"records": records_to_create}
    
    try:
        response = requests.post(AIRTABLE_API_URL, headers=headers, json=airtable_payload, timeout=30)
        print(f"Airtable API Response Status (ID only): {response.status_code}", flush=True)
        response_json = response.json()
        print(f"Airtable API Response JSON (ID only): {json.dumps(response_json, indent=2)}", flush=True)
        response.raise_for_status()
        print("Successfully saved AnnId, Title, Desc, and SentByUser (ID) to Airtable.", flush=True)
        return True
    except requests.exceptions.RequestException as e_airtable_req:
        print(f"Airtable API RequestException (ID only): {str(e_airtable_req)}", flush=True)
        if response is not None and response.text:
             print(f"Airtable error response text: {response.text}", flush=True)
        traceback.print_exc(); sys.stdout.flush()
    except json.JSONDecodeError as e_airtable_json:
        print(f"Airtable API JSONDecodeError (ID only). Response text: {response.text if response else None}", flush=True)
        traceback.print_exc(); sys.stdout.flush()
    except Exception as e_general:
        print(f"An unexpected error occurred while saving (ID only) to Airtable: {str(e_general)}", flush=True)
        traceback.print_exc(); sys.stdout.flush()
    return False

@app.route("/api/fetch-and-save-announcements", methods=["POST"])
def fetch_and_save_announcements():
    try:
        data = request.get_json()
        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            return jsonify({"error": "Username and password are required"}), 400

        session = requests.Session()
        print(f"Attempting SchoolStatus login for user: {username}", flush=True)
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
            print(f"SchoolStatus Login Response Status: {login_response.status_code}", flush=True)
            login_response.raise_for_status()
            login_data = login_response.json()

            if login_data.get("errors"):
                error_message = login_data["errors"][0]["message"]
                print(f"SchoolStatus login GraphQL error: {error_message}", flush=True)
                return jsonify({"error": f"SchoolStatus login failed: {error_message}"}), 401
            
            if login_data.get("data", {}).get("sessionCreate", {}).get("error"):
                error_message = login_data["data"]["sessionCreate"]["error"]
                print(f"SchoolStatus login failed (sessionCreate error): {error_message}", flush=True)
                return jsonify({"error": f"SchoolStatus login failed: {error_message}"}), 401
            print("SchoolStatus login successful.", flush=True)

        except requests.exceptions.RequestException as e_login_req:
            print("Login RequestException Details:", flush=True); traceback.print_exc(); sys.stdout.flush()
            return jsonify({"error": f"Error during SchoolStatus login: {str(e_login_req)}"}), 500
        except json.JSONDecodeError as e_login_json:
            print("Login JSONDecodeError Details:", flush=True); traceback.print_exc(); sys.stdout.flush()
            print(f"Failed to parse SchoolStatus login response. Response text: {login_response.text if login_response else None}", flush=True)
            return jsonify({"error": "Failed to parse SchoolStatus login response"}), 500

        print("Attempting to fetch announcements from SchoolStatus.", flush=True)
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
                          createdAt # Keep createdAt for potential future use or logging, but not for Airtable SentTime
                          user {
                            id # Only user ID is fetched
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
            print(f"SchoolStatus Announcements Response Status: {announcements_response.status_code}", flush=True)
            announcements_response.raise_for_status()
            announcements_data_full_response = announcements_response.json()

            if "errors" in announcements_data_full_response:
                error_details = announcements_data_full_response["errors"]
                print(f"Failed to fetch announcements: {json.dumps(error_details)}", flush=True)
                return jsonify({"error": f"Failed to fetch announcements: {error_details[0]['message'] if error_details else 'Unknown GraphQL error'}"}), 500
            print("Successfully fetched announcements data from SchoolStatus.", flush=True)
            
            processed_announcements_for_frontend = []
            announcements_to_save_in_airtable = []

            data_content = announcements_data_full_response.get("data")
            if data_content:
                viewer_content = data_content.get("viewer")
                if viewer_content:
                    announcements_gql_content = viewer_content.get("announcements")
                    if announcements_gql_content and announcements_gql_content.get("edges"):
                        processed_announcements_for_frontend = announcements_gql_content
                        announcements_to_save_in_airtable = [edge["node"] for edge in announcements_gql_content["edges"] if edge and edge.get("node")]
                        print(f"Processed {len(announcements_to_save_in_airtable)} announcements for Airtable saving.", flush=True)
                        if announcements_to_save_in_airtable:
                            save_announcements_to_airtable(announcements_to_save_in_airtable)
                        else:
                            print("No announcements to save to Airtable after processing edges.", flush=True)
                        print("Returning announcements content to frontend.", flush=True)
                        return jsonify(processed_announcements_for_frontend), 200
                    else:
                        print("No announcements edges found or announcements data is null.", flush=True)
                        return jsonify({"message": "No announcements found or announcements data is null."}), 200 
                else:
                    print("Failed to parse announcements: 'viewer' field missing or null.", flush=True)
                    return jsonify({"error": "Failed to parse announcements: 'viewer' field missing or null."}), 500
            else:
                print("Failed to parse announcements: 'data' field missing or null.", flush=True)
                return jsonify({"error": "Failed to parse announcements: 'data' field missing or null."}), 500

        except requests.exceptions.RequestException as e_ann_req:
            print("Announcements RequestException Details:", flush=True); traceback.print_exc(); sys.stdout.flush()
            return jsonify({"error": f"Error fetching announcements: {str(e_ann_req)}"}), 500
        except json.JSONDecodeError as e_ann_json:
            print("Announcements JSONDecodeError Details:", flush=True); traceback.print_exc(); sys.stdout.flush()
            print(f"Failed to parse announcements response. Response text: {announcements_response.text if announcements_response else None}", flush=True)
            return jsonify({"error": "Failed to parse announcements response"}), 500

    except Exception as e_main:
        print("Unhandled Exception in fetch_and_save_announcements:", flush=True); traceback.print_exc(); sys.stdout.flush()
        return jsonify({"error": f"An unexpected server error occurred: {str(e_main)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)

