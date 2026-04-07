# ChessLib

A lightweight, headless C# chess engine. It handles board state management, move generation, and strict rule validation including castling, en passant, pawn promotion, and threefold repetition.

## Installation

Install the library via NuGet:

```bash
dotnet add package ChessLibbyMrNaniii
```

## Usage

The primary entry point for interacting with the engine is the `GameManager` class. Below is a quick guide on how to use the core features of the library.

### Initialization and Basic Flow

```csharp
using ChessLib.Core;
using ChessLib.Logic;
using ChessLib.Pieces;

// 1. Initialize a new game (sets up the standard starting position)
GameManager game = new GameManager();

// 2. Check the current turn
PieceColor turn = game.CurrentTurn; // Starts as PieceColor.White

// 3. Get all legal moves for a piece at a specific position (e.g., e2)
Position e2 = new Position(4, 6);
var legalMoves = game.GetLegalMoves(e2);

// 4. Make a move (e.g., e2 to e4)
Position e4 = new Position(4, 4);
bool isSuccess = game.MakeMove(e2, e4, out var promotionOptions);
```

### Handling Pawn Promotion

If a pawn reaches the last rank, `MakeMove` will return a list of available pieces for promotion via the `out` parameter.

```csharp
if (promotionOptions != null)
{
    // Apply the promotion choice (e.g., Queen)
    game.PromotePawn(targetPosition, PieceType.Queen);
}
```

### Game State and Rules

The engine automatically tracks the history of the board to handle complex chess rules.

```csharp
// Check if the current position has occurred 3 times (Draw)
bool isDraw = game.IsThreefoldRepetition();
```

### Exporting Board Data

You can easily export the current state of the board to interact with external APIs, Python scripts, or UI frameworks.

```csharp
// Returns a dictionary mapping algebraic coordinates to piece strings (e.g., "e2" -> "WhitePawn")
var boardState = game.Board.ExportBoardState();
```