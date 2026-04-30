using ChessLib.Core;
using ChessLib.Pieces;

namespace ChessAI;

public static class Evaluator
{
    private const int PawnValue = 100;
    private const int KnightValue = 320;
    private const int BishopValue = 330;
    private const int RookValue = 500;
    private const int QueenValue = 900;
    private const int KingValue = 20000;

    private static readonly int[,] PawnTable = {
        {  0,  0,  0,  0,  0,  0,  0,  0},
        { 50, 50, 50, 50, 50, 50, 50, 50},
        { 10, 10, 20, 30, 30, 20, 10, 10}, 
        {  5,  5, 10, 25, 25, 10,  5,  5}, 
        {  0,  0,  0, 20, 20,  0,  0,  0}, 
        {  5, -5,-10,  0,  0,-10, -5,  5}, 
        {  5, 10, 10,-20,-20, 10, 10,  5}, 
        {  0,  0,  0,  0,  0,  0,  0,  0}  
    };

    private static readonly int[,] KnightTable = {
        {-50,-40,-30,-30,-30,-30,-40,-50},
        {-40,-20,  0,  0,  0,  0,-20,-40},
        {-30,  0, 10, 15, 15, 10,  0,-30},
        {-30,  5, 15, 20, 20, 15,  5,-30},
        {-30,  0, 15, 20, 20, 15,  0,-30},
        {-30,  5, 10, 15, 15, 10,  5,-30},
        {-40,-20,  0,  5,  5,  0,-20,-40},
        {-50,-40,-30,-30,-30,-30,-40,-50}
    };

    private static readonly int[,] BishopTable = {
        {-20,-10,-10,-10,-10,-10,-10,-20},
        {-10,  0,  0,  0,  0,  0,  0,-10},
        {-10,  0,  5, 10, 10,  5,  0,-10},
        {-10,  5,  5, 10, 10,  5,  5,-10},
        {-10,  0, 10, 10, 10, 10,  0,-10},
        {-10, 10, 10, 10, 10, 10, 10,-10},
        {-10,  5,  0,  0,  0,  0,  5,-10},
        {-20,-10,-10,-10,-10,-10,-10,-20}
    };

    private static readonly int[,] KingTable = {
        {-30,-40,-40,-50,-50,-40,-40,-30},
        {-30,-40,-40,-50,-50,-40,-40,-30},
        {-30,-40,-40,-50,-50,-40,-40,-30},
        {-30,-40,-40,-50,-50,-40,-40,-30},
        {-20,-30,-30,-40,-40,-30,-30,-20},
        {-10,-20,-20,-20,-20,-20,-20,-10},
        { 20, 20,  0,  0,  0,  0, 20, 20},
        { 20, 30, 10,  0,  0, 10, 30, 20}
    };

    public static int Evaluate(Board board)
    {
        int score = 0;

        for (int x = 0; x < 8; x++)
        {
            for (int y = 0; y < 8; y++)
            {
                var piece = board.Grid[x, y];
                if (piece != null)
                {
                    int pieceValue = 0;
                    int positionalBonus = 0;

                    int rank = piece.Color == PieceColor.White ? y : 7 - y;

                    switch (piece.Type)
                    {
                        case PieceType.Pawn:
                            pieceValue = PawnValue;
                            positionalBonus = PawnTable[rank, x];
                            break;
                        case PieceType.Knight:
                            pieceValue = KnightValue;
                            positionalBonus = KnightTable[rank, x];
                            break;
                        case PieceType.Bishop:
                            pieceValue = BishopValue;
                            positionalBonus = BishopTable[rank, x];
                            break;
                        case PieceType.Rook:
                            pieceValue = RookValue;
                            break;
                        case PieceType.Queen:
                            pieceValue = QueenValue;
                            break;
                        case PieceType.King:
                            pieceValue = KingValue;
                            positionalBonus = KingTable[rank, x];
                            break;
                    }

                    int totalPieceScore = pieceValue + positionalBonus;

                    if (piece.Color == PieceColor.White)
                    {
                        score += totalPieceScore;
                    }
                    else
                    {
                        score -= totalPieceScore;
                    }
                }
            }
        }

        return score;
    }
}