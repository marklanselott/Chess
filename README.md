# ♟️ Chess Logic Microservice API

A high-performance, **stateless** REST API built with C# and ASP.NET Core. This microservice acts as the core chess engine for a multiplayer chess platform, handling move validation, AI opponent calculation, and deep game analysis.

Since the API is completely **stateless**, it relies entirely on **FEN (Forsyth-Edwards Notation)** strings passed by the client. It does not use a database or store active games in memory (except for asynchronous background analysis jobs), making it extremely fast, scalable, and crash-resistant.

---

## ✨ Features

- **Full Move Validation:** Validates player moves and accurately determines checks, checkmates, and stalemates.
- **Pawn Promotion Support:** Fully supports stateless pawn promotion on the back rank (seamlessly handles client-side piece selection).
- **Automatic Draw Detection:** Detects stalemates and draws due to insufficient material (e.g., King and Bishop vs. King).
- **Legal Moves Detection:** Instantly calculates all valid destination squares for a specific piece (ideal for UI highlighting).
- **AI Opponent:** Calculates the best move for a bot using the Alpha-Beta pruning algorithm, enhanced with MVV-LVA move ordering. Difficulty is dynamically adjustable via search depth.
- **Game Analysis (Asynchronous):** Analyzes completed games in the background to detect blunders, mistakes, and inaccuracies.

---

## 🚀 Getting Started (Local Development)

### Prerequisites
- .NET 8.0 SDK (or later)
- Core logic is powered by the custom `ChessLib` and `ChessAI` packages.

### Installation & Running

1. Clone the repository.
2. Navigate to the project directory:
   
    cd ChessAPI

3. Run the API:
   
    dotnet run

4. Open your browser and navigate to `http://localhost:<port>/swagger` to explore and test the endpoints via the Swagger UI.

---

## 🌍 Deployment & Hosting (Production)

To run this API on a production server (e.g., a Linux VPS), publish the app and configure the listening ports correctly.

### 1. Publish the App
Compile the project into an optimized release build:

    dotnet publish -c Release -o ./publish

Move the contents of the `publish` folder to your production server.

### 2. Run and Configure the Port
Navigate to the publish folder on your server and run the `.dll` file. You can dynamically specify the port using the `--urls` flag.

**Local access only (if frontend/other services are on the SAME server):**

    dotnet ChessAPI.dll --urls "http://localhost:5000"


**External access (if connecting from external services or Docker containers):**
Use `*` or `0.0.0.0` to allow external connections.

    dotnet ChessAPI.dll --urls "http://*:5000"


---

## 📡 API Reference

### 1. Make a Player Move
Validates a move made by a human player. Supports pawn promotion.

**Endpoint:** `POST /api/chess/move`
**Request Body:**
  
    {
      "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
      "from": "e2",
      "to": "e4",
      "promoteTo": "q"
    }

  *(Note: `promoteTo` is optional but required if a pawn reaches the final rank. Valid options: `"q", "r", "b", "n"`).*

**Response (200 OK):**
  
    {
      "isLegal": true,
      "newFen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
      "isCheck": false,
      "isCheckmate": false,
      "isDraw": false,
      "message": "Succes move"
    }


### 2. Get Legal Moves for a Piece
Returns a list of all valid squares a piece can move to from a given starting square. Highly useful for UI logic (e.g., highlighting valid moves when a user clicks a piece).

**Endpoint:** `POST /api/chess/legal-moves`
**Request Body:**
  
    {
      "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
      "from": "e2"
    }

**Response (200 OK):**
  
    {
      "legalMoves": [
        "e3",
        "e4"
      ],
      "message": "Success"
    }


### 3. Generate an AI Move
Calculates the best move for the computer. If the bot promotes a pawn, it automatically selects a Queen.

**Endpoint:** `POST /api/chess/bot-move`
**Request Body:**
  
    {
      "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
      "depth": 3
    }

  *(Note: `depth` controls the AI difficulty).*

**Response (200 OK):**
  
    {
      "newFen": "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2",
      "moveFrom": "e7",
      "moveTo": "e5",
      "isCheck": false,
      "isCheckmate": false
    }


### 4. Analyze a Game (Asynchronous)
Since analyzing a full game array at higher depths is resource-intensive, this feature uses an async polling pattern to prevent HTTP timeouts.

#### Step 4a: Start the Analysis
**Endpoint:** `POST /api/chess/analyze/start`
**Request Body:**
  
    {
      "historyFens": [
        "FEN_1...",
        "FEN_2...",
        "FEN_3..."
      ],
      "depth": 4
    }

**Response (202 Accepted):**
  
    {
      "jobId": "a1b2c3d4-e5f6-7890-1234-56789abcdef0",
      "message": "Start analyzing"
    }


#### Step 4b: Check Analysis Status (Polling)
The client frontend should poll this endpoint every 3-5 seconds. **Note:** Once the status is "Completed", the job is deleted from server memory.

**Endpoint:** `GET /api/chess/analyze/status/{jobId}`
**Response (When finished):**
  
    {
      "jobId": "a1b2c3d4...",
      "status": "Completed",
      "results": [
        {
          "fen": "FEN_1...",
          "evaluation": 150,
          "bestMove": "e2e4",
          "annotation": "Normal"
        },
        {
          "fen": "FEN_2...",
          "evaluation": -350,
          "bestMove": "g8f6",
          "annotation": "Blunder"
        }
      ]
    }


---

## 🛠 Architecture & Performance Notes

- **MakeMove / UndoMove Optimization:** The AI avoids cloning board objects during its recursive depth searches. Instead, it makes and un-makes moves on a single board instance in memory. This eliminates heavy Garbage Collection overhead, increasing calculation speed exponentially.
- **Stateless Scaling:** Scaling this microservice is as simple as spinning up multiple container instances behind a load balancer (like Nginx or Kubernetes). It requires no persistent database connections or sticky sessions.
- **Thread-Safe Job Dictionary:** Background game analysis relies on a thread-safe `ConcurrentDictionary` to temporarily hold analytical data. Data is instantly cleared from RAM the moment the client retrieves it.