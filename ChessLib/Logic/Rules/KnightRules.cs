using ChessLib.Core;
using ChessLib.Pieces;

namespace ChessLib.Logic;

public class KnightRules : IMoveRule
{
    public List<Position> GetMoves(Board board, Position pos, Piece piece)
    {
        var moves = new List<Position>();
        int [,] dir = {
            { 2, 1 }, { 2, -1 }, { 1, 2 }, { -1, 2 }, { -2, 1 }, { -2, -1 }, { 1, -2 }, { -1, -2 }        
        };

        for (int i = 0; i < dir.GetLength(0); i++)
        {
            var nextPos = new Position(pos.X + dir[i, 0], pos.Y + dir[i, 1]);
            MoveHelper.TryAddMove(board, piece, moves, nextPos);
        }

        return moves;
    }
}