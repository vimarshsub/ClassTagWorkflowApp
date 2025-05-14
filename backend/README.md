## Working State - May 13, 2025
- Basic document fetch functionality is working
- Backend successfully:
  - Authenticates with SchoolStatus
  - Fetches documents for announcement ID
  - Returns document list with URLs and metadata
- Frontend successfully:
  - Connects to backend on port 5001
  - Displays fetched documents
  - Handles user authentication

Known Issues:
- Announcement verification query has an error with 'deletedAt' field
- Some CORS warnings in development mode 