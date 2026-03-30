using System.Security.Cryptography.X509Certificates;
using ChessLib.Core;
using ChessLib.Pieces;

namespace ChessLib.Logic;

public class PawnRules : IMoveRule
{
    public List<Position> GetMoves(Board board, Position pos, Piece piece)
    {
        var moves = new List<Position>();
        int direction = piece.Color == PieceColor.White ? -1 : 1;

        // move forward
        var forward = new Position(pos.X, pos.Y + direction);
        if (MoveHelper.IsInside(forward) && board.GetPiece(forward) == null)
            moves.Add(forward);

        // double move
        bool isStartPos = piece.Color == PieceColor.White ? pos.Y == 6 : pos.Y == 1;
        if (isStartPos && board.GetPiece(forward) == null)
        {
            var forward2 = new Position(pos.X, pos.Y + direction * 2);
            if (MoveHelper.IsInside(forward2) && board.GetPiece(forward2) == null)
                moves.Add(forward2);
        }

        // attack
        foreach (int dx in new int[] { -1, 1 })
        {
            var diag = new Position(pos.X + dx, pos.Y + direction);

            if (!MoveHelper.IsInside(diag))
                continue;

            var target = board.GetPiece(diag);

            if (target != null && target.Color != piece.Color)
                moves.Add(diag);
        }

        return moves;
    }
}