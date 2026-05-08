# ♟️ Chess Logic Microservice API

A high-performance, **stateless** REST API built with C# and ASP.NET Core. This microservice acts as the core chess engine for a multiplayer chess platform, handling move validation, AI opponent calculation, and deep game analysis.

Since the API is stateless, it relies entirely on **FEN (Forsyth-Edwards Notation)** strings passed by the client. It does not use a database or store active games in memory (except for asynchronous background jobs), making it extremely fast, scalable, and crash-resistant.

## ✨ Features
- **Move Validation:** Validates player moves and generates the updated board state.
- **Legal Moves Detection:** Instantly calculates all valid destination squares for a specific piece (useful for UI highlighting).
- **AI Opponent:** Calculates the best move for a bot using the Alpha-Beta pruning algorithm. Difficulty is dynamically adjustable via search depth.
- **Game Analysis:** Analyzes completed games asynchronously to detect blunders, mistakes, and inaccuracies.
- **Stateless Architecture:** Easy to scale; memory-efficient.

---

## 🚀 Getting Started (Local Development)

### Prerequisites
- .NET 8.0 SDK (or later)
- The core logic is powered by a custom ChessLib package.

### Installation & Running
1. Clone the repository.
2. Navigate to the project directory:

    cd ChessAPI

3. Run the API:

    dotnet run

4. Open your browser and navigate to `http://localhost:<port>/swagger` to explore and test the endpoints via the Swagger UI.

---

## 🌍 Deployment & Hosting (Linux / Production)

To run this API on a production server (e.g., a Linux VPS), you need to publish the app and configure the listening ports correctly.

### 1. Publish the App
Compile the project into an optimized release build:

    dotnet publish -c Release -o ./publish

Move the contents of the `publish` folder to your production server.

### 2. Run and Configure the Port
Navigate to the publish folder on your server and run the `.dll` file. You can dynamically specify the port using the `--urls` flag.

**Local access only (if Python and C# are on the SAME server):**

    dotnet ChessAPI.dll --urls "http://localhost:5000"

**External access (if Python is on a DIFFERENT server or in Docker):**
Use `*` or `0.0.0.0` to allow external connections from the internet or other containers.

    dotnet ChessAPI.dll --urls "http://*:5000"

---

## 📡 API Reference

### 1. Make a Player Move
Validates a move made by a human player.

**Endpoint:** `POST /api/chess/move`

**Request Body:**

    {
      "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w - - 0 1",
      "from": "e2",
      "to": "e4"
    }

**Response:**

    {
      "isLegal": true,
      "newFen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b - - 0 1",
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

**Response:**

    {
      "legalMoves": [
        "e3",
        "e4"
      ],
      "message": "Успіх"
    }

### 3. Generate an AI Move
Calculates the best move for the computer.

**Endpoint:** `POST /api/chess/bot-move`

**Request Body:**

    {
      "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
      "depth": 3
    }

*(Note: `depth` controls the AI difficulty. e.g., 1 = Easy, 3 = Medium, 5 = Hard).*

**Response:**

    {
      "newFen": "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2",
      "moveFrom": "e7",
      "moveTo": "e5",
      "isCheckmate": false
    }

### 4. Analyze a Game (Asynchronous)
Since analyzing a 40-move game at depth 5 can take a long time, this feature uses an async polling pattern to prevent HTTP timeouts.

#### Step 4a: Start the Analysis
**Endpoint:** `POST /api/chess/analyze/start`

**Request Body:**

    {
      "historyFens": [
        "FEN_1...",
        "FEN_2...",
        "FEN_3..."
      ]
    }

**Response (202 Accepted):**

    {
      "jobId": "a1b2c3d4-e5f6-7890-1234-56789abcdef0",
      "message": "Start analizing"
    }

#### Step 4b: Check Analysis Status (Polling)
The client should poll this endpoint every 5-10 seconds until the status is "Completed".

**Endpoint:** `GET /api/chess/analyze/status/{jobId}`

**Response (While processing):**

    {
      "jobId": "a1b2c3d4...",
      "status": "Processing",
      "results": null
    }

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

## 🛠 Architecture Notes
- **Completely Stateless:** Scaling this service is as simple as running multiple instances behind a load balancer. It requires no persistent database connections.
- **Job Dictionary:** Game analysis relies on a thread-safe `ConcurrentDictionary` to temporarily hold data until the client retrieves it.