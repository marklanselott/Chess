using ChessLib.Core;
using ChessLib.Pieces;

namespace ChessLib.Logic;

public class GameManager
{
    public Board Board { get; private set; }
    public GameState State { get; private set; }
    public PieceColor CurrentTurn { get; private set; }

    private MoveGenerator moveGenerator;

    public GameManager()
    {
        Board = new Board();
        State = new GameState();
        CurrentTurn = PieceColor.White;

        moveGenerator = new MoveGenerator(State);

        Board.SetupInitialPosition();
    }


    public bool MakeMove(Position from, Position to, out List<PieceType> promotionOptions)
    {
        promotionOptions = null;

        var piece = Board.GetPiece(from);

        if (piece == null || piece.Color != CurrentTurn)
            return false;

        var legalMoves = moveGenerator.GetLegalMoves(Board, from);
        if (!legalMoves.Contains(to))
            return false;


        if (piece.Type == PieceType.King && Math.Abs(to.X - from.X) == 2)
        {
            if (to.X == 6)
                Board.Move(new Position(7, from.Y), new Position(5, from.Y));
            else if (to.X == 2)
                Board.Move(new Position(0, from.Y), new Position(3, from.Y));
        }

        UpdateGameState(piece, from);

        Board.Move(from, to);


        if (piece.Type == PieceType.Pawn)
        {
            int startRow = piece.Color == PieceColor.White ? 6 : 1;
            if (Math.Abs(to.Y - from.Y) == 2)
            {
                State.LastDoublePawnMove = to;
            }
            else
            {
                State.LastDoublePawnMove = null;
            }


            bool isPromotionRow = (piece.Color == PieceColor.White && to.Y == 0) ||
                                  (piece.Color == PieceColor.Black && to.Y == 7);
            if (isPromotionRow)
            {
                promotionOptions = new List<PieceType> { PieceType.Queen, PieceType.Rook, PieceType.Bishop, PieceType.Knight };
            }
        }

        if (piece.Type == PieceType.Pawn && from.X != to.X && Board.GetPiece(to) == null)
        {
            var capturedPawnPos = new Position(to.X, from.Y);
            Board.Grid[capturedPawnPos.X, capturedPawnPos.Y] = null;
        }

        CurrentTurn = CurrentTurn == PieceColor.White ? PieceColor.Black : PieceColor.White;

        return true;
    }

    public void PromotePawn(Position pos, PieceType chosenType)
    {
        var pawn = Board.GetPiece(pos);
        if (pawn == null || pawn.Type != PieceType.Pawn)
            return;

        Board.Grid[pos.X, pos.Y] = new Piece(chosenType, pawn.Color);
    }

    private void UpdateGameState(Piece piece, Position from)
    {
        if (piece.Type == PieceType.King)
        {
            if (piece.Color == PieceColor.White)
                State.WhiteKingMoved = true;
            else
                State.BlackKingMoved = true;
        }

        if (piece.Type == PieceType.Rook)
        {
            if (piece.Color == PieceColor.White)
            {
                if (from.X == 0 && from.Y == 7) State.WhiteLeftRookMoved = true;
                if (from.X == 7 && from.Y == 7) State.WhiteRightRookMoved = true;
            }
            else
            {
                if (from.X == 0 && from.Y == 0) State.BlackLeftRookMoved = true;
                if (from.X == 7 && from.Y == 0) State.BlackRightRookMoved = true;
            }
        }
    }
}