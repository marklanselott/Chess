using ChessLib.Core;
using ChessLib.Pieces;

namespace ChessAI;

public static class Evaluator
{
    public static int Evaluate(Board board)
    {
        int score = 0;

        for (int x = 0; x < 8; x++)
        {
            for (int y = 0; y < 8; y++)
            {
                var piece = board.Grid[x, y];
                if (piece!= null)
                {
                    int pieceValue = piece.Type switch
                    {
                        PieceType.Pawn => 10,
                        PieceType.Knight => 30,
                        PieceType.Bishop => 30,
                        PieceType.Rook => 50,
                        PieceType.Queen  => 90,
                        PieceType.King => 9999,
                        _ => 0
                    };

                    if (piece.Color == PieceColor.White)
                    {
                        score += pieceValue;
                    }
                    else
                    {
                        score -= pieceValue;
                    }
                }
            }
        }

        return score;
    }
}