using ChessLib.Core;
using ChessLib.Pieces;

namespace ChessLib.Logic;

public class MoveHelper
{
    public static bool IsInside(Position p)
    {
        return p.X >= 0 && p.X < 8 && p.Y >= 0 && p.Y < 8;
    }

    public static bool TryAddMove(Board board, Piece piece, List<Position> moves, Position pos, bool onlyEnemy = false)
    {
        if (!IsInside(pos))
            return false;

        var target = board.GetPiece(pos);

        if (target == null)
        {
            moves.Add(pos);
            return true;
        }
        else if (target.Color != piece.Color)
        {
            moves.Add(pos);
            return false;
        }
        else
            return false;
    }
}
