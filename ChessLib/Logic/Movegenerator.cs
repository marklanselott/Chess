using ChessLib.Core;
using ChessLib.Pieces;

namespace ChessLib.Logic;

public class MoveGenerator
{
    private Dictionary<PieceType, IMoveRule> rules;

    public MoveGenerator()
    {
        rules = new Dictionary<PieceType, IMoveRule>
        {
            { PieceType.Pawn, new PawnRules() },
            { PieceType.Bishop, new BishopRules() },
            { PieceType.Knight, new KnightRules() },
            { PieceType.Rook, new RookRules() },
            { PieceType.Queen, new QueenRules() },
            { PieceType.King, new KingRules() }
        };
    }


    public bool IsKingInCheck(Board board, PieceColor color)
    {
        var kingPos = board.FindKing(color);
        if (kingPos == null) return false;

        var enemyColor = color == PieceColor.White ? PieceColor.Black : PieceColor.White;
        var enemyPieces = board.GetPiecesOfColor(enemyColor);

        foreach (var piece in enemyPieces)
        {
            var pos = board.FindPiecePosition(piece);
            if (pos == null) continue;

            var moves = GetMoves(board, pos.Value);

            if (moves.Contains(kingPos.Value))
                return true;
        }

        return false;
    }
    

    public List<Position> GetMoves(Board board, Position pos)
    {
        var piece = board.GetPiece(pos);

        if (piece == null || !rules.ContainsKey(piece.Type))
            return new List<Position>();

        return rules[piece.Type].GetMoves(board, pos, piece);
    }
}