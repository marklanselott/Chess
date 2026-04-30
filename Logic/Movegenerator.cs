using System.Collections.Generic;
using ChessLib.Core;
using ChessLib.Pieces;

namespace ChessLib.Logic;

public class MoveGenerator
{
    private readonly Dictionary<PieceType, IMoveRule> rules;
    private readonly GameState state;

    public MoveGenerator(GameState gameState)
    {
        state = gameState ?? throw new System.ArgumentNullException(nameof(gameState));

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
        foreach (var enemyPiece in board.GetPiecesOfColor(enemyColor))
        {
            var pos = board.FindPiecePosition(enemyPiece);
            if (pos == null) continue;

            var moves = GetMoves(board, pos.Value);
            if (moves.Contains(kingPos.Value))
                return true;
        }
        return false;
    }

    private void AddCastlingMoves(Board board, Position kingPos, Piece king, List<Position> moves)
    {
        if (IsKingInCheck(board, king.Color)) return; 

        int rank = king.Color == PieceColor.White ? 7 : 0;

        // Short castling (King-side)
        var rookRight = board.GetPiece(new Position(7, rank));
        if (rookRight != null && rookRight.Type == PieceType.Rook && rookRight.Color == king.Color)
        {
            bool kingSideFree = board.GetPiece(new Position(5, rank)) == null &&
                                board.GetPiece(new Position(6, rank)) == null;

            if (!kingSideFree) return;
            if ((king.Color == PieceColor.White && !state.WhiteKingMoved && !state.WhiteRightRookMoved) ||
                (king.Color == PieceColor.Black && !state.BlackKingMoved && !state.BlackRightRookMoved))
            {
                var copy = board.Clone();
                copy.Move(kingPos, new Position(5, rank));
                if (!IsKingInCheck(copy, king.Color))
                {
                    copy.Move(new Position(5, rank), new Position(6, rank));
                    if (!IsKingInCheck(copy, king.Color))
                        moves.Add(new Position(6, rank));
                }
            }
        }

        // Long castling (Queen-side)
        var rookLeft = board.GetPiece(new Position(0, rank));
        if (rookLeft != null && rookLeft.Type == PieceType.Rook && rookLeft.Color == king.Color)
        {
            bool queenSideFree = board.GetPiece(new Position(1, rank)) == null &&
                                 board.GetPiece(new Position(2, rank)) == null &&
                                 board.GetPiece(new Position(3, rank)) == null;

            if (!queenSideFree) return;
            if ((king.Color == PieceColor.White && !state.WhiteKingMoved && !state.WhiteLeftRookMoved) ||
                (king.Color == PieceColor.Black && !state.BlackKingMoved && !state.BlackLeftRookMoved))
            {
                var copy = board.Clone();
                copy.Move(kingPos, new Position(3, rank));
                if (!IsKingInCheck(copy, king.Color))
                {
                    copy.Move(new Position(3, rank), new Position(2, rank));
                    if (!IsKingInCheck(copy, king.Color))
                        moves.Add(new Position(2, rank));
                }
            }
        }
    }

    public bool IsCheckMate(Board board, PieceColor color)
        => IsKingInCheck(board, color) && NoLegalMoves(board, color);

    public bool IsStalemate(Board board, PieceColor color)
        => !IsKingInCheck(board, color) && NoLegalMoves(board, color);

    public bool NoLegalMoves(Board board, PieceColor color)
    {
        foreach (var piece in board.GetPiecesOfColor(color))
        {
            var pos = board.FindPiecePosition(piece);
            if (pos == null) continue;

            if (GetLegalMoves(board, pos.Value).Count > 0)
                return false;
        }
        return true;
    }

    public List<Position> GetMoves(Board board, Position pos)
    {
        var piece = board.GetPiece(pos);
        if (piece == null || !rules.ContainsKey(piece.Type))
            return new List<Position>();

        return rules[piece.Type].GetMoves(board, pos, piece, state);
    }

    public List<Position> GetLegalMoves(Board board, Position pos)
    {
        var piece = board.GetPiece(pos);
        if (piece == null) return new List<Position>();

        var moves = GetMoves(board, pos);

        if (piece.Type == PieceType.King)
            AddCastlingMoves(board, pos, piece, moves);

        var legalMoves = new List<Position>();
        foreach (var move in moves)
        {
            var copy = board.Clone();
            copy.Move(pos, move);
            if (!IsKingInCheck(copy, piece.Color))
                legalMoves.Add(move);
        }

        return legalMoves;
    }

    public List<Position> ReturnAllLegalMoves(Board board, PieceColor color)
    {
        var allMoves = new List<Position>();
        foreach (var piece in board.GetPiecesOfColor(color))
        {
            var pos = board.FindPiecePosition(piece);
            if (pos == null) continue;

            allMoves.AddRange(GetLegalMoves(board, pos.Value));
        }
        return allMoves;
    }
}