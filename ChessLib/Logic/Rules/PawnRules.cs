using System.Security.Cryptography.X509Certificates;
using ChessLib.Core;
using ChessLib.Pieces;

namespace ChessLib.Logic;

public class PawnRules : IMoveRule
{
    public List<Position> GetMoves(Board board, Position pos, Piece piece, GameState state)
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

        // en passant
        if ((piece.Color == PieceColor.White && pos.Y == 3) ||
            (piece.Color == PieceColor.Black && pos.Y == 4))
        {
            foreach (int dx in new int[] { -1, 1 })
            {
                var sidePos = new Position(pos.X + dx, pos.Y);
                var target = board.GetPiece(sidePos);

                if (target != null && target.Type == PieceType.Pawn && target.Color != piece.Color)
                {
                    if (state.LastDoublePawnMove.HasValue &&
                        state.LastDoublePawnMove.Value.X == sidePos.X &&
                        state.LastDoublePawnMove.Value.Y == sidePos.Y)
                    {
                        var capturePos = new Position(sidePos.X, pos.Y + direction);
                        moves.Add(capturePos);
                    }
                }
            }
        }

        return moves;
    }
}