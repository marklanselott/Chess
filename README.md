# ChessAI

A chess artificial intelligence module built to work seamlessly with the `ChessLib` engine. It uses the Minimax algorithm with Alpha-Beta pruning to evaluate board positions and calculate the best possible moves.

## Installation

Install the library via NuGet (this will automatically include `ChessLib` as a dependency):

```bash
dotnet add package ChessAIbyMrNaniii
```

## Usage

To use the AI, you need an active instance of the `GameManager` from `ChessLib`. 

### Initialization

```csharp
using ChessLib.Logic;
using ChessLib.Pieces;
using ChessAI;

// 1. Initialize the game engine
GameManager game = new GameManager();

// 2. Initialize the bot
// Parameters: The color the bot plays as, and the search depth (e.g., 3 half-moves)
Bot aiBot = new Bot(PieceColor.Black, 3);
```

### Finding and Making the Best Move

When it is the bot's turn, pass the current game state to the bot to calculate the best move.

```csharp
// 1. Calculate the best move
var bestMove = aiBot.FindBestMove(game);

// 2. Validate that a move was found (returns 0,0 if checkmated or stalemated)
if (bestMove.from.X != 0 || bestMove.from.Y != 0)
{
    // 3. Apply the move to the engine
    game.MakeMove(bestMove.from, bestMove.to, out _);
    
    Console.WriteLine("The bot has made its move!");
}
else
{
    Console.WriteLine("Game Over. The bot has no legal moves.");
}
```

### Difficulty Levels

You can easily adjust the difficulty of the bot by changing the `depth` parameter in the constructor. A higher depth results in a stronger opponent but requires more processing time.

* **Depth 1-2:** Beginner (Very fast)
* **Depth 3-4:** Intermediate (Good balance of speed and skill)
* **Depth 5+:** Advanced (Stronger calculation, requires more computation time)
```