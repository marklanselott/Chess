using ChessLib.Core;
using ChessLib.Pieces;

namespace ChessLib.Logic;

public class KingRules : IMoveRule
{
    public List<Position> GetMoves(Board board, Position pos, Piece piece, GameState state)
    {
        var moves = new List<Position>();

        int [,] dir =
        {
            { 1, 0 },   // right
            { -1, 0 },  // left
            { 0, 1 },   // up
            { 0, -1 },  // down
            { 1, 1 },   // top-right
            { 1, -1 },  // bottom-right
            { -1, 1 },  // top-left
            { -1, -1 }  // bottom-left
        };

        for (int d = 0; d < dir.GetLength(0); d++)
        {
            int dx = dir[d, 0];
            int dy = dir[d, 1];

            var nextPos = new Position(pos.X + dx, pos.Y + dy);
            MoveHelper.TryAddMove(board, piece, moves, nextPos);
        }

        return moves;
    }
}